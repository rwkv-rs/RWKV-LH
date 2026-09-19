"""Candidate evidence can be sealed without weakening zero-only data admission."""
import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.collection_retirement import seal_run
from rwkv_lh.direct_trace_data import replay_run

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / 'data/experiments/RWKV_UNIFIED_CORRECTION_TRAIN_R6_ONE_EPOCH_20260915/evaluation/runs/release-numbers--candidate--r1/execution'
MODEL = '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'


def profile():
    states = json.loads((TRACE / 'state_snapshot.json').read_text())['model_states']
    state = next(iter(states.values()))
    return {'id': state['state_profile_id'], 'sha256': state['state_profile_sha256']}


def test_training_default_still_rejects_nonzero_evidence():
    with pytest.raises(ValueError, match='zero|profile'):
        replay_run(TRACE, MODEL)


def test_explicit_candidate_profile_seals_real_inputs_without_relabelling(tmp_path):
    before = hashlib.sha256((TRACE / 'state_snapshot.json').read_bytes()).hexdigest()
    expected = profile()
    result = seal_run(TRACE, tmp_path / 'sealed', MODEL, expected_state_profile=expected)
    assert result['training_rows'] == 0
    assert result['state_profile'] == expected
    rows = [json.loads(line) for line in (tmp_path / 'sealed/boundaries.jsonl').read_text().splitlines()]
    assert rows and all(row['training_admitted'] is False for row in rows)
    assert all(row['source_state_profile'] == expected for row in rows)
    assert hashlib.sha256((TRACE / 'state_snapshot.json').read_bytes()).hexdigest() == before


def test_candidate_cannot_be_sealed_as_a_different_state(tmp_path):
    wrong = dict(profile(), sha256='a' * 64)
    with pytest.raises(ValueError, match='profile'):
        seal_run(TRACE, tmp_path / 'sealed', MODEL, expected_state_profile=wrong)
    assert not (tmp_path / 'sealed').exists()
