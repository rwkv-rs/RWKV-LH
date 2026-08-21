"""Context-local request metadata and request-level sampling controls."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator

from rwkv_lh.runtime.settings import get_runtime_settings


current_task_id: ContextVar[str] = ContextVar("rwkv_lh_task_id", default="UNKNOWN_TASK")
current_model_lane: ContextVar[str] = ContextVar("rwkv_lh_model_lane", default="control")
_request_temperature: ContextVar[float | None] = ContextVar(
    "rwkv_lh_request_temperature", default=None
)
_request_id: ContextVar[str] = ContextVar("rwkv_lh_request_id", default="")
_request_top_p: ContextVar[float | None] = ContextVar("rwkv_lh_request_top_p", default=None)
_request_top_k: ContextVar[int | None] = ContextVar("rwkv_lh_request_top_k", default=None)
_request_presence_penalty: ContextVar[float | None] = ContextVar(
    "rwkv_lh_request_presence_penalty", default=None
)
_request_frequency_penalty: ContextVar[float | None] = ContextVar(
    "rwkv_lh_request_frequency_penalty", default=None
)
_request_penalty_decay: ContextVar[float | None] = ContextVar(
    "rwkv_lh_request_penalty_decay", default=None
)


@dataclass(frozen=True)
class SamplingSnapshot:
    temperature: float
    top_p: float
    top_k: int
    presence_penalty: float
    frequency_penalty: float
    penalty_decay: float
    request_id: str
    task_id: str
    lane: str


def get_request_temperature() -> float:
    selected = _request_temperature.get()
    return (
        float(selected)
        if selected is not None
        else get_runtime_settings().default_temperature
    )


def get_request_seed() -> int | None:
    """Compatibility shim: vllm-rwkv rapid-sampling has no request seed."""

    return None


def get_request_id() -> str:
    return _request_id.get()


def get_request_sampling() -> SamplingSnapshot:
    settings = get_runtime_settings()
    return SamplingSnapshot(
        temperature=get_request_temperature(),
        top_p=settings.default_top_p if _request_top_p.get() is None else float(_request_top_p.get()),
        top_k=settings.default_top_k if _request_top_k.get() is None else int(_request_top_k.get()),
        presence_penalty=(
            settings.default_presence_penalty
            if _request_presence_penalty.get() is None
            else float(_request_presence_penalty.get())
        ),
        frequency_penalty=(
            settings.default_frequency_penalty
            if _request_frequency_penalty.get() is None
            else float(_request_frequency_penalty.get())
        ),
        penalty_decay=(
            settings.default_penalty_decay
            if _request_penalty_decay.get() is None
            else float(_request_penalty_decay.get())
        ),
        request_id=get_request_id(),
        task_id=current_task_id.get(),
        lane=current_model_lane.get(),
    )


def sampling_snapshot() -> SamplingSnapshot:
    return get_request_sampling()


@contextmanager
def sampling_parameters(
    temperature: float,
    *,
    seed: int | None = None,
    request_id: str = "",
    top_p: float | None = None,
    top_k: int | None = None,
    presence_penalty: float | None = None,
    frequency_penalty: float | None = None,
    penalty_decay: float | None = None,
) -> Iterator[None]:
    selected = float(temperature)
    if seed is not None:
        raise ValueError("seed is unsupported by vllm-rwkv rapid-sampling")
    if not 1e-5 <= selected <= 2:
        raise ValueError("request temperature must be between 1e-5 and 2")
    tokens = [
        (_request_temperature, _request_temperature.set(selected)),
        (_request_id, _request_id.set(str(request_id or ""))),
        (_request_top_p, _request_top_p.set(top_p)),
        (_request_top_k, _request_top_k.set(top_k)),
        (_request_presence_penalty, _request_presence_penalty.set(presence_penalty)),
        (_request_frequency_penalty, _request_frequency_penalty.set(frequency_penalty)),
        (_request_penalty_decay, _request_penalty_decay.set(penalty_decay)),
    ]
    try:
        yield
    finally:
        for variable, token in reversed(tokens):
            variable.reset(token)


@contextmanager
def model_lane(lane: str) -> Iterator[None]:
    token = current_model_lane.set(str(lane or "control").casefold())
    try:
        yield
    finally:
        current_model_lane.reset(token)


__all__ = [
    "SamplingSnapshot",
    "current_model_lane",
    "current_task_id",
    "get_request_seed",
    "get_request_id",
    "get_request_sampling",
    "get_request_temperature",
    "model_lane",
    "sampling_parameters",
    "sampling_snapshot",
]
