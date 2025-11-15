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
    # SK: negative timestamp for LIFO ordering
    pk = format_key(PREFIX_LIST, list_name)
    timestamp = int(time.time())
    sk = str(-timestamp)  # Negative for LIFO - newest items sort first

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
    # SK: positive timestamp for FIFO ordering
    pk = format_key(PREFIX_LIST, list_name)
    timestamp = int(time.time())
    sk = str(timestamp)  # Positive for FIFO - oldest items sort first

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
    Remove and return last item from list.

    Uses descending query (ScanIndexForward=False) to get item with largest SK.
    For lists with lpush, this gives FIFO behavior (oldest first).
    For lists with rpush, this gives LIFO behavior (most recent first).

    Args:
        client: DynamoDB client
        list_name: Name of the list

    Returns:
        Dictionary with list name, value, and position, or None if list is empty

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_LIST, list_name)

    # Query for last item (largest SK) - use client.table.query directly for ScanIndexForward
    response = client.table.query(
        KeyConditionExpression=Key(ATTR_PK).eq(pk),
        ScanIndexForward=False,  # Descending order
        Limit=1,
    )

    items = response.get("Items", [])

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
    Remove and return first item from list.

    Uses ascending query (ScanIndexForward=True) to get item with smallest SK.
    For lists with lpush, this gives LIFO behavior (most recent first).
    For lists with rpush, this gives FIFO behavior (oldest first).

    Args:
        client: DynamoDB client
        list_name: Name of the list

    Returns:
        Dictionary with list name, value, and position, or None if list is empty

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_LIST, list_name)

    # Query for first item (smallest SK) with ascending order
    items = client.query(
        key_condition_expression=Key(ATTR_PK).eq(pk),
        limit=1,
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
