"""Private collection contracts; artifact checks never rewrite model answers."""
import hashlib
import json
from pathlib import Path
from .stdio_verifier import validate_stdio_cases, verify_python_submission


def load_contract(item):
    raw = Path(item['acceptance_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['acceptance_sha256']:
        raise ValueError('acceptance changed after freeze')
    contract = json.loads(raw)
    kind = contract.get('kind')
    if kind == 'manual_rubric':
        rubric = contract.get('criteria')
        if not isinstance(rubric, list) or not rubric or any(not isinstance(x, str) or not x.strip() for x in rubric):
            raise ValueError('nonempty frozen manual criteria required')
    elif kind == 'stdio_exact':
        validate_stdio_cases(contract['cases'])
        if contract.get('comparison') != 'exact_rstrip':
            raise ValueError('explicit exact_rstrip applicability required')
    else:
        raise ValueError('unsupported external acceptance contract')
    return contract


def evaluate_artifact(item, result):
    contract = load_contract(item)
    if contract['kind'] == 'manual_rubric':
        return {'status': 'pending_manual_review', 'contract_sha256': item['acceptance_sha256']}
    if item['job']['tool_scope'] != 'coding':
        raise ValueError('stdio verification requires a coding workspace')
    workspace = Path(item['job']['output_dir']) / 'workspace'
    if not workspace.is_dir():
        return {'status': 'unreviewable', 'reason': 'no_workspace'}
    checked = verify_python_submission(workspace, contract['cases'])
    return {'status': 'passed' if checked['passed'] else 'failed',
            'scope': 'artifact_only', 'contract_sha256': item['acceptance_sha256'], 'details': checked}
