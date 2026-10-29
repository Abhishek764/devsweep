from __future__ import annotations

from types import SimpleNamespace

import devsweep.updater as updater


def test_uv_update_is_deferred_when_the_running_tool_needs_replacement(
    monkeypatch,
) -> None:
    command = ["uv", "tool", "install", "--force", "--upgrade", updater.REPOSITORY]
    monkeypatch.setattr(updater, "_commands", lambda: [command])
    monkeypatch.setattr(updater, "_schedule_uv_update", lambda value: value == command)

    called = False

    def run(*_args, **_kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(returncode=1)

    assert updater.update(run=run) == "uv (scheduled after exit)"
    assert called is False
