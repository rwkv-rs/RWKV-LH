"""Coding job data shared by Project entrypoints and offline collection."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CodingJob:
    task_id: str
    request: str
    source_workspace: str
    output_dir: str
    max_calls: int = 12
    max_seconds: float = 600
    record_generation_snapshots: bool = field(default=False, kw_only=True)
    protected_paths: tuple[str, ...] = field(default=(), kw_only=True)
    unit_calls: int | None = field(default=None, kw_only=True)
    unit_seconds: float | None = field(default=None, kw_only=True)
    require_initial_plan: bool = field(default=False, kw_only=True)
