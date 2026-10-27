from textual.widgets import Collapsible, Input, OptionList, Static

from git_companion.app import CommandDialog, CommandHelpDialog, CompanionApp
from git_companion.catalog import BY_ID, COMMANDS


async def test_app_search_preview_and_resize(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(130, 45)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.query_one("#commands", OptionList).option_count > 0
        # Vertical option padding is not included in Textual 6's line map.
        # Keep list rows readable, including their first and second text lines.
        categories = app.query_one("#categories", OptionList)
        assert categories.get_component_styles("option-list--option").padding.top == 0
        await pilot.press("ctrl+f")
        app.query_one("#search", Input).value = "prune force"
        await pilot.pause()
        assert {c.id for c in app.visible_commands} == {"prune-force", "prune-force-preview"}
        app.push_screen(CommandDialog(BY_ID["prune-force"]))
        await pilot.pause()
        assert "git lfs prune --force" in str(app.screen.query_one("#preview", Static).render())
        await pilot.click("#execute")
        assert isinstance(app.screen, CommandDialog)  # no destructive action without RUN
        await pilot.press("escape")
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        assert app.screen.has_class("compact")


async def test_argument_form_keeps_input_literal(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        app.push_screen(CommandDialog(BY_ID["commit"]))
        await pilot.pause()
        app.screen.query_one("#field-message", Input).value = "fix [brackets] & spaces"
        await pilot.pause()
        assert app.screen.arguments()[-1] == "fix [brackets] & spaces"
        await pilot.press("escape")


async def test_examples_are_opt_in_and_reset_only_when_changing_action(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(130, 45)) as pilot:
        await app.workers.wait_for_complete()
        app.query_one("#search", Input).value = "lfs track"
        await pilot.pause()
        commands = app.query_one("#commands", OptionList)
        commands.highlighted = next(i for i, c in enumerate(app.visible_commands) if c.id == "lfs-track")
        await pilot.pause()
        panel = app.query_one("#detail-help", Collapsible)
        assert panel.collapsed
        assert "Tell LFS" in str(app.query_one("#detail-description", Static).render())
        await pilot.click("#detail-help CollapsibleTitle")
        assert not panel.collapsed
        text = str(app.query_one("#detail-examples", Static).render())
        assert "*.psd" in text and "*.blend" in text
        app.update_commands()  # idle refresh must not close help while someone is reading
        await pilot.pause()
        assert not panel.collapsed
        commands.highlighted = 0
        await pilot.pause()
        assert panel.collapsed


async def test_small_terminal_help_and_review_forms_have_examples(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("f2")
        await pilot.pause()
        assert isinstance(app.screen, CommandHelpDialog)
        assert "EXAMPLES" in str(app.screen.query_one("#help-examples", Static).render())
        await pilot.press("escape")
        app.push_screen(CommandDialog(BY_ID["commit"]))
        await pilot.pause()
        assert app.screen.query_one("#dialog-help", Collapsible).collapsed
        await pilot.press("f2")
        assert not app.screen.query_one("#dialog-help", Collapsible).collapsed
        await pilot.press("escape")


async def test_dedicated_search_completion_review_and_escape(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(110, 40)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("ctrl+f")
        await pilot.pause()
        field = app.query_one("#search", Input)
        assert field.has_focus
        assert len(app.visible_commands) == len(COMMANDS)  # includes actions outside For you
        await pilot.press(*"git com")
        await pilot.pause()
        await pilot.press("tab")
        assert field.value == "git commit -m"
        assert field.has_focus
        await pilot.press("escape")
        assert field.value == "" and not app.search_mode
        await pilot.press("ctrl+f")
        await pilot.press(*"git in")
        await pilot.pause()
        await pilot.press("right")  # Textual's visible inline suggestion is also accepted by Right
        assert field.value == "git init"
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, CommandDialog)
        assert app.screen.command.id == "init"
        assert not (tmp_path / ".git").exists()  # completion and Enter only open review
        await pilot.press("escape")


async def test_search_results_navigation_clear_and_empty_state(tmp_path):
    app = CompanionApp(tmp_path, auto_install=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.press("ctrl+f")
        field = app.query_one("#search", Input)
        field.value = "git lfs prune --f"
        await pilot.pause()
        assert {c.id for c in app.visible_commands} == {"prune-force", "prune-force-preview"}
        await pilot.press("down")
        assert app.query_one("#commands", OptionList).has_focus
        await pilot.press("down")
        assert app.selected_command().id == "prune-force"
        await pilot.press("ctrl+f")
        field.value = "git lfs prune --force --dry-run"
        await pilot.pause()
        assert app.selected_command().id == "prune-force-preview"
        field.value = "git lfs prune --force"
        await pilot.pause()
        assert app.selected_command().id == "prune-force"  # new query chooses its best match
        field.value = "no-such-command-xyz"
        await pilot.pause()
        assert not app.visible_commands
        assert "No matches" in str(app.query_one("#section", Static).render())
        await pilot.press("tab")  # no completion: Tab keeps its normal focus-navigation role
        assert not field.has_focus
        await pilot.press("escape")
        assert app.visible_commands
