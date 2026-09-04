"""Repository-wide pytest isolation from deployment-local RWKV services."""

from __future__ import annotations

import pytest

from rwkv_lh.runtime.settings import get_runtime_settings


@pytest.fixture(autouse=True)
def bounded_prompt_replay_test_ablation(monkeypatch: pytest.MonkeyPatch):
    """Keep structural unit tests independent of the live native-state server.

    Individual native-state tests inject ``RuntimeSettings`` explicitly.  The
    remaining suite is a bounded/offline ablation and must not acquire a live
    service merely by constructing a model schema.  Production defaults and
    Goal-mode controller construction remain ``native_required``.
    """

    # Unit tests must not depend on an ignored deployment-local .env.local.
    # Tests that exercise missing/conflicting identities delete or replace this
    # value explicitly.
    monkeypatch.setenv("RWKV_MODEL", "rwkv-test")
    monkeypatch.setenv("RWKV_LH_EXECUTOR_MODEL", "rwkv-test")
    monkeypatch.setenv("RWKV_STATE_TRANSPORT", "prompt_replay")
    monkeypatch.setenv("RWKV_LH_EXECUTOR_STATE_TRANSPORT", "prompt_replay")
    get_runtime_settings.cache_clear()
    try:
        yield
    finally:
        get_runtime_settings.cache_clear()
