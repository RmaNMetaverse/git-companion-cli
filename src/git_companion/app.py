"""The terminal cockpit: browse intent, preview commands, stream real output."""

import re
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import Button, Collapsible, Footer, Header, Input, Label, OptionList, RichLog, Static
from textual.widgets.option_list import Option

from .bootstrap import bootstrap
from .catalog import BY_ID, CATEGORIES, COMMANDS, Command, search
from .discovery import CommandSearch, CommandSuggester
from .engine import RepoState, Runner, display_command, inspect_repo


def command_help(command: Command) -> str:
    lines = ["EXAMPLES", ""]
    for number, example in enumerate(command.examples, 1):
        lines += [f"{number}. {example.label}", display_command(command.build(dict(example.values))), ""]
    lines += ["A LITTLE MORE", command.description]
    return "\n".join(lines)


class CommandHelpDialog(ModalScreen):
    """Optional help remains available when the side panel cannot fit."""

    BINDINGS: ClassVar = [("escape", "dismiss", "Close")]

    def __init__(self, command: Command):
        super().__init__()
        self.command = command

    def compose(self):
        with VerticalScroll(id="help-dialog"):
            yield Label(self.command.title, id="dialog-title")
            yield Static(self.command.hint, markup=False)
            yield Static(command_help(self.command), id="help-examples", markup=False)
            if self.command.risk:
                yield Static("CAUTION  " + self.command.risk, classes="help-risk", markup=False)
            yield Button("Back", id="close-help", variant="primary")

    @on(Button.Pressed, "#close-help")
    def close_help(self):
        self.dismiss()


class CommandDialog(ModalScreen[list[str] | None]):
    BINDINGS: ClassVar = [("escape", "dismiss(None)", "Cancel"), ("f2", "examples", "Examples")]

    def __init__(self, command: Command):
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Label(self.command.title, id="dialog-title")
            yield Static(self.command.hint, markup=False)
            with Collapsible(title="Details & examples", collapsed=True, id="dialog-help"):
                yield Static(command_help(self.command), markup=False)
            if self.command.risk:
                yield Static("CAUTION  " + self.command.risk, id="risk", markup=False)
            for field in self.command.fields:
                yield Label(field.label)
                yield Input(value=field.default, placeholder=field.label, id=f"field-{field.name}")
            yield Label("COMMAND PREVIEW", classes="eyebrow")
            yield Static("", id="preview", markup=False)
            if self.command.risk:
                yield Label("Type RUN to confirm this operation")
                yield Input(placeholder="RUN", id="confirmation")
            yield Static("", id="validation", markup=False)
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Run command", variant="error" if self.command.risk else "primary", id="execute")

    def on_mount(self):
        self.update_preview()
        inputs = list(self.query(Input))
        (inputs[0] if inputs else self.query_one("#execute", Button)).focus()

    @on(Input.Changed)
    def update_preview(self):
        try:
            self.query_one("#preview", Static).update(display_command(self.arguments()))
            self.query_one("#validation", Static).update("")
        except ValueError as error:
            self.query_one("#preview", Static).update("Complete the fields above to build this command.")
            self.query_one("#validation", Static).update(str(error))

    def arguments(self):
        return self.command.build(
            {f.name: self.query_one(f"#field-{f.name}", Input).value for f in self.command.fields}
        )

    def action_examples(self):
        panel = self.query_one("#dialog-help", Collapsible)
        panel.collapsed = not panel.collapsed

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#execute")
    def execute(self):
        try:
            args = self.arguments()
            if self.command.risk and self.query_one("#confirmation", Input).value != "RUN":
                raise ValueError("Type RUN to acknowledge the operation described above.")
        except ValueError as error:
            self.query_one("#validation", Static).update(str(error))
            return
        self.dismiss(args)


class FolderDialog(ModalScreen[Path | None]):
    BINDINGS: ClassVar = [("escape", "dismiss(None)", "Cancel")]

    def compose(self):
        with Vertical(id="folder-dialog"):
            yield Label("Open a workspace", id="dialog-title")
            yield Input(str(self.app.cwd), id="folder")
            yield Static(
                "Enter an existing directory. Git repositories are detected automatically.",
                id="folder-error",
                markup=False,
            )
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="folder-cancel")
                yield Button("Open workspace", variant="primary", id="folder-open")

    def on_mount(self):
        self.query_one(Input).focus()

    @on(Button.Pressed, "#folder-cancel")
    def cancel(self):
        self.dismiss(None)

    @on(Input.Submitted)
    @on(Button.Pressed, "#folder-open")
    def open_folder(self):
        path = Path(self.query_one(Input).value).expanduser().resolve()
        if path.is_dir():
            self.dismiss(path)
        else:
            self.query_one("#folder-error", Static).update("That directory does not exist.")


class CompanionApp(App):
    TITLE = "Git Companion CLI"
    SUB_TITLE = "Your repository. In good company."
    CSS_PATH = "style.tcss"
    BINDINGS: ClassVar = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+f", "search", "Search"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+o", "open_folder", "Workspace"),
        Binding("ctrl+x", "cancel", "Stop"),
        Binding("ctrl+t", "theme", "Theme"),
        Binding("f1", "help", "Help"),
        Binding("f2", "examples", "Examples"),
        Binding("escape", "clear_search", "Back"),
    ]

    def __init__(self, cwd: Path, auto_install=True, ascii_only=False):
        super().__init__()
        self.cwd = cwd
        self.auto_install = auto_install
        self.ascii_only = ascii_only
        self.state = RepoState()
        self.category = "recommended"
        self.visible_commands: list[Command] = []
        self.runner = Runner()
        self.busy = False
        self.refreshing = False
        self.pending_output = ""
        self.theme = "textual-dark"
        self.detail_command_id = ""
        self.search_mode = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="hero"):
            art = "  o---o\n  |  /\n  o-o" if self.ascii_only else "  ●━━━━●\n  ┃   ╱\n  ●━━●"
            yield Static(art, id="branch-art")
            with Vertical(id="wordmark"):
                yield Static("GIT COMPANION", id="brand")
                yield Static("A little clarity for every commit.", id="tagline")
            yield Static("GIT + LFS\nTERMINAL COCKPIT", id="edition")
        yield Static("Detecting your workspace...", id="repo", markup=False)
        with Horizontal(id="metrics"):
            for name in ("branch", "staged", "modified", "sync"):
                yield Static("...", id=f"metric-{name}", markup=False)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("YOUR WORKFLOW", classes="eyebrow")
                yield OptionList(
                    *(Option(f"{n}  {title}", id=key) for key, (n, title, _) in CATEGORIES.items()),
                    id="categories",
                )
                yield Static("Small steps.\nClean history.\nRoom for the big files.", id="sidebar-note")
            with Vertical(id="main"):
                yield Label("SEARCH ALL COMMANDS  /  Ctrl+F", id="search-label")
                yield CommandSearch(
                    placeholder="Type a task or command...  e.g. git lfs pr",
                    id="search",
                    suggester=CommandSuggester(),
                )
                yield Static(
                    "Tab or Right: complete  /  Down: suggestions  /  Enter: review", id="search-tip"
                )
                yield Static("", id="section", markup=False)
                with Horizontal(id="browser"):
                    yield OptionList(id="commands")
                    with Vertical(id="details"):
                        with VerticalScroll(id="detail-content"):
                            yield Static("", id="detail-title", markup=False)
                            yield Static("", id="detail-description", markup=False)
                            with Collapsible(title="Details & examples", collapsed=True, id="detail-help"):
                                yield Static("", id="detail-examples", markup=False)
                            yield Static("", id="detail-risk", markup=False)
                        yield Button("Review & run", variant="primary", id="review")
                with Horizontal(id="console-bar"):
                    yield Label("LIVE TERMINAL", classes="eyebrow")
                    yield Static("READY", id="run-state", markup=False)
                    yield Button("Clear", id="clear", compact=True)
                yield RichLog(id="output", highlight=False, markup=False, wrap=True, max_lines=2000)
        yield Footer()

    def on_mount(self):
        self.screen.set_class(self.size.width < 105 or self.size.height < 34, "compact")
        self.query_one("#categories", OptionList).highlighted = 0
        self.set_interval(5, self.periodic_refresh)
        self.startup()

    def on_resize(self, event: Resize):
        self.screen.set_class(event.size.width < 105 or event.size.height < 34, "compact")

    @work
    async def startup(self):
        self.busy = True
        self.query_one("#run-state", Static).update("CHECKING TOOLS")
        try:
            await bootstrap(self.cwd, self.runner, self.emit, self.auto_install)
        except OSError as error:
            self.emit(f"Setup failed: {error}\n")
        finally:
            self.flush_output()
            self.busy = False
            self.query_one("#run-state", Static).update("READY")
        await self.refresh_state()
        self.query_one("#commands", OptionList).focus()

    def emit(self, chunk: str):
        # Keep partial lines between reads, normalize progress CRs, and strip terminal control codes.
        self.pending_output += chunk.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in self.pending_output:
            line, self.pending_output = self.pending_output.split("\n", 1)
            self.write_output(line)
        if len(self.pending_output) > 8192:
            self.write_output(self.pending_output)
            self.pending_output = ""

    def write_output(self, line: str):
        line = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", line)
        line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
        line = "".join(char for char in line if char == "\t" or ord(char) >= 32)
        self.query_one("#output", RichLog).write(Text(line))

    def flush_output(self):
        if self.pending_output:
            self.write_output(self.pending_output)
            self.pending_output = ""

    async def periodic_refresh(self):
        if not self.busy and not self.refreshing and not isinstance(self.screen, ModalScreen):
            await self.refresh_state()

    async def refresh_state(self):
        if self.refreshing:
            return
        self.refreshing = True
        try:
            self.state = await inspect_repo(self.cwd)
            state = self.state
            self.query_one("#repo", Static).update(str(self.cwd))
            for name, value in {
                "branch": f"BRANCH\n{state.branch}",
                "staged": f"STAGED\n{state.staged:02d} ready to commit",
                "modified": f"WORKING TREE\n{state.modified:02d} edited / {state.untracked:02d} new / {state.conflicts:02d} conflicts",
                "sync": f"UPSTREAM\n{state.ahead} ahead / {state.behind} behind"
                if state.upstream
                else "UPSTREAM\nNot configured",
            }.items():
                self.query_one(f"#metric-{name}", Static).update(value)
            self.update_commands()
        finally:
            self.refreshing = False

    @on(OptionList.OptionHighlighted, "#categories")
    def category_highlighted(self, event):
        self.category = event.option.id
        self.search_mode = False
        self.query_one("#search", Input).value = ""
        self.update_commands()

    @on(OptionList.OptionSelected, "#categories")
    def category_selected(self):
        self.search_mode = False
        self.query_one("#search", Input).value = ""
        self.update_commands()
        self.query_one("#commands", OptionList).focus()

    @on(CommandSearch.Activated)
    def search_activated(self):
        self.search_mode = True
        self.update_commands()

    @on(Input.Changed, "#search")
    def search_changed(self):
        field = self.query_one("#search", Input)
        self.search_mode = bool(field.value.strip()) or field.has_focus or self.search_mode
        self.update_commands()

    @on(Input.Submitted, "#search")
    def search_submitted(self):
        self.query_one("#commands", OptionList).focus()
        if self.visible_commands:
            self.review()

    def update_commands(self):
        query = self.query_one("#search", Input).value
        category = None if query.strip() or self.search_mode else self.category
        commands = self.query_one("#commands", OptionList)
        old_id = None
        if commands.highlighted is not None and commands.option_count:
            old_id = commands.get_option_at_index(commands.highlighted).id
        self.visible_commands = search(query, category, self.state.recommendations)
        commands.clear_options()
        for command in self.visible_commands:
            icon = "!" if command.risk else ">" if self.ascii_only else "◇"
            syntax = f"\n   {command.completion}" if query.strip() else ""
            text = Text(f"{icon}  {command.title}\n   {command.hint}{syntax}")
            text.stylize("#ffb86c" if command.risk else "#8be9fd", 0, 1)
            text.stylize("dim", text.plain.index("\n") + 1)
            commands.add_option(Option(text, id=command.id))
        self.query_one("#section", Static).update(
            (
                f"{'ALL COMMANDS' if category is None else CATEGORIES[category][1].upper()}"
                f"   /   {len(self.visible_commands)} actions"
            )
            if self.visible_commands
            else "No matches. Try a task, command name, or fewer words."
        )
        ids = [command.id for command in self.visible_commands]
        commands.highlighted = ids.index(old_id) if old_id in ids else (0 if ids else None)
        self.update_details()

    @on(OptionList.OptionHighlighted, "#commands")
    def command_highlighted(self):
        self.update_details()

    def selected_command(self):
        commands = self.query_one("#commands", OptionList)
        if commands.highlighted is not None and commands.option_count:
            return BY_ID[commands.get_option_at_index(commands.highlighted).id]
        return None

    def update_details(self):
        command = self.selected_command()
        command_id = command.id if command else None
        if command_id == self.detail_command_id:
            return
        self.detail_command_id = command_id
        self.query_one("#detail-title", Static).update(command.title if command else "No matching commands")
        self.query_one("#detail-description", Static).update(
            command.hint if command else "Try another search term."
        )
        help_panel = self.query_one("#detail-help", Collapsible)
        help_panel.collapsed = True
        help_panel.display = command is not None
        self.query_one("#detail-examples", Static).update(command_help(command) if command else "")
        self.query_one("#detail-risk", Static).update(
            "CAUTION\n" + command.risk if command and command.risk else ""
        )
        self.query_one("#review", Button).disabled = command is None

    @on(OptionList.OptionSelected, "#commands")
    @on(Button.Pressed, "#review")
    def review(self):
        command = self.selected_command()
        if self.busy:
            self.notify("A command is running. Stop it or wait for completion.", severity="warning")
        elif command:
            if command.repo and not self.state.root:
                self.notify("Open or initialize a repository first.", severity="warning")
                return
            self.push_screen(CommandDialog(command), self.command_chosen)

    def command_chosen(self, args):
        if args:
            self.execute_command(args)

    @work
    async def execute_command(self, args: list[str]):
        if self.busy:
            return
        self.busy = True
        self.query_one("#run-state", Static).update("RUNNING  /  Ctrl+X to stop")
        self.emit(f"\n$ {display_command(args)}\n")
        try:
            code = await self.runner.run(args, self.cwd, self.emit)
            self.flush_output()
            self.emit(f"\n{'Completed' if code == 0 else 'Failed / stopped'} (exit {code})\n")
            if code:
                self.emit(
                    "For authentication, configure a credential helper or SSH agent in your normal terminal, then retry.\n"
                )
        except OSError as error:
            self.emit(f"Unable to run command: {error}\n")
        finally:
            self.busy = False
            self.query_one("#run-state", Static).update("READY")
            await self.refresh_state()

    def action_search(self):
        self.search_mode = True
        self.query_one("#search", Input).focus()
        self.update_commands()

    def action_examples(self):
        if isinstance(self.screen, CommandDialog):
            panel = self.screen.query_one("#dialog-help", Collapsible)
            panel.collapsed = not panel.collapsed
        elif not isinstance(self.screen, ModalScreen):
            command = self.selected_command()
            if command:
                self.push_screen(CommandHelpDialog(command))

    def action_clear_search(self):
        self.search_mode = False
        self.query_one("#categories", OptionList).focus()
        self.query_one("#search", Input).value = ""
        self.update_commands()

    @work
    async def action_refresh(self):
        if not self.busy:
            await self.refresh_state()

    def action_open_folder(self):
        if self.busy:
            self.notify("Wait for the current operation before changing workspaces.")
        else:
            self.push_screen(FolderDialog(), self.folder_chosen)

    def folder_chosen(self, path):
        if path:
            self.cwd = path
            self.action_refresh()

    async def action_cancel(self):
        if self.busy:
            await self.runner.cancel()

    async def action_quit(self):
        await self.runner.cancel()
        self.exit()

    def action_theme(self):
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"

    def action_help(self):
        self.emit(
            f"\nGit Companion / {len(COMMANDS)} workflows\n"
            "Tab cycles panels. Arrow keys browse. Enter reviews a command.\n"
            "Ctrl+F searches every command, hint, flag and example across all categories.\n"
            "Tab or Right completes a command; Down browses suggestions; Enter opens review.\n"
            "Escape clears search and returns to your workflow.\n"
            "Ctrl+O changes workspace; Ctrl+R refreshes; Ctrl+T changes theme.\n"
            "Ctrl+X stops a process; Ctrl+Q quits. Mouse navigation also works.\n"
            "F2 opens optional details and two examples for the selected action.\n"
            "Every command is previewed. Destructive operations require typing RUN.\n"
            "Git handles credentials through your configured helper or SSH agent.\n"
            "No embedded editor: commit and tag messages are entered in forms.\n"
        )

    @on(Button.Pressed, "#clear")
    def clear_output(self):
        self.query_one("#output", RichLog).clear()
