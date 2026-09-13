from pathlib import Path
import json,shutil,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
reg=json.loads((D/'REGISTRATION.json').read_text())
for rel,sha in reg['source_pins'].items():
    src=R/rel;assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
    dst=D/'source'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
