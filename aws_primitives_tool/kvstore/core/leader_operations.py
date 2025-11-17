"""
Leader election operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import time
from typing import Any

from ..constants import ATTR_PK, ATTR_SK, PREFIX_LEADER
from ..exceptions import ConditionFailedError, KeyNotFoundError, LeaderElectionError
from ..utils import format_key
from .client import DynamoDBClient


def elect_leader(
    client: DynamoDBClient,
    pool_name: str,
    agent_id: str,
    ttl: int = 30,
) -> dict[str, Any]:
    """
    Elect leader in a pool using atomic conditional write.

    Args:
        client: DynamoDB client
        pool_name: Leader pool name
        agent_id: Agent ID to become leader
        ttl: Leadership lease TTL in seconds (default: 30)

    Returns:
        Leader election data

    Raises:
        LeaderElectionError: If another agent is already leader
    """
    pk = format_key(PREFIX_LEADER, pool_name)
    sk = pk
    timestamp = int(time.time())
    ttl_timestamp = timestamp + ttl

    item = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        "value": agent_id,
        "type": "leader",
        "ttl": ttl_timestamp,
        "metadata": {"elected_at": timestamp},
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    condition = "attribute_not_exists(PK)"

    try:
        client.put_item(item, condition_expression=condition)
        return {
            "pool": pool_name,
            "leader": agent_id,
            "ttl": ttl_timestamp,
            "elected_at": timestamp,
        }
    except ConditionFailedError:
        msg = (
            f"Leadership election failed for pool '{pool_name}': another agent is the leader. "
            f"Wait for the current leader's lease to expire (TTL) or check leadership status with "
            f"'aws-primitives-tool kvstore leader-check {pool_name}'"
        )
        raise LeaderElectionError(msg)


def resign_leader(
    client: DynamoDBClient,
    pool_name: str,
    agent_id: str,
) -> dict[str, Any]:
    """
    Resign from leader position.

    Only the current leader can resign. Operation is idempotent - if the leader
    position is already vacant, the operation succeeds.

    Args:
        client: DynamoDB client
        pool_name: Leader pool name
        agent_id: Agent ID (must match current leader)

    Returns:
        Resignation confirmation

    Raises:
        ConditionFailedError: If agent is not the current leader
    """
    pk = format_key(PREFIX_LEADER, pool_name)
    sk = pk

    try:
        client.delete_item(
            {ATTR_PK: pk, ATTR_SK: sk},
            condition_expression="#value = :agent_id",
            expression_attribute_names={"#value": "value"},
            expression_attribute_values={":agent_id": agent_id},
        )
    except KeyNotFoundError:
        # Already resigned or expired - treat as success (idempotent)
        return {"pool": pool_name, "resigned": True}
    except ConditionFailedError:
        msg = (
            f"Cannot resign from leader pool '{pool_name}': "
            f"not the current leader (expected '{agent_id}')"
        )
        raise ConditionFailedError(msg)

    return {"pool": pool_name, "resigned": True}


def check_leader(
    client: DynamoDBClient,
    pool_name: str,
) -> dict[str, Any] | None:
    """
    Check if a leader exists for the given pool.

    Args:
        client: DynamoDB client
        pool_name: Name of the leader pool

    Returns:
        Leader information if a leader exists, None if no leader
    """
    pk = format_key(PREFIX_LEADER, pool_name)
    sk = pk

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    if not item:
        return None

    return {
        "pool": pool_name,
        "leader": item["value"],
        "ttl": item.get("ttl"),
        "elected_at": item.get("metadata", {}).get("elected_at"),
    }


def heartbeat_leader(
    client: DynamoDBClient,
    pool_name: str,
    agent_id: str,
    ttl: int = 30,
) -> dict[str, Any]:
    """
    Send heartbeat to extend leadership lease.

    Only the current leader can heartbeat. Updates TTL to maintain leadership.

    Args:
        client: DynamoDB client
        pool_name: Leader pool name
        agent_id: Agent ID (must be current leader)
        ttl: TTL extension in seconds (default: 30)

    Returns:
        Heartbeat confirmation with new TTL

    Raises:
        ConditionFailedError: If agent is not the current leader
    """
    pk = format_key(PREFIX_LEADER, pool_name)
    sk = pk
    timestamp = int(time.time())
    new_ttl = timestamp + ttl

    try:
        client.update_item(
            key={ATTR_PK: pk, ATTR_SK: sk},
            update_expression="SET #ttl = :new_ttl, updated_at = :ts",
            expression_attribute_names={"#ttl": "ttl", "#value": "value"},
            expression_attribute_values={
                ":new_ttl": new_ttl,
                ":agent_id": agent_id,
                ":ts": timestamp,
            },
            condition_expression="#value = :agent_id",
            return_values="ALL_NEW",
        )
    except ConditionFailedError:
        msg = (
            f"Cannot heartbeat for pool '{pool_name}': "
            f"not the current leader (agent_id '{agent_id}')"
        )
        raise ConditionFailedError(msg)

    return {
        "pool": pool_name,
        "leader": agent_id,
        "ttl": new_ttl,
        "heartbeat": True,
    }
