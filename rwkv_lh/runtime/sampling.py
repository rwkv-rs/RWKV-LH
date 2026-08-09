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
_request_seed: ContextVar[int | None] = ContextVar("rwkv_lh_request_seed", default=None)


@dataclass(frozen=True)
class SamplingSnapshot:
    temperature: float
    seed: int | None
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
    return _request_seed.get()


def sampling_snapshot() -> SamplingSnapshot:
    return SamplingSnapshot(
        temperature=get_request_temperature(),
        seed=get_request_seed(),
        task_id=current_task_id.get(),
        lane=current_model_lane.get(),
    )


@contextmanager
def sampling_parameters(temperature: float, *, seed: int | None = None) -> Iterator[None]:
    selected = float(temperature)
    if not 0 <= selected <= 2:
        raise ValueError("request temperature must be between 0 and 2")
    temperature_token = _request_temperature.set(selected)
    seed_token = _request_seed.set(None if seed is None else int(seed))
    try:
        yield
    finally:
        _request_seed.reset(seed_token)
        _request_temperature.reset(temperature_token)


@contextmanager
def model_lane(lane: str) -> Iterator[None]:
    token = current_model_lane.set(str(lane or "control").casefold())
    try:
        yield
    finally:
        current_model_lane.reset(token)


# Compatibility aliases used by the architecture regression suite.
get_llm_temperature = get_request_temperature
get_llm_seed = get_request_seed


__all__ = [
    "SamplingSnapshot",
    "current_model_lane",
    "current_task_id",
    "get_llm_seed",
    "get_llm_temperature",
    "get_request_seed",
    "get_request_temperature",
    "model_lane",
    "sampling_parameters",
    "sampling_snapshot",
]
