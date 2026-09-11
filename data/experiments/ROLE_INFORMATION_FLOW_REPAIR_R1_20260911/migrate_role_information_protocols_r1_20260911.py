"""Replace current role modules and their live callers, never historical runs."""
from pathlib import Path

root=Path('/home/chase/GitHub/RWKV-LH')
changes={
    'selector_intent_v6':'selector_intent_v7', 'executor_args_v6':'executor_args_v7',
    'auditor_step_v6':'auditor_step_v7', 'selector-intent-menu.v6':'selector-intent-menu.v7',
    'selector-intent.v6':'selector-intent.v7', 'selector-intent-v6':'selector-intent-v7',
    'executor-args.v6':'executor-args.v7', 'auditor-step.v6':'auditor-step.v7',
    'finalizer-answer.v2':'finalizer-answer.v3','auditor-final.v4':'auditor-final.v5',
    'FinalizerAnswerPromptV2':'FinalizerAnswerPromptV3','AuditorFinalPromptV4':'AuditorFinalPromptV5',
    'ExecutorArgsPromptV6':'ExecutorArgsPromptV7','AuditorStepPromptV6':'AuditorStepPromptV7',
    'SelectorIntentPromptV6':'SelectorIntentPromptV7','SelectorIntentMenuV6':'SelectorIntentMenuV7',
    'SelectorIntentRoleV6':'SelectorIntentRoleV7','SelectorIntentV6':'SelectorIntentV7',
}
for folder in ('rwkv_lh','tests','scripts','data/test_fixtures'):
    for path in (root/folder).rglob('*'):
        if not path.is_file() or path.suffix not in {'.py','.json'}:
            continue
        text=path.read_text()
        new=text
        for old,replacement in changes.items():
            new=new.replace(old,replacement)
        if new!=text:
            path.write_text(new)
for stem in ('selector_intent','executor_args','auditor_step'):
    (root/f'rwkv_lh/goal_state_protocols/{stem}_v6.py').rename(root/f'rwkv_lh/goal_state_protocols/{stem}_v7.py')
for path in (root/'rwkv_lh').rglob('*.pyc'):
    if any(stem+'_v6' in path.name for stem in ('selector_intent','executor_args','auditor_step')):
        path.unlink()
