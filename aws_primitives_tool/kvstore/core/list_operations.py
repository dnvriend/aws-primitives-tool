"""
List operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
from typing import Any

from boto3.dynamodb.conditions import Key

from ..constants import ATTR_CREATED_AT, ATTR_PK, ATTR_SK, ATTR_UPDATED_AT, ATTR_VALUE, PREFIX_LIST
from ..models import ItemType
from ..utils import format_key
from .client import DynamoDBClient


def prepend_to_list(
    client: DynamoDBClient,
    list_name: str,
    value: str,
) -> dict[str, Any]:
    """
    Prepend value to list (LIFO order).

    Uses negative timestamp as sort key so newest items appear first when querying.
    This enables efficient LIFO (Last In First Out) behavior when combined with lpop.

    Args:
        client: DynamoDB client
        list_name: Name of the list
        value: Value to prepend to the list

    Returns:
        Dictionary with list name, value, and position:
        {"list": "mylist", "value": "item", "position": "head"}

    Raises:
        KVStoreError: For DynamoDB errors
    """
    # Construct keys
    # PK: list:{list_name}
    # SK: offset - timestamp for head items (lpush)
    # Uses 2^62 as offset to ensure proper ordering:
    # - More recent lpush: smaller SK (offset - larger_ts)
    # - lpush items have SK < offset
    # - rpush items have SK > offset
    # With ascending sort: lpush (most recent first), then rpush (oldest first)
    pk = format_key(PREFIX_LIST, list_name)
    timestamp = int(time.time())
    timestamp_ns = time.time_ns()  # Nanosecond precision to prevent collisions
    offset = 2**62
    # Zero-pad to 20 digits for lexicographic sorting
    sk = f"{offset - timestamp_ns:020d}"

    # Build item
    item: dict[str, Any] = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        ATTR_VALUE: value,
        "type": ItemType.LIST.value,
        ATTR_CREATED_AT: timestamp,
        ATTR_UPDATED_AT: timestamp,
    }

    # Put item (not idempotent - each call adds a new item with unique timestamp)
    client.put_item(item)

    return {
        "list": list_name,
        "value": value,
        "position": "head",
    }


def append_to_list(
    client: DynamoDBClient,
    list_name: str,
    value: str,
) -> dict[str, Any]:
    """
    Append value to list (FIFO order).

    Uses positive timestamp as sort key so oldest items appear first when querying.
    This enables efficient FIFO (First In First Out) behavior when combined with lpop.

    Args:
        client: DynamoDB client
        list_name: Name of the list
        value: Value to append to the list

    Returns:
        Dictionary with list name, value, and position:
        {"list": "mylist", "value": "item", "position": "tail"}

    Raises:
        KVStoreError: For DynamoDB errors
    """
    # Construct keys
    # PK: list:{list_name}
    # SK: offset + timestamp for tail items (rpush)
    # Uses 2^62 as offset to ensure proper ordering:
    # - More recent rpush: larger SK (offset + larger_ts)
    # - rpush items have SK > offset
    # - lpush items have SK < offset
    # With ascending sort: lpush (most recent first), then rpush (oldest first)
    pk = format_key(PREFIX_LIST, list_name)
    timestamp = int(time.time())
    timestamp_ns = time.time_ns()  # Nanosecond precision to prevent collisions
    offset = 2**62
    # Zero-pad to 20 digits for lexicographic sorting
    sk = f"{offset + timestamp_ns:020d}"

    # Build item
    item: dict[str, Any] = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        ATTR_VALUE: value,
        "type": ItemType.LIST.value,
        ATTR_CREATED_AT: timestamp,
        ATTR_UPDATED_AT: timestamp,
    }

    # Put item (not idempotent - each call adds a new item with unique timestamp)
    client.put_item(item)

    return {
        "list": list_name,
        "value": value,
        "position": "tail",
    }


def get_range(
    client: DynamoDBClient,
    list_name: str,
    start: int = 0,
    stop: int | None = None,
) -> dict[str, Any]:
    """
    Get range of items from list.

    Uses Python slicing semantics:
    - start: inclusive start index (0-based, negative supported)
    - stop: exclusive end index (None = end of list, negative supported)

    Examples:
        get_range(client, "mylist", 0, 5)   # First 5 items
        get_range(client, "mylist", 2, 4)   # Items at index 2-3
        get_range(client, "mylist", -3, -1) # 3rd and 2nd to last items

    Args:
        client: DynamoDB client
        list_name: Name of the list
        start: Starting index (inclusive, 0-based, negative supported)
        stop: Ending index (exclusive, None = end of list, negative supported)

    Returns:
        Dictionary with list name, start, stop, count, and items:
        {"list": "mylist", "start": 0, "stop": 5, "count": 5, "items": [...]}

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_LIST, list_name)

    # Get all items (we need to for negative indexing and slicing)
    # Use ascending order (ScanIndexForward=True) to get items in list order:
    # - lpush items: offset - timestamp (more recent = smaller SK)
    # - rpush items: offset + timestamp (more recent = larger SK)
    # - All lpush SKs < offset < all rpush SKs
    # Ascending sort gives proper list order: [newest_lpush...oldest_lpush, oldest_rpush...newest_rpush]
    # This matches standard list semantics: [head_items..., tail_items...]
    response = client.table.query(
        KeyConditionExpression=Key(ATTR_PK).eq(pk),
        ScanIndexForward=True,
    )

    items = response.get("Items", [])

    # Apply Python slicing
    sliced_items = items[start:stop]

    return {
        "list": list_name,
        "start": start,
        "stop": stop,
        "count": len(sliced_items),
        "items": [item[ATTR_VALUE] for item in sliced_items],
    }


def pop_last(
    client: DynamoDBClient,
    list_name: str,
) -> dict[str, Any] | None:
    """
    Remove and return last item from list (from tail/right side).

    Uses ascending query (ScanIndexForward=True) to get item with largest SK (least negative).
    - For lpush lists (negative timestamps): ascending order gives largest SK first = oldest item
    - For rpush lists (positive timestamps): ascending order gives smallest SK first = first item

    Args:
        client: DynamoDB client
        list_name: Name of the list

    Returns:
        Dictionary with list name, value, and position, or None if list is empty

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_LIST, list_name)

    # Query for last item (largest/least negative SK) with ascending order
    items = client.query(
        key_condition_expression=Key(ATTR_PK).eq(pk),
        limit=1,
        scan_index_forward=True,  # Ascending - get largest SK (oldest for lpush)
    )

    if not items:
        return None

    item = items[0]

    # Delete the item
    client.delete_item(
        {
            ATTR_PK: item[ATTR_PK],
            ATTR_SK: item[ATTR_SK],
        }
    )

    return {
        "list": list_name,
        "value": item[ATTR_VALUE],
        "position": "tail",
    }


def pop_first(
    client: DynamoDBClient,
    list_name: str,
) -> dict[str, Any] | None:
    """
    Remove and return first item from list (from head/left side).

    Uses descending query (ScanIndexForward=False) to get item with smallest SK (most negative).
    - For lpush lists (negative timestamps): descending order gives smallest SK first
      = newest item (LIFO)  # noqa: E501
    - For rpush lists (positive timestamps): descending order gives largest SK first = last item

    Args:
        client: DynamoDB client
        list_name: Name of the list

    Returns:
        Dictionary with list name, value, and position, or None if list is empty

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_LIST, list_name)

    # Query for first item (smallest/most negative SK) with descending order
    items = client.query(
        key_condition_expression=Key(ATTR_PK).eq(pk),
        limit=1,
        scan_index_forward=False,  # Descending - get smallest SK (newest for lpush)
    )

    if not items:
        return None

    item = items[0]

    # Delete the item
    client.delete_item(
        {
            ATTR_PK: item[ATTR_PK],
            ATTR_SK: item[ATTR_SK],
        }
    )

    return {
        "list": list_name,
        "value": item[ATTR_VALUE],
        "position": "head",
    }
