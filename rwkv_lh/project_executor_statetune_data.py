"""Executor StateTune row adapter; admission requires a separate verified freeze."""
from . import statetune_core as core
from .project_protocols import executor
from .project_statetune_data import _normalize_project_row

ROLE = 'project_executor'
ROW_SCHEMA = 'rwkv-lh.project-executor-training-row.v1'


def protocol_identity():
    return executor.PROTOCOL, core.sha256_file(executor.__file__)


def normalize_row(row, *, model_sha256, context_tokens, vocab_size, bos_token_id, expected_split='train'):
    return _normalize_project_row(row, role=ROLE, row_schema=ROW_SCHEMA, protocol=protocol_identity(),
                                  model_sha256=model_sha256, context_tokens=context_tokens,
                                  vocab_size=vocab_size, bos_token_id=bos_token_id, expected_split=expected_split)
