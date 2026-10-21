"""python -m src.cli --help. No training or official export command."""
import argparse
import json
from pathlib import Path
import platform
import hashlib
import sys
import numpy as np
import PIL
from src.contracts import read_jsonl,write_jsonl,SCHEMA_VERSION,SYNTHETIC_POLICY
from src.data import Dataset,validate_manifest
from src.data.synthetic import create_synthetic
from src.data.splits import make_split
from src.models import MockDetector
from src.evaluation import evaluate
from src.submission import export_internal

def dump(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')

def predict(data_root,manifest,out):
    rows=validate_manifest(read_jsonl(manifest),'predict')
    if any(r['source_split']!='synthetic' for r in rows):
        raise ValueError('MockDetector is restricted to synthetic input')
    detector=MockDetector();predictions=[]
    with Dataset(data_root) as ds:
        for row in rows:predictions.append(detector.predict(ds.image(row),row['image_id']))
    export_internal(predictions,{r['image_id']:(r['width'],r['height']) for r in rows},out)
    return predictions

def main(argv=None):
    parser=argparse.ArgumentParser();subs=parser.add_subparsers(dest='command',required=True)
    demo=subs.add_parser('demo');demo.add_argument('--out',required=True)
    val=subs.add_parser('validate');val.add_argument('--data-root',required=True);val.add_argument('--manifest',required=True);val.add_argument('--level',choices=['word','line'],required=True);val.add_argument('--out',required=True)
    pred=subs.add_parser('predict');pred.add_argument('--data-root',required=True);pred.add_argument('--manifest',required=True);pred.add_argument('--out',required=True)
    ev=subs.add_parser('evaluate');ev.add_argument('--data-root',required=True);ev.add_argument('--manifest',required=True);ev.add_argument('--predictions',required=True);ev.add_argument('--level',choices=['word','line'],required=True);ev.add_argument('--split-id',required=True);ev.add_argument('--coordinate-policy-id',required=True);ev.add_argument('--confidence-threshold',type=float,default=0.);ev.add_argument('--iou-threshold',type=float,default=.5);ev.add_argument('--out',required=True)
    sp=subs.add_parser('split');sp.add_argument('--manifest',required=True);sp.add_argument('--out',required=True);sp.add_argument('--seed',type=int,default=2026)
    ex=subs.add_parser('export-internal');ex.add_argument('--predictions',required=True);ex.add_argument('--manifest',required=True);ex.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    if args.command=='demo':
        out=Path(args.out)
        if out.exists() and any(out.iterdir()):raise ValueError('Demo output must be new or empty')
        rows=create_synthetic(out/'data')
        predictions=predict(out/'data',out/'data/images_manifest.jsonl',out/'predictions.jsonl')
        with Dataset(out/'data') as ds:gt=[ds.ground_truth(r,'word') for r in rows]
        metrics=evaluate(predictions,gt,split_id='synthetic_v1',coordinate_policy_id=SYNTHETIC_POLICY)
        metrics.update(detector='MockDetector',data_status='synthetic_only_not_model_performance')
        dump(out/'metrics.json',metrics)
        export_internal(predictions,{r['image_id']:(r['width'],r['height']) for r in rows},out/'internal_export.jsonl')
        dump(out/'run_metadata.json',{'run_id':out.name,'schema_version':SCHEMA_VERSION,'detector':'MockDetector','synthetic_only':True,'coordinate_policy_id':SYNTHETIC_POLICY,'annotation_level':'word','protocol_id':'eval_local_v0','split_id':'synthetic_v1','python':sys.version,'numpy':np.__version__,'pillow':PIL.__version__,'os':platform.system(),'training_performed':False})
        metadata=json.loads((out/'run_metadata.json').read_text(encoding='utf8'))
        metadata.update(git_commit=None,git_status='not_a_repository',seed=2026,manifest_sha256=hashlib.sha256((out/'data/manifest.jsonl').read_bytes()).hexdigest(),weights_sha256=None,confidence_threshold=0.,iou_threshold=.5,model_performance_measured=False)
        dump(out/'run_metadata.json',metadata)
        print('Synthetic demo completed; no model performance measured.')
    elif args.command=='predict':predict(args.data_root,args.manifest,args.out)
    elif args.command=='split':dump(args.out,make_split(read_jsonl(args.manifest),seed=args.seed))
    elif args.command=='export-internal':
        rows=validate_manifest(read_jsonl(args.manifest),'predict');export_internal(read_jsonl(args.predictions),{r['image_id']:(r['width'],r['height']) for r in rows},args.out)
    elif args.command in ('validate','evaluate'):
        rows=validate_manifest(read_jsonl(args.manifest))
        if args.command=='evaluate' and any(r['source_split']=='test' for r in rows):raise ValueError('Test evaluation is quarantined pending authorization')
        results=[];gt=[]
        with Dataset(args.data_root) as ds:
            for row in rows:
                ds.image(row);truth=ds.ground_truth(row,args.level);gt.append(truth);results.append({'image_id':row['image_id'],'issues':truth['issues'],'regions':len(truth['objects'])})
        if args.command=='validate':dump(args.out,results)
        else:
            if any(r['issues'] for r in gt):raise ValueError('Resolve annotation issues before evaluation')
            dump(args.out,evaluate(read_jsonl(args.predictions),gt,split_id=args.split_id,coordinate_policy_id=args.coordinate_policy_id,confidence_threshold=args.confidence_threshold,iou_threshold=args.iou_threshold))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as exc:
        print('Run failed: '+type(exc).__name__+'; inspect inputs locally.',file=sys.stderr)
        raise SystemExit(1)
