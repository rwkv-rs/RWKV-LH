"""Configuration used by the Project Planner's official DeepSeek transport."""
from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import math
from pathlib import Path

from . import deepseek_api
from .runtime.role_config import role_bool, role_env, role_float, role_int
from .runtime.settings import DEFAULT_ENV_FILE, load_local_env


@dataclass(frozen=True)
class ProjectPlannerSettings:
    base_url: str
    api_key: str
    model: str
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 240.0
    retry_attempts: int = 1
    retry_backoff_seconds: float = 0.5
    verify_tls: bool = True
    max_plan_tokens: int = 8192
    serialize_requests: bool = False
    request_lock_path: str = '/tmp/rwkv-lh-project-planner.lock'
    circuit_breaker_failures: int = 2
    circuit_breaker_cooldown_seconds: float = 30.0
    backend_profile: str = deepseek_api.BACKEND_PROFILE
    stream_responses: bool = False
    planner_request_options: Mapping = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.planner_request_options, Mapping):
            raise ValueError('Planner request options must be a JSON object')
        options = deepseek_api.request_options(dict(self.planner_request_options))
        object.__setattr__(self, 'planner_request_options', options)

    @classmethod
    def from_env(cls, path=DEFAULT_ENV_FILE):
        load_local_env(path, allowed_prefixes=('RWKV_LH_PLANNER_',))
        if role_env('planner', 'fallback_models'):
            raise ValueError('Planner automatic model fallback is unsupported')
        try:
            options = json.loads(role_env('planner', 'request_options', default='{}'))
        except ValueError as exc:
            raise ValueError('Planner request options must be a JSON object') from exc
        settings = cls(
            base_url=role_env('planner', 'base_url').rstrip('/'),
            api_key=role_env('planner', 'api_key'), model=role_env('planner', 'model'),
            backend_profile=role_env('planner', 'backend_profile', default=deepseek_api.BACKEND_PROFILE),
            planner_request_options=options,
            stream_responses=role_bool('planner', 'stream', default=False),
            connect_timeout_seconds=role_float('planner', 'connect_timeout', default=10.0),
            read_timeout_seconds=role_float('planner', 'read_timeout', default=240.0),
            retry_attempts=role_int('planner', 'retry_attempts', default=1),
            retry_backoff_seconds=role_float('planner', 'retry_backoff', default=0.5),
            verify_tls=role_bool('planner', 'verify_tls', default=True),
            max_plan_tokens=role_int('planner', 'max_plan_tokens', default=8192),
            serialize_requests=role_bool('planner', 'serialize_requests', default=False),
            request_lock_path=role_env('planner', 'request_lock_path',
                default='/tmp/rwkv-lh-project-planner.lock'),
            circuit_breaker_failures=role_int('planner', 'circuit_breaker_failures', default=2),
            circuit_breaker_cooldown_seconds=role_float('planner', 'circuit_breaker_cooldown', default=30.0),
        )
        settings.validate()
        return settings

    def validate(self):
        if self.backend_profile != deepseek_api.BACKEND_PROFILE:
            raise ValueError('Project Planner requires the official DeepSeek backend')
        deepseek_api.endpoint(self.base_url)
        deepseek_api.request_options(dict(self.planner_request_options))
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError('RWKV_LH_PLANNER_API_KEY must be configured')
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError('RWKV_LH_PLANNER_MODEL must be configured')
        if self.verify_tls is not True:
            raise ValueError('official DeepSeek requires TLS verification')
        if type(self.stream_responses) is not bool or type(self.serialize_requests) is not bool:
            raise ValueError('Planner stream and serialization settings must be boolean')
        for name in ('connect_timeout_seconds', 'read_timeout_seconds'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('Planner timeouts must be finite and positive')
        if type(self.retry_attempts) is not int or not 1 <= self.retry_attempts <= 5:
            raise ValueError('Planner retry attempts must be between 1 and 5')
        if type(self.max_plan_tokens) is not int or self.max_plan_tokens < 256:
            raise ValueError('Planner output token budget must be at least 256')
        if type(self.circuit_breaker_failures) is not int or not 1 <= self.circuit_breaker_failures <= 10:
            raise ValueError('Planner circuit breaker failures must be between 1 and 10')
        for name in ('retry_backoff_seconds', 'circuit_breaker_cooldown_seconds'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('Planner backoff and cooldown must be finite and nonnegative')
        if self.serialize_requests and not Path(self.request_lock_path).is_absolute():
            raise ValueError('Planner request lock path must be absolute')
