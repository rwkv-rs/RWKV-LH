"""Keep the published read contract aligned with actual byte/token semantics."""
from pathlib import Path
import json

import pytest

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel, ModelProtocolError
from rwkv_lh.schema import TaskAction
from test_unified_controller import build

FAILURES = json.loads(
    (Path(__file__).parent / 'fixtures/read_file_parameter_failures_r3.json').read_text()
)
FAILURES += json.loads(
    (Path(__file__).parent / 'fixtures/read_file_parameter_failures_r4.json').read_text()
)


@pytest.mark.parametrize('failure', FAILURES, ids=['end-byte-first', 'end-byte-second', 'byte-line-limits', 'code-regression', 'missing-regression'])
def test_real_read_parameter_failures_remain_rejected_with_explicit_prompt_contract(tmp_path, failure):
    controller, store, workspace, client, model = build(tmp_path, [failure['raw_output']])
    (workspace / 'README.md').write_text('Reading evidence.\n')
    state = store.load('RUN')
    with pytest.raises(ModelProtocolError, match='unknown arguments'):
        model.next_command(state, controller._persist_callback)
    assert not state.actions
    assert len(client.prompts) == 1
    assert failure['raw_output'] in [d.raw_output for d in state.decisions.values()]
    definition = next(d for d in model.direct_definitions() if d['name'] == 'read_file')
    parameters = definition['parameters']
    assert parameters['required'] == ['path']
    assert parameters['additionalProperties'] is False
    assert set(parameters['properties']) == {'path', 'start_byte', 'max_tokens'}
    # These are missing semantic clauses, not new accepted fields or defaults.
    assert 'caller supplies no ending position' in definition['description']
    assert 'end_byte' not in definition['description']
    assert 'not a byte or line limit' in parameters['properties']['max_tokens']['description']
    assert 'Optional; omitted means 0' in parameters['properties']['start_byte']['description']
    assert 'inclusive' in parameters['properties']['start_byte']['description']
    assert 'caller supplies no ending position' in client.prompts[0]
    assert 'not a byte or line limit' in client.prompts[0]


def test_published_read_defaults_and_half_open_utf8_range_match_harness(tmp_path):
    harness = ActionHarness()
    content = '你abc\n'
    (tmp_path / 'sample.txt').write_text(content, encoding='utf-8')
    goal = LongHorizonModel.create_literal_goal('Read sample.txt', str(tmp_path))
    default = harness.normalize_action(TaskAction('read_file', {'path': 'sample.txt'}))
    assert default.arguments == {'path': 'sample.txt', 'start_byte': 0, 'max_tokens': 4096}
    result = harness.execute(TaskAction('read_file', {'path': 'sample.txt', 'start_byte': 3}), goal)
    assert result.success
    assert result.output.encode() == content.encode()[3:result.metadata['end_byte']]
    assert result.metadata['end_byte'] == len(content.encode())
    assert result.metadata['next_start_byte'] is None
    eof = harness.execute(TaskAction('read_file', {'path': 'sample.txt', 'start_byte': len(content.encode())}), goal)
    assert eof.success and eof.output == ''
    for offset in (1, len(content.encode()) + 1):
        invalid = harness.execute(TaskAction('read_file', {'path': 'sample.txt', 'start_byte': offset}), goal)
        assert not invalid.success
