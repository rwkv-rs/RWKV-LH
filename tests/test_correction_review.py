import copy
import json
import tarfile
from pathlib import Path

import pytest

from rwkv_lh.correction_review import build_review_packet, validate_review


@pytest.fixture
def source():
    archive = Path(__file__).resolve().parents[1] / 'data/experiments/RWKV_VERIFIED_CORRECTIONS_R1_20260914/EVIDENCE.tar.gz'
    with tarfile.open(archive) as tar:
        return {name: json.load(tar.extractfile(f'candidates/{name}/REVIEW_REQUEST.json'))
                for name in ('numeric', 'execution_claim', 'effective_edit')}


def packet(source, name):
    row = source[name]
    return build_review_packet(actual_rwkv_input=row['actual_rwkv_input'], candidate=row['candidate'])


def test_real_final_and_atomic_edit_have_different_review_scope(source):
    assert packet(source, 'numeric')['review_scope'] == 'final_answer'
    p = packet(source, 'effective_edit')
    assert p['review_scope'] == 'next_action'
    assert p['candidate'] == source['effective_edit']['candidate']
    assert p['actual_rwkv_input'] == source['effective_edit']['actual_rwkv_input']


def test_old_boolean_votes_are_insufficient(source):
    with pytest.raises(ValueError, match='fields'):
        validate_review(packet(source, 'execution_claim'), {'accepted': True, 'issues': []})


def test_unsupported_fact_cannot_receive_positive_vote(source):
    p = packet(source, 'execution_claim')
    judgment = {'accepted': True, 'issues': [], 'assessment': 'Implementation gaps correctly identified.',
                'claims': [{'quote': '405 或类似', 'status': 'unsupported', 'evidence_quote': '',
                            'reason': 'No observed status supports this claim.'}]}
    with pytest.raises(ValueError, match='unsupported'):
        validate_review(p, judgment)
    judgment.update(accepted=False, issues=['Unsupported status.'])
    assert validate_review(p, judgment)['accepted'] is False


def test_citation_must_be_from_original_input_not_future_result(source):
    p = packet(source, 'execution_claim')
    judgment = {'accepted': True, 'issues': [], 'assessment': 'Reviewed.',
                'claims': [{'quote': '405 或类似', 'status': 'supported', 'evidence_quote': 'future test says 405',
                            'reason': 'A future test cannot justify prior execution.'}]}
    with pytest.raises(ValueError, match='visible input'):
        validate_review(p, judgment)


def test_final_requires_fact_audit_and_quote_in_answer(source):
    p = packet(source, 'numeric')
    j = {'accepted': True, 'issues': [], 'assessment': 'Reviewed.', 'claims': []}
    with pytest.raises(ValueError, match='claim'):
        validate_review(p, j)
    j['claims'] = [{'quote': 'invented final text', 'status': 'supported', 'evidence_quote': 'RWKV',
                    'reason': 'Invalid anchor.'}]
    with pytest.raises(ValueError, match='candidate'):
        validate_review(p, j)


def test_next_action_does_not_need_to_claim_future_test_success(source):
    p = packet(source, 'effective_edit')
    j = {'accepted': True, 'issues': [], 'assessment': 'One bounded edit; efficacy requires separate execution.',
         'claims': []}
    result = validate_review(p, j)
    assert result['accepted'] is True
    assert result['training_admitted'] is False


def test_tampered_packet_is_rejected(source):
    p = packet(source, 'numeric')
    p['actual_rwkv_input'] += 'future facts'
    with pytest.raises(ValueError, match='binding'):
        validate_review(p, {})


def test_acceptance_cannot_hide_issues(source):
    p = packet(source, 'effective_edit')
    with pytest.raises(ValueError, match='issues'):
        validate_review(p, {'accepted': True, 'issues': ['unresolved'], 'assessment': 'Review', 'claims': []})


def test_rejection_needs_concrete_issue(source):
    p = packet(source, 'effective_edit')
    with pytest.raises(ValueError, match='issues'):
        validate_review(p, {'accepted': False, 'issues': [], 'assessment': 'Review', 'claims': []})


def test_parser_never_repairs_candidate(source):
    p = source['numeric']
    with pytest.raises(ValueError):
        build_review_packet(actual_rwkv_input=p['actual_rwkv_input'], candidate=p['candidate'][:-1])
