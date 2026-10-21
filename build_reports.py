import pathlib,json,collections,math,hashlib,csv,itertools,zipfile,shutil
P=pathlib.Path;root=P(__file__).resolve().parents[1];pr=root/'reports/private';share=root/'reports/shareable';share.mkdir(parents=True,exist_ok=True)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def stats(v):
 v=sorted(v)
 return {'n':len(v),'min':v[0] if v else None,'p10':v[int((len(v)-1)*.1)] if v else None,'median':v[len(v)//2] if v else None,'p90':v[int((len(v)-1)*.9)] if v else None,'max':v[-1] if v else None}
rows=[json.loads(l) for l in (pr/'checkpoint.jsonl').read_text(encoding='utf8').splitlines()];by={r['name']:r for r in rows};images=[r for r in rows if r.get('kind')=='image'];xml=[r for r in rows if r.get('kind')=='xml'];yolo=[r for r in rows if r.get('kind')=='yolo'];env=json.loads((pr/'environment_archive.json').read_text(encoding='utf8'));issues=collections.Counter(v for r in rows for v in r['issues']);groups={};private_extra=[]
def split(r):return r['name'].split('/')[1].lower() if r.get('kind')=='image' else r['name'].split('/')[2].lower()
for r in rows:
 folder=r['name'].rsplit('/',1)[0] if '/' in r['name'] else '.';g=groups.setdefault(folder,{'files':0,'bytes':0,'compressed_bytes':0});g['files']+=1;g['bytes']+=r['bytes'];g['compressed_bytes']+=r['compressed']
splits={}
for sp in ['train','test']:
 splits[sp]={'images':sum(split(r)==sp for r in images),'xml_word':sum(split(r)==sp and '/Word-Level/' in r['name'] for r in xml),'xml_line':sum(split(r)==sp and '/Line-Level/' in r['name'] for r in xml),'yolo_word':sum(split(r)==sp and '/Word-Level/' in r['name'] for r in yolo),'yolo_line':sum(split(r)==sp and '/Line-Level/' in r['name'] for r in yolo)}
missing=collections.Counter();mismatches=collections.Counter();delta=[];yolo_mismatch=[];box_stats={};classes=sorted(set(k for r in xml for k in r['class_counts']));classmap={v:'CLASS_'+str(k+1) for k,v in enumerate(classes)}
for r in images:
 for level in ['Word-Level','Line-Level']:
  for typ,base,ext in [('xml','Annotations','.xml'),('yolo','YOLO_Annotations','.txt')]:
   n=f'{base}/{level}/{split(r).title()}/{P(r["name"]).stem}{ext}'
   if n not in by:missing['image_without_'+typ+'_'+level]+=1
for r in xml+yolo:
 n=f'Images/{split(r)}/{P(r["name"]).stem}.JPG'
 if n not in by:missing['orphan_'+r['kind']]+=1
 elif r['kind']=='xml':
  im=by[n]
  if (r['width'],r['height'])!=(im.get('width'),im.get('height')):mismatches['xml_image_dimensions']+=1;private_extra.append({'name':r['name'],'issue':'xml_image_dimensions'})
 if r['kind']=='xml':
  yn=r['name'].replace('Annotations/','YOLO_Annotations/',1).replace('.xml','.txt');yr=by.get(yn)
  if yr:
   if len(r['regions'])!=len(yr['regions']):mismatches['xml_yolo_count']+=1;yolo_mismatch.append(r['name'])
   else:
    maxd=0
    for b,v in zip(r['regions'],yr['regions']):
     expected=[(b[0]+b[2])/2/r['width'],(b[1]+b[3])/2/r['height'],(b[2]-b[0])/r['width'],(b[3]-b[1])/r['height']];maxd=max(maxd,max(abs(x-y) for x,y in zip(expected,v[1:])))
    delta.append(maxd)
    if maxd>1e-5:mismatches['xml_yolo_geometry_gt_1e-5']+=1;yolo_mismatch.append(r['name'])
for level in ['Word-Level','Line-Level']:
 rr=[r for r in xml if '/'+level+'/' in r['name']];bb=[b for r in rr for b in r['regions']];cc=collections.Counter()
 for r in rr:
  cc.update({classmap[k]:v for k,v in r['class_counts'].items()})
 box_stats[level]={'regions':len(bb),'regions_per_image':stats([len(r['regions']) for r in rr]),'empty_files':sum(not r['regions'] for r in rr),'width_pixels':stats([b[2]-b[0] for b in bb]),'height_pixels':stats([b[3]-b[1] for b in bb]),'area_pixels':stats([(b[2]-b[0])*(b[3]-b[1]) for b in bb]),'classes_anonymized':dict(cc),'flags':dict(sum((collections.Counter(r['flags']) for r in rr),collections.Counter()))}
def duplicates(field):
 d=collections.defaultdict(list)
 for r in images:d[r[field]].append(r)
 g=[a for a in d.values() if len(a)>1];return {'groups':len(g),'extra_images':sum(len(a)-1 for a in g),'cross_split_groups':sum(len(set(split(r) for r in a))>1 for a in g)},[[r['name'] for r in a] for a in g]
exact,ex=duplicates('sha256');pixel,px=duplicates('pixel_sha256');candidates=[];near_cross=0;ints=[int(r['dhash'],16) for r in images]
for i in range(len(images)):
 for j in range(i):
  d=(ints[i]^ints[j]).bit_count()
  if d<=4:
   candidates.append({'a':images[i]['name'],'b':images[j]['name'],'distance':d});near_cross+=split(images[i])!=split(images[j])
save(pr/'similarity_candidates.json',candidates);save(pr/'duplicate_groups.json',{'bytes':ex,'pixels':px});save(pr/'additional_issues.json',{'pairing_dimensions':private_extra,'xml_yolo_mismatches':yolo_mismatch});save(pr/'class_map_PRIVATE.json',classmap)
summary={'report_version':'1.0','audit_date':'2026-10-19','archive':{k:v for k,v in env.items() if k not in ['python','os','gpu','libraries','ram_bytes','pillow']},'coverage':{'archive_files_read':len(rows),'crc_pass':sum(r.get('crc')=='pass' for r in rows),'images_decoded':len(images),'xml_parsed':len(xml),'yolo_parsed':len(yolo),'full_automated_inventory':len(rows)==env['entries']-17,'human_visual_review':0,'official_metrics':'not_measured'},'folders':groups,'splits':splits,'image_statistics':{'width':stats([r['width'] for r in images]),'height':stats([r['height'] for r in images]),'aspect_ratio':stats([r['width']/r['height'] for r in images]),'modes':dict(collections.Counter(r['mode'] for r in images)),'channels':dict(collections.Counter(r['channels'] for r in images)),'exif_orientation':dict(collections.Counter(r['orientation'] for r in images))},'annotations':box_stats,'issues':dict(issues),'pairing_issues':dict(missing),'consistency_issues':dict(mismatches),'xml_filename_mismatch':sum(not r['filename_matches'] for r in xml),'xml_yolo_max_normalized_difference':stats(delta),'duplicates':{'file_sha256':exact,'decoded_RGB_sha256':pixel,'dhash_pairs_hamming_le_4':len(candidates),'dhash_cross_split_pairs':near_cross,'method':'all pairs; 9x8 grayscale thumbnail; 64-bit horizontal dHash; Hamming <=4; candidate only, not proof of same scene'},'environment':{k:env[k] for k in ['python','os','gpu','ram_bytes','pillow','libraries']},'limitations':['No human visual review or crop-aware scene clustering','XML axis-aligned boxes do not encode text rotation or polygons','Class labels anonymized; official script mapping unknown','No official evaluator, no official metrics','Dataset version/source not authenticated; test labels quarantined from training planning','License agreement linked DOCX could not be fetched by web reader; agreement terms unverified']}
extra=json.loads((pr/'supplemental_checks.json').read_text(encoding='utf8'))
summary['archive']['sha256_unchanged_after_audit']=extra['archive_hash_unchanged']
summary['actual_image_geometry_issues']=extra['geometry_actual_image']
summary['image_extensions'] = dict(collections.Counter(P(r['name']).suffix for r in images))
for level in box_stats:
 box_stats[level]['flags']={k:v for k,v in box_stats[level]['flags'].items() if not k.startswith('pose:')}
 box_stats[level]['pose_distinct_values']=1
summary['audit_private_bytes']=sum(x.stat().st_size for x in pr.rglob('*') if x.is_file())
summary['coverage']['image_decode_percent']=100*len(images)/sum(P(r['name']).suffix.lower()=='.jpg' for r in rows)
save(share/'dataset_summary.json',summary)
schema={'schema_version':'1.0','observed':{'xml':{'encoding':'XML bytes parsed by ElementTree; no decoding fallback','root':'annotation','metadata':{'folder':'string','filename':'string','path':'string, private metadata, never share values','source.database':'string','size':{'width':'integer','height':'integer','depth':'integer'},'segmented':'integer'},'object[]':{'name':'categorical string; 3 distinct labels, anonymized','pose':'categorical string','truncated':'0|1 observed','difficult':'0 observed','bndbox':{'xmin':'number','ymin':'number','xmax':'number','ymax':'number'}}},'yolo':{'encoding':'UTF-8 / optional BOM; all files decoded','row':['class_id','center_x','center_y','width','height'],'coordinates':'normalized hypothesis checked numerically against XML boxes','class_id_mapping':'not documented; requires explicit reviewed mapping'},'geometry':'axis-aligned rectangles; x,y interpretation supported by XML names and paired normalized conversion; 0/1-based edge convention unresolved','text_recognition':'No transcription field observed; class name values are categories, not recognition truth'},'synthetic_example_only':{'image_id':'synthetic/sample_001.jpg','width':640,'height':480,'xml_object':{'name':'SYNTHETIC_CLASS','pose':'SYNTHETIC','truncated':0,'difficult':0,'bndbox':{'xmin':20,'ymin':30,'xmax':140,'ymax':70}},'yolo_row':[0,.125,.104166667,.1875,.083333333],'internal_prediction':{'schema_version':'1.0','image_id':'synthetic/sample_001.jpg','width':640,'height':480,'detections':[{'polygon':[[20,30],[140,30],[140,70],[20,70]],'score':.9,'script':None}]}}}
save(share/'annotation_schema.json',schema)
print(json.dumps({'splits':splits,'boxes':box_stats,'issues':dict(issues),'pairing':dict(missing),'consistency':dict(mismatches),'duplicates':summary['duplicates'],'env':summary['environment'],'image_stats':summary['image_statistics'],'xml_yolo_delta':stats(delta)},ensure_ascii=True))
