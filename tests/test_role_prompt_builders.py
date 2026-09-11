from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_state_protocols import auditor_final, auditor_step_v7, finalizer_answer
from rwkv_lh.goal_state_protocols import executor_args_v7
from rwkv_lh.model import LongHorizonModel, ModelProtocolError
from rwkv_lh.harness import ActionHarness
from rwkv_lh.token_budget import get_token_count


_BASELINE = (
    Path(__file__).resolve().parents[1]
    / 'data/test_fixtures/controller_role_closure_v1/role_prompt_wire_baseline.json'
)
_PROTOCOLS = {
    'auditor_step_v7': auditor_step_v7,
    'auditor_final': auditor_final,
    'finalizer_answer': finalizer_answer,
}


@pytest.mark.parametrize('protocol_name', tuple(_PROTOCOLS))
def test_role_builder_preserves_registered_prompt_bytes(protocol_name: str) -> None:
    baseline = json.loads(_BASELINE.read_text(encoding='utf-8'))
    record = next(item for item in baseline['records'] if item['protocol'] == protocol_name)
    protocol = _PROTOCOLS[protocol_name]
    source = protocol.build_prompt_source(**record['arguments'])
    assert protocol.render_prompt(source) == record['prompt']
    assert protocol.render_prompt(source).startswith(protocol.PROMPT_PREFIX)


@pytest.mark.parametrize('protocol_name', ('auditor_step_v7', 'auditor_final'))
def test_auditor_builder_owns_catalog_construction(
    protocol_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = json.loads(_BASELINE.read_text(encoding='utf-8'))
    record = next(item for item in baseline['records'] if item['protocol'] == protocol_name)
    protocol = _PROTOCOLS[protocol_name]
    calls = []
    original = protocol.build_gap_catalog

    def record_catalog(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(protocol, 'build_gap_catalog', record_catalog)
    source = protocol.build_prompt_source(**record['arguments'])
    assert calls
    assert source['gap_catalog'] == original(*calls[0])
    assert protocol.render_prompt(source) == record['prompt']


def test_independent_selector_cannot_use_generic_terminal_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = object.__new__(LongHorizonModel)
    model.tool_selector = object()

    def checkpoint_must_not_run(*args):
        raise AssertionError('generic terminal path reached the model session')

    monkeypatch.setattr(model, '_checkpoint', checkpoint_must_not_run)
    with pytest.raises(ModelProtocolError, match='dedicated Finalizer'):
        model.terminal_answer(None, None, event=None)


def test_executor_budget_uses_current_source_and_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = object.__new__(LongHorizonModel)
    model.tool_selector = object()
    definition = next(
        item for item in ActionHarness().g1i_tool_definitions()
        if item['name'] == 'read_file'
    )
    model._action_definitions = [definition]
    model._definitions_by_name = {'read_file': definition}
    state = SimpleNamespace(model_events={}, actions={}, goal=SimpleNamespace(request='Read README.md'))
    checkpoint = SimpleNamespace(event_ids=())
    monkeypatch.setattr(LongHorizonModel, '_bound_executor_fact_records', lambda *args, **kwargs: ())
    target = executor_args_v7.build_target_contract(
        phase='observe',
        roots=['README.md'],
        target_descriptors=[
            {'path': 'README.md', 'type': 'file', 'target_kind': 'text_file', 'exists': True}
        ],
        operations=("read_file",),
    )
    execution = executor_args_v7.build_execution_state(
        active_step_id='S1',
        active_step_revision=1,
        declared_phase='observe',
        effective_phase='observe',
        assigned_actions=[],
        mechanical_evidence={'missing_read_roots': ['README.md'], 'missing_write_roots': []},
        target_contract=target,
    )
    rendered = []
    original = executor_args_v7.render_generation_prompt

    def capture(source):
        value = original(source)
        rendered.append((source, value))
        return value

    monkeypatch.setattr(executor_args_v7, 'render_generation_prompt', capture)
    budget = model._max_disclosure_tokens_for_state(
        state, checkpoint,
        current_requirement='Read the exact current README contents.',
        fact_action_ids=(),
        execution_state=execution,
        eligible_operations=('read_file',),
    )
    assert len(rendered) == 1
    source, prompt = rendered[0]
    assert source['current_requirement'] == 'Read the exact current README contents.'
    assert source['execution_state'] == execution
    assert source['committed_fact_refs'] == []
    assert budget == get_token_count('\n\n' + prompt)
