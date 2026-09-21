from pathlib import Path
import json, subprocess, sys, tempfile, unittest
SCRIPT = Path(__file__).resolve().parent / 'timebook.py'
class OffsetTests(unittest.TestCase):
    def test_offset_validation_and_existing_add(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / 'time.sqlite'
            def invoke(ident, offset):
                return subprocess.run([sys.executable, str(SCRIPT), 'add', str(db), '--id', ident, '--project', 'team', '--start', '2024-02-29T08:00:00' + offset, '--end', '2024-02-29T09:00:00' + offset], capture_output=True, text=True, timeout=10)
            for n, offset in enumerate(('Z', '+00:00', '+08:00', '-08:00', '+05:30')):
                with self.subTest(valid=offset):
                    first = invoke('valid-' + str(n), offset)
                    self.assertEqual(first.returncode, 0, first.stderr)
                    self.assertEqual(json.loads(first.stdout), {'inserted': 1, 'duplicates': 0})
                    second = invoke('valid-' + str(n), offset)
                    self.assertEqual(second.returncode, 0, second.stderr)
                    self.assertEqual(json.loads(second.stdout), {'inserted': 0, 'duplicates': 1})
            for n, offset in enumerate(('+00:60', '+00:99', '-00:60', '+24:00', '+99:00')):
                with self.subTest(invalid=offset):
                    bad = invoke('bad-' + str(n), offset)
                    self.assertNotEqual(bad.returncode, 0, bad.stdout)
                    self.assertTrue(bad.stderr.strip())
if __name__ == '__main__': unittest.main()
