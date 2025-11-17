"""
Transaction operations for kvstore using DynamoDB TransactWriteItems.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import json
import time
from typing import Any

from ..constants import ATTR_CREATED_AT, ATTR_PK, ATTR_SK, ATTR_TYPE, ATTR_UPDATED_AT, ATTR_VALUE
from ..exceptions import KVStoreError
from ..utils import format_key
from .client import DynamoDBClient


def execute_transaction(
    client: DynamoDBClient,
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Execute multiple operations atomically using DynamoDB transactions.

    Supports mixing different operation types (kv, counter, lock, etc.) in a single transaction.
    Maximum 100 operations per transaction, 4 MB total size limit.

    Args:
        client: DynamoDB client
        operations: List of operation dictionaries with:
            - action: "Put", "Update", or "Delete"
            - type: "kv", "counter", "lock", "queue", "leader", "set", "list"
            - key: Key name
            - value: Value for Put operations (optional)
            - condition: Condition expression (optional)
            - operation: For counters: "inc" or "dec" (optional)

    Returns:
        Dictionary with transaction result:
        {
            "success": True,
            "operations_count": 3,
            "timestamp": 1234567890
        }

    Raises:
        KVStoreError: If transaction fails or validation errors
    """
    if not operations:
        raise KVStoreError("Transaction requires at least one operation")

    if len(operations) > 100:
        raise KVStoreError("Transaction cannot exceed 100 operations")

    timestamp = int(time.time())
    transact_items: list[dict[str, Any]] = []

    for idx, op in enumerate(operations):
        try:
            transact_item = _build_transact_item(client.table_name, op, timestamp)
            transact_items.append(transact_item)
        except Exception as e:
            raise KVStoreError(f"Error building operation {idx}: {e}")

    # Execute transaction
    try:
        client.client.transact_write_items(TransactItems=transact_items)  # type: ignore[arg-type]
        return {
            "success": True,
            "operations_count": len(operations),
            "timestamp": timestamp,
        }
    except Exception as e:
        raise KVStoreError(f"Transaction failed: {e}")


def _build_transact_item(
    table_name: str,
    operation: dict[str, Any],
    timestamp: int,
) -> dict[str, Any]:
    """
    Build a single DynamoDB transact item from operation specification.

    Args:
        table_name: DynamoDB table name
        operation: Operation dictionary
        timestamp: Current timestamp

    Returns:
        DynamoDB transact item dictionary

    Raises:
        KVStoreError: If operation is invalid
    """
    action = operation.get("action")
    op_type = operation.get("type")
    key = operation.get("key")

    if not action or not op_type or not key:
        raise KVStoreError("Operation must specify action, type, and key")

    # Build PK/SK based on type
    pk, sk = _build_keys(op_type, key)

    if action == "Put":
        return _build_put_item(table_name, pk, sk, operation, timestamp)
    elif action == "Update":
        return _build_update_item(table_name, pk, sk, operation, timestamp)
    elif action == "Delete":
        return _build_delete_item(table_name, pk, sk, operation)
    else:
        raise KVStoreError(f"Unsupported action: {action}")


def _build_keys(op_type: str, key: str) -> tuple[str, str]:
    """
    Build PK and SK based on operation type.

    Args:
        op_type: Operation type (kv, counter, lock, etc.)
        key: Key name

    Returns:
        Tuple of (PK, SK)
    """
    type_prefixes = {
        "kv": "kv",
        "counter": "counter",
        "lock": "lock",
        "queue": "queue",
        "leader": "leader",
        "set": "set",
        "list": "list",
    }

    prefix = type_prefixes.get(op_type)
    if not prefix:
        raise KVStoreError(f"Unsupported type: {op_type}")

    pk = format_key(prefix, key)

    # For most types, SK = PK; for composite types, more complex logic needed
    if op_type in ["queue", "set", "list"]:
        raise KVStoreError(f"Type '{op_type}' not yet supported in transactions")

    sk = pk
    return pk, sk


def _build_put_item(
    table_name: str,
    pk: str,
    sk: str,
    operation: dict[str, Any],
    timestamp: int,
) -> dict[str, Any]:
    """Build a Put transact item."""
    value = operation.get("value")
    if value is None:
        raise KVStoreError("Put operation requires 'value'")

    item = {
        ATTR_PK: {"S": pk},
        ATTR_SK: {"S": sk},
        ATTR_VALUE: {"S": str(value)},
        ATTR_TYPE: {"S": operation.get("type", "kv")},
        ATTR_CREATED_AT: {"N": str(timestamp)},
        ATTR_UPDATED_AT: {"N": str(timestamp)},
    }

    transact_item: dict[str, Any] = {
        "Put": {
            "TableName": table_name,
            "Item": item,
        }
    }

    # Add condition if specified
    condition = operation.get("condition")
    if condition:
        transact_item["Put"]["ConditionExpression"] = condition

    return transact_item


def _build_update_item(
    table_name: str,
    pk: str,
    sk: str,
    operation: dict[str, Any],
    timestamp: int,
) -> dict[str, Any]:
    """Build an Update transact item."""
    op_type = operation.get("type")
    counter_op = operation.get("operation")  # "inc" or "dec"

    if op_type == "counter" and counter_op:
        # Counter increment/decrement
        value = operation.get("value", 1)
        if counter_op == "dec":
            value = -abs(value)

        transact_item: dict[str, Any] = {
            "Update": {
                "TableName": table_name,
                "Key": {
                    ATTR_PK: {"S": pk},
                    ATTR_SK: {"S": sk},
                },
                "UpdateExpression": f"ADD #val :val SET {ATTR_UPDATED_AT} = :ts, #type = :type",
                "ExpressionAttributeNames": {"#val": ATTR_VALUE, "#type": ATTR_TYPE},
                "ExpressionAttributeValues": {
                    ":val": {"N": str(value)},
                    ":ts": {"N": str(timestamp)},
                    ":type": {"S": "counter"},
                },
            }
        }
    else:
        # Generic value update
        value = operation.get("value")
        if value is None:
            raise KVStoreError("Update operation requires 'value'")

        transact_item = {
            "Update": {
                "TableName": table_name,
                "Key": {
                    ATTR_PK: {"S": pk},
                    ATTR_SK: {"S": sk},
                },
                "UpdateExpression": f"SET #val = :val, {ATTR_UPDATED_AT} = :ts, #type = :type",
                "ExpressionAttributeNames": {"#val": ATTR_VALUE, "#type": ATTR_TYPE},
                "ExpressionAttributeValues": {
                    ":val": {"S": str(value)},
                    ":ts": {"N": str(timestamp)},
                    ":type": {"S": op_type or "kv"},
                },
            }
        }

    # Add condition if specified
    condition = operation.get("condition")
    if condition:
        transact_item["Update"]["ConditionExpression"] = condition

    return transact_item


def _build_delete_item(
    table_name: str,
    pk: str,
    sk: str,
    operation: dict[str, Any],
) -> dict[str, Any]:
    """Build a Delete transact item."""
    transact_item: dict[str, Any] = {
        "Delete": {
            "TableName": table_name,
            "Key": {
                ATTR_PK: {"S": pk},
                ATTR_SK: {"S": sk},
            },
        }
    }

    # Add condition if specified
    condition = operation.get("condition")
    if condition:
        transact_item["Delete"]["ConditionExpression"] = condition

    return transact_item


def load_transaction_file(file_path: str) -> list[dict[str, Any]]:
    """
    Load transaction operations from a JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of operations

    Raises:
        KVStoreError: If file cannot be loaded or is invalid
    """
    try:
        with open(file_path) as f:
            data: dict[str, Any] = json.load(f)

        operations = data.get("operations")
        if not operations or not isinstance(operations, list):
            raise KVStoreError("Transaction file must contain 'operations' array")

        return operations  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        raise KVStoreError(f"Invalid JSON in transaction file: {e}")
    except FileNotFoundError:
        raise KVStoreError(f"Transaction file not found: {file_path}")
    except Exception as e:
        raise KVStoreError(f"Error loading transaction file: {e}")
