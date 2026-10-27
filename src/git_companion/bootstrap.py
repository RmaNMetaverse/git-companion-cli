"""OS-aware installation plans and post-install binary discovery."""

import os
import platform
import shutil
from collections.abc import Callable
from pathlib import Path

from .engine import Runner, capture, display_command


def refresh_path():
    additions = []
    if os.name == "nt":
        try:
            import winreg

            for hive, key in (
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                (winreg.HKEY_CURRENT_USER, "Environment"),
            ):
                try:
                    with winreg.OpenKey(hive, key) as handle:
                        additions += os.path.expandvars(winreg.QueryValueEx(handle, "Path")[0]).split(";")
                except OSError:
                    pass
        except ImportError:
            pass
        for base in (os.getenv("ProgramFiles"), os.getenv("LOCALAPPDATA")):
            if base:
                additions += [
                    str(Path(base) / "Git" / "cmd"),
                    str(Path(base) / "Programs" / "Git" / "cmd"),
                    str(Path(base) / "Git LFS"),
                ]
    else:
        additions += ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"]
    os.environ["PATH"] = os.pathsep.join(
        dict.fromkeys(os.environ.get("PATH", "").split(os.pathsep) + additions)
    )


def install_plan(
    system: str, packages: list[str], which: Callable = shutil.which, root: bool = False
) -> list[list[str]]:
    if not packages:
        return []
    if system == "Windows" and which("winget"):
        ids = {"git": "Git.Git", "git-lfs": "GitHub.GitLFS"}
        return [
            [
                "winget",
                "install",
                "--id",
                ids[p],
                "--exact",
                "--source",
                "winget",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--disable-interactivity",
            ]
            for p in packages
        ]
    if system == "Darwin":
        if which("brew"):
            return [["brew", "install", *packages]]
        if which("port"):
            prefix = [] if root else ["sudo", "-n"]
            return [[*prefix, "port", "install", *packages]]
        raise RuntimeError(
            "Install Homebrew from https://brew.sh, then restart Git Companion. Alternatively install Git and Git LFS manually."
        )
    if system == "Linux":
        prefix = [] if root else ["sudo", "-n"]
        if not root and not which("sudo"):
            raise RuntimeError("No sudo available. Ask an administrator to install git and git-lfs.")
        if which("apt-get"):
            return [[*prefix, "apt-get", "update"], [*prefix, "apt-get", "install", "-y", *packages]]
        for manager, flags in (
            ("dnf", ["install", "-y"]),
            ("yum", ["install", "-y"]),
            ("pacman", ["-S", "--needed", "--noconfirm"]),
            ("zypper", ["--non-interactive", "install"]),
            ("apk", ["add"]),
        ):
            if which(manager):
                return [[*prefix, manager, *flags, *packages]]
    raise RuntimeError(
        "No supported package manager found. Install Git and Git LFS, then restart Git Companion."
    )


async def bootstrap(cwd: Path, runner: Runner, emit, auto_install: bool = True) -> bool:
    refresh_path()
    git_ok = (await capture(["git", "--version"], cwd))[0] == 0
    lfs_ok = git_ok and (await capture(["git", "lfs", "version"], cwd))[0] == 0
    if git_ok and lfs_ok:
        emit("Git and Git LFS are ready.\n")
        return True
    missing = ([] if git_ok else ["git"]) + ([] if lfs_ok else ["git-lfs"])
    emit(f"Missing tools: {', '.join(missing)}\n")
    if not auto_install:
        emit("Automatic installation disabled. Install the missing tools and restart.\n")
        return False
    try:
        plan = install_plan(platform.system(), missing, root=hasattr(os, "geteuid") and os.geteuid() == 0)
        for args in plan:
            # Git for Windows can already include LFS; recheck before installing it separately.
            if "GitHub.GitLFS" in args:
                refresh_path()
                if (await capture(["git", "lfs", "version"], cwd))[0] == 0:
                    continue
            emit(f"Installing in background: {display_command(args)}\n")
            if await runner.run(args, cwd, emit):
                emit(
                    "Installation failed or needs elevation. Run the displayed command in an administrator terminal (Linux/macOS: remove '-n' from sudo) and restart.\n"
                )
                return False
            refresh_path()
        ready = (await capture(["git", "--version"], cwd))[0] == 0
        ready = ready and (await capture(["git", "lfs", "version"], cwd))[0] == 0
        if ready:
            emit("Tools installed. Enabling Git LFS filters...\n")
            return await runner.run(["git", "lfs", "install", "--skip-repo"], cwd, emit) == 0
        emit("Tools could not be found after installation. Restart your terminal to reload PATH.\n")
    except (OSError, RuntimeError) as error:
        emit(f"Setup: {error}\n")
    return False
