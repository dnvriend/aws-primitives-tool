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
from aws_primitives_tool.kvstore.commands.info_commands import (
    info_command,
    stats_command,
    status_command,
)
from aws_primitives_tool.kvstore.commands.kv_commands import (
    delete_command,
    exists_command,
    get_command,
    list_command,
    set_command,
)
from aws_primitives_tool.kvstore.commands.leader_commands import (
    leader_check_command,
    leader_elect_command,
    leader_heartbeat_command,
    leader_resign_command,
)
from aws_primitives_tool.kvstore.commands.list_commands import (
    lpop_command,
    lpush_command,
    lrange_command,
    rpop_command,
    rpush_command,
)
from aws_primitives_tool.kvstore.commands.lock_commands import (
    lock_acquire_command,
    lock_check_command,
    lock_extend_command,
    lock_release_command,
)
from aws_primitives_tool.kvstore.commands.queue_commands import (
    queue_ack_command,
    queue_peek_command,
    queue_pop_command,
    queue_push_command,
    queue_size_command,
)
from aws_primitives_tool.kvstore.commands.set_commands import (
    sadd_command,
    scard_command,
    sismember_command,
    smembers_command,
    srem_command,
)
from aws_primitives_tool.kvstore.commands.table_commands import (
    create_table_command,
    delete_table_command,
    drop_table_command,
)
from aws_primitives_tool.kvstore.commands.transaction_commands import transaction_command


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
kvstore.add_command(delete_table_command)  # Alias for drop-table

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

# Register queue commands
kvstore.add_command(queue_push_command)
kvstore.add_command(queue_pop_command)
kvstore.add_command(queue_peek_command)
kvstore.add_command(queue_size_command)
kvstore.add_command(queue_ack_command)

# Register leader commands
kvstore.add_command(leader_elect_command)
kvstore.add_command(leader_heartbeat_command)
kvstore.add_command(leader_check_command)
kvstore.add_command(leader_resign_command)

# Register set commands
kvstore.add_command(sadd_command)
kvstore.add_command(srem_command)
kvstore.add_command(sismember_command)
kvstore.add_command(smembers_command)
kvstore.add_command(scard_command)


# Register list commands
kvstore.add_command(lpush_command)
kvstore.add_command(rpush_command)
kvstore.add_command(lpop_command)
kvstore.add_command(rpop_command)
kvstore.add_command(lrange_command)

# Register transaction commands
kvstore.add_command(transaction_command)

# Register info/stats/status commands
kvstore.add_command(info_command)
kvstore.add_command(stats_command)
kvstore.add_command(status_command)

if __name__ == "__main__":
    main()
