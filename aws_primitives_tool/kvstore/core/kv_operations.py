"""
Key-value operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
from typing import Any

from ..constants import ATTR_PK, ATTR_SK, PREFIX_KV
from ..exceptions import KeyNotFoundError
from ..models import ItemType
from ..utils import format_key
from .client import DynamoDBClient


def set_value(
    client: DynamoDBClient,
    key: str,
    value: str,
    ttl: int | None = None,
    if_not_exists: bool = False,
) -> dict[str, Any]:
    """
    Set a key-value pair.

    Args:
        client: DynamoDB client
        key: Key name
        value: Value to store
        ttl: TTL in seconds (optional)
        if_not_exists: Only set if key doesn't exist

    Returns:
        Item data

    Raises:
        ConditionFailedError: If if_not_exists=True and key exists
    """
    pk = format_key(PREFIX_KV, key)
    sk = pk
    timestamp = int(time.time())

    item = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        "value": value,
        "type": ItemType.KV.value,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    if ttl:
        item["ttl"] = timestamp + ttl

    condition = "attribute_not_exists(PK)" if if_not_exists else None
    client.put_item(item, condition_expression=condition)

    return {"key": key, "value": value, "created_at": timestamp, "updated_at": timestamp}


def get_value(
    client: DynamoDBClient, key: str, default: str | None = None
) -> dict[str, Any]:
    """
    Get a value by key.

    Args:
        client: DynamoDB client
        key: Key name
        default: Default value if key not found

    Returns:
        Item data

    Raises:
        KeyNotFoundError: If key not found and no default
    """
    pk = format_key(PREFIX_KV, key)
    sk = pk

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    if not item:
        if default is not None:
            return {"key": key, "value": default, "default": True}
        message = (
            f"Key '{key}' not found. "
            f"Use 'aws-primitives-tool kvstore set {key} <value>' to create it."
        )
        raise KeyNotFoundError(message)

    return {
        "key": key,
        "value": item.get("value"),
        "type": item.get("type"),
        "ttl": item.get("ttl"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }
