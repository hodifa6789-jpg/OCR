# Audit tools

Use the bundled audit runtime or an isolated Python with Pillow installed. No packages were installed for this round. Run from project root:

1. python tools/audit_dataset.py --archive <LOCAL_ARCHIVE_PATH>
2. python tools/supplemental_checks.py
3. python tools/build_reports.py
4. python tools/finalize_reports.py

The first tool accepts a path. Supplemental checks currently use the original supplied archive path; change that local configuration when moving this audit workspace. The report generator intentionally describes this audit, not an arbitrary future dataset. Do not use unchanged narrative for new data. Inventory and checkpoints remain private. A checkpoint identity mismatch halts reuse; start a separate output workspace for another dataset. Each processed file is flushed; a truncated final checkpoint line is ignored when reading, but should be reviewed before resuming. No extraction, training, or raw upload is performed.

Actual runtime: Python 3.12.14, Pillow 12.3.0. build_reports.py compares every image pair using 64-bit dHash and validates pairing, dimensions, normalized YOLO geometry and aggregate coverage. Private supplemental_checks.json records the one dimension mismatch and actual-image bounds check. finalize_reports.py uses an explicit four-file allowlist and checks basic personal path markers before packing. An independent final content scan also checked actual class strings were absent from the four files.
