"""Keyboard-friendly input for global command search and inline completion."""

from typing import ClassVar

from textual.binding import Binding
from textual.message import Message
from textual.suggester import Suggester
from textual.widgets import Input

from .catalog import complete


class CommandSuggester(Suggester):
    async def get_suggestion(self, value: str) -> str | None:
        return complete(value)


class CommandSearch(Input):
    BINDINGS: ClassVar = [
        Binding("tab", "complete", "Complete", show=False),
        Binding("down", "browse_results", "Suggestions", show=False),
    ]

    class Activated(Message):
        """A click or shortcut opens search across the entire catalog."""

    def on_focus(self):
        self.post_message(self.Activated())

    def action_complete(self):
        suggestion = complete(self.value) if self.cursor_at_end else None
        if suggestion:
            self.value = suggestion
            self.cursor_position = len(suggestion)
        else:
            self.app.action_focus_next()

    def action_browse_results(self):
        self.app.query_one("#commands").focus()
