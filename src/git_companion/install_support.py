"""Register an installed private runtime without changing the caller's directory."""

import argparse
import os
import shlex
import sys
from pathlib import Path


def atomic_write(path: Path, content: str, executable: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="")
    if executable:
        temporary.chmod(0o755)
    temporary.replace(path)


def write_launcher(python: Path, bin_dir: Path, windows: bool | None = None) -> Path:
    windows = os.name == "nt" if windows is None else windows
    if windows:
        # CMD expands percent signs even inside quotes. Preserve literal path characters.
        executable = str(python).replace("%", "%%")
        content = (
            "@echo off\r\nsetlocal DisableDelayedExpansion\r\n"
            f'"{executable}" -I -m git_companion %*\r\nexit /b %errorlevel%\r\n'
        )
        launcher = bin_dir / "git-companion.cmd"
    else:
        content = f'#!/bin/sh\nexec {shlex.quote(str(python))} -I -m git_companion "$@"\n'
        launcher = bin_dir / "git-companion"
    atomic_write(launcher, content, executable=not windows)
    return launcher


def update_posix_path(home: Path, bin_dir: Path, zdotdir: Path | None = None):
    """Add a small managed PATH file and idempotent references from common shells."""
    config = home / ".config" / "git-companion" / "path.sh"
    quoted_bin = shlex.quote(str(bin_dir))
    atomic_write(
        config,
        (
            "# Added by Git Companion setup.\n"
            f"case :${{PATH-}}: in\n  *:{quoted_bin}:*) ;;\n"
            f'  *) export PATH={quoted_bin}:"${{PATH-}}" ;;\nesac\n'
        ),
    )
    source = f". {shlex.quote(str(config))} # git-companion PATH"
    zhome = zdotdir or home
    files = {home / ".profile", home / ".bashrc", zhome / ".zprofile", zhome / ".zshrc"}
    # Creating .bash_profile would stop Bash from reading an existing .profile or .bash_login.
    files.update(path for path in (home / ".bash_profile", home / ".bash_login") if path.exists())
    for path in files:
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        # Preserve existing configuration verbatim; append only our own exact line.
        if source not in existing.splitlines():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="") as handle:
                handle.write(("" if not existing or existing.endswith("\n") else "\n") + source + "\n")
    fish_bin = str(bin_dir).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    atomic_write(
        home / ".config" / "fish" / "conf.d" / "git-companion.fish",
        f'# Added by Git Companion setup.\nfish_add_path --global --path "{fish_bin}"\n',
    )


def update_windows_path(bin_dir: Path):
    import ctypes
    import winreg
    from ctypes import wintypes

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            current, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current, kind = "", winreg.REG_EXPAND_SZ
        normalized = os.path.normcase(os.path.normpath(str(bin_dir)))
        paths = current.split(";")
        if not any(
            os.path.normcase(os.path.normpath(os.path.expandvars(p))) == normalized for p in paths if p
        ):
            winreg.SetValueEx(
                key, "Path", 0, kind, current.rstrip(";") + (";" if current else "") + str(bin_dir)
            )
    # Notify Explorer and other listening processes; existing terminal processes retain their old PATH.
    result = ctypes.c_size_t()
    notify = ctypes.windll.user32.SendMessageTimeoutW
    notify.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPCWSTR,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    notify.restype = wintypes.LPARAM
    notify(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, ctypes.byref(result))


def main():
    parser = argparse.ArgumentParser(description="Internal setup helper")
    parser.add_argument("--bin", required=True, type=Path)
    parser.add_argument("--no-path", action="store_true", help="Do not edit shell or registry settings")
    args = parser.parse_args()
    # A POSIX venv's python is often a symlink. Resolving it would bypass that venv.
    launcher = write_launcher(Path(sys.executable).absolute(), args.bin.resolve())
    if not args.no_path:
        if os.name == "nt":
            update_windows_path(args.bin.resolve())
        else:
            zdotdir = os.environ.get("ZDOTDIR")
            update_posix_path(
                Path.home(), args.bin.resolve(), Path(zdotdir).expanduser() if zdotdir else None
            )
    print(f"Installed command: {launcher}")


if __name__ == "__main__":
    main()
