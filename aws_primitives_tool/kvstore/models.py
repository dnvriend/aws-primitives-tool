"""
Type models for kvstore operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(Enum):
    """Types of items stored in kvstore."""

    KV = "kv"
    COUNTER = "counter"
    LOCK = "lock"
    QUEUE = "queue"
    LEADER = "leader"
    SET = "set"
    LIST = "list"


@dataclass
class Item:
    """Base item model for DynamoDB storage."""

    pk: str
    sk: str
    value: Any
    type: ItemType
    ttl: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: int = 0
    updated_at: int = 0
    version: int = 1


@dataclass
class Counter:
    """Counter model for atomic increment/decrement operations."""

    key: str
    value: int
    type: ItemType = ItemType.COUNTER
    created_at: int = 0
    updated_at: int = 0


@dataclass
class Lock:
    """Distributed lock model for coordination primitives."""

    name: str
    owner: str
    ttl: int
    acquired_at: int
    type: ItemType = ItemType.LOCK


@dataclass
class QueueMessage:
    """Queue message model for work distribution."""

    queue: str
    data: dict[str, Any]
    receipt: str | None = None
    visibility_timeout: int | None = None
    created_at: int = 0


@dataclass
class Leader:
    """Leader model for leader election patterns."""

    pool: str
    leader_id: str
    ttl: int
    elected_at: int
    type: ItemType = ItemType.LEADER
