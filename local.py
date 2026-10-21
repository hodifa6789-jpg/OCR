"""eval_local_v0: provisional class-agnostic bbox matching, not ACIT rules."""
from src.contracts import validate_predictions, polygon_bbox, validate_polygon

def iou(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/union if union>0 else 0.0

def evaluate(predictions,ground_truth,*,split_id,coordinate_policy_id,confidence_threshold=0.,iou_threshold=.5):
    from src.contracts import number
    if not 0<=number(confidence_threshold)<=1 or not 0<number(iou_threshold)<=1:
        raise ValueError('Invalid evaluation threshold')
    if not split_id or not coordinate_policy_id:raise ValueError('Protocol context required')
    gt={}
    for row in ground_truth:
        if row['image_id'] in gt:raise ValueError('Duplicate GT image_id')
        if row['coordinate_policy_id']!=coordinate_policy_id:raise ValueError('Mixed coordinate policies')
        for obj in row['objects']:
            if obj['difficult']!=0:raise ValueError('New difficult flag requires reviewed policy')
            validate_polygon(obj['polygon'],row['width'],row['height'])
        gt[row['image_id']]=row
    pred=validate_predictions(predictions,{k:(r['width'],r['height']) for k,r in gt.items()})
    tp=fp=fn=0;diagnostics=[]
    for key in sorted(gt):
        boxes=[polygon_bbox(o['polygon']) for o in gt[key]['objects']];matched=set();pairs=[]
        ranked=sorted(enumerate(pred[key]['detections']),key=lambda v:(-v[1]['score'],v[0]))
        for index,d in ranked:
            if d['score']<confidence_threshold:continue
            choices=[(iou(polygon_bbox(d['polygon']),b),j) for j,b in enumerate(boxes) if j not in matched]
            best=min(choices,key=lambda v:(-v[0],v[1])) if choices else (0.,-1)
            if best[1]>=0 and best[0]>=iou_threshold:
                tp+=1;matched.add(best[1]);pairs.append({'prediction_index':index,'gt_index':best[1],'status':'TP','iou':best[0]})
            else:fp+=1;pairs.append({'prediction_index':index,'status':'FP'})
        fn+=len(boxes)-len(matched);diagnostics.append({'image_id':key,'matches':pairs,'missed_gt_indices':sorted(set(range(len(boxes)))-matched)})
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return {'evaluation_status':'provisional','protocol_id':'eval_local_v0','split_id':split_id,'coordinate_policy_id':coordinate_policy_id,'geometry':'axis_aligned_bbox_envelope','class_agnostic':True,'confidence_threshold':confidence_threshold,'iou_threshold':iou_threshold,'zero_denominator_policy':'return_zero','truncated_policy':'retain','difficult_policy':'reject_nonzero_until_reviewed','TP':tp,'FP':fp,'FN':fn,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.,'diagnostics':diagnostics}
