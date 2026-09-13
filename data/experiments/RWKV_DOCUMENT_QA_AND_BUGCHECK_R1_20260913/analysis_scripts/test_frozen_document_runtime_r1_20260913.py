import sys
from pathlib import Path
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/source'))
import rwkv_lh.read_only_agent
import pytest
raise SystemExit(pytest.main(['-q',str(R/'tests/test_read_only_agent.py')]))
