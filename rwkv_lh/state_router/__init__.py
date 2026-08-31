"""Advisory RWKV State Router contracts and local inference components."""

from rwkv_lh.state_router.model import (
    HiddenFeatureExtractor,
    HiddenFeatures,
    MultiHeadMLPArtifact,
    StateRouter,
)
from rwkv_lh.state_router.local_backend import (
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.protocol import (
    AbstainThresholds,
    ContextMode,
    EvidenceState,
    ExecutionPhase,
    NetworkRecommendation,
    PolicyState,
    RouteFamily,
    RouterInput,
    RouterOutput,
    resolve_router_output,
)
from rwkv_lh.state_router.wkv_projection import ProjectedWKVExtractor
from rwkv_lh.state_router.shadow import (
    LocalShadowObserver,
    ShadowController,
    read_shadow_records,
    shadow_enabled,
    shadow_policy,
    wrap_controller_for_shadow,
)

__all__ = [
    "AbstainThresholds",
    "ContextMode",
    "EvidenceState",
    "ExecutionPhase",
    "HiddenFeatureExtractor",
    "HiddenFeatures",
    "LocalVLLMRWKVExtractor",
    "LocalVLLMRWKVSettings",
    "LocalShadowObserver",
    "MultiHeadMLPArtifact",
    "NetworkRecommendation",
    "PolicyState",
    "ProjectedWKVExtractor",
    "RouteFamily",
    "RouterInput",
    "RouterOutput",
    "StateRouter",
    "ShadowController",
    "read_shadow_records",
    "resolve_router_output",
    "shadow_enabled",
    "shadow_policy",
    "wrap_controller_for_shadow",
]
