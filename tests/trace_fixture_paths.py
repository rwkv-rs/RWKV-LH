"""Resolve archived fixture workspaces locally without changing trace bytes."""
from dataclasses import replace

from rwkv_lh.harness import ActionHarness


def use_fixture_workspace(monkeypatch, workspace):
    original = ActionHarness.workspace_manifest

    def manifest(self, goal, **kwargs):
        return original(self, replace(goal, workspace_root=str(workspace)), **kwargs)

    monkeypatch.setattr(ActionHarness, 'workspace_manifest', manifest)
