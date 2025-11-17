"""
Lock operations for kvstore.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import os
import socket
import time
from typing import Any

from ..constants import ATTR_PK, ATTR_SK, PREFIX_LOCK
from ..exceptions import ConditionFailedError, LockUnavailableError
from ..utils import format_key
from .client import DynamoDBClient


def acquire_lock(
    client: DynamoDBClient,
    lock_name: str,
    ttl: int,
    owner: str,
    wait: int = 0,
) -> dict[str, Any]:
    """
    Acquire a distributed lock.

    Args:
        client: DynamoDB client
        lock_name: Lock name
        ttl: Lock TTL in seconds
        owner: Owner ID
        wait: Wait time in seconds with exponential backoff (0 for no wait)

    Returns:
        Lock data

    Raises:
        LockUnavailableError: If lock is held by another owner
    """
    pk = format_key(PREFIX_LOCK, lock_name)
    sk = pk
    timestamp = int(time.time())
    ttl_timestamp = timestamp + ttl

    item = {
        ATTR_PK: pk,
        ATTR_SK: sk,
        "value": owner,
        "type": "lock",
        "ttl": ttl_timestamp,
        "metadata": {"acquired_at": timestamp, "owner": owner},
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    # Allow lock acquisition if:
    # 1. Lock doesn't exist (attribute_not_exists)
    # 2. Lock is owned by the same owner (value = :owner) - idempotent
    condition = "attribute_not_exists(PK) OR #v = :owner"
    expression_attribute_names = {"#v": "value"}
    expression_attribute_values = {":owner": owner}

    if wait == 0:
        # Try once, no retries
        try:
            client.put_item(
                item,
                condition_expression=condition,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
            )
            return {
                "lock": lock_name,
                "owner": owner,
                "ttl": ttl_timestamp,
                "acquired_at": timestamp,
            }
        except ConditionFailedError:
            msg = (
                f"Lock '{lock_name}' is held by another owner. "
                f"Use 'aws-primitives-tool kvstore lock-release {lock_name}' "
                f"to release it, or wait for TTL expiration."
            )
            raise LockUnavailableError(msg)
    else:
        # Retry with exponential backoff
        start_time = time.time()
        attempt = 0

        while True:
            try:
                client.put_item(
                    item,
                    condition_expression=condition,
                    expression_attribute_names=expression_attribute_names,
                    expression_attribute_values=expression_attribute_values,
                )
                return {
                    "lock": lock_name,
                    "owner": owner,
                    "ttl": ttl_timestamp,
                    "acquired_at": timestamp,
                }
            except ConditionFailedError:
                elapsed = time.time() - start_time
                if elapsed >= wait:
                    msg = (
                        f"Lock '{lock_name}' is held by another owner after waiting {wait}s. "
                        f"Use 'aws-primitives-tool kvstore lock-release {lock_name}' "
                        f"to release it, or wait for TTL expiration."
                    )
                    raise LockUnavailableError(msg)

                # Exponential backoff: min(0.1 * (2 ** attempt), 5.0)
                backoff_time = min(0.1 * (2**attempt), 5.0)
                remaining_time = wait - elapsed

                if remaining_time <= 0:
                    msg = (
                        f"Lock '{lock_name}' is held by another owner after waiting {wait}s. "
                        f"Use 'aws-primitives-tool kvstore lock-release {lock_name}' "
                        f"to release it, or wait for TTL expiration."
                    )
                    raise LockUnavailableError(msg)

                sleep_time = min(backoff_time, remaining_time)
                time.sleep(sleep_time)
                attempt += 1


def release_lock(client: DynamoDBClient, lock_name: str, owner: str) -> dict[str, Any]:
    """
    Release a distributed lock. This operation is idempotent.

    Args:
        client: DynamoDB client
        lock_name: Name of the lock to release
        owner: Owner ID (must match lock holder)

    Returns:
        Lock release confirmation

    Raises:
        KVStoreError: For any unexpected DynamoDB errors.
    """
    pk = format_key(PREFIX_LOCK, lock_name)
    sk = pk

    try:
        client.delete_item(
            {ATTR_PK: pk, ATTR_SK: sk},
            condition_expression="#value = :owner",
            expression_attribute_names={"#value": "value"},
            expression_attribute_values={":owner": owner},
        )
        # If delete is successful, the lock was held and is now released.
        return {"lock": lock_name, "released": True, "status": "released"}
    except ConditionFailedError:
        # This error means the lock either doesn't exist or is owned by someone else.
        # In either case, the lock is not held by the specified owner, so the
        # operation can be considered a success from an idempotency standpoint.
        return {"lock": lock_name, "released": True, "status": "not_owned_or_already_released"}


def extend_lock(
    client: DynamoDBClient,
    lock_name: str,
    ttl: int,
    owner: str,
) -> dict[str, Any]:
    """
    Extend lock TTL.

    Args:
        client: DynamoDB client
        lock_name: Lock name
        ttl: New TTL in seconds from now
        owner: Owner ID

    Returns:
        Lock data

    Raises:
        ConditionFailedError: If lock is not held by this owner or doesn't exist
    """
    pk = format_key(PREFIX_LOCK, lock_name)
    sk = pk
    timestamp = int(time.time())
    new_ttl = timestamp + ttl

    try:
        client.update_item(
            key={ATTR_PK: pk, ATTR_SK: sk},
            update_expression="SET #ttl = :new_ttl, updated_at = :ts",
            expression_attribute_names={"#ttl": "ttl", "#value": "value"},
            expression_attribute_values={":new_ttl": new_ttl, ":owner": owner, ":ts": timestamp},
            condition_expression="#value = :owner",
            return_values="ALL_NEW",
        )
    except ConditionFailedError:
        raise ConditionFailedError(
            f"Cannot extend lock '{lock_name}': not owned by '{owner}' or lock does not exist"
        )

    return {
        "lock": lock_name,
        "owner": owner,
        "ttl": new_ttl,
        "extended": True,
    }


def check_lock(client: DynamoDBClient, lock_name: str) -> dict[str, Any] | None:
    """
    Check if a lock is held.

    Args:
        client: DynamoDB client
        lock_name: Name of the lock

    Returns:
        Lock information if locked, None if free
    """
    pk = format_key(PREFIX_LOCK, lock_name)
    sk = pk

    item = client.get_item({ATTR_PK: pk, ATTR_SK: sk})

    if not item:
        return None

    return {
        "lock": lock_name,
        "owner": item["value"],
        "ttl": item.get("ttl"),
        "acquired_at": item.get("metadata", {}).get("acquired_at"),
    }


def generate_default_owner() -> str:
    """
    Generate default owner ID.

    Returns:
        Owner ID in format hostname-pid
    """
    return f"{socket.gethostname()}-{os.getpid()}"
