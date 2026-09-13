from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913')
for p in sorted((D/'advice').glob('*/ADVICE.json')):
 print(p.parent.name);print(json.loads(p.read_text())['advice'])
