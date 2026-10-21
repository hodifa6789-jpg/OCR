import pathlib,json,collections,hashlib,zipfile,time
p=pathlib.Path('reports/private');rs=[json.loads(l) for l in (p/'checkpoint.jsonl').read_text(encoding='utf8').splitlines()];by={r['name']:r for r in rs};mapping=collections.defaultdict(collections.Counter);bad=collections.Counter();details=[];filebounds=0
for r in rs:
 if r.get('kind')!='xml':continue
 im=by['Images/'+r['name'].split('/')[2].lower()+'/'+pathlib.Path(r['name']).stem+'.JPG'];invalid=0
 for b in r['regions']:
  if b[0]<0 or b[1]<0 or b[2]>im['width'] or b[3]>im['height']:invalid+=1
 if invalid:bad['boxes_outside_actual_image']+=invalid;filebounds+=1
 if (r['width'],r['height'])!=(im['width'],im['height']):details.append({'xml':r['name'],'image':im['name'],'xml_size':[r['width'],r['height']],'actual_size':[im['width'],im['height']],'outside_boxes':invalid})
# No actual classes or text returned to chat.
s={'geometry_actual_image':dict(bad),'files_outside_actual':filebounds,'dimension_mismatch_details':details,'empty_xml_files':[r['name'] for r in rs if r.get('kind')=='xml' and not r['regions']]}
(p/'supplemental_checks.json').write_text(json.dumps(s,indent=2),encoding='utf8')
t=time.monotonic();h=hashlib.sha256()
with open(r'C:\Users\GiGabyte\Downloads\SYPHAXAR.zip','rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
env=json.loads((p/'environment_archive.json').read_text(encoding='utf8'));assert h.hexdigest()==env['sha256'];s['archive_hash_unchanged']=True;s['final_hash_seconds']=time.monotonic()-t
(p/'supplemental_checks.json').write_text(json.dumps(s,indent=2),encoding='utf8');print(json.dumps({'actual_image_bound_issues':dict(bad),'mismatch_dimensions':[{'xml_size':v['xml_size'],'actual_size':v['actual_size'],'outside_boxes':v['outside_boxes']} for v in details],'archive_hash_unchanged':True,'audit_private_bytes':sum(x.stat().st_size for x in p.rglob('*') if x.is_file())}))
