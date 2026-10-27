"""Render the actual TUI to a shareable SVG without changing a repository."""

import asyncio
import os
from pathlib import Path

from textual.widgets import Collapsible, Input, OptionList

from git_companion.app import CompanionApp


async def main():
    os.environ.pop("NO_COLOR", None)
    os.environ["TERM"] = "xterm-256color"
    app = CompanionApp(Path.cwd(), auto_install=False)
    async with app.run_test(size=(140, 46)) as pilot:
        await app.workers.wait_for_complete()
        app.query_one("#search", Input).value = "lfs track"
        await pilot.pause()
        app.query_one("#commands", OptionList).highlighted = next(
            i for i, command in enumerate(app.visible_commands) if command.id == "lfs-track"
        )
        await pilot.pause()
        output = Path(__file__).resolve().parents[1] / "artifacts"
        output.mkdir(parents=True, exist_ok=True)
        print(app.save_screenshot("preview.svg", path=output))
        app.query_one("#detail-help", Collapsible).collapsed = False
        await pilot.pause()
        print(app.save_screenshot("examples.svg", path=output))
        field = app.query_one("#search", Input)
        field.focus()
        field.value = "git lfs pr"
        field.cursor_position = len(field.value)
        await pilot.pause()
        print(app.save_screenshot("search.svg", path=output))


if __name__ == "__main__":
    asyncio.run(main())
