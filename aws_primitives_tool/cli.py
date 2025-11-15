"""CLI entry point for aws-primitives-tool.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from aws_primitives_tool.kvstore.commands.counter_commands import (
    dec_command,
    get_counter_command,
    inc_command,
)
from aws_primitives_tool.kvstore.commands.kv_commands import (
    delete_command,
    exists_command,
    get_command,
    list_command,
    set_command,
)
from aws_primitives_tool.kvstore.commands.lock_commands import (
    lock_acquire_command,
    lock_check_command,
    lock_extend_command,
    lock_release_command,
)
from aws_primitives_tool.kvstore.commands.table_commands import (
    create_table_command,
    drop_table_command,
)


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """A CLI that provides AWS serverless primitives as composable CLI commands"""
    pass


@main.group("kvstore")
def kvstore() -> None:
    """DynamoDB-backed key-value store with atomic operations"""
    pass


# Register table commands
kvstore.add_command(create_table_command)
kvstore.add_command(drop_table_command)

# Register kv commands
kvstore.add_command(set_command)
kvstore.add_command(get_command)
kvstore.add_command(exists_command)
kvstore.add_command(delete_command)
kvstore.add_command(list_command)

# Register counter commands
kvstore.add_command(inc_command)
kvstore.add_command(dec_command)
kvstore.add_command(get_counter_command)

# Register lock commands
kvstore.add_command(lock_acquire_command)
kvstore.add_command(lock_release_command)
kvstore.add_command(lock_extend_command)
kvstore.add_command(lock_check_command)


if __name__ == "__main__":
    main()
