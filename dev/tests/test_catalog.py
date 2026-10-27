import pytest

from git_companion.catalog import BY_ID, COMMANDS, complete, search


def test_unique_ids_and_all_commands_build():
    assert len(BY_ID) == len(COMMANDS)
    for command in COMMANDS:
        values = {field.name: field.default or "example" for field in command.fields}
        args = command.build(values)
        assert args[0] == "git"
        assert not any("{" in arg and "}" in arg for arg in args[1:] if arg != "stash@{0}")


def test_shell_metacharacters_remain_one_literal_argument():
    message = 'fix: "quotes"; $(touch hacked) & echo nope'
    assert BY_ID["commit"].build({"message": message}) == ["git", "commit", "-m", message]
    assert BY_ID["stage"].build({"path": "-file name.txt"}) == ["git", "add", "--", "-file name.txt"]


def test_option_injection_and_missing_values_rejected():
    with pytest.raises(ValueError):
        BY_ID["switch"].build({"branch": "--detach"})
    with pytest.raises(ValueError):
        BY_ID["commit"].build({"message": ""})
    with pytest.raises(ValueError):
        BY_ID["stage"].build({"path": "x\x00y"})


def test_prune_actions_include_previews_and_warnings():
    assert "--dry-run" in BY_ID["prune-preview"].build()
    assert "--force" in BY_ID["prune-force"].build()
    assert "--dry-run" in BY_ID["prune-force-preview"].build()
    assert BY_ID["prune-force"].risk
    assert not BY_ID["prune-preview"].risk


def test_search_across_intents():
    assert "prune-force" in {c.id for c in search("prune force")}
    assert all(c.category == "lfs" for c in search("", "lfs"))
    assert [c.id for c in search("", "recommended", ("commit", "staged"))] == ["commit", "staged"]


def test_every_command_is_findable_by_name_and_full_git_syntax():
    for command in COMMANDS:
        assert command in search(command.title), command.id
        assert command in search(command.command_line.upper()), command.id
        assert command in search(command.completion), command.id
    assert search("git lfs prune --force")[0].id == "prune-force"
    assert search("git lfs prune --dry-run")[0].id == "prune-preview"
    assert {command.id for command in search("git")} == set(BY_ID)
    assert "lfs-track" in {command.id for command in search("Photoshop")}


def test_autocomplete_for_command_syntax_and_friendly_titles():
    assert complete("git com") == "git commit -m"
    assert complete("lfs pru").startswith("lfs prune")
    assert complete("Create a com") == "Create a commit"
    assert complete("git lfs prune --dry-r") == "git lfs prune --dry-run --verbose"
    assert complete("git lfs prune --force") is None
    assert complete("git commit -m") is None
    assert complete("") is None
    assert complete("a command that does not exist") is None
