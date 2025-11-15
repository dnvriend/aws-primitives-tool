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


def get_value(client: DynamoDBClient, key: str, default: str | None = None) -> dict[str, Any]:
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


def exists_value(client: DynamoDBClient, key: str) -> bool:
    """
    Check if a key exists.

    Args:
        client: DynamoDB client
        key: Key name

    Returns:
        True if key exists, False otherwise
    """
    pk = format_key(PREFIX_KV, key)
    sk = pk

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    return item is not None


def delete_value(client: DynamoDBClient, key: str, if_value: str | None = None) -> dict[str, Any]:
    """
    Delete a key-value pair.

    Args:
        client: DynamoDB client
        key: Key name
        if_value: Only delete if value matches

    Returns:
        Item data

    Raises:
        ConditionFailedError: If if_value provided and doesn't match
    """
    pk = format_key(PREFIX_KV, key)
    sk = pk

    condition = None
    expression_attribute_names = None
    expression_attribute_values = None

    if if_value is not None:
        condition = "#value = :if_value"
        expression_attribute_names = {"#value": "value"}
        expression_attribute_values = {":if_value": if_value}

    try:
        client.delete_item(
            {ATTR_PK: pk, ATTR_SK: sk},
            condition_expression=condition,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
        )
    except KeyNotFoundError:
        # Deletion is idempotent - deleting non-existent key succeeds
        pass

    return {"key": key, "deleted": True}


def list_keys(client: DynamoDBClient, prefix: str = "", limit: int | None = None) -> dict[str, Any]:
    """
    List keys by prefix.

    Args:
        client: DynamoDB client
        prefix: Key prefix to filter by (empty for all keys)
        limit: Maximum number of keys to return

    Returns:
        Dictionary with prefix, keys list, and count
    """
    from boto3.dynamodb.conditions import Key

    # Build the key condition
    if prefix:
        # Query for specific prefix
        pk_value = format_key(PREFIX_KV, prefix)
        key_condition = Key(ATTR_PK).begins_with(pk_value)
    else:
        # Query for all KV items (PK starts with "kv:")
        key_condition = Key(ATTR_PK).begins_with(PREFIX_KV + ":")

    items = client.query(key_condition, limit)

    # Transform items to output format
    keys = []
    for item in items:
        pk = item.get(ATTR_PK, "")
        # Strip the "kv:" prefix from the key
        _, user_key = pk.split(":", 1) if ":" in pk else ("", pk)

        keys.append(
            {
                "key": user_key,
                "value": item.get("value"),
                "type": item.get("type"),
                "created_at": item.get("created_at"),
            }
        )

    return {"prefix": prefix, "keys": keys, "count": len(keys)}
