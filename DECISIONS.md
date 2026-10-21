# Decision register — 2026-10-19

| ID | Decision | Status/evidence |
|---|---|---|
| D01 | Word initial target, line explicit alternative | Phase 1 inventory and phase 2 plan; no implicit mixing |
| D02 | XML raw fields; check YOLO classes independently | class_mapping_summary; global mapping is NOT one-to-one |
| D03 | Numeric VOC passthrough under named policy | Provisional; edge convention unresolved |
| D04 | No rescale/clip/class remap | Dimension mismatch and class anomalies await review |
| D05 | Exclude six known train issue images from provisional pool | Not deletion/correction; cross-level conservative exclusion |
| D06 | Test quarantined | Its provided labels inspected for quality/mapping only |
| D07 | Seed 2026, ~15% image-only validation | Scene grouping/leakage unresolved |
| D08 | Stable CLASS_1..3 aliases inherited | True names private; README gives no class definitions |
| D09 | IoU .5 one-to-one score-first bbox evaluation | Engineering eval_local_v0, not official |
| D10 | MockDetector synthetic red rectangles | No learned model/performance claims |
| D11 | Overlays are preparation only | Every review record pending_human_review, reviewer blank |
| D12 | Project venv shares existing runtime packages read-only | ensurepip failed; --without-pip --system-site-packages; not a training environment |
| D13 | Agreement statements in plan are supplied context | Local DOCX not supplied/read in this round; no independent legal verification |

Open: SYPHAXAR vs ACIT-C edition and test use; official script target/classes;
class ID inconsistencies; VOC edges; evaluator/ignore rules; official export;
weights/data licenses, signatures and cutoff timezone. No organizer message sent.
No framework installation, GPU tensor execution, training, true resource/model
benchmark, official metrics or second-member execution performed.
