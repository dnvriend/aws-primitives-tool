# KVStore Primitives Design Document

**Author:** Dennis Vriend
**Date:** 2025-11-15
**Status:** Design Document
**Version:** 1.0

> Design specification for DynamoDB-backed key-value store primitives with atomic transactional operations for distributed systems.

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [DynamoDB Architecture](#dynamodb-architecture)
4. [Primitive Operations](#primitive-operations)
5. [CLI Command Specifications](#cli-command-specifications)
6. [Implementation Architecture](#implementation-architecture)
7. [Error Handling](#error-handling)
8. [Use Cases & Examples](#use-cases--examples)
9. [Cost Analysis](#cost-analysis)
10. [Testing Strategy](#testing-strategy)

---

## Overview

The `kvstore` primitive provides a globally distributed, always-on, atomic transactional key-value store backed by Amazon DynamoDB. It enables distributed coordination patterns including:

- **Key-Value Storage** - Simple get/set operations
- **Atomic Counters** - Thread-safe increment/decrement
- **Distributed Locks** - Coordination primitives with TTL
- **Work Queues** - FIFO and priority queue implementations
- **Leader Election** - Singleton task coordination
- **Sets & Lists** - Collection primitives
- **TTL Management** - Automatic expiration

### Why DynamoDB?

✅ **Atomic Operations** - Built-in atomic increments, conditional updates
✅ **Global Availability** - 99.999% SLA, single-digit millisecond latency
✅ **True Serverless** - Scales to zero, pay-per-request
✅ **Cost-Effective** - $4-8/month for most use cases, 25GB+25WCU+25RCU free tier
✅ **No Infrastructure** - Zero servers, fully managed
✅ **ACID Transactions** - TransactWriteItems for multi-item operations

---

## Design Principles

### 1. Table Selection

**All kvstore commands require a table name:**

```bash
# Option 1: Explicit table argument (highest priority)
kvstore set counter 0 --table my-custom-table

# Option 2: Environment variable (if no --table provided)
export KVSTORE_TABLE=my-custom-table
kvstore set counter 0

# Option 3: Default table name (if no --table and no env var)
kvstore set counter 0  # Uses "aws-primitives-tool-kvstore"
```

**Table Name Priority**:
1. `--table` argument (explicit)
2. `KVSTORE_TABLE` environment variable
3. Default: `aws-primitives-tool-kvstore`

**Global Option**:
- `--table <table-name>` - DynamoDB table name (default: `aws-primitives-tool-kvstore`)

This allows users to:
- Use multiple isolated kvstore tables (dev, staging, prod)
- Share tables across projects via environment variables
- Get started quickly with sensible defaults

### 2. Atomic-First Design

**All operations MUST be atomic** - No race conditions, no partial updates.

- Use DynamoDB's atomic operations: `UpdateItem` with `ADD`, `SET`, `DELETE`
- Use conditional expressions for compare-and-swap (CAS)
- Use transactions for multi-item updates (`TransactWriteItems`)
- Never use read-modify-write patterns without conditions

### 3. CLI-Friendly & Agent-Friendly

**Commands must be composable and pipeable:**

```bash
# Composable with pipes
kvstore get counter | jq '.value'

# Composable with shell scripts
if kvstore lock acquire deploy --ttl 300; then
  deploy.sh
  kvstore lock release deploy
fi

# Agent-friendly JSON output
kvstore queue pop tasks --format json | process-task.py
```

### 3. Idempotent Operations

**Same command, same effect, no matter how many times:**

- `set key value` - Always sets to value (idempotent)
- `inc counter` - Atomic, but creates if missing (safe)
- `lock acquire task-123` - Returns existing lock if held (idempotent with same TTL)
- `queue push task data` - Use deduplication ID for idempotency

### 4. Idempotent Operations

**Same command, same effect, no matter how many times:**

- `set key value` - Always sets to value (idempotent)
- `inc counter` - Atomic, but creates if missing (safe)
- `lock acquire task-123` - Returns existing lock if held (idempotent with same TTL)
- `queue push task data` - Use deduplication ID for idempotency

### 5. Explicit Table Management

**Users control table lifecycle:**

```bash
# Create table (one-time setup)
kvstore create-table --table my-store --billing on-demand

# Use table explicitly or via environment variable
kvstore set counter 0 --table my-store
# OR
export KVSTORE_TABLE=my-store
kvstore set counter 0

# Or use default table (no --table, no env var)
kvstore set counter 0  # Uses "aws-primitives-tool-kvstore"
```

### 6. Consistent Error Handling

**Errors must inform and guide:**

```
Error: Key "counter" does not exist
Solution: Use 'kvstore set counter 0' to initialize or 'kvstore inc counter --create' to create if missing
```

**Exit codes:**
- `0` - Success
- `1` - Operation failed (key not found, condition failed)
- `2` - Invalid arguments
- `3` - AWS error (throttling, permissions)
- `4` - Lock unavailable (non-blocking lock acquire)

---

## DynamoDB Architecture

### Table Schema

**Single-table design** for maximum flexibility and cost efficiency.

```
Table Name: {user-defined} (e.g., claude-code-kvstore)
Billing Mode: On-Demand (recommended) or Provisioned

Primary Key:
  PK (String, Partition Key): Namespace-prefixed key (e.g., "kv:counter", "lock:deploy", "queue:tasks")
  SK (String, Sort Key): Item-specific identifier (e.g., timestamp for queue items)

Attributes:
  - value (String, Number, Binary, or Map): The stored value
  - type (String): Item type (kv, counter, lock, queue, set, list)
  - ttl (Number): Unix timestamp for automatic expiration
  - metadata (Map): Additional operation-specific data
  - created_at (Number): Unix timestamp
  - updated_at (Number): Unix timestamp
  - version (Number): Optimistic locking version counter

TTL Attribute: ttl (automatic cleanup by DynamoDB)
```

### Namespace Prefixes

**Prevent key collisions and enable efficient queries:**

| Prefix | Purpose | Example Key |
|--------|---------|-------------|
| `kv:` | Simple key-value | `kv:config/api-key` |
| `counter:` | Atomic counters | `counter:api-requests` |
| `lock:` | Distributed locks | `lock:deploy-prod` |
| `queue:` | Work queues | `queue:tasks#{timestamp}` |
| `leader:` | Leader election | `leader:build-manager` |
| `set:` | Set collections | `set:active-agents#{member}` |
| `list:` | List collections | `list:recent-logs#{index}` |

### Global Secondary Indexes (GSI)

**GSI-1: Type-based queries**
```
Partition Key: type (String)
Sort Key: updated_at (Number, descending)

Use case: List all locks, list all queues, etc.
Query: "Give me all locks sorted by most recently updated"
```

**GSI-2: TTL-based queries (optional)**
```
Partition Key: type (String)
Sort Key: ttl (Number, ascending)

Use case: Find items expiring soon
Query: "Give me all locks expiring in next 5 minutes"
```

---

## Primitive Operations

### 1. Key-Value Operations

#### `set` - Store a value

**Operation:** `PutItem` (overwrites existing)

```bash
kvstore set <key> <value> [--ttl SECONDS] [--if-not-exists]

# Examples
kvstore set config/api-key "sk-abc123" --ttl 3600
kvstore set agent/status "active" --if-not-exists
```

**DynamoDB:**
```python
table.put_item(
    Item={
        'PK': 'kv:config/api-key',
        'SK': 'kv:config/api-key',
        'value': 'sk-abc123',
        'type': 'kv',
        'ttl': int(time.time()) + 3600,
        'created_at': timestamp,
        'updated_at': timestamp,
        'version': 1
    },
    ConditionExpression='attribute_not_exists(PK)' if if_not_exists else None
)
```

#### `get` - Retrieve a value

**Operation:** `GetItem`

```bash
kvstore get <key> [--default VALUE]

# Examples
kvstore get config/api-key
kvstore get config/missing --default "none"
```

**Output (JSON):**
```json
{
  "key": "config/api-key",
  "value": "sk-abc123",
  "type": "kv",
  "ttl": 1731699600,
  "created_at": 1731696000,
  "updated_at": 1731696000
}
```

#### `delete` - Remove a key

**Operation:** `DeleteItem`

```bash
kvstore delete <key> [--if-value VALUE]

# Examples
kvstore delete config/api-key
kvstore delete config/api-key --if-value "sk-abc123"  # Conditional delete
```

#### `exists` - Check if key exists

**Operation:** `GetItem` (ProjectionExpression to minimize cost)

```bash
kvstore exists <key>

# Exit code: 0 if exists, 1 if not
```

#### `list` - List keys by prefix

**Operation:** `Query` on PK prefix

```bash
kvstore list [PREFIX] [--limit N] [--format json|keys]

# Examples
kvstore list config/
kvstore list --limit 100 --format keys
```

---

### 2. Counter Operations

#### `inc` - Atomic increment

**Operation:** `UpdateItem` with `ADD` expression (atomic)

```bash
kvstore inc <key> [--by N] [--create]

# Examples
kvstore inc api-requests
kvstore inc api-requests --by 10
kvstore inc new-counter --by 1 --create  # Initialize to 0 if missing
```

**DynamoDB:**
```python
table.update_item(
    Key={'PK': 'counter:api-requests', 'SK': 'counter:api-requests'},
    UpdateExpression='ADD #value :inc SET updated_at = :ts',
    ExpressionAttributeNames={'#value': 'value'},
    ExpressionAttributeValues={':inc': 1, ':ts': timestamp},
    ReturnValues='ALL_NEW'
)
```

**Atomicity:** DynamoDB guarantees atomic ADD operations - no race conditions.

#### `dec` - Atomic decrement

**Operation:** `UpdateItem` with `ADD` (negative number)

```bash
kvstore dec <key> [--by N]

# Examples
kvstore dec rate-limit-remaining
kvstore dec rate-limit-remaining --by 5
```

#### `get-counter` - Read counter value

**Operation:** `GetItem`

```bash
kvstore get-counter <key>

# Output
{"key": "api-requests", "value": 12345, "type": "counter"}
```

---

### 3. Lock Operations (Distributed Coordination)

#### `lock acquire` - Acquire distributed lock

**Operation:** `PutItem` with `attribute_not_exists(PK)` condition

```bash
kvstore lock acquire <lock-name> [--ttl SECONDS] [--wait SECONDS] [--owner ID]

# Examples
kvstore lock acquire deploy-prod --ttl 300
kvstore lock acquire deploy-prod --ttl 300 --wait 60  # Wait up to 60s
kvstore lock acquire task-123 --owner agent-abc --ttl 120
```

**DynamoDB:**
```python
table.put_item(
    Item={
        'PK': 'lock:deploy-prod',
        'SK': 'lock:deploy-prod',
        'value': owner_id,  # Who owns the lock
        'type': 'lock',
        'ttl': int(time.time()) + ttl_seconds,
        'metadata': {'acquired_at': timestamp, 'owner': owner_id},
        'created_at': timestamp,
        'updated_at': timestamp
    },
    ConditionExpression='attribute_not_exists(PK)'  # Only acquire if free
)
```

**Wait behavior:**
- `--wait 0` (default): Return immediately if lock unavailable (exit code 4)
- `--wait N`: Retry with exponential backoff up to N seconds

**Exit codes:**
- `0` - Lock acquired
- `4` - Lock unavailable (non-blocking or timeout)

#### `lock release` - Release lock

**Operation:** `DeleteItem` with owner condition (prevent accidental release by other processes)

```bash
kvstore lock release <lock-name> [--owner ID]

# Examples
kvstore lock release deploy-prod
kvstore lock release task-123 --owner agent-abc
```

**DynamoDB:**
```python
table.delete_item(
    Key={'PK': 'lock:deploy-prod', 'SK': 'lock:deploy-prod'},
    ConditionExpression='#value = :owner',  # Only owner can release
    ExpressionAttributeNames={'#value': 'value'},
    ExpressionAttributeValues={':owner': owner_id}
)
```

#### `lock check` - Check lock status

**Operation:** `GetItem`

```bash
kvstore lock check <lock-name>

# Output
{"lock": "deploy-prod", "owner": "agent-123", "ttl": 1731696300, "acquired_at": 1731696000}

# Exit code: 0 if locked, 1 if free
```

#### `lock extend` - Extend lock TTL

**Operation:** `UpdateItem` with owner condition

```bash
kvstore lock extend <lock-name> --ttl SECONDS [--owner ID]

# Examples
kvstore lock extend deploy-prod --ttl 600 --owner agent-123
```

---

### 4. Queue Operations

#### `queue push` - Add item to queue

**Operation:** `PutItem` with timestamp-based sort key

```bash
kvstore queue push <queue-name> <data> [--priority N] [--dedup-id ID]

# Examples
kvstore queue push tasks '{"task": "analyze-logs", "params": {...}}'
kvstore queue push tasks '{"task": "urgent"}' --priority 1  # Lower = higher priority
kvstore queue push tasks '{"task": "idempotent"}' --dedup-id task-123
```

**DynamoDB:**
```python
# Standard queue (FIFO by timestamp)
table.put_item(
    Item={
        'PK': 'queue:tasks',
        'SK': f'queue:tasks#{priority:010d}#{timestamp}#{uuid}',  # Composite sort key
        'value': data,
        'type': 'queue',
        'ttl': ttl if provided else None,
        'metadata': {'dedup_id': dedup_id, 'priority': priority},
        'created_at': timestamp
    }
)
```

**Sort key design:**
- `{priority:010d}` - Zero-padded priority (lower = processed first)
- `{timestamp}` - Unix timestamp with microseconds
- `{uuid}` - Unique identifier for ties

#### `queue pop` - Remove and return item

**Operation:** `Query` (get oldest) + `DeleteItem` (atomic via condition)

```bash
kvstore queue pop <queue-name> [--visibility-timeout SECONDS]

# Examples
kvstore queue pop tasks
kvstore queue pop tasks --visibility-timeout 300  # Hide for 5 minutes
```

**DynamoDB:**
```python
# Step 1: Query for oldest item
response = table.query(
    KeyConditionExpression='PK = :pk',
    ExpressionAttributeValues={':pk': 'queue:tasks'},
    Limit=1,
    ScanIndexForward=True  # Ascending order (oldest first)
)

# Step 2: Delete item (mark as invisible if visibility-timeout)
if visibility_timeout:
    # Update with visibility deadline
    table.update_item(
        Key={'PK': item['PK'], 'SK': item['SK']},
        UpdateExpression='SET #ttl = :deadline',
        ExpressionAttributeNames={'#ttl': 'ttl'},
        ExpressionAttributeValues={':deadline': time.time() + visibility_timeout}
    )
else:
    # Delete immediately
    table.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})
```

**Output (JSON):**
```json
{
  "queue": "tasks",
  "data": {"task": "analyze-logs", "params": {}},
  "receipt": "queue:tasks#0000000001#1731696000#abc123",
  "visibility_timeout": 300
}
```

#### `queue peek` - View next item without removing

**Operation:** `Query` (read-only)

```bash
kvstore queue peek <queue-name> [--count N]

# Examples
kvstore queue peek tasks
kvstore queue peek tasks --count 10
```

#### `queue size` - Count items in queue

**Operation:** `Query` with `Select=COUNT`

```bash
kvstore queue size <queue-name>

# Output
{"queue": "tasks", "size": 42}
```

#### `queue ack` - Acknowledge processed item

**Operation:** `DeleteItem` (for visibility-timeout pattern)

```bash
kvstore queue ack <queue-name> <receipt>

# Example
kvstore queue ack tasks "queue:tasks#0000000001#1731696000#abc123"
```

---

### 5. Leader Election Operations

#### `leader elect` - Attempt to become leader

**Operation:** `PutItem` with `attribute_not_exists(PK)` condition

```bash
kvstore leader elect <pool-name> [--ttl SECONDS] [--id AGENT_ID]

# Examples
kvstore leader elect build-manager --ttl 30 --id agent-123
```

**DynamoDB:**
```python
table.put_item(
    Item={
        'PK': 'leader:build-manager',
        'SK': 'leader:build-manager',
        'value': agent_id,  # Current leader
        'type': 'leader',
        'ttl': int(time.time()) + ttl_seconds,
        'metadata': {'elected_at': timestamp},
        'created_at': timestamp,
        'updated_at': timestamp
    },
    ConditionExpression='attribute_not_exists(PK)'
)
```

**Exit codes:**
- `0` - Elected as leader
- `4` - Another agent is leader

#### `leader heartbeat` - Extend leadership

**Operation:** `UpdateItem` with current leader condition

```bash
kvstore leader heartbeat <pool-name> [--ttl SECONDS] [--id AGENT_ID]

# Example
kvstore leader heartbeat build-manager --ttl 30 --id agent-123
```

**DynamoDB:**
```python
table.update_item(
    Key={'PK': 'leader:build-manager', 'SK': 'leader:build-manager'},
    UpdateExpression='SET #ttl = :new_ttl, updated_at = :ts',
    ConditionExpression='#value = :agent_id',  # Only current leader can heartbeat
    ExpressionAttributeNames={'#ttl': 'ttl', '#value': 'value'},
    ExpressionAttributeValues={
        ':new_ttl': int(time.time()) + ttl_seconds,
        ':agent_id': agent_id,
        ':ts': timestamp
    }
)
```

#### `leader check` - Check current leader

**Operation:** `GetItem`

```bash
kvstore leader check <pool-name>

# Output
{"pool": "build-manager", "leader": "agent-123", "ttl": 1731696030, "elected_at": 1731696000}

# Exit code: 0 if leader exists, 1 if no leader
```

#### `leader resign` - Step down as leader

**Operation:** `DeleteItem` with owner condition

```bash
kvstore leader resign <pool-name> [--id AGENT_ID]

# Example
kvstore leader resign build-manager --id agent-123
```

---

### 6. Set Operations

#### `sadd` - Add member to set

**Operation:** `PutItem` with composite sort key

```bash
kvstore sadd <set-name> <member>

# Examples
kvstore sadd active-agents agent-123
kvstore sadd active-agents agent-456
```

**DynamoDB:**
```python
table.put_item(
    Item={
        'PK': 'set:active-agents',
        'SK': f'set:active-agents#{member}',
        'value': member,
        'type': 'set',
        'created_at': timestamp
    }
)
```

#### `srem` - Remove member from set

**Operation:** `DeleteItem`

```bash
kvstore srem <set-name> <member>

# Example
kvstore srem active-agents agent-123
```

#### `sismember` - Check if member exists

**Operation:** `GetItem`

```bash
kvstore sismember <set-name> <member>

# Exit code: 0 if exists, 1 if not
```

#### `smembers` - List all members

**Operation:** `Query` on PK

```bash
kvstore smembers <set-name>

# Output
{"set": "active-agents", "members": ["agent-123", "agent-456"]}
```

#### `scard` - Count members

**Operation:** `Query` with `Select=COUNT`

```bash
kvstore scard <set-name>

# Output
{"set": "active-agents", "size": 2}
```

---

### 7. List Operations

#### `lpush` - Prepend to list

**Operation:** `PutItem` with negative timestamp (newest first)

```bash
kvstore lpush <list-name> <value>

# Example
kvstore lpush recent-logs "Error at 12:34:56"
```

#### `rpush` - Append to list

**Operation:** `PutItem` with positive timestamp (oldest first)

```bash
kvstore rpush <list-name> <value>

# Example
kvstore rpush task-queue "Task 123"
```

#### `lpop` - Remove and return first item

**Operation:** `Query` + `DeleteItem`

```bash
kvstore lpop <list-name>

# Output
{"list": "recent-logs", "value": "Error at 12:34:56"}
```

#### `rpop` - Remove and return last item

**Operation:** `Query` (reverse) + `DeleteItem`

```bash
kvstore rpop <list-name>
```

#### `lrange` - Get range of items

**Operation:** `Query` with limit

```bash
kvstore lrange <list-name> <start> <stop>

# Example
kvstore lrange recent-logs 0 9  # Get first 10 items
```

---

### 8. Transaction Operations

#### `transaction` - Execute multiple operations atomically

**Operation:** `TransactWriteItems` (up to 100 operations)

```bash
kvstore transaction --file tx.json

# tx.json example:
[
  {"op": "set", "key": "account/balance", "value": 1000, "condition": "attribute_not_exists(PK)"},
  {"op": "inc", "key": "counter/transactions", "by": 1},
  {"op": "delete", "key": "temp/lock", "condition": "attribute_exists(PK)"}
]
```

**DynamoDB:**
```python
table.meta.client.transact_write_items(
    TransactItems=[
        {'Put': {...}},
        {'Update': {...}},
        {'Delete': {...}}
    ]
)
```

**Atomicity:** All operations succeed or all fail (ACID transaction).

---

## CLI Command Specifications

### Command Structure

**Pattern:** `kvstore <category> <operation> [arguments] [options]`

```bash
# Category-based grouping
kvstore set key value              # Key-value operations (flat)
kvstore inc counter                # Counter operations (flat)
kvstore lock acquire name          # Lock operations (nested)
kvstore queue push name data       # Queue operations (nested)
kvstore leader elect pool          # Leader operations (nested)
kvstore sadd set member            # Set operations (flat, Redis-style)
kvstore lpush list value           # List operations (flat, Redis-style)
```

### Global Options

**Available on all commands:**

```bash
--table TABLE              # DynamoDB table name (default: "aws-primitives-tool-kvstore")
                           # Priority: 1) --table arg, 2) KVSTORE_TABLE env var, 3) default
--region REGION            # AWS region (or AWS_REGION env var)
--profile PROFILE          # AWS profile (or AWS_PROFILE env var)
--format json|text|value   # Output format (default: json)
--verbose / -V             # Verbose output (stderr)
--quiet / -q               # Suppress output
```

**Table Name Resolution Priority**:
1. `--table` argument (explicit, highest priority)
2. `KVSTORE_TABLE` environment variable (if no `--table`)
3. Default: `aws-primitives-tool-kvstore` (if no `--table` and no env var)

This allows:
- Multiple isolated environments (dev, staging, prod)
- Shared configuration via environment variables
- Zero-config getting started with sensible defaults

### Environment Variables

```bash
# Primary configuration
export KVSTORE_TABLE=my-custom-table  # Override default table name
export AWS_REGION=eu-central-1
export AWS_PROFILE=default

# Optional
export KVSTORE_DEFAULT_TTL=3600     # Default TTL for keys
export KVSTORE_LOCK_TTL=300         # Default lock TTL
export KVSTORE_QUEUE_VISIBILITY=60  # Default queue visibility timeout
```

### Agent-Friendly Help Examples

**Every command includes self-documenting examples:**

```python
@click.command()
def inc():
    """Atomically increment a counter.

    Increments are atomic and thread-safe. If the counter does not exist,
    use --create to initialize it to 0 before incrementing.

    Examples:

    \b
        # Increment by 1
        kvstore inc api-requests

    \b
        # Increment by custom amount
        kvstore inc api-requests --by 10

    \b
        # Create counter if missing (initialize to 0)
        kvstore inc new-counter --create

    \b
    Output Format:
        Returns JSON with new value:
        {"key": "api-requests", "value": 123, "previous": 122}
    """
    pass
```

---

## Implementation Architecture

### Project Structure

```
aws_primitives_tool/
├── cli.py                          # Main CLI entry point with command groups
├── kvstore/
│   ├── __init__.py                 # Public API exports
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── kv_commands.py          # Key-value commands (set, get, delete, etc.)
│   │   ├── counter_commands.py     # Counter commands (inc, dec)
│   │   ├── lock_commands.py        # Lock commands (acquire, release, check, extend)
│   │   ├── queue_commands.py       # Queue commands (push, pop, peek, ack)
│   │   ├── leader_commands.py      # Leader commands (elect, heartbeat, check, resign)
│   │   ├── set_commands.py         # Set commands (sadd, srem, smembers, etc.)
│   │   ├── list_commands.py        # List commands (lpush, rpush, lpop, etc.)
│   │   └── transaction_commands.py # Transaction command
│   ├── core/
│   │   ├── __init__.py
│   │   ├── client.py               # DynamoDB client wrapper
│   │   ├── kv_operations.py        # Core key-value logic
│   │   ├── counter_operations.py   # Core counter logic
│   │   ├── lock_operations.py      # Core lock logic
│   │   ├── queue_operations.py     # Core queue logic
│   │   ├── leader_operations.py    # Core leader logic
│   │   ├── set_operations.py       # Core set logic
│   │   ├── list_operations.py      # Core list logic
│   │   └── transaction_operations.py # Core transaction logic
│   ├── models.py                   # Type models (Item, Lock, QueueMessage, etc.)
│   ├── exceptions.py               # Custom exceptions
│   └── utils.py                    # Shared utilities
└── utils.py                        # Global utilities
```

### Code Organization Principles

1. **Separation of Concerns:**
   - `commands/` - CLI interface (Click decorators, argument parsing)
   - `core/` - Business logic (pure functions, no CLI dependencies)
   - `models.py` - Type definitions
   - `exceptions.py` - Error types

2. **Importable Library:**
   - Core functions can be imported: `from aws_primitives_tool.kvstore import set_value, inc_counter`
   - CLI-independent for programmatic use

3. **Exception-Based Errors:**
   - Core functions raise custom exceptions (NOT `sys.exit()`)
   - CLI layer catches exceptions and formats output/exit codes

### Type Definitions (models.py)

```python
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum

class ItemType(Enum):
    KV = "kv"
    COUNTER = "counter"
    LOCK = "lock"
    QUEUE = "queue"
    LEADER = "leader"
    SET = "set"
    LIST = "list"

@dataclass
class Item:
    """Base item model."""
    pk: str
    sk: str
    value: Any
    type: ItemType
    ttl: Optional[int] = None
    metadata: dict[str, Any] = None
    created_at: int = 0
    updated_at: int = 0
    version: int = 1

@dataclass
class Counter:
    """Counter model."""
    key: str
    value: int
    type: ItemType = ItemType.COUNTER
    created_at: int = 0
    updated_at: int = 0

@dataclass
class Lock:
    """Distributed lock model."""
    name: str
    owner: str
    ttl: int
    acquired_at: int
    type: ItemType = ItemType.LOCK

@dataclass
class QueueMessage:
    """Queue message model."""
    queue: str
    data: dict[str, Any]
    priority: int = 0
    receipt: Optional[str] = None
    visibility_timeout: Optional[int] = None
    created_at: int = 0

@dataclass
class Leader:
    """Leader model."""
    pool: str
    leader_id: str
    ttl: int
    elected_at: int
    type: ItemType = ItemType.LEADER
```

### Exception Hierarchy (exceptions.py)

```python
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

class AWSThrottlingError(KVStoreError):
    """DynamoDB throttling occurred."""
    pass

class AWSPermissionError(KVStoreError):
    """AWS permission denied."""
    pass
```

### DynamoDB Client (core/client.py)

```python
import boto3
from typing import Optional
from botocore.exceptions import ClientError

class DynamoDBClient:
    """DynamoDB client wrapper with error handling."""

    def __init__(
        self,
        table_name: str,
        region: Optional[str] = None,
        profile: Optional[str] = None
    ):
        session = boto3.Session(profile_name=profile, region_name=region)
        self.dynamodb = session.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name

    def put_item(self, item: dict, condition: Optional[str] = None) -> dict:
        """Put item with optional condition."""
        try:
            kwargs = {'Item': item}
            if condition:
                kwargs['ConditionExpression'] = condition
            return self.table.put_item(**kwargs)
        except ClientError as e:
            self._handle_error(e)

    def get_item(self, key: dict, projection: Optional[str] = None) -> Optional[dict]:
        """Get item with optional projection."""
        try:
            kwargs = {'Key': key}
            if projection:
                kwargs['ProjectionExpression'] = projection
            response = self.table.get_item(**kwargs)
            return response.get('Item')
        except ClientError as e:
            self._handle_error(e)

    def update_item(
        self,
        key: dict,
        update_expression: str,
        expression_values: dict,
        condition: Optional[str] = None,
        return_values: str = 'ALL_NEW'
    ) -> dict:
        """Update item with expressions."""
        try:
            kwargs = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values,
                'ReturnValues': return_values
            }
            if condition:
                kwargs['ConditionExpression'] = condition
            return self.table.update_item(**kwargs)
        except ClientError as e:
            self._handle_error(e)

    def delete_item(self, key: dict, condition: Optional[str] = None) -> dict:
        """Delete item with optional condition."""
        try:
            kwargs = {'Key': key}
            if condition:
                kwargs['ConditionExpression'] = condition
            return self.table.delete_item(**kwargs)
        except ClientError as e:
            self._handle_error(e)

    def query(
        self,
        key_condition: str,
        expression_values: dict,
        limit: Optional[int] = None,
        ascending: bool = True
    ) -> list[dict]:
        """Query items."""
        try:
            kwargs = {
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': expression_values,
                'ScanIndexForward': ascending
            }
            if limit:
                kwargs['Limit'] = limit
            response = self.table.query(**kwargs)
            return response.get('Items', [])
        except ClientError as e:
            self._handle_error(e)

    def _handle_error(self, error: ClientError) -> None:
        """Convert boto3 errors to kvstore exceptions."""
        code = error.response['Error']['Code']

        if code == 'ConditionalCheckFailedException':
            raise ConditionFailedError(f"Condition failed: {error}")
        elif code == 'ResourceNotFoundException':
            raise KVStoreError(f"Table '{self.table_name}' not found")
        elif code == 'ProvisionedThroughputExceededException':
            raise AWSThrottlingError("DynamoDB throttling - retry with backoff")
        elif code == 'AccessDeniedException':
            raise AWSPermissionError("AWS permission denied")
        else:
            raise KVStoreError(f"DynamoDB error: {error}")
```

### Core Operations Example (core/counter_operations.py)

```python
import time
from .client import DynamoDBClient
from ..models import Counter, ItemType
from ..exceptions import KeyNotFoundError

def increment_counter(
    client: DynamoDBClient,
    key: str,
    by: int = 1,
    create: bool = False
) -> Counter:
    """Atomically increment a counter.

    Args:
        client: DynamoDB client
        key: Counter key
        by: Amount to increment (default: 1)
        create: Create counter if missing (default: False)

    Returns:
        Counter object with new value

    Raises:
        KeyNotFoundError: Counter does not exist and create=False
    """
    pk = f"counter:{key}"
    sk = pk
    timestamp = int(time.time())

    try:
        response = client.update_item(
            key={'PK': pk, 'SK': sk},
            update_expression='ADD #value :inc SET updated_at = :ts, #type = :type',
            expression_values={
                ':inc': by,
                ':ts': timestamp,
                ':type': ItemType.COUNTER.value
            },
            condition=None if create else 'attribute_exists(PK)',
            return_values='ALL_NEW'
        )

        item = response['Attributes']
        return Counter(
            key=key,
            value=int(item['value']),
            created_at=item.get('created_at', timestamp),
            updated_at=item['updated_at']
        )

    except ConditionFailedError:
        raise KeyNotFoundError(
            f"Counter '{key}' does not exist. "
            f"Use 'kvstore inc {key} --create' to initialize."
        )
```

### CLI Command Example (commands/counter_commands.py)

```python
import click
import json
from ..core.client import DynamoDBClient
from ..core.counter_operations import increment_counter
from ..exceptions import KVStoreError, KeyNotFoundError

@click.command('inc')
@click.argument('key')
@click.option('--by', type=int, default=1, help='Amount to increment (default: 1)')
@click.option('--create', is_flag=True, help='Create counter if missing')
@click.option('--table', envvar='KVSTORE_TABLE', required=True, help='DynamoDB table name')
@click.option('--region', envvar='AWS_REGION', help='AWS region')
@click.option('--profile', envvar='AWS_PROFILE', help='AWS profile')
@click.option('--format', type=click.Choice(['json', 'value']), default='json', help='Output format')
@click.option('--verbose', '-V', is_flag=True, help='Verbose output')
def inc_command(key: str, by: int, create: bool, table: str, region: str, profile: str, format: str, verbose: bool):
    """Atomically increment a counter.

    Increments are atomic and thread-safe. If the counter does not exist,
    use --create to initialize it to 0 before incrementing.

    Examples:

    \b
        # Increment by 1
        kvstore inc api-requests

    \b
        # Increment by custom amount
        kvstore inc api-requests --by 10

    \b
        # Create counter if missing (initialize to 0)
        kvstore inc new-counter --create

    \b
    Output Format:
        Returns JSON with new value:
        {"key": "api-requests", "value": 123}
    """
    try:
        if verbose:
            click.echo(f"Incrementing counter '{key}' by {by}...", err=True)

        client = DynamoDBClient(table_name=table, region=region, profile=profile)
        counter = increment_counter(client, key, by=by, create=create)

        if format == 'json':
            output = {
                'key': counter.key,
                'value': counter.value,
                'updated_at': counter.updated_at
            }
            click.echo(json.dumps(output))
        elif format == 'value':
            click.echo(str(counter.value))

        if verbose:
            click.echo(f"Counter '{key}' = {counter.value}", err=True)

    except KeyNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo(
            f"\nSolution: Use 'kvstore inc {key} --create' to initialize the counter",
            err=True
        )
        raise click.Exit(1)

    except KVStoreError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Exit(3)
```

---

## Error Handling

### Error Categories

1. **User Errors (Exit 1):**
   - Key not found
   - Key already exists (if-not-exists failed)
   - Invalid condition

2. **Invalid Arguments (Exit 2):**
   - Missing required arguments
   - Invalid value types
   - Out of range values

3. **AWS Errors (Exit 3):**
   - DynamoDB throttling
   - Permission denied
   - Table not found
   - Network errors

4. **Coordination Errors (Exit 4):**
   - Lock unavailable
   - Not elected as leader
   - Queue empty (non-blocking pop)

### Error Message Format

**Structure:**

```
Error: <concise description>

Solution: <actionable remedy>

Details (optional):
  - <additional context>
```

**Examples:**

```bash
# Key not found
Error: Key "counter" does not exist

Solution: Initialize the counter with 'kvstore set counter 0' or use 'kvstore inc counter --create'

# Lock unavailable
Error: Lock "deploy-prod" is currently held by agent-123 (expires in 120 seconds)

Solution: Wait for lock to expire or use 'kvstore lock acquire deploy-prod --wait 120' to retry

# AWS throttling
Error: DynamoDB throttling - request rate exceeded

Solution: Retry with exponential backoff. Consider switching to provisioned capacity for predictable throughput.

Details:
  - Current table: claude-code-kvstore
  - Billing mode: On-demand
  - Retry after: 1 second
```

---

## Use Cases & Examples

### Use Case 1: Distributed Rate Limiting

**Problem:** Prevent API abuse across multiple agents.

```bash
# Initialize rate limit counter
kvstore set rate-limit/api-key-123 1000 --ttl 3600  # 1000 requests/hour

# On each API call (atomic decrement)
kvstore dec rate-limit/api-key-123 || echo "Rate limit exceeded"

# Check remaining quota
kvstore get rate-limit/api-key-123
# Output: {"key": "rate-limit/api-key-123", "value": 857}
```

### Use Case 2: Distributed Deployment Lock

**Problem:** Prevent concurrent deployments to production.

```bash
# Agent 1: Acquire lock before deploying
if kvstore lock acquire deploy-prod --ttl 600 --owner agent-1; then
  echo "Lock acquired, deploying..."
  deploy.sh
  kvstore lock release deploy-prod --owner agent-1
else
  echo "Deployment already in progress"
  exit 1
fi

# Agent 2: Tries to deploy (blocked)
kvstore lock acquire deploy-prod --ttl 600 --owner agent-2
# Exit code: 4 (lock unavailable)
```

### Use Case 3: Task Distribution via Queue

**Problem:** Distribute work across multiple agents.

```bash
# Producer: Add tasks to queue
for task in task1 task2 task3; do
  kvstore queue push work-queue "{\"task\": \"$task\", \"params\": {...}}"
done

# Consumer agents (parallel workers)
while true; do
  # Pop task with 5-minute visibility timeout
  task=$(kvstore queue pop work-queue --visibility-timeout 300)

  if [ $? -eq 0 ]; then
    # Process task
    process-task.py "$task"

    # Acknowledge completion (delete from queue)
    receipt=$(echo "$task" | jq -r '.receipt')
    kvstore queue ack work-queue "$receipt"
  else
    echo "Queue empty, waiting..."
    sleep 10
  fi
done
```

### Use Case 4: Leader Election for Singleton Tasks

**Problem:** Ensure only one agent runs periodic cleanup.

```bash
# Agent attempts to become leader
if kvstore leader elect cleanup-manager --ttl 30 --id agent-123; then
  echo "I am the leader!"

  while true; do
    # Perform singleton task
    cleanup-old-logs.sh

    # Extend leadership with heartbeat
    kvstore leader heartbeat cleanup-manager --ttl 30 --id agent-123

    sleep 20
  done
else
  echo "Another agent is leader, standing by..."
fi
```

### Use Case 5: Atomic Counter for Request IDs

**Problem:** Generate unique, sequential request IDs.

```bash
# Generate unique ID (atomic increment)
request_id=$(kvstore inc request-counter --create --format value)
echo "Processing request ID: $request_id"

# Use in distributed system
curl -H "X-Request-ID: $request_id" https://api.example.com/process
```

### Use Case 6: Deduplication with Sets

**Problem:** Track processed messages to prevent duplicates.

```bash
# Check if message already processed
message_id="msg-abc-123"

if kvstore sismember processed-messages "$message_id"; then
  echo "Message already processed, skipping"
  exit 0
fi

# Process message
process-message.sh "$message_id"

# Mark as processed
kvstore sadd processed-messages "$message_id"
```

### Use Case 7: Recent Activity Log (List)

**Problem:** Maintain a bounded log of recent events.

```bash
# Add event to front of log (newest first)
kvstore lpush activity-log "User login at $(date)"

# Retrieve last 100 events
kvstore lrange activity-log 0 99

# Trim old events (keep only last 1000)
kvstore ltrim activity-log 0 999
```

### Use Case 8: Multi-Step Transaction

**Problem:** Update multiple counters atomically.

```bash
# Create transaction file
cat > tx.json <<EOF
[
  {"op": "inc", "key": "total-requests", "by": 1},
  {"op": "inc", "key": "successful-requests", "by": 1},
  {"op": "set", "key": "last-request-time", "value": "$(date -u +%s)"}
]
EOF

# Execute atomically
kvstore transaction --file tx.json
```

---

## Cost Analysis

### DynamoDB Pricing (EU: eu-central-1)

**On-Demand Mode (Recommended for Claude Code):**

| Operation | Cost | Free Tier |
|-----------|------|-----------|
| Write (1 KB) | $1.40/million | None |
| Read (4 KB) | $0.28/million | None |
| Storage | $0.283/GB-month | 25 GB |

**Provisioned Mode (For Predictable Workloads):**

| Operation | Cost | Free Tier |
|-----------|------|-----------|
| Write Capacity Unit (WCU) | $0.00065/hour | 25 WCU |
| Read Capacity Unit (RCU) | $0.00013/hour | 25 RCU |
| Storage | $0.283/GB-month | 25 GB |

### Example Cost Calculations

**Scenario 1: Light Usage (Personal Projects)**

```
Operations:
  - 500k reads/month (key-value lookups)
  - 100k writes/month (set operations, counters)
  - 1 GB storage

Cost:
  - Reads: 500,000 × $0.28/million = $0.14
  - Writes: 100,000 × $1.40/million = $0.14
  - Storage: 1 GB × $0.283 = $0.28
Total: $0.56/month
```

**Scenario 2: Moderate Usage (Distributed Agents)**

```
Operations:
  - 5 million reads/month
  - 1 million writes/month
  - 10 GB storage

Cost:
  - Reads: 5M × $0.28/million = $1.40
  - Writes: 1M × $1.40/million = $1.40
  - Storage: 10 GB × $0.283 = $2.83
Total: $5.63/month
```

**Scenario 3: Heavy Usage (Production System)**

```
Operations:
  - 50 million reads/month
  - 10 million writes/month
  - 50 GB storage

Cost:
  - Reads: 50M × $0.28/million = $14.00
  - Writes: 10M × $1.40/million = $14.00
  - Storage: 50 GB × $0.283 = $14.15
Total: $42.15/month
```

### Cost Optimization Tips

1. **Use Batch Operations:**
   - `BatchGetItem` (up to 100 items) - 1 read per item
   - `BatchWriteItem` (up to 25 items) - 1 write per item

2. **Reduce Read Capacity:**
   - Use `ProjectionExpression` to retrieve only needed attributes
   - Use eventually consistent reads (50% cheaper, but not available in on-demand)

3. **Leverage TTL:**
   - Automatic deletion of expired items (free)
   - No need for cleanup Lambda

4. **Choose Right Billing Mode:**
   - On-demand: Unpredictable traffic, <1M requests/month
   - Provisioned: Predictable traffic, >1M requests/month (can save 60%)

5. **Monitor with CloudWatch:**
   - Track consumed capacity
   - Set alarms for unexpected spikes
   - Switch billing modes as needed

---

## Testing Strategy

### Unit Tests (pytest)

**Test Core Operations in Isolation:**

```python
# tests/kvstore/test_counter_operations.py
import pytest
from aws_primitives_tool.kvstore.core.counter_operations import increment_counter
from aws_primitives_tool.kvstore.exceptions import KeyNotFoundError
from unittest.mock import MagicMock

def test_increment_counter_creates_if_missing():
    """Test counter creation on first increment."""
    client = MagicMock()
    client.update_item.return_value = {
        'Attributes': {'value': 1, 'updated_at': 1731696000}
    }

    counter = increment_counter(client, 'test-counter', by=1, create=True)

    assert counter.value == 1
    assert counter.key == 'test-counter'
    client.update_item.assert_called_once()

def test_increment_counter_fails_if_not_exists():
    """Test error when counter missing and create=False."""
    client = MagicMock()
    client.update_item.side_effect = ConditionFailedError("Key not found")

    with pytest.raises(KeyNotFoundError):
        increment_counter(client, 'missing-counter', by=1, create=False)
```

### Integration Tests (pytest + localstack)

**Test Against Local DynamoDB:**

```python
# tests/kvstore/test_integration.py
import pytest
import boto3
from moto import mock_aws

@mock_aws
def test_lock_acquire_and_release():
    """Test distributed lock lifecycle."""
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='test-kvstore',
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )

    # Test lock operations
    from aws_primitives_tool.kvstore.core.client import DynamoDBClient
    from aws_primitives_tool.kvstore.core.lock_operations import acquire_lock, release_lock

    client = DynamoDBClient('test-kvstore')

    # Acquire lock
    lock = acquire_lock(client, 'deploy', owner='agent-1', ttl=300)
    assert lock.name == 'deploy'
    assert lock.owner == 'agent-1'

    # Release lock
    release_lock(client, 'deploy', owner='agent-1')
```

### CLI Tests (Click CliRunner)

**Test CLI Commands:**

```python
# tests/kvstore/test_cli.py
from click.testing import CliRunner
from aws_primitives_tool.cli import cli

def test_inc_command_success(mock_dynamodb_table):
    """Test inc command with mocked DynamoDB."""
    runner = CliRunner()
    result = runner.invoke(cli, ['inc', 'test-counter', '--table', 'test-kvstore'])

    assert result.exit_code == 0
    assert 'value' in result.output

def test_inc_command_missing_counter(mock_dynamodb_table):
    """Test inc command with missing counter."""
    runner = CliRunner()
    result = runner.invoke(cli, ['inc', 'missing-counter', '--table', 'test-kvstore'])

    assert result.exit_code == 1
    assert 'does not exist' in result.output
    assert 'Solution' in result.output
```

### End-to-End Tests

**Test Real-World Scenarios:**

```bash
# tests/e2e/test_lock_workflow.sh
#!/usr/bin/env bash
set -e

# Setup
export KVSTORE_TABLE=e2e-test-kvstore
aws dynamodb create-table --cli-input-json file://table-schema.json

# Test: Two agents competing for lock
(
  kvstore lock acquire deploy --ttl 5 --owner agent-1
  echo "Agent 1 acquired lock"
  sleep 2
  kvstore lock release deploy --owner agent-1
  echo "Agent 1 released lock"
) &

sleep 1

(
  if kvstore lock acquire deploy --ttl 5 --owner agent-2 --wait 10; then
    echo "Agent 2 acquired lock after waiting"
    kvstore lock release deploy --owner agent-2
  else
    echo "Agent 2 timed out"
    exit 1
  fi
) &

wait

# Cleanup
aws dynamodb delete-table --table-name e2e-test-kvstore
```

### Performance Tests

**Measure Operation Latency:**

```python
# tests/performance/test_latency.py
import time
import statistics
from aws_primitives_tool.kvstore.core.client import DynamoDBClient
from aws_primitives_tool.kvstore.core.kv_operations import set_value, get_value

def test_set_get_latency():
    """Measure average latency for set/get operations."""
    client = DynamoDBClient('perf-test-kvstore')

    # Warmup
    for i in range(10):
        set_value(client, f'warmup-{i}', 'value')

    # Measure set latency
    set_times = []
    for i in range(100):
        start = time.time()
        set_value(client, f'key-{i}', f'value-{i}')
        set_times.append(time.time() - start)

    # Measure get latency
    get_times = []
    for i in range(100):
        start = time.time()
        get_value(client, f'key-{i}')
        get_times.append(time.time() - start)

    # Report results
    print(f"SET - Avg: {statistics.mean(set_times)*1000:.2f}ms, "
          f"P50: {statistics.median(set_times)*1000:.2f}ms, "
          f"P99: {statistics.quantiles(set_times, n=100)[98]*1000:.2f}ms")

    print(f"GET - Avg: {statistics.mean(get_times)*1000:.2f}ms, "
          f"P50: {statistics.median(get_times)*1000:.2f}ms, "
          f"P99: {statistics.quantiles(get_times, n=100)[98]*1000:.2f}ms")
```

---

## Next Steps

### Phase 1: Foundation (Week 1)
- [ ] Implement DynamoDB client wrapper
- [ ] Implement key-value operations (set, get, delete, exists, list)
- [ ] Implement counter operations (inc, dec, get-counter)
- [ ] Add unit tests for core operations
- [ ] Create CLI commands for kv and counter

### Phase 2: Coordination (Week 2)
- [ ] Implement lock operations (acquire, release, check, extend)
- [ ] Implement queue operations (push, pop, peek, size, ack)
- [ ] Add integration tests with moto/localstack
- [ ] Create CLI commands for lock and queue

### Phase 3: Advanced (Week 3)
- [ ] Implement leader election operations
- [ ] Implement set operations (sadd, srem, smembers, etc.)
- [ ] Implement list operations (lpush, rpush, lpop, etc.)
- [ ] Add end-to-end tests
- [ ] Performance benchmarks

### Phase 4: Transactions & Polish (Week 4)
- [ ] Implement transaction operations
- [ ] Add comprehensive error handling
- [ ] Write documentation (README, CLAUDE.md)
- [ ] Create example use cases
- [ ] Release v0.1.0

---

## References

### DynamoDB Documentation
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/latest/developerguide/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [DynamoDB Atomic Counters](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.AtomicCounters)
- [DynamoDB Conditional Writes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ConditionalUpdate)
- [DynamoDB Transactions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html)

### AWS Pricing
- [DynamoDB Pricing (EU Regions)](https://aws.amazon.com/dynamodb/pricing/)
- [AWS Free Tier](https://aws.amazon.com/free/)

### Related Projects
- [Redis Commands Reference](https://redis.io/commands/) - Inspiration for set/list operations
- [etcd Documentation](https://etcd.io/docs/) - Distributed coordination patterns
- [Consul KV Store](https://www.consul.io/docs/dynamic-app-config/kv) - Lock and leader election patterns

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Status:** Ready for Implementation
**Next Review:** After Phase 1 Completion
