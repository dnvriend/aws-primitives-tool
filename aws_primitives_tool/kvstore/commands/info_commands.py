"""
Info commands for kvstore - metadata and status.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.info_operations import get_key_info, get_table_stats
from ..core.status_operations import get_table_status
from ..exceptions import KeyNotFoundError, KVStoreError, TableNotFoundError
from ..logging_config import get_logger, setup_logging
from ..utils import error_json, error_text, output_json, output_text

logger = get_logger(__name__)


@click.command("info")
@click.argument("key")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def info_command(
    ctx: click.Context,
    key: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Get metadata about a specific key.

    Shows key type, timestamps, size, and type-specific information.

    Examples:

    \b
        # Get info about a key
        aws-primitives-tool kvstore info mykey

    \b
        # Get counter info
        aws-primitives-tool kvstore info api-requests

    \b
        # Get list info
        aws-primitives-tool kvstore info tasks

    \b
    Output Format:
        Returns JSON with key metadata:
        {"key": "mykey", "type": "kv", "created_at": 1234567890,
         "updated_at": 1234567890, "value_size": 128}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Getting info for key '{key}'")
        logger.debug(f"Table: {table}, Region: {region}")

        client = DynamoDBClient(table, region, profile)
        result = get_key_info(client, key)

        if text:
            output_text(f"Key: {result['key']}")
            output_text(f"Type: {result['type']}")
            if "created_at" in result:
                output_text(f"Created: {result['created_at']}")
            if "updated_at" in result:
                output_text(f"Updated: {result['updated_at']}")
            if "ttl" in result:
                output_text(f"TTL: {result['ttl']}")

            # Type-specific info
            if "value" in result:
                output_text(f"Value: {result['value']}")
            if "value_size" in result:
                output_text(f"Size: {result['value_size']} bytes")
            if "item_count" in result:
                output_text(f"Items: {result['item_count']}")
            if "member_count" in result:
                output_text(f"Members: {result['member_count']}")
            if "owner" in result:
                output_text(f"Owner: {result['owner']}")
            if "node_id" in result:
                output_text(f"Leader: {result['node_id']}")
        else:
            output_json(result)

    except KeyNotFoundError as e:
        if text:
            click.echo(error_text(str(e), "Check key name with 'list' command"), err=True)
        else:
            click.echo(error_json(str(e), "Key not found", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("stats")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def stats_command(
    ctx: click.Context,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Get inventory of all primitives in the table.

    Scans entire table and shows counts/values for all primitives.

    Examples:

    \b
        # Get table inventory
        aws-primitives-tool kvstore stats

    \b
        # Get stats with text output
        aws-primitives-tool kvstore stats --text

    \b
        # Get stats from specific table
        aws-primitives-tool kvstore stats --table my-kvstore

    \b
    Output Format:
        Returns JSON with primitive inventory:
        {"counters": [...], "lists": [...], "sets": [...],
         "queues": [...], "locks": [...], "leaders": [...],
         "kv_pairs": 45, "total_items": 248}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Getting stats for table '{table}'")
        logger.debug(f"Region: {region}")

        client = DynamoDBClient(table, region, profile)
        result = get_table_stats(client)

        if text:
            output_text(f"=== Table Statistics: {table} ===\n")

            if result["counters"]:
                output_text("Counters:")
                for counter in result["counters"]:
                    output_text(f"  {counter['key']}: {counter['value']}")

            if result["lists"]:
                output_text("\nLists:")
                for lst in result["lists"]:
                    output_text(f"  {lst['key']}: {lst['size']} items")

            if result["sets"]:
                output_text("\nSets:")
                for s in result["sets"]:
                    output_text(f"  {s['key']}: {s['size']} members")

            if result["queues"]:
                output_text("\nQueues:")
                for q in result["queues"]:
                    output_text(f"  {q['key']}: {q['size']} pending")

            if result["locks"]:
                output_text("\nActive Locks:")
                for lock in result["locks"]:
                    output_text(f"  {lock['key']} (owner: {lock['owner']})")

            if result["leaders"]:
                output_text("\nLeaders:")
                for leader in result["leaders"]:
                    output_text(f"  {leader['key']}: {leader['leader']}")

            output_text(f"\nKV Pairs: {result['kv_pairs']}")
            output_text(f"Total Items: {result['total_items']}")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("status")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def status_command(
    ctx: click.Context,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Get DynamoDB table status and CloudWatch metrics.

    Shows table health, capacity, and usage statistics.

    Examples:

    \b
        # Get table status
        aws-primitives-tool kvstore status

    \b
        # Get status for specific table
        aws-primitives-tool kvstore status --table my-kvstore

    \b
        # Get status with text output
        aws-primitives-tool kvstore status --text

    \b
    Output Format:
        Returns JSON with table status:
        {"table_name": "...", "status": "ACTIVE", "item_count": 248,
         "size_bytes": 102400, "billing_mode": "PAY_PER_REQUEST",
         "read_consumed_last_hour": 1523}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Getting status for table '{table}'")
        logger.debug(f"Region: {region}")

        result = get_table_status(table, region, profile)

        if text:
            output_text(f"=== Table Status: {result['table_name']} ===\n")
            output_text(f"Status: {result['status']}")
            output_text(f"ARN: {result['arn']}")
            output_text(f"Created: {result['creation_time']}")
            output_text(f"Items: {result['item_count']:,}")
            output_text(f"Size: {result['size_bytes']:,} bytes")
            output_text(f"Billing: {result['billing_mode']}")

            if "read_capacity" in result:
                output_text("\nProvisioned Capacity:")
                output_text(f"  Read: {result['read_capacity']} units")
                output_text(f"  Write: {result['write_capacity']} units")

            if "read_consumed_last_hour" in result:
                output_text("\nUsage (Last Hour):")
                output_text(f"  Read: {result['read_consumed_last_hour']:.2f} units")
                output_text(f"  Write: {result.get('write_consumed_last_hour', 0):.2f} units")

            if "global_secondary_indexes" in result:
                output_text(f"\nGlobal Secondary Indexes: {result['global_secondary_indexes']}")
        else:
            output_json(result)

    except TableNotFoundError as e:
        if text:
            click.echo(error_text(str(e), "Check table name"), err=True)
        else:
            click.echo(error_json(str(e), "Table not found", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check AWS credentials and permissions"), err=True)
        else:
            click.echo(error_json(str(e), "Check credentials and permissions", 3), err=True)
        ctx.exit(3)
