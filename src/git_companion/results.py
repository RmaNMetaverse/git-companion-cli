"""A persistent result for the last command and a prominent live output view."""

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Static


@dataclass
class CommandResult:
    command: str
    directory: str
    lines: deque[str] = field(default_factory=lambda: deque(maxlen=2000))
    partial: str = ""
    kind: str = "running"
    exit_code: int | None = None
    started: float = field(default_factory=monotonic)
    duration: float | None = None

    @property
    def summary(self) -> str:
        elapsed = self.duration if self.duration is not None else monotonic() - self.started
        if self.kind == "running":
            return f"Running — {elapsed:.1f}s  /  Output appears below as it arrives."
        if self.kind == "stopped":
            return f"Stopped by you — {elapsed:.1f}s"
        if self.kind == "success":
            return f"Completed successfully — exit 0 — {elapsed:.1f}s"
        if self.exit_code is None:
            return f"Could not start the command — {elapsed:.1f}s"
        return f"Command failed — exit {self.exit_code} — {elapsed:.1f}s"

    def finish(self, code: int | None, stopped: bool = False):
        self.duration = monotonic() - self.started
        self.exit_code = code
        self.kind = "stopped" if stopped else "success" if code == 0 else "failure"


class ResultsScreen(ModalScreen):
    BINDINGS: ClassVar = [
        ("escape", "dismiss", "Back"),
        ("f3", "dismiss", "Back"),
        ("ctrl+x", "stop", "Stop"),
        ("ctrl+q", "quit_app", "Quit"),
    ]

    def __init__(self, result: CommandResult):
        super().__init__()
        self.result = result

    def compose(self):
        with Vertical(id="results-dialog"):
            yield Static("COMMAND RESULTS", id="result-title")
            yield Static(self.result.command, id="result-command", markup=False)
            yield Static(self.result.directory, id="result-directory", markup=False)
            yield Static(self.result.summary, id="result-summary", markup=False)
            yield RichLog(id="result-log", min_width=1, wrap=True, markup=False, max_lines=2000)
            yield Static("", id="result-partial", markup=False)
            with Horizontal(id="result-controls"):
                yield Button("Stop command", id="stop-command", variant="error")
                yield Button("Back to commands", id="back-to-commands", variant="primary")
            yield Static("Scroll to read output. Escape: back. F3: reopen latest result.", id="result-tip")

    def on_mount(self):
        log = self.query_one("#result-log", RichLog)
        for line in self.result.lines:
            log.write(Text(line))
        self.update_partial()
        self.update_summary()
        self.set_interval(0.25, self.update_summary)
        log.focus()

    def append_line(self, line: str):
        self.query_one("#result-log", RichLog).write(Text(line))

    def update_partial(self):
        partial = self.query_one("#result-partial", Static)
        partial.update(self.result.partial)
        partial.display = bool(self.result.partial)

    def update_summary(self):
        self.query_one("#result-summary", Static).update(self.result.summary)
        self.query_one("#results-dialog").set_classes(self.result.kind)
        self.query_one("#stop-command", Button).disabled = self.result.kind != "running"

    @on(Button.Pressed, "#back-to-commands")
    def back(self):
        self.dismiss()

    @on(Button.Pressed, "#stop-command")
    async def action_stop(self):
        await self.app.action_cancel()

    async def action_quit_app(self):
        await self.app.action_quit()
