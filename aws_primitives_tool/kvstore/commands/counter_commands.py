"""
Counter commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.counter_operations import decrement_counter, get_counter, increment_counter
from ..exceptions import KeyNotFoundError, KVStoreError
from ..logging_config import get_logger, setup_logging
from ..utils import error_json, error_text, output_json, output_text

logger = get_logger(__name__)


@click.command("inc")
@click.argument("key")
@click.option("--by", type=int, default=1, help="Amount to increment (default: 1)")
@click.option("--create", is_flag=True, help="Create counter if missing")
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
def inc_command(
    ctx: click.Context,
    key: str,
    by: int,
    create: bool,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Atomically increment a counter.

    Increments are atomic and thread-safe. DynamoDB guarantees no race conditions.

    Examples:

    \b
        # Increment by 1
        aws-primitives-tool kvstore inc api-requests

    \b
        # Increment by custom amount
        aws-primitives-tool kvstore inc api-requests --by 10

    \b
        # Create counter if missing (initialize to 0)
        aws-primitives-tool kvstore inc new-counter --create

    \b
    Output Format:
        Returns JSON:
        {"key": "api-requests", "value": 123, "updated_at": 1234567890}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Incrementing counter '{key}' by {by}")
        logger.debug(f"Table: {table}, Region: {region}, Create: {create}")

        client = DynamoDBClient(table, region, profile)
        result = increment_counter(client, key, by, create)

        if text:
            output_text(f"✅ {key} = {result['value']}")
        else:
            output_json(result)

    except KeyNotFoundError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    f"Use 'aws-primitives-tool kvstore inc {key} --create' to initialize",
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Use --create flag to initialize", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("dec")
@click.argument("key")
@click.option("--by", type=int, default=1, help="Amount to decrement (default: 1)")
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
def dec_command(
    ctx: click.Context,
    key: str,
    by: int,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Atomically decrement a counter.

    Decrements are atomic and thread-safe. Counter must exist before decrementing.

    Examples:

    \b
        # Decrement by 1
        aws-primitives-tool kvstore dec rate-limit-remaining

    \b
        # Decrement by custom amount
        aws-primitives-tool kvstore dec rate-limit-remaining --by 5

    \b
    Output Format:
        Returns JSON:
        {"key": "rate-limit-remaining", "value": 95, "updated_at": 1234567890}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Decrementing counter '{key}' by {by}")
        logger.debug(f"Table: {table}, Region: {region}")

        client = DynamoDBClient(table, region, profile)
        result = decrement_counter(client, key, by)

        if text:
            output_text(f"✅ {key} = {result['value']}")
        else:
            output_json(result)

    except KeyNotFoundError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    f"Use 'aws-primitives-tool kvstore inc {key} --create' to create it first",
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Create counter first with 'inc --create'", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("get-counter")
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
def get_counter_command(
    ctx: click.Context,
    key: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Read counter value.

    Retrieves the current value of a counter.

    Examples:

    \b
        # Get counter value
        aws-primitives-tool kvstore get-counter api-requests

    \b
        # Extract value with jq
        aws-primitives-tool kvstore get-counter api-requests | jq -r '.value'

    \b
    Output Format:
        Returns JSON:
        {"key": "api-requests", "value": 12345, "type": "counter",
         "created_at": 1234567890, "updated_at": 1234567900}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Getting counter '{key}'")
        logger.debug(f"Table: {table}, Region: {region}")

        client = DynamoDBClient(table, region, profile)
        result = get_counter(client, key)

        if text:
            output_text(f"{key} = {result['value']}")
        else:
            output_json(result)

    except KeyNotFoundError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    f"Use 'aws-primitives-tool kvstore inc-counter {key}' to create it",
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Create counter with inc-counter", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
