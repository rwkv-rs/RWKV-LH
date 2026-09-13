from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913')
for name in ['numeric_relation-advised-r2','remaining_status_code-advised-r2']:
 print(name);print(json.loads((D/'runs'/name/'execution/RESULT.json').read_text())['final'])
