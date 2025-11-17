"""
Queue operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
import uuid
from typing import Any

from boto3.dynamodb.conditions import Key

from ..constants import (
    ATTR_METADATA,
    ATTR_PK,
    ATTR_SK,
    ATTR_TTL,
    ATTR_VALUE,
    PREFIX_QUEUE,
)
from ..exceptions import ConditionFailedError, KeyExistsError, KeyNotFoundError, KVStoreError
from ..models import ItemType
from ..utils import format_key
from .client import DynamoDBClient


def push_to_queue(
    client: DynamoDBClient,
    queue_name: str,
    data: str,
    priority: int = 5,
    dedup_id: str | None = None,
    ttl: int | None = None,
) -> dict[str, Any]:
    """
    Push a message to a queue with priority and optional deduplication.

    Messages are ordered by priority (higher number = higher priority), then by
    timestamp (FIFO within priority).

    Args:
        client: DynamoDB client
        queue_name: Name of the queue
        data: Message data to store
        priority: Priority level (0-9999999999, default: 5, higher = higher priority)
        dedup_id: Optional deduplication ID for idempotent pushes
        ttl: Optional TTL in seconds from now for automatic expiration

    Returns:
        Dictionary with queue name, receipt (SK), priority, and timestamp

    Raises:
        KeyExistsError: If dedup_id already exists in the queue
        KVStoreError: For other DynamoDB errors
    """
    # Validate priority range
    if not 0 <= priority <= 9999999999:
        raise ValueError("Priority must be between 0 and 9999999999")

    # Check for duplicate if dedup_id provided
    if dedup_id:
        pk = format_key(PREFIX_QUEUE, queue_name)
        existing = client.query(
            key_condition_expression=Key(ATTR_PK).eq(pk),
            limit=1000,  # Reasonable limit for dedup check
        )
        for existing_item in existing:
            if existing_item.get(ATTR_METADATA, {}).get("dedup_id") == dedup_id:
                raise KeyExistsError(
                    f"Message with dedup_id '{dedup_id}' already exists in queue '{queue_name}'"
                )

    # Generate timestamp with microseconds for FIFO ordering
    now = time.time()
    timestamp_micros = int(now * 1_000_000)
    unix_ts = int(now)

    # Generate UUID for tie-breaking
    message_uuid = str(uuid.uuid4())

    # Invert priority for sorting: higher number = higher priority = smaller SK
    inverted_priority = 9999999999 - priority
    # Construct composite sort key: {inverted_priority:010d}#{timestamp}#{uuid}
    sk = f"{inverted_priority:010d}#{timestamp_micros}#{message_uuid}"
    pk = format_key(PREFIX_QUEUE, queue_name)

    # Build item
    item: dict[str, Any] = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        ATTR_VALUE: data,
        "type": ItemType.QUEUE.value,
        "created_at": unix_ts,
        ATTR_METADATA: {
            "priority": priority,
            "timestamp_micros": timestamp_micros,
            "message_uuid": message_uuid,
        },
    }

    # Add dedup_id to metadata if provided
    if dedup_id:
        item[ATTR_METADATA]["dedup_id"] = dedup_id

    # Add TTL if provided
    if ttl:
        item[ATTR_TTL] = unix_ts + ttl

    # Put item (no condition needed - we checked dedup above)
    client.put_item(item)

    # Return receipt
    return {
        "queue": queue_name,
        "receipt": sk,
        "priority": priority,
        "timestamp": unix_ts,
        "message_uuid": message_uuid,
        "dedup_id": dedup_id,
    }


def acknowledge_message(
    client: DynamoDBClient,
    queue_name: str,
    receipt: str,
) -> dict[str, Any]:
    """
    Acknowledge (delete) a message from the queue.

    This operation is idempotent: if the message doesn't exist (already acknowledged
    or expired), it returns success anyway.

    The receipt format is: {priority:010d}#{timestamp}#{uuid}

    Args:
        client: DynamoDB client
        queue_name: Queue name
        receipt: Receipt handle from queue-pop operation (full SK value)

    Returns:
        Dictionary with queue name, receipt, and acknowledgment status

    Raises:
        KVStoreError: For DynamoDB errors (excluding KeyNotFoundError)
    """
    pk = format_key(PREFIX_QUEUE, queue_name)
    sk = receipt

    try:
        # Delete the item using the receipt as SK
        client.delete_item(
            key={ATTR_PK: pk, ATTR_SK: sk},
        )

        return {
            "queue": queue_name,
            "receipt": receipt,
            "acknowledged": True,
        }

    except (ConditionFailedError, KeyNotFoundError):
        # Idempotent: if item doesn't exist, treat as success
        # This can happen if:
        # - Message was already acknowledged
        # - Message expired (TTL deleted it)
        # - Invalid receipt handle
        return {
            "queue": queue_name,
            "receipt": receipt,
            "acknowledged": True,
        }


def peek_queue(
    client: DynamoDBClient,
    queue_name: str,
    count: int = 10,
) -> dict[str, Any]:
    """
    Peek at messages in a queue without changing their state.

    This is a read-only operation that does not modify message visibility
    or provide receipts. Use this to inspect queue contents without
    consuming messages.

    Args:
        client: DynamoDB client
        queue_name: Name of the queue
        count: Maximum number of messages to peek (default: 10)

    Returns:
        Dictionary with queue name, list of items, and count

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_QUEUE, queue_name)

    # Query for items with PK = queue:{queue_name}, sorted by SK ascending
    key_condition = Key(ATTR_PK).eq(pk)

    items = client.query(key_condition_expression=key_condition, limit=count)

    # Parse items into readable format
    parsed_items = []
    for item in items:
        metadata = item.get(ATTR_METADATA, {})
        priority = metadata.get("priority", 0)
        timestamp_micros = metadata.get("timestamp_micros", 0)

        parsed_items.append(
            {
                "message": item.get(ATTR_VALUE, {}),
                "priority": priority,
                "timestamp": timestamp_micros,
            }
        )

    return {
        "queue": queue_name,
        "items": parsed_items,
        "count": len(parsed_items),
    }


def get_queue_size(
    client: DynamoDBClient,
    queue_name: str,
) -> dict[str, Any]:
    """
    Get the size of a queue.

    This operation efficiently counts queue items using DynamoDB's COUNT query,
    which doesn't consume read capacity for item data.

    Args:
        client: DynamoDB client
        queue_name: Queue name

    Returns:
        Dictionary with queue name and size count

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_QUEUE, queue_name)

    # Query with Select=COUNT for efficient counting
    key_condition = Key(ATTR_PK).eq(pk)
    count = client.query_count(key_condition)

    return {
        "queue": queue_name,
        "size": count,
    }


def pop_from_queue(
    client: DynamoDBClient,
    queue_name: str,
    visibility_timeout: int = 0,
) -> dict[str, Any] | None:
    """
    Pop the highest-priority message from a queue.

    This is a two-step operation:
    1. Query for the highest-priority item (lowest SK value)
    2. Either delete it (permanent pop) or update TTL (visibility timeout)

    Args:
        client: DynamoDB client
        queue_name: Name of the queue
        visibility_timeout: If 0, permanently delete. If > 0, hide for N seconds.

    Returns:
        Dictionary with queue message data, or None if queue is empty:
        {
            "queue": "task-queue",
            "message": {"task": "process"},
            "receipt": "{priority:010d}#{timestamp}#{uuid}",
            "priority": 10,
            "timestamp": 1234567890000
        }

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_QUEUE, queue_name)

    # Step 1: Query for highest-priority item (sorted by SK ascending, limit 1)
    try:
        key_condition = Key(ATTR_PK).eq(pk)
        items = client.query(
            key_condition_expression=key_condition,
            limit=1,
            scan_index_forward=True,  # Ascending order retrieves smallest SK first
        )

        if not items:
            return None

        item = items[0]
        sk = item[ATTR_SK]

        # Step 2: Either delete or update with visibility timeout
        if visibility_timeout == 0:
            # Permanent pop - delete the item
            client.delete_item(key={ATTR_PK: pk, ATTR_SK: sk})
        else:
            # Temporary hide - set TTL to now + visibility_timeout
            ts = int(time.time())
            ttl = ts + visibility_timeout

            client.update_item(
                key={ATTR_PK: pk, ATTR_SK: sk},
                update_expression="SET #ttl = :ttl",
                expression_attribute_names={"#ttl": "ttl"},
                expression_attribute_values={":ttl": ttl},
            )

        # Extract and return message data from metadata
        metadata = item.get(ATTR_METADATA, {})
        priority = metadata.get("priority", 0)
        timestamp_micros = metadata.get("timestamp_micros", 0)

        return {
            "queue": queue_name,
            "message": item.get(ATTR_VALUE, {}),
            "receipt": sk,
            "priority": priority,
            "timestamp": timestamp_micros,
        }

    except Exception as e:
        if isinstance(e, KVStoreError):
            raise
        raise KVStoreError(f"Failed to pop from queue '{queue_name}': {e}")
