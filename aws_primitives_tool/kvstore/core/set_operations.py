"""
Set operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
from typing import Any

from boto3.dynamodb.conditions import Key

from ..constants import ATTR_PK, ATTR_SK, ATTR_VALUE, PREFIX_SET
from ..exceptions import KeyNotFoundError
from ..models import ItemType
from ..utils import format_key
from .client import DynamoDBClient


def add_to_set(
    client: DynamoDBClient,
    set_name: str,
    member: str,
) -> dict[str, Any]:
    """
    Add a member to a set.

    This operation is idempotent: adding an existing member has no effect.
    Uses composite sort key pattern for efficient membership checks and scans.

    Args:
        client: DynamoDB client
        set_name: Name of the set
        member: Member value to add to the set

    Returns:
        Dictionary with set name, member, and added status:
        {"set": "myset", "member": "value1", "added": True}

    Raises:
        KVStoreError: For DynamoDB errors
    """
    # Construct composite keys
    # PK: set:{set_name}
    # SK: set:{set_name}#{member}
    pk = format_key(PREFIX_SET, set_name)
    sk = f"{PREFIX_SET}:{set_name}#{member}"

    # Get current timestamp
    unix_ts = int(time.time())

    # Build item
    item: dict[str, Any] = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        ATTR_VALUE: member,
        "type": ItemType.SET.value,
        "created_at": unix_ts,
    }

    # Put item (idempotent - overwrite if exists)
    client.put_item(item)

    return {
        "set": set_name,
        "member": member,
        "added": True,
    }


def get_set_size(
    client: DynamoDBClient,
    set_name: str,
) -> dict[str, Any]:
    """
    Get the size (cardinality) of a set.

    This operation efficiently counts set members using DynamoDB's COUNT query,
    which doesn't consume read capacity for item data.

    Args:
        client: DynamoDB client
        set_name: Name of the set

    Returns:
        Dictionary with set name and size count

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_SET, set_name)

    # Query with Select=COUNT for efficient counting
    key_condition = Key("PK").eq(pk)
    count = client.query_count(key_condition)

    return {
        "set": set_name,
        "size": count,
    }


def is_member(
    client: DynamoDBClient,
    set_name: str,
    member: str,
) -> bool:
    """
    Check if member exists in set.

    Args:
        client: DynamoDB client
        set_name: Name of the set
        member: Member to check

    Returns:
        True if member exists in set, False otherwise
    """
    pk = format_key(PREFIX_SET, set_name)
    sk = f"{pk}#{member}"

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    return item is not None


def remove_from_set(
    client: DynamoDBClient,
    set_name: str,
    member: str,
) -> dict[str, Any]:
    """
    Remove member from set.

    Operation is idempotent - no error if member doesn't exist.

    Args:
        client: DynamoDB client
        set_name: Set name
        member: Member to remove from set

    Returns:
        Dictionary with set, member, and removed status
    """
    pk = format_key(PREFIX_SET, set_name)
    sk = f"{PREFIX_SET}:{set_name}#{member}"

    try:
        client.delete_item({ATTR_PK: pk, ATTR_SK: sk})
    except KeyNotFoundError:
        # Idempotent - deleting non-existent member succeeds
        pass

    return {"set": set_name, "member": member, "removed": True}


def get_members(
    client: DynamoDBClient,
    set_name: str,
) -> dict[str, Any]:
    """
    Get all members of a set.

    This operation queries DynamoDB on PK to retrieve all members of a set.
    The SK format is "set:{set_name}#{member}", and this function extracts
    the member portion from the SK.

    Args:
        client: DynamoDB client
        set_name: Name of the set

    Returns:
        Dictionary with set name, members list, and count

    Raises:
        KVStoreError: For DynamoDB errors
    """
    pk = format_key(PREFIX_SET, set_name)

    # Query all items with this PK
    key_condition = Key(ATTR_PK).eq(pk)
    items = client.query(key_condition)

    # Extract members from SK (format: "set:{set_name}#{member}")
    members = []
    for item in items:
        sk = item.get(ATTR_SK, "")
        # Parse SK to extract member: "set:{set_name}#{member}" -> "member"
        if "#" in sk:
            _, member = sk.split("#", 1)
            members.append(member)

    return {
        "set": set_name,
        "members": members,
        "count": len(members),
    }
