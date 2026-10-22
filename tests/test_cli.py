from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path

import pytest

from devsweep.cli import main


def old(path: Path) -> None:
    stamp = time.time() - 86400 * 60
    os.utime(path, (stamp, stamp))


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("devsweep.cli.load_config", lambda: {})
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk").write_bytes(b"junk")
    old(tmp_path / "package.json")
    return tmp_path


def test_scan_json_is_valid_and_clean_json_dry_run_is_valid(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scan", os.fspath(project), "--json", "--older-than", "30d"]) == 0
    scan_payload = json.loads(capsys.readouterr().out)
    assert scan_payload["items"][0]["type"] == "node_modules"
    assert main(["clean", os.fspath(project), "--json", "--older-than", "30d"]) == 0
    clean_payload = json.loads(capsys.readouterr().out)
    assert clean_payload["dry_run"] is True
    assert (project / "node_modules").exists()


def test_clean_json_yes_emits_one_document_and_removes_target(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["clean", os.fspath(project), "--json", "--yes", "--older-than", "30d"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is False
    assert payload["deleted"]
    assert not (project / "node_modules").exists()


def test_json_progress_diagnostics_stay_on_stderr(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import devsweep.cli as cli

    class TTY(io.StringIO):
        encoding = "utf-8"

        def isatty(self) -> bool:
            return True

    diagnostics = TTY()
    monkeypatch.setattr(cli.sys, "stderr", diagnostics)

    assert main(["scan", os.fspath(project), "--json", "--older-than", "30d"]) == 0

    output = capsys.readouterr().out
    assert json.loads(output)["items"]
    assert "Scanning" in diagnostics.getvalue()


def test_cli_handles_invalid_size_and_missing_root(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scan", os.fspath(project), "--min-size", "bad"]) == 2
    assert "Error:" in capsys.readouterr().err
    assert main(["scan", os.fspath(project / "missing")]) == 2
    assert main(["clean", os.fspath(project / "missing")]) == 2
