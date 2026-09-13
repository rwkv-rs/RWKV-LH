"""Public behavioral test for the requested collect API; no repair implementation."""
from pathlib import Path
import runpy,tempfile,json,hashlib,sys
sys.dont_write_bytecode=True
rootdir=Path(__file__).resolve().parent
collect=runpy.run_path(str(rootdir/'document_index/documents.py'))['collect']
with tempfile.TemporaryDirectory(prefix='.public-check-',dir=rootdir) as td:
 root=Path(td);(root/'sub/deep').mkdir(parents=True)
 samples={'top.md':b'TOP','sub/nested.md':'中文 Mixed'.encode(),'sub/deep/bottom.md':b'BAD\xff'}
 for name,data in samples.items():(root/name).write_bytes(data)
 (root/'sub/ignore.txt').write_text('not markdown')
 rows=collect(root);actual=sorted(row['path'] for row in rows);expected=['bottom.md','nested.md','top.md']
 checks={'recursive_paths':actual==expected,'original_fields_and_content':all(set(r)=={'path','content','digest','search','mtime'} and any(r['content']==b.decode('utf-8',errors='replace') and r['search']==b.decode('utf-8',errors='replace').lower() and r['digest']==hashlib.sha256(b).hexdigest() for b in samples.values()) for r in rows)}
 print(json.dumps({'checks':checks,'expected_paths':expected,'actual_paths':actual,'passed':all(checks.values())},ensure_ascii=False))
 sys.exit(0 if all(checks.values()) else 1)
