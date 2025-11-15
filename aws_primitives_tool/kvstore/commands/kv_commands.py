"""
Key-value commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.kv_operations import get_value, set_value
from ..exceptions import KeyNotFoundError, KVStoreError
from ..utils import error_json, error_text, output_json, output_text


@click.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--ttl", type=int, help="TTL in seconds")
@click.option("--if-not-exists", is_flag=True, help="Only set if key doesn't exist")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def set_command(
    ctx: click.Context,
    key: str,
    value: str,
    ttl: int | None,
    if_not_exists: bool,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Store a key-value pair.

    Sets a value in kvstore. Use --ttl to auto-expire keys.
    Use --if-not-exists to prevent overwriting existing keys.

    Examples:

    \b
        # Set a simple key-value
        aws-primitives-tool kvstore set mykey "hello world"

    \b
        # Set with TTL (auto-expire in 1 hour)
        aws-primitives-tool kvstore set session-token "abc123" --ttl 3600

    \b
        # Set only if key doesn't exist
        aws-primitives-tool kvstore set config "default" --if-not-exists

    \b
    Output Format:
        Returns JSON:
        {"key": "mykey", "value": "hello world", "created_at": 1234567890}
    """
    try:
        if verbose:
            click.echo(f"Setting key '{key}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = set_value(client, key, value, ttl, if_not_exists)

        if text:
            output_text(f"✅ Set {key} = {value}")
            if ttl:
                output_text(f"TTL: {ttl} seconds")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(
                error_text(
                    str(e), "Check table exists with 'aws-primitives-tool kvstore create-table'"
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Check table exists", 3), err=True)
        ctx.exit(3)


@click.command("get")
@click.argument("key")
@click.option("--default", help="Default value if key not found")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def get_command(
    ctx: click.Context,
    key: str,
    default: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Retrieve a value by key.

    Gets a value from kvstore. Use --default to provide fallback value.

    Examples:

    \b
        # Get a key
        aws-primitives-tool kvstore get mykey

    \b
        # Get with default fallback
        aws-primitives-tool kvstore get mykey --default "not found"

    \b
        # Get and extract value with jq
        aws-primitives-tool kvstore get mykey | jq -r '.value'

    \b
    Output Format:
        Returns JSON:
        {"key": "mykey", "value": "hello world", "type": "kv", "created_at": 1234567890}
    """
    try:
        if verbose:
            click.echo(f"Getting key '{key}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = get_value(client, key, default)

        if text:
            if result.get("default"):
                output_text(f"⚠️  {key} = {result['value']} (default)")
            else:
                output_text(f"{key} = {result['value']}")
        else:
            output_json(result)

    except KeyNotFoundError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    f"Use 'aws-primitives-tool kvstore set {key} <value>' or provide --default",
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Set key or use --default", 1), err=True)
        ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
