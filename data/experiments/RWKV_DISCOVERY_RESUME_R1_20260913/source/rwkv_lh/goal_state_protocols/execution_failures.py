"""Shared durable action rejection facts; no planning or completion authority."""
from collections.abc import Mapping, Sequence
from copy import deepcopy

from rwkv_lh.goal_state_protocols import _exact_fields, _nonempty, _nonnegative_int

FIELDS = ("event_id", "selection_id", "step_id", "step_revision", "selected_operation",
          "rejected_arguments", "error_kind", "error", "action_executed")


def validate_rejections(value):
    if not isinstance(value, list):
        raise ValueError("recent_rejections must be an array")
    identifiers = set()
    for item in value:
        record = _exact_fields(item, FIELDS, "action rejection")
        for name in ("event_id", "selection_id", "step_id", "selected_operation", "error"):
            _nonempty(record[name], name)
        if _nonnegative_int(record["step_revision"], "step_revision") < 1:
            raise ValueError("rejection must bind a positive step revision")
        if not isinstance(record["rejected_arguments"], Mapping) or not isinstance(record["error_kind"], str):
            raise ValueError("invalid rejection arguments or error kind")
        if record["event_id"] in identifiers or record["action_executed"] is not False:
            raise ValueError("rejection is duplicated or claims an executed action")
        identifiers.add(record["event_id"])
    return value


def build_rejections(records: Sequence[Mapping]) -> list[dict]:
    result = [deepcopy(dict(record)) for record in records]
    validate_rejections(result)
    return result
