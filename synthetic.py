"""Fabricated fixtures: rectangle, empty image, Arabic filename."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
from src.contracts import SYNTHETIC_POLICY,write_jsonl

def create_synthetic(root):
    root=Path(root);images=root/'Images/synthetic';images.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,box in [('rectangle.JPG',[13,21,61,39]),('empty.JPG',None),('مثال.JPG',[7,11,35,27])]:
        im=Image.new('RGB',(96,64),'white')
        if box:ImageDraw.Draw(im).rectangle([box[0],box[1],box[2]-1,box[3]-1],fill=(255,0,0))
        im.save(images/name,format='JPEG',quality=100,subsampling=0)
        ann=f'Annotations/Word-Level/Synthetic/{Path(name).stem}.xml';ap=root/ann;ap.parent.mkdir(parents=True,exist_ok=True)
        obj='' if box is None else '<object><name>SYNTHETIC_CLASS</name><difficult>0</difficult><truncated>1</truncated><bndbox>'+''.join(f'<{k}>{v}</{k}>' for k,v in zip(('xmin','ymin','xmax','ymax'),box))+'</bndbox></object>'
        ap.write_text(f'<annotation><filename>{name}</filename><size><width>96</width><height>64</height><depth>3</depth></size>{obj}</annotation>',encoding='utf8')
        key='Images/synthetic/'+name
        manifest.append({'image_id':key,'image_path':key,'annotation_path':ann,'annotation_level':'word','source_split':'synthetic','split':'synthetic','width':96,'height':64,'coordinate_policy_id':SYNTHETIC_POLICY,'eligible_for_training':True})
    write_jsonl(root/'manifest.jsonl',manifest)
    write_jsonl(root/'images_manifest.jsonl',[{k:v for k,v in r.items() if k!='annotation_path'} for r in manifest])
    return manifest
