"""Async subprocess execution and repository facts; never executes shell strings."""

import asyncio
import codecs
import os
import shlex
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


def display_command(args: list[str]) -> str:
    return subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)


def environment() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "Never",
        "GIT_EDITOR": "true",
        "GIT_SEQUENCE_EDITOR": "true",
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
        "NO_COLOR": "1",
        "TERM": "dumb",
    }


async def capture(args: list[str], cwd: Path, timeout: float = 10) -> tuple[int, str]:
    runner = Runner()
    output: list[str] = []
    try:
        code = await asyncio.wait_for(runner.run(args, cwd, output.append), timeout)
        return code, "".join(output).strip()
    except (OSError, asyncio.TimeoutError) as error:
        return 1, str(error) or "Command timed out"


class Runner:
    def __init__(self):
        self.process: asyncio.subprocess.Process | None = None

    async def run(self, args: list[str], cwd: Path, emit: Callable[[str], None]) -> int:
        options = {}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        self.process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            env=environment(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            **options,
        )
        decoder = codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while chunk := await self.process.stdout.read(4096):
                emit(decoder.decode(chunk))
            emit(decoder.decode(b"", final=True))
            return await self.process.wait()
        finally:
            if self.process.returncode is None:
                await self.cancel()
            self.process = None

    async def cancel(self):
        process = self.process
        if not process or process.returncode is not None:
            return
        try:
            if os.name == "nt":
                killer = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await killer.wait()
            else:
                os.killpg(process.pid, signal.SIGTERM)
            await asyncio.wait_for(process.wait(), 3)
        except (ProcessLookupError, asyncio.TimeoutError):
            if process.returncode is None:
                if os.name != "nt":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                await process.wait()


@dataclass
class RepoState:
    root: str = ""
    branch: str = "No repository"
    staged: int = 0
    modified: int = 0
    untracked: int = 0
    conflicts: int = 0
    ahead: int = 0
    behind: int = 0
    upstream: str = ""
    merging: bool = False
    rebasing: bool = False
    lfs: bool = False
    error: str = ""
    recommendations: tuple[str, ...] = field(default_factory=lambda: ("init", "clone", "identity"))


def parse_status(output: str, root: str) -> RepoState:
    state = RepoState(root=root, branch="Unborn branch")
    # NUL records preserve filenames containing newlines, spaces and non-ASCII characters.
    records = iter(output.split("\0"))
    for record in records:
        if record.startswith("# branch.head "):
            state.branch = record[14:]
        elif record.startswith("# branch.upstream "):
            state.upstream = record[18:]
        elif record.startswith("# branch.ab "):
            parts = record.split()
            state.ahead = int(parts[2][1:])
            state.behind = int(parts[3][1:])
        elif record.startswith(("1 ", "2 ")):
            xy = record.split(" ", 2)[1]
            state.staged += xy[0] != "."
            state.modified += xy[1] != "."
            if record.startswith("2 "):
                next(records, None)  # original pathname in a rename record
        elif record.startswith("u "):
            state.conflicts += 1
        elif record.startswith("? "):
            state.untracked += 1
    return state


async def inspect_repo(cwd: Path) -> RepoState:
    code, root = await capture(["git", "rev-parse", "--show-toplevel"], cwd)
    if code:
        return RepoState(error=root)
    code, status = await capture(["git", "status", "--porcelain=v2", "--branch", "-z"], cwd)
    if code:
        return RepoState(root=root, error=status, recommendations=("status", "reflog"))
    state = parse_status(status, root)
    for name, attribute in (
        ("MERGE_HEAD", "merging"),
        ("rebase-merge", "rebasing"),
        ("rebase-apply", "rebasing"),
    ):
        code, path = await capture(["git", "rev-parse", "--git-path", name], cwd)
        if not code and (cwd / path).exists():
            setattr(state, attribute, True)
    state.lfs = (await capture(["git", "lfs", "version"], cwd))[0] == 0
    suggested = []
    if state.conflicts:
        suggested += ["status", "stage"]
    if state.rebasing:
        suggested += ["rebase-continue", "rebase-abort"]
    elif state.merging:
        suggested += ["commit", "merge-abort"]
    elif state.staged:
        suggested += ["staged", "commit"]
    if state.modified or state.untracked:
        suggested += ["patch", "stage", "stash"]
    if not state.conflicts and not state.rebasing and not state.merging:
        if state.ahead:
            suggested.append("push")
        if state.behind:
            suggested.append("pull")
    suggested += ["status", "graph", "fetch"]
    if state.lfs:
        suggested += ["lfs-status", "prune-preview"]
    state.recommendations = tuple(dict.fromkeys(suggested))
    return state
