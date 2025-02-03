import json
import subprocess
from typing import List, Optional

import click

from lib.router import Router
from optypes.op_types import Item

router = Router()


def parse_selection(selection: str) -> str:
    """Parse the user's input and return the corresponding action."""
    actions = list(router.action_opts.keys())
    if selection.isdigit():
        index = int(selection) - 1
        if 0 <= index < len(actions):
            return actions[index]
    elif selection in actions:
        return selection

    raise click.BadParameter(
        "Invalid selection. Use --help to see valid options."
    )


@click.command(context_settings=dict(help_option_names=["--help", "-h"]))
@click.option(
    "--selection",
    prompt="Please select which action you'd like to take:\n\n"
    + router.get_help_text()
    + "\n",
    show_choices=False,
)
@click.option(
    "--testing",
    default=False,
    is_flag=True,
    help="Enable testing mode.",
)
def main(selection: str, testing: bool):
    """Main entry point for selecting and executing an action."""
    router = Router(testing)
    action = parse_selection(selection)
    click.echo(f"You selected: {action}")
    result = router.run_action(action)
    if result:
        click.echo(result)


def show_help(ctx):
    click.echo(
        "Available actions, select either a number or enter the relevant command:\n"
    )
    click.echo(router.get_help_text())
    ctx.exit()


if __name__ == "__main__":
    main()
