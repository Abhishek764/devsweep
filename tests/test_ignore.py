from __future__ import annotations

from pathlib import Path

from devsweep.ignore import _matches_one, is_ignored, load_devsweep_patterns, matches, read_patterns


def test_read_patterns_ignores_comments_and_bad_encoding(tmp_path: Path) -> None:
    path = tmp_path / ".devsweepignore"
    path.write_bytes(b"# comment\n\nfoo/**\nbar\\baz\n")
    assert read_patterns(path) == ("foo/**", "bar\\baz")
    assert read_patterns(tmp_path / "missing") == ()


def test_patterns_match_relative_paths_and_negation(tmp_path: Path) -> None:
    target = tmp_path / "packages" / "app" / "node_modules"
    target.mkdir(parents=True)
    assert matches(target, tmp_path, ("node_modules",))
    assert matches(target, tmp_path, ("packages/**",))
    assert not matches(target, tmp_path, ("packages/**", "!packages/app/node_modules"))
    assert is_ignored(target, tmp_path, ("node_modules",))
    assert not is_ignored(tmp_path, tmp_path, ("*",))
    assert not _matches_one("foo", "")
    assert not _matches_one("foo", "/")
    assert _matches_one("a/foo/bar", "foo/")
    assert _matches_one("a/b", "b")
    assert _matches_one("dist", "**/dist")
    assert _matches_one("packages/app/dist", "**/dist/")
    assert _matches_one("packages/app/dist", "packages/*/dist")


def test_load_devsweep_patterns_includes_cli_patterns(tmp_path: Path) -> None:
    (tmp_path / ".devsweepignore").write_text("one\n", encoding="utf-8")
    assert load_devsweep_patterns(tmp_path, ("two",)) == ("one", "two")
    assert not matches(tmp_path / "x", tmp_path / "other", ("x",))
    assert not matches(tmp_path / "x", tmp_path, ("# comment",))
