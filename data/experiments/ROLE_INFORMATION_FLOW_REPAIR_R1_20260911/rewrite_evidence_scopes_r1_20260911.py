"""Mechanical source edits for the registered evidence-flow repair."""
from pathlib import Path

root=Path('/home/chase/GitHub/RWKV-LH')
p=root/'rwkv_lh/stateful_goal_loop.py'
s=p.read_text()
start=s.index('        """Keep the latest boundary',s.index('    def _step_audit_evidence_refs('))
end=s.index('    @classmethod\n    def _step_mechanical_evidence_coverage',start)
s=s[:start]+'''        """Retain cumulative current-step and declared-dependency evidence."""
        return goal_step_evidence_action_ids(state, step_id, step_revision)

'''+s[end:]
start=s.index('        """Return only current-step',s.index('    def _step_executor_fact_action_ids('))
end=s.index('    def _goal_step_operations(',start)
s=s[:start]+'''        """Share the exact responsibility scope with Selector and Step Auditor."""
        return goal_step_evidence_action_ids(state, step_id, step_revision)

'''+s[end:]
p.write_text(s)
p=root/'rwkv_lh/model.py'
s=p.read_text()
start=s.index('        checkpoint: ModelCheckpoint | None = None',s.index('    def _start_clean_executor_turn('))
end=s.index('        checkpoint = self._bind_executor_fact_scope(',start)
s=s[:start]+'''        retained_fact_action_ids = self._bounded_assignment_action_ids(
            state, recent_limit=None, action_ids=fact_action_ids,
        )
        # All facts requested by the responsibility boundary are mandatory.
        # The model's input budget can interrupt this turn, never erase evidence.
        checkpoint = self.session.prepare_bootstrap(
            ModelLaneKind.ACTION,
            self._assignment(state, recent_limit=None, executor_only=True,
                action_ids=fact_action_ids, focus_text=focus_text),
            self._menu_definitions, lane_id=self.ACTION_LANE_ID, event_ids=(),
            progressive_tool_disclosure=True, independent_tool_selector=True,
        )
'''+s[end:]
s=s.replace('"causal_fact_recent_limit": selected_recent_limit,','"causal_fact_complete": True,')
s=s.replace('                "input_budget_fallback_used": bool(budget_fallbacks),\n                "input_budget_fallbacks": budget_fallbacks,\n','')
# Uncap the current independent Executor's cache reconstruction as well.
start=s.index('        last_budget_error: Exception | None = None',s.index('    def _rebuild_native_executor_cache('))
end=s.index('    def _record_role_fact(',start)
old=s[start:end]
body=old[old.index('            state.model_states[rebuilt.checkpoint_id]'):old.index('        raise InputBudgetError(')]
body='\n'.join(line[4:] if line.startswith('    ') else line for line in body.splitlines())+'\n\n'
s=s[:start]+'''        rebuilt = self.session.bootstrap(
            ModelLaneKind.ACTION,
            self._assignment(state, recent_limit=None,
                executor_only=self.tool_selector is not None),
            definitions, lane_id=self.ACTION_LANE_ID, event_ids=(),
            progressive_tool_disclosure=self._progressive_tool_disclosure,
            independent_tool_selector=self.tool_selector is not None,
        )
'''+body+s[end:]
s=s.replace('    _EXECUTOR_CAUSAL_FACT_LIMITS = (12, 8, 4, 2, 0)\n','')
s=s.replace('        recent_limit: int,','        recent_limit: int | None,')
s=s.replace('        limit = max(0, int(recent_limit))\n        if not limit:\n','        limit = None if recent_limit is None else max(0, int(recent_limit))\n        if limit == 0:\n')
s=s.replace('        )[-limit:]\n        return tuple(action.action_id for action in actions)','        )\n        if limit is not None:\n            actions = actions[-limit:]\n        return tuple(action.action_id for action in actions)')
# Generic legacy replay still supports its own reductions; independent roles
# must not fall back to an incomplete fresh assignment even on prompt_replay.
s=s.replace('        for recent_limit in (12, 8, 4, 2, 0):','        for recent_limit in ((None,) if self.tool_selector is not None else (12, 8, 4, 2, 0)):')
s=s.replace('                if recent_limit == 0:\n                    raise','                if recent_limit is None or recent_limit == 0:\n                    raise')
p.write_text(s)
# Fixtures must stop overwriting the caller-supplied diagnostic prose.
p=root/'tests/test_stateful_goal_loop.py'
s=p.read_text()
start=s.index('    if step_id and verdict in',s.index('def _audit_call('))
end=s.index('        if verdict == "repair" and gaps',start)
s=s[:start]+'    if not step_id and verdict in {"ready_for_final", "repair"}:\n'+s[end:]
s=s.replace('progress["completion_preconditions_satisfied"]','progress["mechanical_preconditions_satisfied"]')
p.write_text(s)
for p in (root/'tests').glob('*.py'):
    s=p.read_text()
    s=s.replace('auditor_step_v7.REASON_INCOMPLETE','"The current step still lacks the required evidence."')
    s=s.replace('step_protocol.REASON_INCOMPLETE','"The current step still lacks the required evidence."')
    p.write_text(s)
