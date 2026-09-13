"""Request one optional diagnosis of an existing answer; never replace that answer."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rwkv_lh.runtime.settings import load_local_env
from rwkv_lh.schema import RunState
from rwkv_lh.summary_advice import build_advice_request, request_advice
from rwkv_lh.supervisor_openai import SupervisorAPISettings, OpenAICompatibleSupervisorClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--file', action='append', required=True, help='explicit visible file relative to the parent workspace')
    parser.add_argument('--output', type=Path, required=True, help='new advice receipt directory')
    parser.add_argument('--max-tokens', type=int, default=4096)
    args = parser.parse_args()
    if args.max_tokens < 1:
        parser.error('positive token budget required')
    load_local_env(Path(__file__).resolve().parents[1] / '.env.local')
    state = RunState.from_dict(json.loads((args.parent / 'state_snapshot.json').read_text()))
    result_bytes = (args.parent / 'RESULT.json').read_bytes()
    result = json.loads(result_bytes)
    workspace = Path(state.goal.workspace_root).resolve()
    files = {}
    for name in args.file:
        path = (workspace / name).resolve(strict=True)
        if not path.is_relative_to(workspace):
            parser.error('advice files must be inside the task workspace')
        files[name] = path.read_text()
    output = args.output.resolve()
    if output == workspace or workspace in output.parents:
        parser.error('advice evidence must stay outside the model workspace')
    output.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    payload = build_advice_request(state.goal, files, result.get('final') or '')
    save('INPUT.json', payload)
    settings = replace(SupervisorAPISettings.from_env(), retry_attempts=1,
        semantic_repair_attempts=0, fallback_models=(), plan_cache_enabled=False, read_timeout_seconds=180)
    def audit(event):
        with (output / 'strong_trace.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event), ensure_ascii=False) + '\n')
    client = OpenAICompatibleSupervisorClient(settings=settings, audit_hook=audit)
    try:
        advice = request_advice(client, state.goal, files, result.get('final') or '', result['id'], args.max_tokens)
        save('ADVICE.json', {'model': settings.model, 'advice': advice,
            'parent_result_sha256': hashlib.sha256(result_bytes).hexdigest(),
            'source_sha256': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}})
    except Exception as exc:
        save('ERROR.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
    finally:
        client.close()
    print(str(output / 'ADVICE.json'))


if __name__ == '__main__':
    main()
