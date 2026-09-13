"""Retrieval-kernel contracts and optional Harness action extensions.

This package does not contain an Agent loop.  RWKV-LH remains the only
planner/action/final authority; retrieval is an execution capability selected
through the normal ActionDefinition registry.
"""

from rwkv_lh.retrieval.actions import (
    FrozenRetrievalBackend,
    RetrievalBackend,
    build_retrieval_actions,
)
from rwkv_lh.retrieval.contracts import (
    EXTERNAL_EVIDENCE_SCHEMA_VERSION,
    EvidenceRecord,
    EvidenceSpan,
    ExternalEvidenceEnvelope,
    ExternalEvidenceRequestMismatch,
    SourceObject,
    external_evidence_request_digest,
    validate_external_evidence_request,
)
from rwkv_lh.retrieval.policy import (
    EgressProvenance,
    NetworkPolicy,
    NetworkPolicyDecision,
    NetworkPolicyMode,
)
from rwkv_lh.retrieval.gateway import (
    LiveRetrievalBackend,
    build_live_retrieval_backend,
)
from rwkv_lh.retrieval.projections import fold_retrieval_ledger
from rwkv_lh.retrieval.snapshot import SnapshotStore, SourceSnapshot
from rwkv_lh.retrieval.runtime import (
    RetrievalRuntimeConfig,
    WorkspaceProvenanceResolver,
    build_product_harness,
    network_policy_from_goal,
    operation_allowed_by_retrieval_policy,
    retrieval_policy_from_goal,
    runtime_policy_document,
)

__all__ = [
    "EXTERNAL_EVIDENCE_SCHEMA_VERSION",
    "EgressProvenance",
    "EvidenceRecord",
    "EvidenceSpan",
    "ExternalEvidenceEnvelope",
    "ExternalEvidenceRequestMismatch",
    "FrozenRetrievalBackend",
    "LiveRetrievalBackend",
    "NetworkPolicy",
    "NetworkPolicyDecision",
    "NetworkPolicyMode",
    "RetrievalBackend",
    "RetrievalRuntimeConfig",
    "SnapshotStore",
    "SourceSnapshot",
    "SourceObject",
    "WorkspaceProvenanceResolver",
    "build_product_harness",
    "build_retrieval_actions",
    "build_live_retrieval_backend",
    "external_evidence_request_digest",
    "fold_retrieval_ledger",
    "network_policy_from_goal",
    "operation_allowed_by_retrieval_policy",
    "retrieval_policy_from_goal",
    "runtime_policy_document",
    "validate_external_evidence_request",
]
