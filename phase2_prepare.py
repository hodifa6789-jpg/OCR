"""Reuse audit checkpoints; read annotation pairs only for missing class mapping.

Only the review sample's images are decoded. Outputs containing actual IDs,
class names, labels or overlays stay under reports/private.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import zipfile
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data import Dataset,parse_xml,parse_yolo
from src.data.splits import make_split
from src.contracts import REAL_POLICY,write_jsonl

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];private=root/'reports/private';share=root/'reports/shareable';dest=private/'phase2';dest.mkdir(parents=True,exist_ok=True)
    checkpoint=private/'checkpoint.jsonl';rows=[json.loads(l) for l in checkpoint.read_text(encoding='utf8').splitlines()];by={r['name']:r for r in rows}
    aliases=json.loads((private/'class_map_PRIVATE.json').read_text(encoding='utf8'))
    stats=collections.defaultdict(lambda:collections.Counter());mapping=collections.defaultdict(collections.Counter);problems=[];manifests={'word':[],'line':[]};parsed={};image_issues=collections.defaultdict(set);pair_count=0;geometry_failures=0
    with Dataset(args.archive) as ds:
        for r in rows:
            if r.get('kind')!='xml':continue
            n=r['name'];split=n.split('/')[2].lower();level='word' if '/Word-Level/' in n else 'line';stem=Path(n).stem
            im=by[f'Images/{split}/{stem}.JPG'];truth=parse_xml(ds.read(n));parsed[n]=truth
            yn=n.replace('Annotations/','YOLO_Annotations/',1).replace('.xml','.txt');yr=parse_yolo(ds.read(yn));pair_count+=1
            issues=[]
            if not r['filename_matches']:issues.append('xml_filename_mismatch')
            if (truth['source_width'],truth['source_height'])!=(im['width'],im['height']):issues.append('xml_image_dimensions')
            if not truth['objects']:issues.append('empty_annotation_pending_review')
            if level=='word' and any(aliases[o['class_name']]=='CLASS_2' for o in truth['objects']):issues.append('rare_word_category_pending_definition')
            compatible=len(truth['objects'])==len(yr)
            if compatible:
                for obj,y in zip(truth['objects'],yr):
                    a,b,c,d=obj['raw_bbox'];expected=[(a+c)/2/truth['source_width'],(b+d)/2/truth['source_height'],(c-a)/truth['source_width'],(d-b)/truth['source_height']]
                    if max(abs(v-w) for v,w in zip(expected,y['normalized_box']))>1e-5:compatible=False;break
            if not compatible:geometry_failures+=1;issues.append('xml_yolo_correspondence_unresolved')
            if any(y['class_id'] in (15,16) for y in yr):
                issues.append('yolo_id_15_or_16_pending_definition')
            for index,obj in enumerate(truth['objects']):
                alias=aliases[obj['class_name']];stats[(level,split)][alias]+=1
                if compatible:mapping[(level,split,alias)][yr[index]['class_id']]+=1
            for issue in issues:
                problems.append({'image_id':im['name'],'annotation_path':n,'source_split':split,'annotation_level':level,'issue':issue,'status':'pending_human_review' if issue!='rare_word_category_pending_definition' else 'unresolved_definition','correction_version':None})
                image_issues[im['name']].add(issue)
            manifests[level].append({'image_id':im['name'],'image_path':im['name'],'annotation_path':n,'yolo_path':yn,'annotation_level':level,'source_split':split,'split':split,'width':im['width'],'height':im['height'],'source_width':truth['source_width'],'source_height':truth['source_height'],'coordinate_policy_id':REAL_POLICY,'review_status':'pending_human_review','issues':issues,'eligible_for_training':False})
        save(dest/'issues_private.json',problems)
        mapping_private=[{'level':level,'split':split,'raw_name':name,'alias':alias,'observed_yolo_ids':dict(mapping[(level,split,alias)])} for level,split in sorted(stats) for name,alias in aliases.items()]
        save(dest/'class_mapping_private.json',mapping_private)
        for level,mr in manifests.items():
            for row in mr:
                # Conservative exclusion of every known problem image, even if
                # the issue was found only at the other annotation level.
                row['eligible_for_training']=row['source_split']=='train' and not image_issues[row['image_id']]
            write_jsonl(dest/f'manifest_{level}.jsonl',sorted(mr,key=lambda r:r['image_id']))
        train=[r for r in manifests['word'] if r['eligible_for_training']]
        split_plan=make_split(train);split_plan.update(provisional=True,training_authorization='not_asserted',excluded_train_images=len([r for r in manifests['word'] if r['source_split']=='train'])-len(train))
        save(dest/'split_word_provisional.json',split_plan)
        # Review selection includes every known train issue plus extremes;
        # deterministic random fill reaches exactly 40 unique train images.
        all_train=[r for r in manifests['word'] if r['source_split']=='train'];selected={r['image_id'] for r in all_train if image_issues[r['image_id']]};reason={key:'known_issue' for key in selected}
        for metric,label in [(lambda r:len(parsed[r['annotation_path']]['objects']),'region_count'),(lambda r:r['width']/r['height'],'aspect_ratio'),(lambda r:min((o['raw_bbox'][3]-o['raw_bbox'][1] for o in parsed[r['annotation_path']]['objects']),default=float('inf')),'small_box_height')]:
            ordered=sorted(all_train,key=lambda r:(metric(r),r['image_id']))
            for r in ordered[:3]+ordered[-3:]:selected.add(r['image_id']);reason.setdefault(r['image_id'],label)
        pool=sorted(r['image_id'] for r in all_train if r['image_id'] not in selected);random.Random(2026).shuffle(pool)
        for key in pool:
            if len(selected)>=40:break
            selected.add(key);reason[key]='seeded_random_fill'
        # Also prepare any explicit test issue for quality-only review, never
        # for selection/tuning; counted separately.
        selected_test={r['image_id'] for r in problems if r['source_split']=='test'};selected|=selected_test
        review=private/'visual_review';review.mkdir(exist_ok=True);decisions=review/'review_decisions.csv'
        previous={}
        if decisions.exists():
            with decisions.open(encoding='utf-8-sig',newline='') as f:
                previous={(r['image_id'],r['checked_level']):r for r in csv.DictReader(f)}
        review_rows=[]
        for key in sorted(selected):
            row=next(r for r in manifests['word'] if r['image_id']==key);pixels=ds.image(row);base=Image.fromarray(pixels)
            for level in ('word','line'):
                mr=next(r for r in manifests[level] if r['image_id']==key);truth=parsed[mr['annotation_path']];overlay=base.copy();draw=ImageDraw.Draw(overlay)
                for obj in truth['objects']:
                    draw.rectangle(obj['raw_bbox'],outline='red' if level=='word' else 'blue',width=3)
                    draw.text((obj['raw_bbox'][0],obj['raw_bbox'][1]),aliases[obj['class_name']],fill='yellow')
                path=review/(key.split('/')[1]+'_'+Path(key).stem+'_'+level+'.jpg')
                if not path.exists():overlay.save(path,quality=85)
                rec=previous.get((key,level),{'image_id':key,'reviewer':'','checked_level':level,'status':'pending_human_review','decision':'','reason':'','correction_version':''})
                review_rows.append(rec)
        with decisions.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['image_id','reviewer','checked_level','status','decision','reason','correction_version']);writer.writeheader();writer.writerows(review_rows)
        save(review/'selection_private.json',{'seed':2026,'train_images':len(selected-selected_test),'test_quality_only_images':len(selected_test),'selection_reason':reason,'human_review_performed_by_tool':False})
        import html
        tiles=[]
        for key in sorted(selected):
            tiles.append('<h2>'+html.escape(key)+'</h2><p>pending_human_review</p>')
            for level in ('word','line'):
                name=key.split('/')[1]+'_'+Path(key).stem+'_'+level+'.jpg'
                tiles.append('<p>'+level+'</p><a href="'+html.escape(name,quote=True)+'"><img loading="lazy" style="max-width:900px" src="'+html.escape(name,quote=True)+'"></a>')
        (review/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>LOCAL ONLY: pending human review</title><h1>Prepared overlays, not completed review</h1>'+''.join(tiles),encoding='utf8')
    class_summary={'schema_version':'1.1','evidence':'all XML/YOLO annotation pairs; ordered rows checked by normalized geometry <=1e-5 before associating labels','annotation_pairs_read':pair_count,'images_redecoded_for_mapping':0,'geometry_pair_failures':geometry_failures,'semantic_status':'unresolved; README contains no class definitions or official script mapping','official_script_mapping_status':'unresolved','script_in_predictions':None,'aliases_reused_from_phase1':True,'rows':[]}
    for (level,split),counter in sorted(stats.items()):
        for alias in sorted(aliases.values()):class_summary['rows'].append({'annotation_level':level,'source_split':split,'class_alias':alias,'regions':counter[alias],'observed_yolo_class_ids':{str(k):v for k,v in sorted(mapping[(level,split,alias)].items())},'meaning':'not_documented','target_policy':'retain_all_classes_no_remap'})
    mapping_by_alias=collections.defaultdict(set)
    for (_,_,alias),counter in mapping.items():mapping_by_alias[alias].update(counter)
    class_summary['alias_to_observed_yolo_ids']={k:sorted(v) for k,v in sorted(mapping_by_alias.items())}
    class_summary['mapping_is_one_to_one']=len({v for values in mapping_by_alias.values() for v in values})==len(mapping_by_alias) and all(len(v)==1 for v in mapping_by_alias.values())
    class_summary['split_region_totals']=[{'annotation_level':level,'source_split':sp,'regions':sum(counter.values())} for (level,sp),counter in sorted(stats.items())]
    save(share/'class_mapping_summary.json',class_summary)
    grouped=collections.Counter((r['issue'],r['source_split'],r['annotation_level']) for r in problems)
    issue_summary={'schema_version':'1.1','audit_reused':True,'full_archive_reaudit':False,'original_labels_modified':False,'correction_version':None,'visual_review_status':'pending_human_review','reviewer_completed_records':sum(bool(r['reviewer']) and r['status']!='pending_human_review' for r in review_rows),'issues':[{'issue':i,'source_split':sp,'annotation_level':lv,'affected_annotation_files':n,'status':'unresolved_definition' if i.startswith('rare') else 'pending_human_review','decision':'preserve_original; exclude affected image from provisional training pool until reviewed'} for (i,sp,lv),n in sorted(grouped.items())],'review_preparation':{'train_images':len(selected-selected_test),'test_quality_only_images':len(selected_test),'overlays':len(review_rows),'human_review_performed':False},'provisional_split':{'eligible_train_pool':len(train),'train_images':len(split_plan['train_ids']),'val_images':len(split_plan['val_ids']),'excluded_train_images':split_plan['excluded_train_images'],'test_images_excluded':636,'seed':2026,'scene_leakage_status':'unresolved_image_only_split','manifest_sha256':split_plan['manifest_sha256']},'archive_identity':{'sha256_from_phase1':json.loads((private/'checkpoint_identity.json').read_text(encoding='utf8'))['archive_sha256'],'sha256_recomputed_phase2':False,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest()}}
    issue_summary['review_preparation']['total_local_overlay_files_including_retained_previous_selections']=len(list(review.glob('*.jpg')))
    issue_summary['review_preparation']['current_selection_overlays']=len(review_rows)
    save(share/'issue_resolution_summary.json',issue_summary)
    print(json.dumps({'class_summary_rows':len(class_summary['rows']),'annotation_pairs_read':pair_count,'geometry_pair_failures':geometry_failures,'mapping_is_one_to_one':class_summary['mapping_is_one_to_one'],'mapping_alias_ids':class_summary['alias_to_observed_yolo_ids'],'issues':issue_summary['issues'],'provisional_split':issue_summary['provisional_split'],'review_preparation':issue_summary['review_preparation']},ensure_ascii=True))

if __name__=='__main__':main()
