"""Capture real TUI screens in a disposable, isolated artist demo repository."""

import asyncio
import os
import tempfile
from pathlib import Path

from textual.widgets import Collapsible, Input, OptionList

from git_companion.app import CompanionApp
from git_companion.catalog import BY_ID
from git_companion.engine import capture

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "dev" / "artifacts" / "teaser" / "screens"


async def record():
    ASSETS.mkdir(parents=True, exist_ok=True)
    os.environ.pop("NO_COLOR", None)
    os.environ["TERM"] = "xterm-256color"
    # Demo assets and hooks must not use the viewer's global Git settings or shared LFS store.
    os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
    os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    with tempfile.TemporaryDirectory(prefix="demo-", dir=ASSETS.parent) as temporary:
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
        (repo / "artwork/cover.psd").write_bytes(b"Demo placeholder for a Photoshop artwork file.\n")
        (repo / "scenes/studio.blend").write_bytes(b"Demo placeholder for a Blender scene.\n")
        await git("add", ".")
        await git("commit", "-m", "Save the first creative direction")
        (repo / "artwork/cover.psd").write_bytes(b"Demo placeholder: warmer cover palette.\n")
        (repo / "client-notes.txt").write_text("Try warmer colors and softer shadows.\n")

        app = CompanionApp(repo, auto_install=False)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.workers.wait_for_complete()
            for clock in app.query("HeaderClock"):
                clock.display = False

            async def save(name):
                app.query_one("#repo").update("~/projects/studio-collection")
                if app.last_result:
                    app.last_result.directory = "~/projects/studio-collection"
                    if app.screen.query("#result-directory"):
                        app.screen.query_one("#result-directory").update("~/projects/studio-collection")
                await pilot.pause()
                svg = app.export_screenshot()
                (ASSETS / f"{name}.svg").write_text(svg, encoding="utf-8")
                print(f"Captured {name}", flush=True)

            await save("home")
            field = app.query_one("#search", Input)
            field.focus()
            for index, value in enumerate(
                ("g", "git", "git l", "git lf", "git lfs", "git lfs p", "git lfs pr")
            ):
                field.value = value
                field.cursor_position = len(value)
                await save(f"search-{index:02d}")
            await pilot.press("tab")
            await save("completed")

            field.value = "git lfs track"
            await pilot.pause()
            app.query_one("#commands", OptionList).highlighted = next(
                i for i, command in enumerate(app.visible_commands) if command.id == "lfs-track"
            )
            await save("hint")
            app.query_one("#detail-help", Collapsible).collapsed = False
            await save("examples")
            await pilot.press("f2")
            await save("examples-full")
            await pilot.press("escape")

            for name, command in (("prune", "prune-preview"), ("results", "status")):
                app.execute_command(BY_ID[command].build())
                await app.workers.wait_for_complete()
                await save(name)
                await pilot.press("escape")
            await pilot.press("ctrl+f")
            field.value = "git lfs ls-files"
            await save("inventory")


if __name__ == "__main__":
    asyncio.run(record())
