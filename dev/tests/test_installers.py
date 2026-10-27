import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from dev.tools.build_installers import build
from git_companion import install_support
from git_companion.install_support import update_posix_path, update_windows_path, write_launcher


def test_three_setup_files_embed_the_app_and_verified_downloads(tmp_path):
    wheel = tmp_path / "git_companion_cli-0.1.0-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("git_companion_cli-0.1.0.dist-info/METADATA", "Version: 0.1.0\n")
        archive.writestr("git_companion/install_support.py", "# helper\n")
    paths = build(wheel, tmp_path / "out")
    assert {p.name for p in paths} == {"setup-windows.cmd", "setup-macos.command", "setup-linux.sh"}
    manifest = json.loads((paths[0].parent / "manifest.json").read_text())
    for path in paths:
        content = path.read_text()
        assert "@WHEEL_" not in content and "@UV_" not in content
        match = re.search(
            r"^# WHEEL_PAYLOAD_START\n(.*?)^# WHEEL_PAYLOAD_END", content, re.MULTILINE | re.DOTALL
        )
        payload = "".join(line[2:] for line in match[1].splitlines())
        assert base64.b64decode(payload) == wheel.read_bytes()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["setups"][path.name]
        assert "UV_PYTHON_PREFERENCE" in content and "https://pypi.org/simple" in content
        assert "UV_PYTHON_DOWNLOADS" in content
        assert "Close and reopen your terminal" in content
        assert "checksum verification failed" in content


def test_posix_path_registration_preserves_configuration_and_is_idempotent(tmp_path):
    home = tmp_path / "user's home"
    home.mkdir()
    (home / ".profile").write_text("export ORIGINAL=keep")
    zhome = home / "zsh config"
    bin_dir = home / "local bin"
    update_posix_path(home, bin_dir, zhome)
    first = (home / ".profile").read_text()
    update_posix_path(home, bin_dir, zhome)
    assert (home / ".profile").read_text() == first
    assert first.startswith("export ORIGINAL=keep\n")
    assert first.count("# git-companion PATH") == 1
    assert not (home / ".bash_profile").exists()  # do not shadow .profile
    assert "# git-companion PATH" in (zhome / ".zshrc").read_text()
    assert "fish_add_path" in (home / ".config/fish/conf.d/git-companion.fish").read_text()


def test_launchers_preserve_cwd_and_forward_arguments(tmp_path):
    python = sys.executable
    launcher = write_launcher(Path(python), tmp_path / "bin with spaces")
    project = tmp_path / "some other project"
    project.mkdir()
    shadow = project / "git_companion"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise RuntimeError('project package shadowed the app')\n")
    args = [str(launcher), "--version"]
    if os.name == "nt":
        args = ["cmd.exe", "/d", "/c", *args]
    completed = subprocess.run(args, cwd=project, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert "git-companion 0.1.0" in completed.stdout
    assert "cd " not in launcher.read_text()
    assert "%*" in launcher.read_text() if os.name == "nt" else '"$@"' in launcher.read_text()


def test_windows_launcher_escapes_percent_in_installation_path(tmp_path):
    path = write_launcher(Path("C:/user%data%/python.exe"), tmp_path, windows=True)
    assert "user%%data%%" in path.read_text()
    assert "DisableDelayedExpansion" in path.read_text()


def test_windows_path_registration_preserves_entries_and_does_not_duplicate(tmp_path, monkeypatch):
    import ctypes

    registry = {"value": "existing-one;existing-two", "kind": 2}

    def set_value(key, name, reserved, kind, value):
        registry.update(value=value, kind=kind)

    fake_registry = SimpleNamespace(
        HKEY_CURRENT_USER=1,
        REG_EXPAND_SZ=2,
        CreateKey=lambda *args: nullcontext("key"),
        QueryValueEx=lambda *args: (registry["value"], registry["kind"]),
        SetValueEx=set_value,
    )
    monkeypatch.setitem(sys.modules, "winreg", fake_registry)
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(user32=SimpleNamespace(SendMessageTimeoutW=lambda *args: 1)),
        raising=False,
    )
    bin_dir = tmp_path / "command bin"
    update_windows_path(bin_dir)
    update_windows_path(bin_dir)
    assert registry["value"] == "existing-one;existing-two;" + str(bin_dir)
    assert registry["kind"] == 2


@pytest.mark.skipif(os.name == "nt", reason="POSIX virtualenv symlinks")
def test_setup_keeps_virtualenv_symlink_in_launcher(tmp_path, monkeypatch):
    target = tmp_path / "system-python"
    target.touch()
    python = tmp_path / "private-env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(target)
    bin_dir = tmp_path / "command-bin"
    monkeypatch.setattr(sys, "executable", str(python))
    monkeypatch.setattr(sys, "argv", ["setup-helper", "--bin", str(bin_dir), "--no-path"])
    install_support.main()
    launcher = (bin_dir / "git-companion").read_text()
    assert str(python) in launcher and str(target) not in launcher
