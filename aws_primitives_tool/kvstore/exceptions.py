"""
Custom exceptions for kvstore operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""


class KVStoreError(Exception):
    """Base exception for kvstore operations."""

    pass


class KeyNotFoundError(KVStoreError):
    """Key does not exist."""

    pass


class KeyExistsError(KVStoreError):
    """Key already exists (if-not-exists condition failed)."""

    pass


class ConditionFailedError(KVStoreError):
    """Conditional update failed."""

    pass


class LockUnavailableError(KVStoreError):
    """Lock is held by another process."""

    pass


class NotLeaderError(KVStoreError):
    """Operation requires leadership."""

    pass


class QueueEmptyError(KVStoreError):
    """Queue has no items."""

    pass


class LeaderElectionError(KVStoreError):
    """Leader election failed - another agent is the leader."""

    pass


class AWSThrottlingError(KVStoreError):
    """DynamoDB throttling occurred."""

    pass


class AWSPermissionError(KVStoreError):
    """AWS permission denied."""

    pass


class TableNotFoundError(KVStoreError):
    """DynamoDB table does not exist."""

    pass


class TableAlreadyExistsError(KVStoreError):
    """DynamoDB table already exists."""

    pass
