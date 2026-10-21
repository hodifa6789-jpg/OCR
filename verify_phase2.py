"""Validation of generated local artifacts; never displays raw labels/images."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import re
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.contracts import read_jsonl,write_jsonl
from src.data import Dataset,validate_manifest
from src.data.splits import make_split

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];private=root/'reports/private';dest=private/'phase2';share=root/'reports/shareable'
    checked=0
    for level in ('word','line'):
        rows=read_jsonl(dest/f'manifest_{level}.jsonl');validate_manifest(rows);assert len(rows)==3078
        checked+=len(rows)
    word=read_jsonl(dest/'manifest_word.jsonl');eligible=[r for r in word if r['eligible_for_training']];validate_manifest(eligible,'train')
    write_jsonl(dest/'eligible_word_train_pool.jsonl',eligible)
    plan=json.loads((dest/'split_word_provisional.json').read_text(encoding='utf8'));again=make_split(eligible)
    assert plan['train_ids']==again['train_ids'] and plan['val_ids']==again['val_ids'] and plan['manifest_sha256']==again['manifest_sha256']
    assert set(plan['train_ids']).isdisjoint(plan['val_ids'])
    assert set(plan['train_ids'])|set(plan['val_ids'])=={r['image_id'] for r in eligible}
    test_ids={r['image_id'] for r in word if r['source_split']=='test'};assert len(test_ids)==636 and test_ids.isdisjoint(plan['train_ids']+plan['val_ids'])
    problems=json.loads((dest/'issues_private.json').read_text(encoding='utf8'));rechecked=0
    with Dataset(args.archive) as ds:
        for issue in problems:
            if issue['issue'] not in ('xml_image_dimensions','xml_filename_mismatch'):continue
            level=issue['annotation_level'];row=next(r for r in read_jsonl(dest/f'manifest_{level}.jsonl') if r['image_id']==issue['image_id'])
            truth=ds.ground_truth(row,level)
            assert issue['issue'] in truth['issues'];rechecked+=1
    with (private/'visual_review/review_decisions.csv').open(encoding='utf-8-sig',newline='') as f:review=list(csv.DictReader(f))
    assert len(review)==90 and all(r['status']=='pending_human_review' and not r['reviewer'] for r in review)
    for name in ('class_mapping_summary.json','issue_resolution_summary.json'):
        text=(share/name).read_text(encoding='utf8');json.loads(text)
        assert not any(k in text for k in json.loads((private/'class_map_PRIVATE.json').read_text(encoding='utf8')))
        assert all(marker not in text for marker in ('C:\\Users','GiGabyte'))
        assert not re.search(r'image_\d+\.(?:JPG|xml|txt)',text)
    result={'manifest_rows_validated':checked,'eligible_pool':len(eligible),'train':len(plan['train_ids']),'val':len(plan['val_ids']),'test_ids_disjoint':len(test_ids),'real_metadata_cases_rechecked':rechecked,'pending_review_rows':len(review),'raw_images_or_labels_in_shareable':False,'original_archive_written':False}
    (dest/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))

if __name__=='__main__':main()
