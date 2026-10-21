import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from src.cli import main
from src.contracts import read_jsonl
from src.submission.export import export_internal,export_official

class IntegrationTests(unittest.TestCase):
    def test_synthetic_end_to_end_and_deterministic_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'demo';main(['demo','--out',str(out)])
            metrics=json.loads((out/'metrics.json').read_text(encoding='utf8'));self.assertEqual((metrics['TP'],metrics['FP'],metrics['FN']),(2,0,0));self.assertEqual(metrics['data_status'],'synthetic_only_not_model_performance')
            records=read_jsonl(out/'predictions.jsonl');self.assertEqual(len(records),3);self.assertEqual(sum(not r['detections'] for r in records),1)
            export_internal(list(reversed(records)),{r['image_id']:(r['width'],r['height']) for r in records},out/'export2.jsonl')
            self.assertEqual((out/'internal_export.jsonl').read_bytes(),(out/'export2.jsonl').read_bytes())
            with self.assertRaises(NotImplementedError):export_official()
    def test_failure_nonzero_and_no_fake_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'demo';main(['demo','--out',str(out)])
            (out/'data/Images/synthetic/empty.JPG').write_bytes(b'corrupt')
            failed=Path(tmp)/'failed.jsonl'
            result=subprocess.run([sys.executable,'-m','src.cli','predict','--data-root',str(out/'data'),'--manifest',str(out/'data/images_manifest.jsonl'),'--out',str(failed)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(failed.exists())
