import asyncio
import shutil
import sys

import pytest
from textual.widgets import Input, RichLog, Static

from git_companion.app import CommandDialog, CompanionApp
from git_companion.engine import capture
from git_companion.results import ResultsScreen


@pytest.mark.skipif(not shutil.which("git"), reason="Git required")
@pytest.mark.parametrize("size", [(130, 45), (80, 24)])
async def test_real_command_runs_from_review_and_shows_output(tmp_path, size):
    await capture(["git", "init"], tmp_path)
    (tmp_path / "artwork.psd").write_text("test artwork")
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=size) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("ctrl+f")
        app.query_one("#search", Input).value = "git status"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, CommandDialog)
        await pilot.click("#execute")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert isinstance(app.screen, ResultsScreen)
        output = app.screen.query_one("#result-log", RichLog)
        assert "artwork.psd" in "\n".join(line.text for line in output.lines)
        assert output.region.bottom <= size[1], f"Command output is below the terminal: {output.region}"
        assert "Completed successfully" in str(app.screen.query_one("#result-summary", Static).render())
        await pilot.press("escape")
        await pilot.pause()
        history = app.query_one("#output", RichLog)
        assert history.region.bottom <= size[1]
        assert history.scroll_y == history.max_scroll_y
        await pilot.press("f3")
        assert isinstance(app.screen, ResultsScreen)
        assert "artwork.psd" in "\n".join(line.text for line in app.screen.query_one(RichLog).lines)


async def test_silent_success_and_failed_process_have_explicit_results(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await app.workers.wait_for_complete()
        app.execute_command([sys.executable, "-c", "pass"])
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.last_result.kind == "success"
        assert "returned no text output" in "\n".join(app.last_result.lines)
        await pilot.press("escape")
        app.execute_command(
            [sys.executable, "-c", "import sys; print('Failed to read scene', file=sys.stderr); sys.exit(7)"]
        )
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.last_result.kind == "failure" and app.last_result.exit_code == 7
        text = "\n".join(line.text for line in app.screen.query_one(RichLog).lines)
        assert "Failed to read scene" in text and "exit 7" in text
        assert "authentication" not in text
        await pilot.press("escape")
        app.execute_command([str(tmp_path / "missing-git-executable")])
        await app.workers.wait_for_complete()
        assert app.last_result.kind == "failure"
        assert "Could not start" in app.last_result.summary
        assert "Unable to run command" in "\n".join(app.last_result.lines)


async def test_partial_output_is_live_and_stop_is_reported(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await app.workers.wait_for_complete()
        app.execute_command(
            [
                sys.executable,
                "-u",
                "-c",
                "import time; print('Downloading artwork...', end='', flush=True); time.sleep(60)",
            ]
        )
        for _ in range(100):
            await asyncio.sleep(0.05)
            if app.last_result and "Downloading artwork" in app.last_result.partial:
                break
        assert app.busy and app.last_result.kind == "running"
        assert "Downloading artwork" in str(app.screen.query_one("#result-partial", Static).render())
        await pilot.press("escape")
        await pilot.press("f3")
        assert "Downloading artwork" in str(app.screen.query_one("#result-partial", Static).render())
        await pilot.press("ctrl+x")
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.last_result.kind == "stopped"
        assert "Stopped by you" in str(app.screen.query_one("#result-summary", Static).render())
