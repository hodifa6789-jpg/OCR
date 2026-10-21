import argparse,collections,csv,hashlib,io,json,math,os,pathlib,platform,re,shutil,stat,subprocess,sys,time,xml.etree.ElementTree as ET
from PIL import Image,ImageOps
P=pathlib.Path
ap=argparse.ArgumentParser();ap.add_argument('--archive',required=True);a=ap.parse_args();archive=P(a.archive);root=P(__file__).resolve().parents[1];private=root/'reports/private';private.mkdir(parents=True,exist_ok=True)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
t=time.monotonic();h=hashlib.sha256()
with archive.open('rb') as f:
 for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
meta={'archive_bytes':archive.stat().st_size,'sha256':h.hexdigest(),'hash_seconds':time.monotonic()-t,'magic_hex':archive.open('rb').read(8).hex(),'free_bytes':shutil.disk_usage(root).free,'python':sys.version,'os':platform.platform(),'pillow':Image.__version__}
import ctypes
class MEM(ctypes.Structure):_fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','avail','page','availpage','virtual','availvirtual','extended']]
m=MEM();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m));meta['ram_bytes']=m.total
meta['gpu']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],capture_output=True,text=True).stdout.strip()
import importlib.metadata as im
meta['libraries']={n:next((d.version for d in im.distributions() if d.metadata['Name'].lower()==n.lower()),None) for n in ['numpy','Pillow','torch','paddlepaddle','opencv-python','tensorflow']}
import zipfile
state=private/'checkpoint.jsonl';done={}
identity=private/'checkpoint_identity.json'
if state.exists() and not identity.exists():
 raise RuntimeError('Checkpoint identity absent; review existing checkpoint before reuse')
if identity.exists() and json.loads(identity.read_text(encoding='utf8'))['archive_sha256']!=meta['sha256']:
 raise RuntimeError('Archive changed; use a new audit workspace')
save(identity,{'archive_sha256':meta['sha256']})
save(private/'environment_archive.json',meta)
if state.exists():
 for line in state.read_text(encoding='utf8').splitlines():
  try:r=json.loads(line);done[r['name']]=r
  except Exception:pass
with zipfile.ZipFile(archive) as z:
 infos=z.infolist();meta.update(entries=len(infos),uncompressed_bytes=sum(i.file_size for i in infos),compressed_bytes=sum(i.compress_size for i in infos),encrypted=sum(bool(i.flag_bits&1) for i in infos)); counts=collections.Counter(i.filename.casefold() for i in infos);meta['case_collisions']=sum(v-1 for v in counts.values() if v>1)
 meta['nested_archives']=[i.filename for i in infos if P(i.filename).suffix.lower() in ['.zip','.7z','.rar','.tar','.gz']]
 with state.open('a',encoding='utf8') as out:
  for k,i in enumerate(infos):
   if i.is_dir() or i.filename in done:continue
   n=i.filename;r={'name':n,'bytes':i.file_size,'compressed':i.compress_size,'issues':[]};parts=n.replace('\\','/').split('/')
   if n.startswith(('/','\\')) or '..' in parts or re.match(r'^[a-zA-Z]:',n) or stat.S_ISLNK(i.external_attr>>16):r['issues'].append('unsafe_path_or_link')
   if any(p.endswith((' ','.')) or any(c in p for c in ':*?"<>|') or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',p,re.I) for p in parts):r['issues'].append('windows_name')
   try:
    b=z.read(i);r['sha256']=hashlib.sha256(b).hexdigest();r['crc']='pass';ext=P(n).suffix.lower()
    if ext=='.jpg':
     with Image.open(io.BytesIO(b)) as image:
      image.load();w,hh=image.size;r.update(kind='image',width=w,height=hh,mode=image.mode,channels=len(image.getbands()),orientation=image.getexif().get(274,1));thumb=ImageOps.grayscale(image).resize((9,8));v=list(thumb.getdata());r['dhash']=format(sum((v[y*9+x]>v[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8)),'016x');r['pixel_sha256']=hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
    elif ext=='.xml':
     rr=ET.fromstring(b);w=float(rr.findtext('size/width'));hh=float(rr.findtext('size/height'));r.update(kind='xml',width=w,height=hh,fields=dict(collections.Counter(e.tag for e in rr.iter())),regions=[],flags={},class_counts={});cl=collections.Counter();flags=collections.Counter()
     for obj in rr.findall('object'):
      cl[obj.findtext('name','')]+=1
      for tag in ['difficult','truncated','pose']:flags[tag+':'+obj.findtext(tag,'')]+=1
      box=[float(obj.findtext('bndbox/'+q)) for q in ['xmin','ymin','xmax','ymax']];r['regions'].append(box)
      if not all(math.isfinite(v) for v in box):r['issues'].append('nonfinite_box')
      elif box[2]<=box[0] or box[3]<=box[1]:r['issues'].append('degenerate_box')
      elif box[0]<0 or box[1]<0 or box[2]>w or box[3]>hh:r['issues'].append('out_of_bounds_box')
     r['class_counts']=dict(cl);r['flags']=dict(flags);r['filename_matches']=P(rr.findtext('filename','')).stem==P(n).stem
    elif ext=='.txt':
     text=b.decode('utf-8-sig');r.update(kind='yolo',regions=[],class_counts={});cl=collections.Counter()
     for line in text.splitlines():
      if not line.strip():continue
      vals=[float(x) for x in line.split()]
      if len(vals)!=5:r['issues'].append('yolo_field_count');continue
      cl[str(vals[0])]+=1;r['regions'].append(vals)
      if not all(math.isfinite(x) for x in vals):r['issues'].append('nonfinite_yolo')
      elif any(x<0 or x>1 for x in vals[1:]):r['issues'].append('yolo_range')
      elif vals[3]<=0 or vals[4]<=0:r['issues'].append('degenerate_yolo')
     r['class_counts']=dict(cl)
    else:r['kind']='document';(private/'README_source.md').write_bytes(b)
   except Exception as e:r['issues'].append('read_or_parse_error:'+type(e).__name__)
   out.write(json.dumps(r,ensure_ascii=False)+'\n');out.flush();done[n]=r
   if k%250==0:print(json.dumps({'processed':len(done),'total_files':len(infos)-17}),flush=True)
save(private/'environment_archive.json',meta)
with (private/'FILE_INVENTORY.csv').open('w',encoding='utf-8-sig',newline='') as f:
 wr=csv.writer(f);wr.writerow(['relative_path','bytes','compressed','sha256','crc','issues']);wr.writerows([i.filename,0,0,'','','directory'] for i in infos if i.is_dir());wr.writerows([r['name'],r['bytes'],r['compressed'],r.get('sha256'),r.get('crc'),';'.join(r['issues'])] for r in done.values())
print('COMPLETE',len(done),flush=True)
