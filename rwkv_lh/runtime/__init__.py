"""Public model-runtime boundary for RWKV-LH."""

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.protocol import (
    CompletionResponse,
    HealthStatus,
    RWKVHTTPError,
    RWKVOutcomeUnknownError,
    RWKVProtocolError,
    RWKVRuntimeError,
    RWKVTransportError,
    RuntimeCapabilities,
)
from rwkv_lh.runtime.native_state import (
    NATIVE_STATE_PROTOCOL_VERSION,
    NativeRWKVStateClient,
    NativeStateCandidate,
    NativeStateSnapshot,
)
from rwkv_lh.runtime.sampling import (
    current_model_lane,
    current_task_id,
    get_request_seed,
    get_request_id,
    get_request_sampling,
    get_request_temperature,
    sampling_parameters,
)
from rwkv_lh.runtime.settings import RuntimeSettings, get_runtime_settings
from rwkv_lh.runtime.executor_profiles import (
    EXECUTOR_PROFILE_ROUTING_DISABLED,
    EXECUTOR_PROFILE_ROUTING_V1,
    ExecutorProfileBinding,
    executor_profile_binding_for_run,
)


__all__ = [
    "CompletionResponse",
    "EXECUTOR_PROFILE_ROUTING_DISABLED",
    "EXECUTOR_PROFILE_ROUTING_V1",
    "ExecutorProfileBinding",
    "HealthStatus",
    "OpenAICompatibleRWKVClient",
    "RWKVHTTPError",
    "RWKVOutcomeUnknownError",
    "RWKVProtocolError",
    "RWKVRuntimeError",
    "RWKVTransportError",
    "RuntimeCapabilities",
    "NATIVE_STATE_PROTOCOL_VERSION",
    "NativeRWKVStateClient",
    "NativeStateCandidate",
    "NativeStateSnapshot",
    "RuntimeSettings",
    "current_model_lane",
    "current_task_id",
    "get_request_seed",
    "get_request_id",
    "get_request_sampling",
    "get_request_temperature",
    "get_runtime_settings",
    "executor_profile_binding_for_run",
    "sampling_parameters",
]
