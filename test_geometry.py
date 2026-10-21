import copy
import unittest
from src.contracts import bbox_polygon,validate_prediction,validate_predictions
from src.models.transforms import ResizePad

def prediction():
    return {'schema_version':'1.1','image_id':'synthetic/one.JPG','width':200,'height':100,'detections':[{'polygon':bbox_polygon([13,21,61,39]),'score':.9,'script':None}]}

class GeometryTests(unittest.TestCase):
    def test_asymmetric_xy_resize_padding_roundtrip(self):
        polygon=[[13,21],[61,21],[61,39],[13,39]];transform=ResizePad(.5,.25,7,11)
        transformed=transform.forward(polygon)
        self.assertEqual(transformed[0],[13.5,16.25]);self.assertEqual(transform.inverse(transformed),polygon)
    def test_invalid_transform(self):
        for scale in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):ResizePad(scale,1)
    def test_invalid_scores_polygons(self):
        for score in [-.1,1.1,float('nan'),True]:
            p=prediction();p['detections'][0]['score']=score
            with self.assertRaises(ValueError):validate_prediction(p)
        for poly in [[[0,0],[1,1]],[[0,0],[2,2],[4,4]],[[0,0],[200,100],[0,100],[200,0]],[[0,0],[2,0],[2,2],[0,2],[2,0]],[[-1,0],[1,0],[1,2]],[[0,0],[float('inf'),0],[1,2]]]:
            p=prediction();p['detections'][0]['polygon']=poly
            with self.assertRaises(ValueError):validate_prediction(p)
    def test_both_windings_and_no_gt_fields(self):
        p=prediction();p['detections'][0]['polygon'].reverse();validate_prediction(p)
        p['ground_truth']=[]
        with self.assertRaises(ValueError):validate_prediction(p)
    def test_missing_duplicate_dimensions(self):
        p=prediction();expected={p['image_id']:(200,100)}
        with self.assertRaises(ValueError):validate_predictions([],expected)
        with self.assertRaises(ValueError):validate_predictions([p,p],expected)
        with self.assertRaises(ValueError):validate_predictions([p],{p['image_id']:(100,200)})
