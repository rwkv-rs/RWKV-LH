"""Coding job data shared by the agent entry points and batch runs."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CodingJob:
    task_id: str
    request: str
    source_workspace: str
    output_dir: str
    max_calls: int | None = 12
    max_seconds: float | None = 600
    record_generation_snapshots: bool = field(default=False, kw_only=True)
    writable_paths: tuple[str, ...] = field(default=('.',), kw_only=True)
    protected_paths: tuple[str, ...] = field(default=(), kw_only=True)
    rejection_limit: int = field(default=3, kw_only=True)
