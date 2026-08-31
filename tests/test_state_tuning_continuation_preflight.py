from __future__ import annotations

import pytest

from scripts.prepare_remote_rwkv_lh_state_tuning_continuation import (
    validate_training_commands,
)


def row(function: str) -> dict[str, str]:
    prompt = "User: task\nAssistant: ```json\n"
    target = f'{{"function":"{function}","params":{{}}}}'
    return {"prompt": prompt, "target": target, "text": prompt + target}


def test_continuation_preflight_accepts_selector_and_direct_tool_targets() -> None:
    validate_training_commands(
        [row("select_tool"), row("read_json"), row("final_answer")], 3
    )


@pytest.mark.parametrize(
    "invalid",
    [
        {"prompt": "p", "target": "", "text": "p"},
        {"prompt": "p", "target": "not-json", "text": "pnot-json"},
        {"prompt": "p", "target": "{}", "text": "p{}"},
        {"prompt": "p", "target": '{"function":"read_file"}', "text": 'p{"function":"read_file"}'},
    ],
)
def test_continuation_preflight_rejects_malformed_commands(invalid: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        validate_training_commands([invalid], 1)
