"""Read-only directory/ZIP loader. Never trusts XML filename/path metadata."""
import io
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from PIL import Image
from src.contracts import image_id, bbox_polygon, validate_polygon, number

def parse_xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('DTD/entities are prohibited')
    root=ET.fromstring(data)
    if root.tag != 'annotation':
        raise ValueError('Expected Pascal VOC annotation')
    width=int(root.findtext('size/width'));height=int(root.findtext('size/height'))
    if width <= 0 or height <= 0:
        raise ValueError('Invalid XML size')
    objects=[]
    for obj in root.findall('object'):
        box=[float(obj.findtext('bndbox/'+k)) for k in ('xmin','ymin','xmax','ymax')]
        poly=bbox_polygon(box);validate_polygon(poly,width,height)
        flags={k:int(obj.findtext(k,'0')) for k in ('difficult','truncated')}
        if any(v not in (0,1) for v in flags.values()):
            raise ValueError('Unknown annotation flag')
        label=obj.findtext('name')
        if not label:
            raise ValueError('Missing category')
        objects.append({'class_name':label,'raw_bbox':box,'polygon':poly,**flags})
    return {'source_width':width,'source_height':height,'filename':root.findtext('filename',''),'objects':objects}

def parse_yolo(data):
    rows=[]
    for line in data.decode('utf-8-sig').splitlines():
        if not line.strip():
            continue
        parts=line.split()
        if len(parts)!=5:
            raise ValueError('YOLO requires five fields')
        vals=[float(p) for p in parts]
        if not all(math.isfinite(x) for x in vals) or vals[0]<0 or vals[0]!=int(vals[0]) or any(x<0 or x>1 for x in vals[1:]) or vals[3]<=0 or vals[4]<=0:
            raise ValueError('Invalid YOLO row')
        rows.append({'class_id':int(vals[0]),'normalized_box':vals[1:]})
    return rows

def validate_manifest(rows, purpose='inspect'):
    if purpose not in ('inspect','train','validation','predict'):
        raise ValueError('Unknown purpose')
    ids=set();levels=set();pairkeys=set()
    for r in rows:
        key=image_id(r['image_id']);image_id(r['image_path'])
        if key != r['image_path']:
            raise ValueError('image_id must preserve the relative image path')
        if key in ids:
            raise ValueError('Duplicate image_id')
        ids.add(key)
        for field in ('width','height'):
            if isinstance(r[field],bool) or not isinstance(r[field],int) or r[field]<=0:
                raise ValueError('Invalid manifest dimensions')
        if r['source_split'] not in ('train','test','synthetic'):
            raise ValueError('Unknown source split')
        if not isinstance(r.get('coordinate_policy_id'),str) or not r['coordinate_policy_id']:
            raise ValueError('Explicit coordinate_policy_id required')
        # Cross-check path to prevent a relabeled Images/test entry entering train.
        parts=r['image_path'].split('/')
        if len(parts)>1 and parts[0]=='Images' and parts[1] != r['source_split']:
            raise ValueError('Split/path conflict')
        pair=(r['source_split'],Path(r['image_path']).stem)
        if pair in pairkeys:
            raise ValueError('Ambiguous split/stem pairing')
        pairkeys.add(pair)
        if purpose in ('train','validation'):
            if r['source_split']=='test' or r.get('split')=='test':
                raise ValueError('Test is quarantined')
            if r.get('eligible_for_training') is not True:
                raise ValueError('Unresolved review blocks training')
        if purpose=='predict' and any(k in r for k in ('annotation_path','yolo_path','objects','ground_truth')):
            raise ValueError('Prediction manifest must not contain labels')
        if purpose=='predict':
            allowed={'image_id','image_path','width','height','source_split','split','annotation_level','coordinate_policy_id','eligible_for_training','review_status','issues','source_width','source_height'}
            if set(r)-allowed:
                raise ValueError('Unknown field in inference manifest')
        if 'annotation_path' in r:
            image_id(r['annotation_path'])
            if r.get('annotation_level') not in ('word','line'):
                raise ValueError('Explicit annotation level required')
            level_folder='Word-Level' if r['annotation_level']=='word' else 'Line-Level'
            expected=f"Annotations/{level_folder}/{r['source_split'].title()}/{Path(r['image_path']).stem}.xml"
            if r['annotation_path'] != expected:
                raise ValueError('Annotation split/stem/level binding mismatch')
            if 'yolo_path' in r:
                image_id(r['yolo_path'])
                if r['yolo_path'] != expected.replace('Annotations/','YOLO_Annotations/',1).replace('.xml','.txt'):
                    raise ValueError('YOLO binding mismatch')
            levels.add(r['annotation_level'])
    if len(levels)>1:
        raise ValueError('Mixed annotation levels')
    return rows

class Dataset:
    def __init__(self, data_root):
        self.root=Path(data_root)
        self.zip=zipfile.ZipFile(self.root) if self.root.is_file() else None
        self.members={}
        if self.zip:
            for info in self.zip.infolist():
                self.members.setdefault(info.filename,[]).append(info)
    def close(self):
        if self.zip:self.zip.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def read(self,relative):
        image_id(relative)
        if self.zip:
            entries=self.members.get(relative,[])
            if len(entries)!=1:
                raise ValueError('Missing or duplicate archive member')
            return self.zip.read(entries[0])
        path=(self.root/relative).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError('Path escapes DATA_ROOT')
        return path.read_bytes()
    def image(self,row):
        with Image.open(io.BytesIO(self.read(row['image_path']))) as im:
            im.load()
            if im.size != (row['width'],row['height']):
                raise ValueError('Manifest image dimensions mismatch')
            # No EXIF auto-rotation; RGBA alpha explicitly composited on white.
            if im.mode in ('RGBA','LA') or 'transparency' in im.info:
                rgba=im.convert('RGBA');bg=Image.new('RGBA',im.size,'white');im=Image.alpha_composite(bg,rgba).convert('RGB')
            return np.array(im.convert('RGB'),dtype=np.uint8)
    def ground_truth(self,row,level, purpose='inspect'):
        validate_manifest([row],purpose)
        if row.get('annotation_level') != level:
            raise ValueError('Requested annotation level does not match manifest')
        parsed=parse_xml(self.read(row['annotation_path']));issues=[]
        if Path(parsed['filename']).stem != Path(row['image_path']).stem:
            issues.append('xml_filename_mismatch')
        if (parsed['source_width'],parsed['source_height']) != (row['width'],row['height']):
            issues.append('xml_image_dimensions')
        for obj in parsed['objects']:
            validate_polygon(obj['polygon'],row['width'],row['height'])
        return {**parsed,'image_id':row['image_id'],'width':row['width'],'height':row['height'],'coordinate_policy_id':row['coordinate_policy_id'],'issues':issues}
