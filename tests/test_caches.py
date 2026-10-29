from __future__ import annotations

from pathlib import Path

from devsweep.caches import cache_specs, clean_caches, existing_caches


def test_linux_cache_locations_respect_xdg_and_only_include_optional_when_requested(tmp_path: Path) -> None:
    env = {"HOME": str(tmp_path), "XDG_CACHE_HOME": str(tmp_path / "cache"), "XDG_DATA_HOME": str(tmp_path / "data")}
    normal = cache_specs(env=env, platform="linux")
    assert any(item.path == tmp_path / ".npm" / "_cacache" for item in normal)
    assert any(item.path == tmp_path / "cache" / "pip" for item in normal)
    assert not any(item.tool == "Maven" for item in normal)
    optional = cache_specs(env=env, platform="linux", include_maven=True)
    assert any(item.tool == "Maven" and item.optional for item in optional)


def test_windows_cache_locations_use_environment_variables(tmp_path: Path) -> None:
    env = {
        "USERPROFILE": str(tmp_path / "profile"),
        "LOCALAPPDATA": str(tmp_path / "local"),
        "APPDATA": str(tmp_path / "roaming"),
        "TEMP": str(tmp_path / "temp"),
    }
    specs = cache_specs(env=env, platform="win32", include_nuget=True)
    assert any(item.path == tmp_path / "local" / "npm-cache" for item in specs)
    assert any(item.path == tmp_path / "roaming" / "Code" / "Cache" for item in specs)
    assert not any(item.tool == "JetBrains" for item in specs)
    assert any(item.tool == "NuGet global packages" for item in specs)


def test_existing_and_clean_caches_only_touch_existing_known_path(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "pip"
    cache.mkdir(parents=True)
    (cache / "junk").write_bytes(b"cache")
    entries = existing_caches(env={"HOME": str(tmp_path), "XDG_CACHE_HOME": str(tmp_path / "cache")}, platform="linux")
    pip_entries = tuple(item for item in entries if item.spec.tool == "pip")
    assert pip_entries and pip_entries[0].size == 5
    dry = clean_caches(pip_entries)
    assert dry.deleted == []
    assert cache.exists()
    result = clean_caches(pip_entries, yes=True)
    assert result.failures == []
    assert result.freed_bytes == 5
    assert not cache.exists()
