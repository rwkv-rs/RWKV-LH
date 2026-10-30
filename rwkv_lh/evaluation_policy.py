"""Permanent evaluation exclusion, shared by admission and future source filters.

Absence of an exclusion is never production authorization. Keep the directory
marker with every evaluation source, reference, and run; preserve these fields
when exporting metadata. Copies that discard provenance cannot be authorized by
this check and still require the sealed production provenance audits.
"""
from pathlib import Path

MARKER = '.rwkv-evaluation-only.json'
SCHEMA = 'rwkv-lh.evaluation-exclusion.v1'
USAGE_POLICY = 'evaluation_only_never_train'


def evaluation_metadata(suite_id):
    if not isinstance(suite_id, str) or not suite_id.strip():
        raise ValueError('evaluation suite identity required')
    return {'schema_version': SCHEMA, 'suite_id': suite_id,
            'evaluation_only': True, 'training_eligible': False,
            'usage_policy': USAGE_POLICY}


def assert_training_record_allowed(record):
    """A negative label is binding even when external acceptance passed."""
    if (record.get('evaluation_only') is True
            or record.get('usage_policy') == USAGE_POLICY
            or record.get('training_eligible') is False):
        raise ValueError('evaluation-only or explicitly ineligible record cannot enter training')


def assert_training_source_allowed(path):
    """Reject marked ancestors through both lexical and resolved paths.

    Marker presence is sufficient: a malformed or symlinked marker cannot make
    an evaluation tree eligible. No contents are read from protected trees.
    """
    path = Path(path).absolute()
    for candidate in (path, path.resolve()):
        for parent in (candidate, *candidate.parents):
            marker = parent / MARKER
            if marker.exists() or marker.is_symlink():
                raise ValueError('evaluation-only source cannot enter training: ' + str(path))
