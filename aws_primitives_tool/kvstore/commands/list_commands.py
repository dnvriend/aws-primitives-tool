"""
List commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.list_operations import append_to_list, get_range, pop_first, pop_last, prepend_to_list
from ..exceptions import KVStoreError
from ..utils import (
    error_json,
    error_text,
    output_json,
    output_text,
    validate_key,
    validate_table_name,
)


@click.command("lpush")
@click.argument("list_name")
@click.argument("value")
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
def lpush_command(
    ctx: click.Context,
    list_name: str,
    value: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Prepend value to list.

    This operation adds an item to the front of a list (LIFO order).
    Each lpush creates a new item with a unique negative timestamp as sort key,
    ensuring newest items appear first when querying.

    Examples:

    \b
        # Add item to front of list
        aws-primitives-tool kvstore lpush mylist "first item"

    \b
        # Add with verbose output
        aws-primitives-tool kvstore lpush mylist "important task" --verbose

    \b
        # Multiple lpush operations build list in LIFO order
        aws-primitives-tool kvstore lpush tasks "task3"
        aws-primitives-tool kvstore lpush tasks "task2"
        aws-primitives-tool kvstore lpush tasks "task1"
        # List order after queries: task1, task2, task3

    \b
        # Use in shell script
        for task in "compile" "test" "deploy"; do
            aws-primitives-tool kvstore lpush build-steps "$task"
        done

    \b
        # Add JSON data to list
        aws-primitives-tool kvstore lpush events '{"type":"login","user":"alice"}'

    \b
    Output Format:
        Returns JSON:
        {"list": "mylist", "value": "first item", "position": "head"}
    """
    try:
        # Validate inputs
        validate_table_name(table)
        validate_key(list_name)

        if verbose:
            click.echo(f"Prepending value to list '{list_name}'...", err=True)

        # Execute operation
        client = DynamoDBClient(table, region, profile)
        result = prepend_to_list(client, list_name, value)

        # Output result
        if text:
            output_text(f"Added '{value}' to front of list '{list_name}'")
        else:
            output_json(result)

    except ValueError as e:
        # Validation errors
        if text:
            click.echo(error_text(str(e), "Provide valid list name and value"), err=True)
        else:
            click.echo(error_json(str(e), "Provide valid list name and value", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        # AWS/DynamoDB errors
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("rpush")
@click.argument("list_name")
@click.argument("value")
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
def rpush_command(
    ctx: click.Context,
    list_name: str,
    value: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Append value to list.

    This operation adds an item to the end of a list (FIFO order).
    Each rpush creates a new item with a unique positive timestamp as sort key,
    ensuring oldest items appear first when querying.

    Examples:

    \b
        # Add item to end of list
        aws-primitives-tool kvstore rpush mylist "last item"

    \b
        # Build FIFO queue with rpush
        aws-primitives-tool kvstore rpush queue "first"
        aws-primitives-tool kvstore rpush queue "second"
        aws-primitives-tool kvstore rpush queue "third"
        # List order: first, second, third

    \b
        # Add with verbose output
        aws-primitives-tool kvstore rpush mylist "item" --verbose

    \b
        # Use in shell script to build ordered list
        for item in "step1" "step2" "step3"; do
            aws-primitives-tool kvstore rpush workflow "$item"
        done

    \b
        # Add JSON data to list
        aws-primitives-tool kvstore rpush events '{"type":"logout","user":"bob"}'

    \b
    Output Format:
        Returns JSON:
        {"list": "mylist", "value": "last item", "position": "tail"}
    """
    try:
        # Validate inputs
        validate_table_name(table)
        validate_key(list_name)

        if verbose:
            click.echo(f"Appending value to list '{list_name}'...", err=True)

        # Execute operation
        client = DynamoDBClient(table, region, profile)
        result = append_to_list(client, list_name, value)

        # Output result
        if text:
            output_text(f"Added '{value}' to end of list '{list_name}'")
        else:
            output_json(result)

    except ValueError as e:
        # Validation errors
        if text:
            click.echo(error_text(str(e), "Provide valid list name and value"), err=True)
        else:
            click.echo(error_json(str(e), "Provide valid list name and value", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        # AWS/DynamoDB errors
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("lpop")
@click.argument("list_name")
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--quiet", is_flag=True, help="Suppress output")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def lpop_command(
    ctx: click.Context,
    list_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    """Remove and return first item from list.

    Exit codes: 0=success, 1=list empty, 3=error

    Examples:

    \b
        # Pop first item
        aws-primitives-tool kvstore lpop mylist --table kvstore-table

    \b
        # Use in shell script
        value=$(aws-primitives-tool kvstore lpop tasks --table kvstore-table | jq -r '.value')
        if [ $? -eq 0 ]; then
            echo "Processing: $value"
        fi

    \b
        # Pop with text output
        aws-primitives-tool kvstore lpop mylist --text

    \b
        # Pop items until list is empty
        while aws-primitives-tool kvstore lpop tasks --quiet 2>/dev/null; do
            echo "Processed one task"
        done
    """
    try:
        # Validate inputs
        validate_table_name(table)
        validate_key(list_name)

        if verbose:
            click.echo(f"Popping first item from list '{list_name}'...", err=True)

        # Execute operation
        client = DynamoDBClient(table, region, profile)
        result = pop_first(client, list_name)

        if result is None:
            if text:
                output_text(f"List '{list_name}' is empty", quiet)
            else:
                output_json({"list": list_name, "exists": False}, quiet)
            ctx.exit(1)

        # Output result
        if text:
            output_text(f"Popped '{result['value']}' from list '{list_name}'", quiet)
        else:
            output_json(result, quiet)

    except ValueError as e:
        # Validation errors
        if text:
            click.echo(error_text(str(e), "Provide valid list name"), err=True)
        else:
            click.echo(error_json(str(e), "Provide valid list name", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        # AWS/DynamoDB errors
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("lrange")
@click.argument("list_name")
@click.argument("start", type=int, default=0)
@click.argument("stop", type=int, required=False)
@click.option(
    "--table",
    envvar="KVSTORE_TABLE",
    default="aws-primitives-tool-kvstore",
    help="DynamoDB table name",
)
@click.option("--region", envvar="AWS_REGION", help="AWS region")
@click.option("--profile", envvar="AWS_PROFILE", help="AWS profile")
@click.option("--text", is_flag=True, help="Output as human-readable text")
@click.option("--quiet", is_flag=True, help="Suppress output")
@click.option("--verbose", "-V", is_flag=True, help="Verbose output")
@click.pass_context
def lrange_command(
    ctx: click.Context,
    list_name: str,
    start: int,
    stop: int | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    quiet: bool,
    verbose: bool,
) -> None:
    """Get range of items from list.

    Uses Python slicing: start (inclusive), stop (exclusive).
    Negative indices supported.

    Examples:

    \b
        # Get first 5 items
        aws-primitives-tool kvstore lrange mylist 0 5

    \b
        # Get all items
        aws-primitives-tool kvstore lrange mylist

    \b
        # Get last 3 items
        aws-primitives-tool kvstore lrange mylist -3

    \b
        # Get items 2-4 (indices 2 and 3)
        aws-primitives-tool kvstore lrange mylist 2 4

    \b
        # Extract items with jq
        aws-primitives-tool kvstore lrange mylist 0 5 | jq -r '.items[]'

    \b
        # Use in shell script
        ITEMS=$(aws-primitives-tool kvstore lrange tasks 0 10 | jq -r '.items[]')
        for item in $ITEMS; do
            echo "Processing: $item"
        done

    \b
    Output Format:
        Returns JSON:
        {"list": "mylist", "start": 0, "stop": 5, "count": 5, "items": ["item1", "item2", ...]}
    """
    try:
        # Validate inputs
        validate_table_name(table)
        validate_key(list_name)

        if verbose:
            click.echo(
                f"Getting range from list '{list_name}' (start={start}, stop={stop})...", err=True
            )

        # Execute operation
        client = DynamoDBClient(table, region, profile)
        result = get_range(client, list_name, start, stop)

        # Output result
        if text:
            if result["count"] == 0:
                output_text("No items in range", quiet)
            else:
                output_text(f"Found {result['count']} items:", quiet)
                for i, value in enumerate(result["items"], start):
                    output_text(f"  [{i}] {value}", quiet)
        else:
            output_json(result, quiet)

    except ValueError as e:
        # Validation errors
        if text:
            click.echo(error_text(str(e), "Provide valid list name and indices"), err=True)
        else:
            click.echo(error_json(str(e), "Provide valid list name and indices", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        # AWS/DynamoDB errors
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("rpop")
@click.argument("list_name")
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
def rpop_command(
    ctx: click.Context,
    list_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: bool,
) -> None:
    """Remove and return last item from list.

    This operation removes and returns the item with the largest sort key (tail of list).
    For lists built with lpush (negative timestamps), this gives FIFO behavior (oldest first).
    For lists built with rpush (positive timestamps), this gives LIFO behavior (most recent first).

    Exit codes: 0=success, 1=list empty, 2=validation error, 3=AWS error

    Examples:

    \b
        # Pop last item
        aws-primitives-tool kvstore rpop mylist

    \b
        # Use as stack (LIFO with rpush/rpop)
        aws-primitives-tool kvstore rpush stack "bottom"
        aws-primitives-tool kvstore rpush stack "top"
        aws-primitives-tool kvstore rpop stack
        # Returns: "top"

    \b
        # Use as queue (FIFO with lpush/rpop)
        aws-primitives-tool kvstore lpush queue "first"
        aws-primitives-tool kvstore lpush queue "second"
        aws-primitives-tool kvstore rpop queue
        # Returns: "first"

    \b
        # Extract value with jq
        aws-primitives-tool kvstore rpop mylist | jq -r '.value'

    \b
        # Use in shell script to process list items
        while true; do
            RESULT=$(aws-primitives-tool kvstore rpop tasks)
            if [ $? -eq 1 ]; then
                echo "Queue empty"
                break
            fi
            VALUE=$(echo "$RESULT" | jq -r '.value')
            echo "Processing: $VALUE"
        done

    \b
    Output Format:
        Returns JSON when item found:
        {"list": "mylist", "value": "item data", "position": "tail"}

        Returns JSON when list empty:
        {"list": "mylist", "exists": false}
    """
    try:
        # Validate inputs
        validate_table_name(table)
        validate_key(list_name)

        if verbose:
            click.echo(f"Popping last item from list '{list_name}'...", err=True)

        # Execute operation
        client = DynamoDBClient(table, region, profile)
        result = pop_last(client, list_name)

        # Handle empty list
        if result is None:
            if text:
                output_text(f"List '{list_name}' is empty")
            else:
                output_json({"list": list_name, "exists": False})
            ctx.exit(1)

        # Output result
        if text:
            output_text(f"Popped '{result['value']}' from list '{list_name}'")
        else:
            output_json(result)

    except ValueError as e:
        # Validation errors
        if text:
            click.echo(error_text(str(e), "Provide valid list name"), err=True)
        else:
            click.echo(error_json(str(e), "Provide valid list name", 2), err=True)
        ctx.exit(2)

    except KVStoreError as e:
        # AWS/DynamoDB errors
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
