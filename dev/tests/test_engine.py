import asyncio
import shutil
import sys

import pytest

from git_companion.catalog import BY_ID
from git_companion.engine import Runner, capture, inspect_repo, parse_status


def test_porcelain_with_rename_and_newline_filename():
    state = parse_status(
        "# branch.head feature\0# branch.upstream origin/feature\0# branch.ab +2 -3\0"
        "1 M. N... 100644 100644 100644 a a staged.txt\0"
        "1 .M N... 100644 100644 100644 a a edited.txt\0"
        "2 R. N... 100644 100644 100644 a a R100 new.txt\0? oldname\0"
        "? hello\nworld.txt\0u UU N... 100644 100644 100644 100644 a a a conflict.txt\0",
        "/repo",
    )
    assert (state.staged, state.modified, state.untracked, state.conflicts) == (2, 1, 1, 1)
    assert (state.ahead, state.behind, state.upstream) == (2, 3, "origin/feature")


@pytest.mark.skipif(not shutil.which("git"), reason="Git required")
async def test_real_stage_commit_and_context_recommendations(tmp_path):
    assert (await capture(["git", "init"], tmp_path))[0] == 0
    await capture(["git", "config", "user.name", "Test"], tmp_path)
    await capture(["git", "config", "user.email", "test@example.com"], tmp_path)
    (tmp_path / "file with spaces.txt").write_text("hello\n")
    state = await inspect_repo(tmp_path)
    assert state.untracked == 1 and "stage" in state.recommendations
    assert (await capture(BY_ID["stage"].build({"path": "file with spaces.txt"}), tmp_path))[0] == 0
    state = await inspect_repo(tmp_path)
    assert state.staged == 1 and state.recommendations[0] == "staged"
    assert (await capture(BY_ID["commit"].build({"message": "A real test commit"}), tmp_path))[0] == 0
    state = await inspect_repo(tmp_path)
    assert state.staged == state.untracked == 0


async def test_streaming_exit_status_and_cancellation(tmp_path):
    runner = Runner()
    output = []
    code = await runner.run(
        [sys.executable, "-c", "print('hello'); raise SystemExit(7)"], tmp_path, output.append
    )
    assert code == 7 and "hello" in "".join(output)
    task = asyncio.create_task(
        runner.run([sys.executable, "-c", "import time; time.sleep(60)"], tmp_path, output.append)
    )
    for _ in range(100):
        if runner.process:
            break
        await asyncio.sleep(0.02)
    await runner.cancel()
    assert await asyncio.wait_for(task, 5) != 0
