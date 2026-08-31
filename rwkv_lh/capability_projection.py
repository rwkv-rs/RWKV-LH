"""Deterministic Contract Graph v3 capability projection.

The strong Planner authors an atom kind, effect ceiling, evidence needs and
workspace scopes.  It never names a concrete Harness operation.  This module
mechanically projects the authoritative ActionDefinition metadata into the
operation menu from which RWKV makes the actual selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CAPABILITY_PROJECTION_VERSION = "controller_capability_projection.v3"
LEGACY_CAPABILITY_PROJECTION_VERSIONS = frozenset(
    {
        "controller_capability_projection.v1",
        "controller_capability_projection.v2",
    }
)
SUPPORTED_CAPABILITY_PROJECTION_VERSIONS = frozenset(
    {CAPABILITY_PROJECTION_VERSION, *LEGACY_CAPABILITY_PROJECTION_VERSIONS}
)


class AtomKind(str, Enum):
    INVESTIGATE = "investigate"
    MUTATE = "mutate"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"


class EffectCeiling(str, Enum):
    LOCAL_READ_ONLY = "local_read_only"
    PUBLIC_READ_ONLY = "public_read_only"
    WORKSPACE_MUTATION = "workspace_mutation"
    LOCAL_PROCESS_READ_ONLY = "local_process_read_only"
    LOCAL_PROCESS_MUTATION = "local_process_mutation"


@dataclass(frozen=True)
class CapabilityProjection:
    atom_kind: AtomKind
    effect_ceiling: EffectCeiling
    operations: tuple[str, ...]
    exclusive: bool
    minimum_actions: int
    source: str = CAPABILITY_PROJECTION_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.source,
            "atom_kind": self.atom_kind.value,
            "effect_ceiling": self.effect_ceiling.value,
            "operations": list(self.operations),
            "exclusive": self.exclusive,
            "minimum_actions": self.minimum_actions,
        }


def _normalized_catalog(
    operation_catalog: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    entries: list[dict[str, Any]] = []
    names: set[str] = set()
    required = {
        "name",
        "capability_class",
        "network_access",
        "side_effect_class",
        "scope_mode",
    }
    for index, item in enumerate(operation_catalog):
        if not isinstance(item, Mapping):
            raise ValueError(f"operation_catalog[{index}] must be an object")
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(
                f"operation_catalog[{index}] lacks authoritative metadata: {missing}"
            )
        selected = {key: str(item.get(key) or "").strip() for key in required}
        if any(not selected[key] for key in required):
            raise ValueError(
                f"operation_catalog[{index}] has empty authoritative metadata"
            )
        name = selected["name"]
        if name in names:
            raise ValueError(f"operation catalog contains duplicate action {name}")
        names.add(name)
        entries.append({**dict(item), **selected})
    if not entries:
        raise ValueError("capability projection requires a non-empty operation catalog")
    return tuple(entries)


def _validate_kind_ceiling(kind: AtomKind, ceiling: EffectCeiling, role: str) -> None:
    selected_role = str(role or "").strip()
    if selected_role not in {"work", "finalizer"}:
        raise ValueError(f"unsupported atom role: {selected_role}")
    if selected_role == "finalizer":
        if kind != AtomKind.SYNTHESIZE:
            raise ValueError("a finalizer atom must use kind=synthesize")
        if ceiling != EffectCeiling.LOCAL_READ_ONLY:
            raise ValueError("a finalizer atom must use local_read_only")
        return
    allowed: dict[AtomKind, set[EffectCeiling]] = {
        AtomKind.INVESTIGATE: {
            EffectCeiling.LOCAL_READ_ONLY,
            EffectCeiling.PUBLIC_READ_ONLY,
            EffectCeiling.LOCAL_PROCESS_READ_ONLY,
        },
        AtomKind.MUTATE: {
            EffectCeiling.WORKSPACE_MUTATION,
            EffectCeiling.LOCAL_PROCESS_MUTATION,
        },
        AtomKind.VERIFY: {
            EffectCeiling.LOCAL_READ_ONLY,
            EffectCeiling.PUBLIC_READ_ONLY,
            EffectCeiling.LOCAL_PROCESS_READ_ONLY,
        },
        AtomKind.SYNTHESIZE: {EffectCeiling.LOCAL_READ_ONLY},
    }
    if ceiling not in allowed[kind]:
        raise ValueError(
            f"atom kind {kind.value} cannot request effect ceiling {ceiling.value}"
        )


def project_contract_capabilities(
    *,
    atom_kind: AtomKind | str,
    effect_ceiling: EffectCeiling | str,
    role: str,
    operation_catalog: Sequence[Mapping[str, Any]],
    write_roots: Sequence[str] = (),
    evidence_kinds: Sequence[str] = (),
    source_preferences: Sequence[str] = (),
) -> CapabilityProjection:
    """Project one Planner-authored semantic atom to an RWKV operation menu."""

    kind = atom_kind if isinstance(atom_kind, AtomKind) else AtomKind(str(atom_kind))
    ceiling = (
        effect_ceiling
        if isinstance(effect_ceiling, EffectCeiling)
        else EffectCeiling(str(effect_ceiling))
    )
    _validate_kind_ceiling(kind, ceiling, role)
    catalog = _normalized_catalog(operation_catalog)

    def applicable(item: Mapping[str, Any]) -> bool:
        capability = str(item["capability_class"])
        network = str(item["network_access"])
        effect = str(item["side_effect_class"])
        local_read = capability == "local.workspace_read" and network == "none"
        deterministic = capability.startswith("deterministic.") and network == "none"
        workspace_mutation = (
            capability == "local.workspace_mutation"
            and effect == "workspace_mutation"
            and network == "none"
        )
        process_read = capability == "local.process_read" and network == "none"
        process_mutation = (
            capability == "local.process_mutation" and network == "none"
        )
        public_external = (
            network in {"public_web", "structured_source"}
            and effect == "external_read_only"
        )

        if str(role) == "finalizer":
            return local_read
        # For v2 read-only work, the Planner ceilings effects, not information
        # source. If network actions survived system policy and registration,
        # RWKV alone chooses local, deterministic, web, or structured evidence.
        # The old local/public names remain wire-compatible but no longer let the
        # Planner make the browse decision indirectly.
        if ceiling in {
            EffectCeiling.LOCAL_READ_ONLY,
            EffectCeiling.PUBLIC_READ_ONLY,
        }:
            return local_read or deterministic or public_external
        if ceiling == EffectCeiling.WORKSPACE_MUTATION:
            return local_read or deterministic or workspace_mutation
        if ceiling == EffectCeiling.LOCAL_PROCESS_READ_ONLY:
            return local_read or deterministic or public_external or process_read
        if ceiling == EffectCeiling.LOCAL_PROCESS_MUTATION:
            return (
                local_read
                or deterministic
                or workspace_mutation
                or process_read
                or process_mutation
            )
        return False

    applicable_entries = [item for item in catalog if applicable(item)]
    hints = " ".join(
        str(item or "").strip().casefold().replace("-", "_").replace(" ", "_")
        for item in (*evidence_kinds, *source_preferences)
    )

    def rank(item: Mapping[str, Any], index: int) -> tuple[int, int, int]:
        capability = str(item["capability_class"])
        network = str(item["network_access"])
        name = str(item["name"])
        external = network in {"public_web", "structured_source"}
        deterministic = capability.startswith("deterministic.")
        if ceiling == EffectCeiling.PUBLIC_READ_ONLY:
            group = 0 if external else 1 if deterministic else 2
        else:
            group = 0 if not external and not deterministic else 1 if deterministic else 2

        hint_rank = 0
        if "structured_registry" in hints and network == "structured_source":
            hint_rank = -20
        elif "public_web" in hints and network == "public_web":
            hint_rank = -20
        elif "workspace_directory" in hints and name == "list_directory":
            hint_rank = -20
        elif "workspace_file" in hints:
            hint_rank = {
                "read_file": -20,
                "read_json": -19,
                "file_digest": -18,
                "bind_evidence": -17,
            }.get(name, 0)
        elif "deterministic_compute" in hints and deterministic:
            hint_rank = -20
        return group, hint_rank, index

    applicable_entries = [
        item
        for _, item in sorted(
            enumerate(applicable_entries),
            key=lambda pair: rank(pair[1], pair[0]),
        )
    ]
    operations = tuple(str(item["name"]) for item in applicable_entries)
    if not operations:
        raise ValueError(
            f"capability projection produced no operations for {kind.value}/"
            f"{ceiling.value}"
        )
    exclusive = "." in {str(item or "").strip() for item in write_roots} or any(
        str(item["name"]) in operations
        and str(item["scope_mode"]) == "exclusive_side_effect"
        for item in catalog
    )
    minimum_actions = 1
    if kind == AtomKind.MUTATE and write_roots:
        # Every non-overlapping declared write root needs a direct mutation
        # opportunity.  The action budget is validated later when the
        # SupervisorAtom is constructed, so an infeasible Planner patch fails
        # closed before any RWKV request is made.
        minimum_actions = len(tuple(write_roots))
    return CapabilityProjection(
        atom_kind=kind,
        effect_ceiling=ceiling,
        operations=operations,
        exclusive=exclusive,
        # A finalizer's candidate becomes the exact user-visible answer.  It
        # therefore needs at least one current-workspace observation just like
        # every other evidence-producing atom; a zero-action Final is an
        # ungrounded model assertion, not committed evidence.
        minimum_actions=minimum_actions,
    )


__all__ = [
    "AtomKind",
    "CAPABILITY_PROJECTION_VERSION",
    "LEGACY_CAPABILITY_PROJECTION_VERSIONS",
    "CapabilityProjection",
    "EffectCeiling",
    "SUPPORTED_CAPABILITY_PROJECTION_VERSIONS",
    "project_contract_capabilities",
]
