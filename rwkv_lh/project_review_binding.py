"""Reconstructed review subjects; integrity is not semantic or training admission."""
import json
from pathlib import Path

from .harness import ActionHarness
from .model_io import parse_model_command
from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_output_validation import validate_role_output
from .project_role_data import file_sha
from .project_runtime import role_definitions
from .project_trace import role_boundaries


def build_subject(source, registration, operation_id, target):
    """Bind a proposed correction to an actual returned current-role boundary.

    The registration is recorded, not authenticated as prior authorization.
    No dataset eligibility or reviewer independence is inferred here.
    """
    registration = Path(registration)
    registration_sha = file_sha(registration)
    provenance = json.loads(registration.read_text())
    purpose = provenance.get('source_purpose')
    if not isinstance(purpose, str) or not purpose.strip():
        raise ValueError('explicit source purpose required')
    with ProjectLedger.read_snapshot(source) as ledger:
        return _build_locked(ledger, registration, registration_sha, purpose, operation_id, target)


def _build_locked(ledger, registration, registration_sha, purpose, operation_id, target):
    source = ledger.root
    tip = ledger.verified_events()[-1]['digest']
    rows = [r for r in role_boundaries(source) if r['operation_id'] == operation_id]
    if len(rows) != 1 or rows[0]['role'] not in ('decision', 'executor'):
        raise ValueError('one returned Decision/Executor boundary required')
    row = rows[0]
    if not isinstance(target, dict) or set(target) != {'function', 'params'}:
        raise ValueError('exact target call envelope required')
    # Serialize first so caller mutation cannot modify the frozen subject.
    target = json.loads(json.dumps(target, allow_nan=False))
    validate_role_output(row['role'], row['input'], parse_model_command(json.dumps(target)),
                         role_definitions(row['role'], ActionHarness()))
    if ledger.verified_events()[-1]['digest'] != tip or file_sha(registration) != registration_sha:
        raise ValueError('source changed during review reconstruction')
    return {
        'schema': 'rwkv-lh.project-review-subject.v1',
        'operation_id': operation_id, 'role': row['role'],
        'source_chain_tip': tip, 'source_event_digest': row['source_event_digest'],
        'result_event_digest': row['result_event_digest'],
        'registration_sha256': registration_sha, 'source_purpose': purpose,
        'input_protocol': row['input_protocol'], 'input_digest': digest(row['input']),
        'original_result_digest': digest(row['result']),
        'checkpoint_digest': digest(row['checkpoint']),
        'target': target, 'target_digest': digest(target),
        'training_eligible': False,
    }


def validate_binding(subject, review):
    """Check recorded identity separation and integrity, not trusted identity.

    Callers must freshly rebuild the subject from its ledger before checking.
    Author/reviewer names are declarations; formal admission must authenticate
    them and verify semantic evidence independently.
    """
    if subject.get('schema') != 'rwkv-lh.project-review-subject.v1' or subject.get('training_eligible') is not False:
        raise ValueError('non-admitting review subject required')
    if review.get('subject_digest') != digest(subject) or subject.get('target_digest') != digest(subject.get('target')):
        raise ValueError('review subject differs')
    identities = [review.get('author_id'), review.get('reviewer_id')]
    if any(not isinstance(value, str) or not value.strip() for value in identities):
        raise ValueError('distinct author/reviewer identities required')
    if identities[0].strip() == identities[1].strip():
        raise ValueError('distinct author/reviewer identities required')
    if review.get('verdict') != 'accept' or review.get('issues') != []:
        raise ValueError('accepted review without unresolved issues required')
