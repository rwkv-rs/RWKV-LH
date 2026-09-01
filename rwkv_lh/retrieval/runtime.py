"""Product wiring for immutable per-run retrieval policy and provenance."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from rwkv_lh.harness import ActionHarness
from rwkv_lh.retrieval.actions import build_retrieval_actions
from rwkv_lh.retrieval.gateway import build_live_retrieval_backend
from rwkv_lh.retrieval.policy import EgressProvenance, NetworkPolicy, NetworkPolicyMode
from rwkv_lh.schema import GoalState


RETRIEVAL_RUNTIME_SCHEMA_VERSION = "rwkv-lh.retrieval-runtime.v1"
_SKIP_PARTS = {".git", ".hg", ".svn", "__pycache__", "node_modules"}
_SECRET_PATTERN = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(?:api[_-]?key|access[_-]?token|secret|password|passwd)\s*[:=]\s*\S+|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}|"
    r"\b(?:sk[-_]|ghp_|github_pat_)[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)


def _relative_public_path(value: str) -> str:
    text = str(value or "").replace("\\", "/").strip().strip("/")
    path = Path(text)
    if not text or path.is_absolute() or ".." in path.parts or "\x00" in text:
        raise ValueError("public workspace paths must be workspace-relative")
    return path.as_posix()


@dataclass(frozen=True)
class RetrievalRuntimeConfig:
    mode: NetworkPolicyMode = NetworkPolicyMode.OFFLINE
    explicit_approval: bool = False
    public_workspace_paths: tuple[str, ...] = ()
    schema_version: str = RETRIEVAL_RUNTIME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.mode, NetworkPolicyMode):
            object.__setattr__(self, "mode", NetworkPolicyMode(str(self.mode)))
        normalized = tuple(
            dict.fromkeys(_relative_public_path(item) for item in self.public_workspace_paths)
        )
        object.__setattr__(self, "public_workspace_paths", normalized)
        if self.mode != NetworkPolicyMode.EXPLICIT_EGRESS and self.explicit_approval:
            raise ValueError("workspace egress approval requires explicit_egress mode")
        if self.schema_version != RETRIEVAL_RUNTIME_SCHEMA_VERSION:
            raise ValueError(f"unsupported retrieval runtime schema: {self.schema_version}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode.value,
            "explicit_approval": self.explicit_approval,
            "public_workspace_paths": list(self.public_workspace_paths),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "RetrievalRuntimeConfig":
        selected = dict(value or {})
        if not selected:
            return cls()
        return cls(
            schema_version=str(
                selected.get("schema_version") or RETRIEVAL_RUNTIME_SCHEMA_VERSION
            ),
            mode=NetworkPolicyMode(str(selected.get("mode") or "offline")),
            explicit_approval=bool(selected.get("explicit_approval", False)),
            public_workspace_paths=tuple(
                str(item) for item in selected.get("public_workspace_paths") or []
            ),
        )


class WorkspaceProvenanceResolver:
    """Conservatively label outbound strings without changing model arguments."""

    def __init__(
        self,
        config: RetrievalRuntimeConfig,
        *,
        max_scan_bytes: int = 4_000_000,
        max_file_bytes: int = 1_000_000,
        untrusted_text_provider: Callable[[], Iterable[str]] | None = None,
        goal_bound: bool = False,
    ) -> None:
        self.config = config
        self.max_scan_bytes = max(0, int(max_scan_bytes))
        self.max_file_bytes = max(0, int(max_file_bytes))
        self.untrusted_text_provider = untrusted_text_provider
        self.goal_bound = bool(goal_bound)

    def _matches_untrusted_text(self, needle: str) -> bool:
        if self.untrusted_text_provider is None or len(needle.encode("utf-8")) < 3:
            return False
        try:
            values = self.untrusted_text_provider()
        except Exception:
            # Provenance uncertainty must reject at the policy boundary.
            return True
        for value in values:
            candidate = str(value or "").strip()
            if len(candidate.encode("utf-8")) < 3:
                continue
            if needle in candidate or candidate in needle:
                return True
        return False

    def _workspace_matches(
        self,
        goal: GoalState,
        needle: str,
    ) -> tuple[bool, bool, bool]:
        if len(needle.encode("utf-8")) < 3 or self.max_scan_bytes == 0:
            return False, False, False
        root = Path(goal.workspace_root).resolve()
        if not root.is_dir():
            return False, False, False
        config = retrieval_policy_from_goal(goal) if self.goal_bound else self.config
        public_roots = tuple(Path(item) for item in config.public_workspace_paths)
        public_match = False
        sensitive_match = False
        complete = True
        scanned = 0
        paths: list[Path] = []

        def traversal_error(_error: OSError) -> None:
            nonlocal complete
            complete = False

        try:
            for directory, directory_names, file_names in os.walk(
                root,
                topdown=True,
                onerror=traversal_error,
                followlinks=False,
            ):
                directory_names.sort()
                file_names.sort()
                retained_directories: list[str] = []
                for name in directory_names:
                    path = Path(directory) / name
                    try:
                        skipped = name in _SKIP_PARTS or path.is_symlink()
                    except OSError:
                        skipped = True
                    if skipped:
                        complete = False
                    else:
                        retained_directories.append(name)
                directory_names[:] = retained_directories
                paths.extend(Path(directory) / name for name in file_names)
        except OSError:
            complete = False
        needle_bytes = needle.encode("utf-8")
        for path in paths:
            try:
                is_file = path.is_file()
            except OSError:
                complete = False
                continue
            if not is_file:
                complete = False
                continue
            try:
                resolved = path.resolve()
                relative = resolved.relative_to(root)
                size = resolved.stat().st_size
            except (OSError, ValueError):
                complete = False
                continue
            if size > self.max_file_bytes or scanned + size > self.max_scan_bytes:
                complete = False
                continue
            scanned += size
            try:
                content = resolved.read_bytes()
            except OSError:
                complete = False
                continue
            if needle_bytes not in content:
                continue
            declared_public = any(
                relative == public_root or public_root in relative.parents
                for public_root in public_roots
            )
            if declared_public:
                public_match = True
            else:
                sensitive_match = True
                break
        return public_match, sensitive_match, complete

    def __call__(
        self,
        goal: GoalState,
        _tool: str,
        arguments: Mapping[str, Any],
    ) -> Mapping[str, EgressProvenance]:
        labels: dict[str, EgressProvenance] = {}
        for key, value in arguments.items():
            if not isinstance(value, str) or not value.strip():
                continue
            text = value.strip()
            if key == "operation":
                labels[key] = EgressProvenance.MODEL_PUBLIC_QUERY
                continue
            if _SECRET_PATTERN.search(text):
                labels[key] = EgressProvenance.SECRET
                continue
            # A literal supplied by the user remains user-authorized public input
            # even after the same string is echoed by an external provider. Secret
            # detection stays above this branch and therefore cannot be downgraded.
            if text in goal.request:
                labels[key] = EgressProvenance.USER_PUBLIC_LITERAL
                continue
            if self._matches_untrusted_text(text):
                labels[key] = EgressProvenance.TOOL_UNTRUSTED
                continue
            public_match, sensitive_match, complete = self._workspace_matches(
                goal,
                text,
            )
            if sensitive_match:
                labels[key] = EgressProvenance.WORKSPACE_SENSITIVE
            elif not complete:
                labels[key] = EgressProvenance.UNKNOWN
            elif public_match:
                labels[key] = EgressProvenance.WORKSPACE_PUBLIC
            else:
                labels[key] = EgressProvenance.MODEL_PUBLIC_QUERY
        return labels


def retrieval_policy_from_goal(goal: GoalState) -> RetrievalRuntimeConfig:
    value = goal.runtime_policy.get("retrieval")
    return RetrievalRuntimeConfig.from_dict(value if isinstance(value, Mapping) else None)


def network_policy_from_goal(goal: GoalState) -> NetworkPolicy:
    """Resolve the one execution policy persisted with this Goal."""

    config = retrieval_policy_from_goal(goal)
    return NetworkPolicy(
        mode=config.mode,
        explicit_approval=config.explicit_approval,
    )


def operation_allowed_by_retrieval_policy(
    goal: GoalState,
    *,
    network_access: str,
) -> bool:
    """Return whether an operation may enter this run's model-visible menu.

    Stable Selector deployments keep all class definitions registered so the
    head's class order never changes.  Registration is not authorization: an
    offline Goal must remove network classes from its eligible menu before
    selection, while the complete logits and frozen class identity remain intact.
    """

    access = str(network_access or "none").strip()
    if access == "none":
        return True
    if access not in {"public_web", "structured_source"}:
        raise ValueError(f"unsupported operation network_access: {access}")
    return retrieval_policy_from_goal(goal).mode != NetworkPolicyMode.OFFLINE


def runtime_policy_document(
    config: RetrievalRuntimeConfig,
    *,
    supervisor_mode: str = "stateful_goal",
    state_router_mode: str = "disabled",
    execution_mode: str = "bounded",
) -> dict[str, Any]:
    from rwkv_lh.state_router.shadow import shadow_policy
    from rwkv_lh.run_lifecycle import (
        RUN_LIFECYCLE_POLICY_KEY,
        run_lifecycle_policy_document,
    )

    selected_supervisor = str(supervisor_mode or "stateful_goal").strip()
    if selected_supervisor not in {"stateful_goal", "none", "contract_graph"}:
        raise ValueError(
            "supervisor mode must be stateful_goal, none, or contract_graph"
        )
    document = {
        "retrieval": config.to_dict(),
        "supervisor": {"mode": selected_supervisor},
        RUN_LIFECYCLE_POLICY_KEY: run_lifecycle_policy_document(execution_mode),
    }
    selected_router = shadow_policy(state_router_mode)
    if selected_router is not None:
        document["state_router"] = selected_router
    return document


def build_product_harness(
    *,
    config: RetrievalRuntimeConfig,
    snapshot_root: str | Path,
    sandbox_commands: bool = True,
    stable_network_menu: bool = False,
    untrusted_text_provider: Callable[[], Iterable[str]] | None = None,
) -> ActionHarness:
    backend = build_live_retrieval_backend(Path(snapshot_root))
    actions = build_retrieval_actions(
        backend=backend,
        network_policy=NetworkPolicy(
            mode=config.mode,
            explicit_approval=config.explicit_approval,
        ),
        provenance_resolver=WorkspaceProvenanceResolver(
            config,
            untrusted_text_provider=untrusted_text_provider,
            goal_bound=True,
        ),
        network_policy_resolver=network_policy_from_goal,
        connector_operations=backend.connector_operations,
        include_network_actions=stable_network_menu,
    )
    return ActionHarness(sandbox_commands=sandbox_commands, actions=actions)


__all__ = [
    "RETRIEVAL_RUNTIME_SCHEMA_VERSION",
    "RetrievalRuntimeConfig",
    "WorkspaceProvenanceResolver",
    "build_product_harness",
    "network_policy_from_goal",
    "operation_allowed_by_retrieval_policy",
    "retrieval_policy_from_goal",
    "runtime_policy_document",
]
