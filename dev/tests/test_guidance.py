from git_companion.app import command_help
from git_companion.catalog import COMMANDS
from git_companion.guidance import GUIDANCE


def test_every_action_has_a_short_hint_and_two_valid_examples():
    assert set(GUIDANCE) == {command.id for command in COMMANDS}
    for command in COMMANDS:
        assert 10 <= len(command.hint) <= 90, command.id
        assert len(command.examples) == 2
        labels = {example.label for example in command.examples}
        assert len(labels) == 2, command.id
        for example in command.examples:
            assert set(dict(example.values)) <= {field.name for field in command.fields}
            args = command.build(dict(example.values))
            assert args[0] == "git" and len(args) > 1
        assert command.description in command_help(command)
        assert "EXAMPLES" in command_help(command)
