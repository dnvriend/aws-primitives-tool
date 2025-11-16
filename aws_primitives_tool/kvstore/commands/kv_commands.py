"""
Key-value commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.kv_operations import delete_value, exists_value, get_value, list_keys, set_value
from ..doc_data import get_doc_data
from ..doc_generator import display_doc, generate_doc
from ..exceptions import ConditionFailedError, KeyNotFoundError, KVStoreError
from ..utils import error_json, error_text, output_json, output_text


@click.command("set")
@click.argument("key", required=False)
@click.argument("value", required=False)
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
@click.option(
    "--doc",
    is_flag=True,
    help="Show AI agent-optimized documentation (CS semantics, guarantees, composability)",  # noqa: E501
)
@click.pass_context
def set_command(
    ctx: click.Context,
    key: str | None,
    value: str | None,
    ttl: int | None,
    if_not_exists: bool,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
    doc: bool,
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
    # Handle --doc flag
    if doc:
        doc_data = get_doc_data("set")
        if doc_data:
            doc_content = generate_doc(**doc_data)
            display_doc(doc_content)
        else:
            click.echo("Documentation not available for: set", err=True)
            ctx.exit(1)

    # Validate required arguments when not using --doc
    if key is None or value is None:
        click.echo("Error: Missing required arguments KEY and VALUE", err=True)
        click.echo("Try 'aws-primitives-tool kvstore set --help' for usage", err=True)
        ctx.exit(2)

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


@click.command("exists")
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
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def exists_command(
    ctx: click.Context,
    key: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Check if a key exists.

    Exit codes:
    - 0: Key exists
    - 1: Key does not exist
    - 3: AWS error (table not found, permissions, etc.)

    Examples:

    \b
        # Check if key exists
        aws-primitives-tool kvstore exists mykey

    \b
        # Use in shell script
        if aws-primitives-tool kvstore exists mykey; then
            echo "Key exists"
        else
            echo "Key does not exist"
        fi

    \b
    Output Format:
        Returns JSON:
        {"key": "mykey", "exists": true}
    """
    try:
        if verbose:
            click.echo(f"Checking if key '{key}' exists...", err=True)

        client = DynamoDBClient(table, region, profile)
        exists = exists_value(client, key)

        if text:
            if exists:
                output_text(f"✅ Key '{key}' exists")
            else:
                output_text(f"❌ Key '{key}' does not exist")
        else:
            output_json({"key": key, "exists": exists})

        if not exists:
            ctx.exit(1)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("delete")
@click.argument("key")
@click.option("--if-value", help="Only delete if value matches")
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
def delete_command(
    ctx: click.Context,
    key: str,
    if_value: str | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Delete a key-value pair.

    Deletion is idempotent - deleting a non-existent key succeeds.

    Examples:

    \b
        # Delete a key
        aws-primitives-tool kvstore delete mykey

    \b
        # Conditional delete (only if value matches)
        aws-primitives-tool kvstore delete config/api-key --if-value "old-value"

    \b
    Output Format:
        Returns JSON:
        {"key": "mykey", "deleted": true}
    """
    try:
        if verbose:
            click.echo(f"Deleting key '{key}'...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = delete_value(client, key, if_value)

        if text:
            output_text(f"✅ Deleted {key}")
        else:
            output_json(result)

    except ConditionFailedError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    (
                        f"Value does not match. Check current value with "
                        f"'aws-primitives-tool kvstore get {key}'"
                    ),
                ),
                err=True,
            )
        else:
            click.echo(error_json(str(e), "Value does not match expected", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("list")
@click.argument("prefix", default="")
@click.option("--limit", type=int, help="Maximum number of keys to return")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "keys"]),
    default="json",
    help="Output format",
)
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
def list_command(
    ctx: click.Context,
    prefix: str,
    limit: int | None,
    output_format: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """List keys by prefix.

    Lists all keys matching the given prefix. If no prefix provided,
    lists all keys in the kvstore.

    Examples:

    \b
        # List all keys
        aws-primitives-tool kvstore list

    \b
        # List keys with prefix
        aws-primitives-tool kvstore list config/

    \b
        # List with limit
        aws-primitives-tool kvstore list --limit 10

    \b
        # Output only keys (not full objects)
        aws-primitives-tool kvstore list --format keys

    \b
    Output Format:
        Returns JSON:
        {"prefix": "config/", "keys": [...], "count": 2}

        With --format keys:
        config/api-key
        config/db-url
    """
    try:
        if verbose:
            if prefix:
                click.echo(f"Listing keys with prefix '{prefix}'...", err=True)
            else:
                click.echo("Listing all keys...", err=True)

        client = DynamoDBClient(table, region, profile)
        result = list_keys(client, prefix, limit)

        if output_format == "keys":
            # Output only key names, one per line
            for key_data in result["keys"]:
                print(key_data["key"])
        elif text:
            if result["count"] == 0:
                output_text(f"No keys found with prefix '{prefix}'")
            else:
                output_text(f"Found {result['count']} key(s):")
                for key_data in result["keys"]:
                    output_text(f"  {key_data['key']}")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
