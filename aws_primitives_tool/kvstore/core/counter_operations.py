"""
Counter operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
from typing import Any

from ..constants import ATTR_PK, ATTR_SK, PREFIX_COUNTER
from ..exceptions import ConditionFailedError, KeyNotFoundError
from ..models import ItemType
from ..utils import format_key
from .client import DynamoDBClient


def increment_counter(
    client: DynamoDBClient, key: str, by: int = 1, create: bool = False
) -> dict[str, Any]:
    """
    Atomically increment a counter.

    This operation is atomic and thread-safe. DynamoDB guarantees no race
    conditions when multiple processes increment the same counter.

    Args:
        client: DynamoDB client
        key: Counter key
        by: Amount to increment (default: 1)
        create: If True, create counter if missing (default: False)

    Returns:
        Dictionary with counter key, new value, and updated_at timestamp

    Raises:
        KeyNotFoundError: If counter doesn't exist and create=False
        KVStoreError: For other DynamoDB errors
    """
    pk = format_key(PREFIX_COUNTER, key)
    sk = format_key(PREFIX_COUNTER, key)
    ts = int(time.time())

    update_expression = "ADD #value :inc SET updated_at = :ts, #type = :type"
    expression_attribute_names = {"#value": "value", "#type": "type"}
    expression_attribute_values = {
        ":inc": by,
        ":ts": ts,
        ":type": ItemType.COUNTER.value,
    }

    # If create=False, add condition that item must exist
    condition_expression = None if create else "attribute_exists(PK)"

    try:
        response = client.update_item(
            key={ATTR_PK: pk, ATTR_SK: sk},
            update_expression=update_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            condition_expression=condition_expression,
            return_values="ALL_NEW",
        )

        item = response.get("Attributes", {})
        return {
            "key": key,
            "value": int(item["value"]),
            "updated_at": item["updated_at"],
        }

    except ConditionFailedError:
        raise KeyNotFoundError(
            f"Counter '{key}' does not exist. Use --create flag to initialize it."
        )


def decrement_counter(client: DynamoDBClient, key: str, by: int = 1) -> dict[str, Any]:
    """
    Atomically decrement a counter.

    This operation is atomic and thread-safe. DynamoDB guarantees no race
    conditions when multiple processes decrement the same counter.

    Args:
        client: DynamoDB client
        key: Counter key
        by: Amount to decrement (default: 1)

    Returns:
        Dictionary with counter key, new value, and updated_at timestamp

    Raises:
        KeyNotFoundError: If counter doesn't exist
        KVStoreError: For other DynamoDB errors
    """
    pk = format_key(PREFIX_COUNTER, key)
    sk = format_key(PREFIX_COUNTER, key)
    ts = int(time.time())

    update_expression = "ADD #value :dec SET updated_at = :ts"
    expression_attribute_names = {"#value": "value"}
    expression_attribute_values = {
        ":dec": -by,  # Negative value for decrement
        ":ts": ts,
    }

    # Counter must exist (no auto-create for decrement)
    condition_expression = "attribute_exists(PK)"

    try:
        response = client.update_item(
            key={ATTR_PK: pk, ATTR_SK: sk},
            update_expression=update_expression,
            expression_attribute_names=expression_attribute_names,
            expression_attribute_values=expression_attribute_values,
            condition_expression=condition_expression,
            return_values="ALL_NEW",
        )

        item = response.get("Attributes", {})
        return {
            "key": key,
            "value": int(item["value"]),
            "updated_at": item["updated_at"],
        }

    except ConditionFailedError:
        raise KeyNotFoundError(
            f"Counter '{key}' does not exist. "
            f"Use 'aws-primitives-tool kvstore inc {key} --create' to create it first."
        )


def get_counter(client: DynamoDBClient, key: str) -> dict[str, Any]:
    """
    Read counter value.

    Args:
        client: DynamoDB client
        key: Counter key name

    Returns:
        Counter data with key, value, type, and timestamps

    Raises:
        KeyNotFoundError: If counter not found
    """
    pk = format_key(PREFIX_COUNTER, key)
    sk = pk

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    if not item:
        message = (
            f"Counter '{key}' not found. "
            f"Use 'aws-primitives-tool kvstore inc-counter {key}' to create it."
        )
        raise KeyNotFoundError(message)

    return {
        "key": key,
        "value": int(item["value"]),
        "type": item["type"],
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }
