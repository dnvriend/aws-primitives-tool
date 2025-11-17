"""
Info operations for kvstore - key metadata and table inventory.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any

from ..exceptions import KeyNotFoundError
from .client import DynamoDBClient


def get_key_info(client: DynamoDBClient, key: str) -> dict[str, Any]:
    """Get metadata about a specific key.

    Returns key type, timestamps, size, and type-specific metadata.
    """
    # Query all items for this key (PK)
    response = client.table.query(
        KeyConditionExpression="PK = :pk", ExpressionAttributeValues={":pk": key}
    )

    items = response.get("Items", [])
    if not items:
        raise KeyNotFoundError(f"Key '{key}' not found")

    # Determine type from first item
    first_item = items[0]
    item_type = first_item.get("type", "unknown")

    info: dict[str, Any] = {
        "key": key,
        "type": item_type,
        "created_at": first_item.get("created_at"),
        "updated_at": first_item.get("updated_at"),
    }

    # Add TTL if present
    if "ttl" in first_item:
        info["ttl"] = first_item["ttl"]

    # Type-specific metadata
    if item_type == "counter":
        info["value"] = first_item.get("value", 0)
    elif item_type == "kv":
        info["value_size"] = len(str(first_item.get("value", "")))
    elif item_type in ("list", "queue"):
        info["item_count"] = len(items)
    elif item_type == "set":
        info["member_count"] = len(items)
    elif item_type == "lock":
        info["owner"] = first_item.get("owner")
        info["acquired_at"] = first_item.get("acquired_at")
    elif item_type == "leader":
        info["node_id"] = first_item.get("node_id")
        info["elected_at"] = first_item.get("elected_at")

    return info


def get_table_stats(client: DynamoDBClient) -> dict[str, Any]:
    """Get inventory of all primitives in the table.

    Scans entire table and groups by type with counts/values.
    """
    # Scan entire table
    response = client.table.scan()
    items = response["Items"]

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = client.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])

    # Group by type
    counters: list[dict[str, Any]] = []
    lists: list[dict[str, Any]] = []
    sets: list[dict[str, Any]] = []
    queues: list[dict[str, Any]] = []
    locks: list[dict[str, Any]] = []
    leaders: list[dict[str, Any]] = []
    kv_count = 0

    # Track seen keys for collections (they have multiple items)
    seen_lists: dict[str, int] = {}
    seen_sets: dict[str, int] = {}
    seen_queues: dict[str, int] = {}

    for item in items:
        item_type = item.get("type", "unknown")
        pk = str(item.get("PK", ""))

        if item_type == "counter":
            counters.append({"key": pk, "value": item.get("value", 0)})
        elif item_type == "kv":
            kv_count += 1
        elif item_type == "list":
            seen_lists[pk] = seen_lists.get(pk, 0) + 1
        elif item_type == "set":
            seen_sets[pk] = seen_sets.get(pk, 0) + 1
        elif item_type == "queue":
            seen_queues[pk] = seen_queues.get(pk, 0) + 1
        elif item_type == "lock":
            locks.append({"key": pk, "owner": item.get("owner", ""), "ttl": item.get("ttl")})
        elif item_type == "leader":
            leaders.append({"key": pk, "leader": item.get("node_id", ""), "ttl": item.get("ttl")})

    # Convert collection counts to list format
    for key, size in seen_lists.items():
        lists.append({"key": key, "size": size})

    for key, size in seen_sets.items():
        sets.append({"key": key, "size": size})

    for key, size in seen_queues.items():
        queues.append({"key": key, "size": size})

    return {
        "counters": counters,
        "lists": lists,
        "sets": sets,
        "queues": queues,
        "locks": locks,
        "leaders": leaders,
        "kv_pairs": kv_count,
        "total_items": len(items),
    }
