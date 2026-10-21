import hashlib
import json
import random
from src.data.loader import validate_manifest

def make_split(rows, fraction=.15, seed=2026, groups=None):
    validate_manifest(rows,'train')
    if not rows or not 0 < fraction < 1:
        raise ValueError('Nonempty eligible pool and fraction in (0,1) required')
    ids=sorted(r['image_id'] for r in rows)
    if groups is not None and (set(groups)!=set(ids) or any(not isinstance(g,str) or not g for g in groups.values())):
        raise ValueError('Group evidence must cover pool exactly')
    bucket={}
    for key in ids:bucket.setdefault(groups[key] if groups else key,[]).append(key)
    keys=sorted(bucket);random.Random(seed).shuffle(keys)
    val=[];target=max(1,min(len(ids)-1,round(len(ids)*fraction)))
    for key in keys:
        if len(val)<target:val.extend(bucket[key])
    if not val or len(val)==len(ids):raise ValueError('Split must retain both train and validation')
    train=sorted(set(ids)-set(val));val=sorted(val)
    payload=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return {'split_id':'train_holdout_v1','seed':seed,'validation_fraction_target':fraction,'grouping_status':'provided_evidence' if groups else 'image_only_scene_leakage_unresolved','manifest_sha256':hashlib.sha256(payload).hexdigest(),'manifest_hash_method':'utf8 JSON array, sorted object keys, compact separators, input row order','train_ids':train,'val_ids':val}
