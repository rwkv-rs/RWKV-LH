"""Training labels must follow the wire format shown in production inputs."""
import json
from pathlib import Path

import pytest

from rwkv_lh import model_io
from rwkv_lh.direct_trace_data import normalize_direct_row
from rwkv_lh.token_budget import tokenizer


@pytest.fixture
def executed_read_row():
    path = Path(__file__).resolve().parents[1] / 'data/test_fixtures/source_bound_regressions/executed_read_row.jsonl'
    return next(row for line in path.read_text().splitlines()
                if (row := json.loads(line))['label_authority'] == 'executed_read')


@pytest.mark.parametrize('wire', [False, True])
def test_training_requires_documented_envelope_without_changing_live_parser(executed_read_row, wire):
    row = executed_read_row
    stop = model_io.JSON_CALL_STOP_SUFFIXES[0]
    command = model_io.parse_model_command(row['target_text'][:-len(stop)])
    payload = command.to_wire_dict() if wire else command.to_dict()
    target = json.dumps(payload, ensure_ascii=False) + stop
    row.update(target_text=target, target_token_ids=tokenizer().encode(target))
    # Compatibility on the execution transport is deliberately distinct from
    # teaching a model to disobey the format specified in its own input.
    assert model_io.parse_model_command(target[:-len(stop)]) == command
    args = dict(model_sha256=row['model_sha256'], context_tokens=24576,
                vocab_size=65536, bos_token_id=0)
    if wire:
        assert normalize_direct_row(row, **args)['target_token_ids'] == row['target_token_ids']
    else:
        with pytest.raises(ValueError, match='training target.*function/params'):
            normalize_direct_row(row, **args)
