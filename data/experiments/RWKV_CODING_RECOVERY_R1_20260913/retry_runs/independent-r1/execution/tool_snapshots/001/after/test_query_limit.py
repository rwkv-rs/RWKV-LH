import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from document_index.query import query
ROOT=Path(__file__).resolve().parent
class LimitTests(unittest.TestCase):
    def test_query_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); docs=p/'docs'; docs.mkdir(); db=p/'index.db'
            for name in ('c.md','a.md','b.md'):
                (docs/name).write_text('hello world')
            def cli(*args):
                return subprocess.run([sys.executable,'-B',str(ROOT/'index_cli.py'),*args],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli('sync','--root',str(docs),'--db',str(db)).returncode,0)
            full={'count':3,'matches':[{'path':n} for n in ('a.md','b.md','c.md')]}
            self.assertEqual(query(db,'hello'),full)
            self.assertEqual(json.loads(cli('query','--db',str(db),'--text','hello').stdout),full)
            for limit in (1,2,5):
                expected={'count':min(limit,3),'matches':full['matches'][:limit]}
                self.assertEqual(query(db,'hello',limit=limit),expected)
                result=cli('query','--db',str(db),'--text','hello','--limit',str(limit))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),expected)
            self.assertEqual(query(db,'absent',limit=1),{'count':0,'matches':[]})
            for invalid in (0,-1):
                with self.assertRaises(ValueError): query(db,'hello',limit=invalid)
                self.assertNotEqual(cli('query','--db',str(db),'--text','hello','--limit',str(invalid)).returncode,0)
if __name__=='__main__': unittest.main()
