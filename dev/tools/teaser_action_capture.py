"""Capture authentic workflows for the second, sound-effects-only teaser."""

import asyncio
import os
import tempfile
from pathlib import Path

from textual.widgets import Input, OptionList

from git_companion.app import CompanionApp
from git_companion.catalog import CATEGORIES
from git_companion.engine import capture

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "dev/artifacts/teaser-action/screens"


async def record():
    ASSETS.mkdir(parents=True, exist_ok=True)
    os.environ.pop("NO_COLOR", None)
    os.environ.update(TERM="xterm-256color", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    with tempfile.TemporaryDirectory(prefix="studio-", dir=ASSETS.parent) as temporary:
        repo = Path(temporary)

        async def git(*args):
            code, output = await capture(["git", *args], repo)
            if code:
                raise RuntimeError(output)

        await git("init", "-b", "main")
        await git("config", "user.name", "Studio Artist")
        await git("config", "user.email", "demo@example.com")
        await git("lfs", "install", "--local")
        await git("lfs", "track", "*.psd")
        await git("lfs", "track", "*.blend")
        (repo / "artwork").mkdir()
        (repo / "scenes").mkdir()
        (repo / "artwork/cover.psd").write_bytes(b"Demo artwork placeholder.\n")
        (repo / "scenes/studio.blend").write_bytes(b"Demo scene placeholder.\n")
        await git("add", ".")
        await git("commit", "-m", "Save the first creative direction")
        (repo / "artwork/cover.psd").write_bytes(b"Demo: warmer palette.\n")
        (repo / "client-notes.txt").write_text("Try a warmer palette.\n")

        app = CompanionApp(repo, auto_install=False)
        async with app.run_test(size=(120, 46)) as pilot:
            await app.workers.wait_for_complete()
            for clock in app.query("HeaderClock"):
                clock.display = False

            async def save(name):
                app.query_one("#repo").update("~/projects/studio-collection")
                if app.last_result:
                    app.last_result.directory = "~/projects/studio-collection"
                    for label in app.screen.query("#result-directory"):
                        label.update("~/projects/studio-collection")
                await pilot.pause()
                (ASSETS / f"{name}.svg").write_text(app.export_screenshot(), encoding="utf-8")
                print(f"Captured {name}", flush=True)

            await save("home")
            categories = app.query_one("#categories", OptionList)
            for index, category in enumerate(CATEGORIES):
                categories.focus()
                categories.highlighted = index
                await save(f"category-{category}")

            field = app.query_one("#search", Input)
            await pilot.press("ctrl+f")
            for name, value in (
                ("search-save", "save"),
                ("search-flags", "--dry-run"),
                ("search-lfs", "git lfs"),
            ):
                field.value = value
                field.cursor_position = len(value)
                await save(name)
            for index, value in enumerate(
                ("g", "git", "git l", "git lf", "git lfs", "git lfs p", "git lfs pr")
            ):
                field.value = value
                field.cursor_position = len(value)
                await save(f"typing-{index}")
            await pilot.press("tab")
            await save("completed")

            for command, label in (("git status", "status"), ("git lfs prune --dry-run", "prune")):
                await pilot.press("ctrl+f")
                field.value = command
                await pilot.pause()
                app.review()
                await save(f"review-{label}")
                await pilot.click("#execute")
                await app.workers.wait_for_complete()
                await save(f"results-{label}")
                await pilot.press("escape")

            await pilot.press("ctrl+f")
            field.value = "git lfs track"
            await pilot.pause()
            app.query_one("#commands", OptionList).highlighted = next(
                i for i, command in enumerate(app.visible_commands) if command.id == "lfs-track"
            )
            await save("hint")
            await pilot.press("f2")
            await save("examples")


if __name__ == "__main__":
    asyncio.run(record())
