from __future__ import annotations

import io
from pathlib import Path

from devsweep.config import config_path, load_config
from devsweep.docker import docker_cleanup
from devsweep.output import Colors, relative_age, render_table, write_line


def test_output_disables_color_for_non_tty_and_handles_tables() -> None:
    stream = io.StringIO()
    colors = Colors(stream)
    assert not colors.enabled
    assert colors.heading("Title") == "Title"
    assert "A" in render_table(("A", "B"), (("1", "2"),))
    assert relative_age(0) == "unknown"
    assert relative_age(1_000_000, now=1_000_001) == "just now"
    write_line(stream, "hello")
    assert stream.getvalue().endswith("hello\n")


def test_config_path_and_toml_are_optional(tmp_path: Path) -> None:
    env = {"XDG_CONFIG_HOME": str(tmp_path)}
    path = config_path(env=env, platform="linux")
    assert path == tmp_path / "devsweep" / "config.toml"
    path.parent.mkdir()
    path.write_text('older_than = "7d"\n', encoding="utf-8")
    assert load_config(env=env, platform="linux")["older_than"] == "7d"


def test_docker_missing_is_friendly(monkeypatch) -> None:
    monkeypatch.setattr("devsweep.docker.shutil.which", lambda command: None)
    result = docker_cleanup()
    assert result.status == "missing"
    assert result.failures == []
