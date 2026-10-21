import copy
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from src.data import Dataset,validate_manifest,parse_xml,parse_yolo
from src.data.synthetic import create_synthetic
from src.data.splits import make_split
from src.contracts import REAL_POLICY

class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.rows=create_synthetic(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_arabic_uppercase_and_empty(self):
        with Dataset(self.root) as ds:
            self.assertEqual(ds.image(self.rows[2]).shape,(64,96,3))
            self.assertEqual(ds.ground_truth(self.rows[1],'word')['objects'],[])
    def test_gray_alpha_rgb_policy(self):
        with Dataset(self.root) as ds:
            for mode,color in [('L',100),('RGBA',(0,0,0,0))]:
                path=self.root/self.rows[0]['image_path'];Image.new(mode,(96,64),color).save(path,format='PNG')
                pixels=ds.image(self.rows[0]);self.assertEqual(pixels.dtype.name,'uint8');self.assertEqual(pixels.shape,(64,96,3))
                self.assertEqual(int(pixels[0,0,0]),100 if mode=='L' else 255)
    def test_corrupt_is_error_not_empty(self):
        (self.root/self.rows[0]['image_path']).write_bytes(b'broken')
        with Dataset(self.root) as ds:
            with self.assertRaises(OSError):ds.image(self.rows[0])
    def test_metadata_mismatches_preserve_boxes(self):
        path=self.root/self.rows[0]['annotation_path'];text=path.read_text(encoding='utf8').replace('rectangle.JPG','wrong.JPG').replace('<width>96</width>','<width>97</width>');path.write_text(text,encoding='utf8')
        with Dataset(self.root) as ds:
            result=ds.ground_truth(self.rows[0],'word')
        self.assertEqual(set(result['issues']),{'xml_filename_mismatch','xml_image_dimensions'})
        self.assertEqual(result['objects'][0]['raw_bbox'],[13,21,61,39]);self.assertEqual(result['source_width'],97)
    def test_explicit_level_and_unique_ids(self):
        with Dataset(self.root) as ds:
            with self.assertRaises(ValueError):ds.ground_truth(self.rows[0],'line')
        with self.assertRaises(ValueError):validate_manifest(self.rows+[self.rows[0]])
        other=copy.deepcopy(self.rows);other[1]['annotation_level']='line'
        with self.assertRaises(ValueError):validate_manifest(other)
    def test_test_blocked_and_same_stem_across_splits(self):
        row=dict(self.rows[0],image_id='Images/test/rectangle.JPG',image_path='Images/test/rectangle.JPG',annotation_path='Annotations/Word-Level/Test/rectangle.xml',source_split='test',split='test')
        validate_manifest([self.rows[0],row])
        with self.assertRaises(ValueError):make_split([row])
        disguised=dict(row,source_split='train')
        with self.assertRaises(ValueError):validate_manifest([disguised])
    def test_no_labels_in_prediction_manifest(self):
        with self.assertRaises(ValueError):validate_manifest(self.rows,'predict')
    def test_split_deterministic_disjoint_eligible(self):
        rows=[dict(self.rows[0],image_id=f'Images/train/{i}.JPG',image_path=f'Images/train/{i}.JPG',annotation_path=f'Annotations/Word-Level/Train/{i}.xml',source_split='train',split='train') for i in range(20)]
        a=make_split(rows);b=make_split(list(reversed(rows)))
        self.assertEqual(a['train_ids'],b['train_ids']);self.assertEqual(a['val_ids'],b['val_ids']);self.assertEqual(len(a['val_ids']),3)
        self.assertFalse(set(a['train_ids'])&set(a['val_ids']))
        self.assertEqual(set(a['train_ids'])|set(a['val_ids']),{r['image_id'] for r in rows})
        rows[0]['eligible_for_training']=False
        with self.assertRaises(ValueError):make_split(rows)
    def test_group_integrity(self):
        rows=[dict(self.rows[0],image_id=f'Images/train/{i}.JPG',image_path=f'Images/train/{i}.JPG',annotation_path=f'Annotations/Word-Level/Train/{i}.xml',source_split='train',split='train') for i in range(20)]
        groups={r['image_id']:str(i//2) for i,r in enumerate(rows)};result=make_split(rows,groups=groups)
        self.assertFalse({groups[k] for k in result['train_ids']}&{groups[k] for k in result['val_ids']})
    def test_xml_yolo_invalid(self):
        self.assertEqual(parse_yolo(b''),[])
        for bad in [b'0 nan .5 .1 .1',b'0.5 .5 .5 .1 .1',b'0 .5 .5 0 .1',b'0 .5 .5 1.2 .1']:
            with self.assertRaises(ValueError):parse_yolo(bad)
        with self.assertRaises(ValueError):parse_xml(b'<!DOCTYPE x [<!ENTITY x "data">]><annotation/>')
    def test_directory_path_escape(self):
        with Dataset(self.root) as ds:
            with self.assertRaises(ValueError):ds.read('../outside.JPG')

    def test_wrong_annotation_binding(self):
        row=dict(self.rows[0],annotation_path=self.rows[2]['annotation_path'])
        with self.assertRaises(ValueError):validate_manifest([row])
    def test_coordinate_policy_and_boolean_eligibility(self):
        row=dict(self.rows[0]);row.pop('coordinate_policy_id')
        with self.assertRaises(ValueError):validate_manifest([row])
        row=dict(self.rows[0],eligible_for_training='false')
        with self.assertRaises(ValueError):validate_manifest([row],'train')
