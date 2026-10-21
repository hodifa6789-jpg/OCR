"""Validated internal contract 1.1, continuous coordinates without clipping."""
import json
import math
from pathlib import Path

SCHEMA_VERSION = '1.1'
SYNTHETIC_POLICY = 'continuous_zero_based_v1'
REAL_POLICY = 'voc_numeric_passthrough_v0'

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected a finite number')
    return float(value)

def image_id(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Invalid relative image_id')
    return value

def bbox_polygon(box):
    x0, y0, x1, y1 = map(number, box)
    if x1 <= x0 or y1 <= y0:
        raise ValueError('Degenerate box')
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def polygon_bbox(poly):
    return [min(p[0] for p in poly), min(p[1] for p in poly), max(p[0] for p in poly), max(p[1] for p in poly)]

def validate_polygon(poly, width, height):
    if not isinstance(poly, (list, tuple)) or len(poly) < 3:
        raise ValueError('Polygon needs at least 3 points')
    pts = []
    for p in poly:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError('Point must be x,y')
        x, y = map(number, p)
        if not (0 <= x <= width and 0 <= y <= height):
            raise ValueError('Polygon outside image')
        pts.append((x, y))
    if len(set(pts)) != len(pts):
        raise ValueError('Repeated polygon vertex')
    area = sum(pts[i][0]*pts[(i+1)%len(pts)][1]-pts[(i+1)%len(pts)][0]*pts[i][1] for i in range(len(pts)))
    if abs(area) < 1e-9:
        raise ValueError('Zero-area polygon')
    def orient(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def intersects(a,b,c,d):
        o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
        def on(a,b,p):
            return min(a[0],b[0]) <= p[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= p[1] <= max(a[1],b[1])
        return (o1*o2<0 and o3*o4<0) or any(abs(o)<1e-12 and on(u,v,p) for o,u,v,p in [(o1,a,b,c),(o2,a,b,d),(o3,c,d,a),(o4,c,d,b)])
    n=len(pts)
    for i in range(n):
        for j in range(i+1,n):
            if j in (i,(i+1)%n) or i==(j+1)%n:
                continue
            if intersects(pts[i],pts[(i+1)%n],pts[j],pts[(j+1)%n]):
                raise ValueError('Self-intersecting polygon')

def validate_prediction(record):
    required={'schema_version','image_id','width','height','detections'}
    if set(record) != required or record['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Prediction contract mismatch')
    image_id(record['image_id'])
    for dim in ('width','height'):
        if isinstance(record[dim], bool) or not isinstance(record[dim], int) or record[dim] <= 0:
            raise ValueError('Invalid dimensions')
    if not isinstance(record['detections'],list):
        raise ValueError('detections must be a list')
    for d in record['detections']:
        if set(d) != {'polygon','score','script'}:
            raise ValueError('Detection contract mismatch; ground truth prohibited')
        validate_polygon(d['polygon'],record['width'],record['height'])
        if not 0 <= number(d['score']) <= 1 or (d['script'] is not None and not isinstance(d['script'],str)):
            raise ValueError('Invalid score or script')
    return record

def validate_predictions(records, expected):
    found={}
    for r in records:
        validate_prediction(r)
        if r['image_id'] in found:
            raise ValueError('Duplicate prediction image_id')
        found[r['image_id']]=r
    if set(found) != set(expected):
        raise ValueError('Missing or unexpected predictions')
    for key, dims in expected.items():
        if (found[key]['width'],found[key]['height']) != tuple(dims):
            raise ValueError('Prediction dimensions mismatch')
    return found

def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf8').splitlines() if line.strip()]

def write_jsonl(path, rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w',encoding='utf8',newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,allow_nan=False,sort_keys=True)+'\n')
    temporary.replace(path)
