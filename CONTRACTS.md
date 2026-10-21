# Internal contract 1.1

These interfaces are team decisions, not official ACIT submission rules.
Runtime validators: src/contracts.py and src/data/loader.py.

| Component | Input | Output |
|---|---|---|
| Dataset | DATA_ROOT directory/read-only ZIP, manifest | RGB uint8 H,W,3, original dimensions; no EXIF rotation; alpha composited on white |
| GT reader | manifest, explicit word/line, purpose | raw_bbox, source/actual dimensions, polygon, class_name, difficult/truncated, issues |
| Detector | image and image_id, no labels | One validated Prediction per image, including detections=[] |
| ResizePad | scale_x/y and pad_x/y | Forward/inverse polygons without clipping or rounding |
| Evaluator | predictions, authorized GT, protocol context | Provisional eval_local_v0 metrics/diagnostics |
| Internal exporter | predictions and expected IDs/dimensions | Deterministic sorted JSONL including empty images |
| Official exporter | unresolved official specification | Fails explicitly until supplied |

image_id equals relative image_path, normalized with `/`, preserving Unicode,
case and .JPG. It is unique; repeated stems across source splits are allowed.
Manifest annotation bindings must match split, level and stem. XML filename/path
are metadata only. Absolute/traversal paths and directory symlink escapes fail;
ZIP members must be unique. No raw file is rewritten.

Prediction keys: schema_version="1.1", image_id, width, height, detections.
Each detection contains polygon x,y ordered vertices, score in [0,1], script=null
until official categories are confirmed. Unknown fields/GT in predictions fail.
Polygons must be finite, nondegenerate, simple and within image dimensions;
either winding is accepted. Bbox is derived, never independently stored.

Manifest/run context records annotation_level and coordinate_policy_id.
Synthetic geometry: continuous_zero_based_v1, pixel edges 0..width/height.
Real geometry: voc_numeric_passthrough_v0, unapproved numeric passthrough.
No silent -1, clipping, scaling or assumption of inclusive/exclusive VOC maxima.
ResizePad ratios must reflect actual rounded resized dimensions. EXIF/crop
transforms beyond resize/padding are not implemented.

Mismatch of source vs actual dimensions is an issue; source dimensions and
raw_bbox remain intact. Training/validation reject test or ineligible rows.
All known issue images are conservatively excluded from provisional splitting
even if the issue is at the other annotation level. No correction is active.

Inference manifests exclude annotation_path/yolo_path/objects/ground_truth.
MockDetector reads red synthetic rectangles, never GT, and CLI restricts it to
synthetic sources. A corrupted image aborts a run and produces no new partial
prediction file; an existing output is never silently replaced by empty data.

eval_local_v0: class-agnostic axis-aligned bbox envelopes of polygons; confidence
descending order; ties by prediction position. Each prediction matches highest
IoU unmatched GT (ties by GT position) at IoU>=0.5, configurable through API.
Duplicate detections are FP. TP/FP/FN summed across images before P/R/F1; zero
denominators return 0. Truncated regions retained. Nonzero difficult rejected
until reviewed policy. No AP/ROC/confusion matrix implemented. Metrics carry
evaluation_status=provisional, protocol_id, split_id, coordinate_policy_id and
thresholds. Only synthetic evaluation has run, not model performance.

Provisional split: ~15% of eligible train, seed=2026. No scene grouping evidence,
so image-only and explicitly not guaranteed scene-disjoint. make_split accepts
reviewed groups through Python API and keeps groups together. Real manifests,
class maps and split IDs remain private.
