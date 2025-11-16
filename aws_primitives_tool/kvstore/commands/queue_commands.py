"""
Queue commands for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import click

from ..core.client import DynamoDBClient
from ..core.queue_operations import (
    acknowledge_message,
    get_queue_size,
    peek_queue,
    pop_from_queue,
    push_to_queue,
)
from ..exceptions import KeyExistsError, KVStoreError
from ..logging_config import get_logger, setup_logging
from ..utils import error_json, error_text, output_json, output_text

logger = get_logger(__name__)


@click.command("queue-push")
@click.argument("queue_name")
@click.argument("data")
@click.option(
    "--priority",
    type=int,
    default=5,
    help="Priority level (0-9999999999, default: 5, lower = higher priority)",
)
@click.option("--dedup-id", help="Optional deduplication ID for idempotent pushes")
@click.option("--ttl", type=int, help="Optional TTL in seconds for automatic expiration")
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
def queue_push_command(
    ctx: click.Context,
    queue_name: str,
    data: str,
    priority: int,
    dedup_id: str | None,
    ttl: int | None,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Push a message to a queue with priority and optional deduplication.

    Messages are ordered by priority (lower = higher priority), then by
    timestamp (FIFO within priority), then by UUID (strict ordering).

    The receipt handle returned can be used with queue-ack to acknowledge the message.

    Examples:

    \b
        # Push a message with default priority (5)
        aws-primitives-tool kvstore queue-push notifications "Hello, world!"

    \b
        # Push a high-priority message (lower number = higher priority)
        aws-primitives-tool kvstore queue-push tasks "Critical task" --priority 1

    \b
        # Push with deduplication to prevent duplicates
        aws-primitives-tool kvstore queue-push orders "order-123" \\
            --dedup-id "order-123-payment"

    \b
        # Push with TTL for automatic expiration after 3600 seconds (1 hour)
        aws-primitives-tool kvstore queue-push events "temp-event" \\
            --ttl 3600

    \b
        # Combine priority, dedup, and TTL
        aws-primitives-tool kvstore queue-push jobs "job-data" \\
            --priority 3 \\
            --dedup-id "job-456" \\
            --ttl 7200

    \b
        # Extract receipt for later acknowledgment
        RECEIPT=$(aws-primitives-tool kvstore queue-push tasks "task-data" | jq -r '.receipt')
        # Process the task...
        aws-primitives-tool kvstore queue-ack tasks "$RECEIPT"

    \b
    Output Format:
        Returns JSON:
        {"queue": "notifications", "receipt": "queue:notifications#0000000005#...",
         "priority": 5, "timestamp": 1234567890, "message_uuid": "abc-123",
         "dedup_id": "order-123-payment"}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Pushing message to queue '{queue_name}'")
        logger.debug(f"Priority: {priority}, TTL: {ttl}, Dedup: {dedup_id}")

        client = DynamoDBClient(table, region, profile)
        result = push_to_queue(client, queue_name, data, priority, dedup_id, ttl)

        if text:
            output_text(f"✅ Message pushed to queue '{queue_name}'")
            output_text(f"   Priority: {result['priority']}")
            output_text(f"   Receipt: {result['receipt']}")
            if dedup_id:
                output_text(f"   Dedup ID: {dedup_id}")
            if ttl:
                output_text(f"   TTL: {ttl} seconds")
        else:
            output_json(result)

    except KeyExistsError as e:
        if text:
            click.echo(
                error_text(
                    str(e),
                    "Use a different dedup-id or wait for the existing message to be processed",
                ),
                err=True,
            )
        else:
            click.echo(
                error_json(str(e), "Use different dedup-id or wait for processing", 1),
                err=True,
            )
        ctx.exit(1)

    except ValueError as e:
        if text:
            click.echo(
                error_text(str(e), "Priority must be between 0 and 9999999999"),
                err=True,
            )
        else:
            click.echo(
                error_json(str(e), "Priority must be between 0 and 9999999999", 2),
                err=True,
            )
        ctx.exit(2)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("queue-ack")
@click.argument("queue_name")
@click.argument("receipt")
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
def queue_ack_command(
    ctx: click.Context,
    queue_name: str,
    receipt: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Acknowledge (delete) a message from the queue.

    This operation is idempotent. If the message doesn't exist (already acknowledged
    or expired), it still returns success.

    The receipt handle is the full SK value returned from the queue-pop operation,
    formatted as: queue:{queue_name}#{priority:010d}#{timestamp}#{uuid}

    Examples:

    \b
        # Acknowledge a message using receipt handle
        aws-primitives-tool kvstore queue-ack notifications \\
            "queue:notifications#0000000005#1234567890#abc-123"

    \b
        # Extract receipt from pop and acknowledge
        RECEIPT=$(aws-primitives-tool kvstore queue-pop tasks | jq -r '.receipt')
        aws-primitives-tool kvstore queue-ack tasks "$RECEIPT"

    \b
    Output Format:
        Returns JSON:
        {"queue": "notifications", "receipt": "queue:notifications#...", "acknowledged": true}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Acknowledging message from queue '{queue_name}'")

        client = DynamoDBClient(table, region, profile)
        result = acknowledge_message(client, queue_name, receipt)

        if text:
            output_text(f"✅ Message acknowledged from queue '{queue_name}'")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("queue-peek")
@click.argument("queue_name")
@click.option(
    "--count",
    type=int,
    default=10,
    help="Maximum number of messages to peek (default: 10)",
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
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def queue_peek_command(
    ctx: click.Context,
    queue_name: str,
    count: int,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Peek at messages in a queue without consuming them.

    This is a read-only operation that does not modify message visibility
    or provide receipts. Use this to inspect queue contents without consuming
    messages.

    Examples:

    \b
        # Peek at first 10 messages (default)
        aws-primitives-tool kvstore queue-peek notifications

    \b
        # Peek at first 5 messages
        aws-primitives-tool kvstore queue-peek tasks --count 5

    \b
        # Extract message count with jq
        aws-primitives-tool kvstore queue-peek tasks | jq -r '.count'

    \b
        # Extract first message data with jq
        aws-primitives-tool kvstore queue-peek tasks | jq -r '.items[0].data'

    \b
    Output Format:
        Returns JSON:
        {"queue": "notifications", "items": [
            {"data": {...}, "priority": 5, "timestamp": 1234567890},
            {"data": {...}, "priority": 10, "timestamp": 1234567891}
        ], "count": 2}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Peeking at queue '{queue_name}' (count: {count})")

        client = DynamoDBClient(table, region, profile)
        result = peek_queue(client, queue_name, count)

        if text:
            msg = f"Queue '{queue_name}' has {result['count']} messages (showing up to {count})"
            output_text(msg)
            for i, item in enumerate(result["items"], 1):
                output_text(f"\nMessage {i}:")
                output_text(f"  Priority: {item['priority']}")
                output_text(f"  Timestamp: {item['timestamp']}")
                output_text(f"  Data: {item['data']}")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("queue-size")
@click.argument("queue_name")
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
def queue_size_command(
    ctx: click.Context,
    queue_name: str,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Get the size of a queue.

    This operation efficiently counts queue items using DynamoDB's COUNT query,
    which doesn't consume read capacity for item data.

    Examples:

    \b
        # Get queue size
        aws-primitives-tool kvstore queue-size notifications

    \b
        # Extract size with jq
        aws-primitives-tool kvstore queue-size tasks | jq -r '.size'

    \b
        # Use in shell script to check queue depth
        SIZE=$(aws-primitives-tool kvstore queue-size tasks | jq -r '.size')
        if [ "$SIZE" -gt 100 ]; then
            echo "Queue depth exceeded: $SIZE messages"
        fi

    \b
    Output Format:
        Returns JSON:
        {"queue": "notifications", "size": 42}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Getting size of queue '{queue_name}'")

        client = DynamoDBClient(table, region, profile)
        result = get_queue_size(client, queue_name)

        if text:
            output_text(f"Queue '{queue_name}' has {result['size']} messages")
        else:
            output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)


@click.command("queue-pop")
@click.argument("queue_name")
@click.option(
    "--visibility-timeout",
    type=int,
    default=0,
    help="Visibility timeout in seconds (0=permanent pop, >0=hide temporarily)",
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
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity (-v INFO, -vv DEBUG, -vvv TRACE)",
)
@click.pass_context
def queue_pop_command(
    ctx: click.Context,
    queue_name: str,
    visibility_timeout: int,
    table: str,
    region: str | None,
    profile: str | None,
    text: bool,
    verbose: int,
) -> None:
    """Pop the oldest message from a queue (FIFO).

    This is a two-step atomic operation:
    1. Query for the oldest message (lowest SK value)
    2. Either delete it (permanent pop) or set TTL (temporary hide)

    With visibility_timeout=0 (default), the message is permanently deleted.
    With visibility_timeout>0, the message is hidden for N seconds and will
    reappear if not acknowledged within that time.

    Examples:

    \b
        # Permanent pop (delete message)
        aws-primitives-tool kvstore queue-pop tasks

    \b
        # Pop with visibility timeout (hide for 300 seconds)
        aws-primitives-tool kvstore queue-pop tasks --visibility-timeout 300

    \b
        # Extract message data with jq
        aws-primitives-tool kvstore queue-pop tasks | jq -r '.data'

    \b
        # Pop and acknowledge workflow
        RESULT=$(aws-primitives-tool kvstore queue-pop tasks --visibility-timeout 60)
        # Process message...
        RECEIPT=$(echo "$RESULT" | jq -r '.receipt')
        aws-primitives-tool kvstore queue-ack tasks "$RECEIPT"

    \b
    Output Format:
        Returns JSON when message found:
        {"queue": "tasks", "data": {...}, "receipt": "queue:tasks#...",
         "priority": 5, "timestamp": 1234567890}

        Returns JSON when queue empty:
        {"queue": "tasks", "status": "empty"}
    """
    setup_logging(verbose)

    try:
        logger.info(f"Popping message from queue '{queue_name}'")

        client = DynamoDBClient(table, region, profile)
        result = pop_from_queue(client, queue_name, visibility_timeout)

        if result is None:
            # Queue is empty
            if text:
                output_text(f"Queue '{queue_name}' is empty")
            else:
                output_json({"queue": queue_name, "status": "empty"})
            ctx.exit(1)
        else:
            # Message popped successfully
            if text:
                output_text(f"✅ Popped message from queue '{queue_name}'")
                output_text(f"  Receipt: {result['receipt']}")
                output_text(f"  Priority: {result['priority']}")
                output_text(f"  Timestamp: {result['timestamp']}")
                output_text(f"  Data: {result['data']}")
            else:
                output_json(result)

    except KVStoreError as e:
        if text:
            click.echo(error_text(str(e), "Check table exists and AWS credentials"), err=True)
        else:
            click.echo(error_json(str(e), "Check table and credentials", 3), err=True)
        ctx.exit(3)
