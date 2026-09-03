"""Basic scaffold tests.

These tests are intentionally lightweight. They help ensure the package imports
and the directory structure remains stable while implementation begins.
"""

from piano_difficulty.cli.main import build_parser


def test_cli_scaffold_has_extract_command() -> None:
    """The scaffold should expose the planned top-level CLI shape."""

    parser = build_parser()
    action_dests = {action.dest for action in parser._actions}
    assert "command" in action_dests

