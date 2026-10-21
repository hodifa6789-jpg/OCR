import unittest
from src.contracts import bbox_polygon
from src.evaluation.local import evaluate,iou

def gt(boxes):
    return [{'image_id':'synthetic/a.JPG','width':100,'height':100,'coordinate_policy_id':'continuous_zero_based_v1','objects':[{'polygon':bbox_polygon(b),'difficult':0,'truncated':1} for b in boxes]}]
def pred(boxes):
    return [{'schema_version':'1.1','image_id':'synthetic/a.JPG','width':100,'height':100,'detections':[{'polygon':bbox_polygon(b),'score':score,'script':None} for b,score in boxes]}]
def run(p,g,**kwargs):return evaluate(p,g,split_id='synthetic_v1',coordinate_policy_id='continuous_zero_based_v1',**kwargs)

class EvaluationTests(unittest.TestCase):
    def test_tp_fp_fn_duplicate(self):
        g=gt([[0,0,10,10],[50,50,60,60]]);p=pred([([0,0,10,10],.9),([0,0,10,10],.8),([80,80,90,90],.7)])
        r=run(p,g);self.assertEqual((r['TP'],r['FP'],r['FN']),(1,2,1));self.assertAlmostEqual(r['precision'],1/3);self.assertEqual(r['recall'],.5);self.assertAlmostEqual(r['f1'],.4);self.assertEqual(r['evaluation_status'],'provisional')
    def test_exact_threshold_and_just_below(self):
        self.assertEqual(iou([0,0,10,10],[0,0,20,10]),.5)
        self.assertEqual(run(pred([([0,0,20,10],.9)]),gt([[0,0,10,10]]))['TP'],1)
        self.assertEqual(run(pred([([0,0,20.0001,10],.9)]),gt([[0,0,10,10]]))['TP'],0)
    def test_zero_denominators_empty_images(self):
        for p,g,counts in [(pred([]),gt([]),(0,0,0)),(pred([]),gt([[0,0,10,10]]),(0,0,1)),(pred([([0,0,10,10],.9)]),gt([]),(0,1,0))]:
            r=run(p,g);self.assertEqual((r['TP'],r['FP'],r['FN']),counts);self.assertEqual(r['f1'],0)
    def test_confidence_filter_and_new_difficult(self):
        self.assertEqual(run(pred([([0,0,10,10],.4)]),gt([[0,0,10,10]]),confidence_threshold=.5)['FN'],1)
        g=gt([[0,0,10,10]]);g[0]['objects'][0]['difficult']=1
        with self.assertRaises(ValueError):run(pred([]),g)
    def test_deterministic_tie_break_and_highest_iou(self):
        p=pred([([0,0,10,10],.5),([0,0,10,10],.5)])
        r=run(p,gt([[0,0,10,10]]));self.assertEqual(r['diagnostics'][0]['matches'][0]['prediction_index'],0);self.assertEqual(r['diagnostics'][0]['matches'][1]['status'],'FP')
    def test_missing_prediction_and_coordinate_context(self):
        with self.assertRaises(ValueError):run([],gt([]))
        g=gt([]);g[0]['coordinate_policy_id']='other'
        with self.assertRaises(ValueError):run(pred([]),g)
