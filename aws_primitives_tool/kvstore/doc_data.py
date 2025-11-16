"""
Documentation data for all kvstore primitives.

Structured data for AI agent-optimized documentation generation.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Any

# KV Primitive: set
SET_DOC = {
    "name": "set - Store Key-Value Pair",
    "synopsis": "aws-primitives-tool kvstore set KEY VALUE [--ttl SECONDS] [--table NAME]",
    "description": (
        "Atomically stores a key-value pair with PUT semantics (upsert). "
        "Values are stored as UTF-8 strings (max 400KB). "
        "Supports automatic expiration via TTL."
    ),
    "properties": {
        "Operation": "Upsert (INSERT or UPDATE)",
        "Complexity": "O(1) time, O(1) space",
        "Atomicity": "Single-item write is atomic",
        "Consistency": "Strong consistency (not eventually consistent)",
    },
    "guarantees": [
        "Atomicity: Write succeeds completely or fails completely",
        "Idempotency: Multiple identical sets produce same result",
        "Durability: Written to 3 AZs before acknowledgment",
        "Consistency: Strongly consistent reads immediately after write",
        "Isolation: Last-write-wins (no locking required)",
    ],
    "when_to_apply": [
        "Configuration Management: Store app config, feature flags",
        "Session Storage: User sessions with TTL expiration",
        "Caching: Cache expensive computation results",
        "User Preferences: Per-user settings and metadata",
        "Application State: Persist simple state across restarts",
    ],
    "examples": [
        {
            "title": "Simple Key-Value Storage",
            "code": '''# Store user profile
aws-primitives-tool kvstore set "user:alice:email" "alice@example.com"
aws-primitives-tool kvstore set "user:alice:role" "admin"''',
        },
        {
            "title": "Session with TTL",
            "code": '''# Create 1-hour session
SESSION_ID=$(uuidgen)
aws-primitives-tool kvstore set \\
  "session:$SESSION_ID" \\
  "user_id=123" \\
  --ttl 3600''',
        },
        {
            "title": "Feature Flags",
            "code": '''# Enable/disable features dynamically
aws-primitives-tool kvstore set "feature:new_ui" "enabled"
aws-primitives-tool kvstore set "feature:beta_api" "disabled"

# Application reads flag
FLAG=$(aws-primitives-tool kvstore get "feature:new_ui")''',
        },
    ],
    "composability": [
        {
            "title": "Set + Get (Read-After-Write Verification)",
            "code": '''aws-primitives-tool kvstore set "key1" "value1"
aws-primitives-tool kvstore get "key1"  # Verify write succeeded''',
        },
        {
            "title": "Set + Counter (Track Update Count)",
            "code": '''aws-primitives-tool kvstore set "config:url" "https://new.api.com"
aws-primitives-tool kvstore inc "config:url:version"  # Track changes''',
        },
        {
            "title": "Set + Transaction (Atomic Multi-Key Update)",
            "code": '''# Atomically update multiple keys
cat > update.json <<EOF
{
  "operations": [
    {"action": "Put", "type": "kv", "key": "user:status", "value": "active"},
    {"action": "Put", "type": "kv", "key": "user:updated", "value": "2025-01-15"}
  ]
}
EOF
aws-primitives-tool kvstore transaction --file update.json''',
        },
    ],
    "failure_modes": [
        "ItemTooLargeException: Value exceeds 400KB",
        "ProvisionedThroughputExceededException: Rate limit exceeded",
        "ValidationException: Invalid key format or value type",
    ],
    "performance": {
        "Latency": "Single-digit ms (p50), ~20ms (p99)",
        "Throughput": "Unlimited (on-demand mode)",
        "Cost": "$1.25 per million writes",
    },
    "see_also": ["get(1)", "delete(1)", "exists(1)", "list(1)", "transaction(1)"],
}

# KV Primitive: get
GET_DOC = {
    "name": "get - Retrieve Key-Value Pair",
    "synopsis": "aws-primitives-tool kvstore get KEY [--default VALUE] [--table NAME]",
    "description": (
        "Retrieves value for a key using strongly consistent reads. "
        "Returns error if key doesn't exist unless --default is provided."
    ),
    "properties": {
        "Operation": "Point lookup (hash table semantics)",
        "Complexity": "O(1) time, O(1) space",
        "Consistency": "Strong consistency (reads latest committed value)",
        "Atomicity": "Read is atomic snapshot",
    },
    "guarantees": [
        "Strong Consistency: Always reads latest committed value",
        "Atomicity: Read observes complete write or nothing",
        "Isolation: Read does not block writes",
        "Idempotency: Multiple reads return same value (absent concurrent writes)",
    ],
    "when_to_apply": [
        "Configuration Retrieval: Load application settings on startup",
        "Session Validation: Check if session exists and is valid",
        "Cache Lookup: Retrieve cached computation results",
        "State Query: Read current application state",
        "User Data Access: Fetch user attributes and preferences",
    ],
    "examples": [
        {
            "title": "Configuration Loading with Defaults",
            "code": '''# Load config with fallback defaults
API_URL=$(aws-primitives-tool kvstore get "config:api_url" --default "https://api.default.com")
TIMEOUT=$(aws-primitives-tool kvstore get "config:timeout" --default "30")
RETRIES=$(aws-primitives-tool kvstore get "config:retries" --default "3")''',
        },
        {
            "title": "Session Validation",
            "code": '''# Check session before processing request
if aws-primitives-tool kvstore exists "session:$SESSION_ID"; then
  USER_DATA=$(aws-primitives-tool kvstore get "session:$SESSION_ID")
  echo "Valid session for: $USER_DATA"
else
  echo "Session expired"
  exit 401
fi''',
        },
        {
            "title": "Feature Flag Conditional Execution",
            "code": '''# Execute different code paths based on feature flag
FEATURE=$(aws-primitives-tool kvstore get "feature:new_ui" --default "disabled")
if [ "$FEATURE" = "enabled" ]; then
  ./run_new_ui.sh
else
  ./run_old_ui.sh
fi''',
        },
    ],
    "composability": [
        {
            "title": "Get + Conditional Set (Check-Then-Act Pattern)",
            "code": '''# Cache-aside pattern
if aws-primitives-tool kvstore exists "cache:result"; then
  RESULT=$(aws-primitives-tool kvstore get "cache:result")
else
  RESULT=$(expensive_computation)
  aws-primitives-tool kvstore set "cache:result" "$RESULT" --ttl 3600
fi''',
            "note": "Note: Not atomic across get/set boundary",
        },
        {
            "title": "Get + Lock (Protected Read)",
            "code": '''# Read with exclusive access
aws-primitives-tool kvstore lock-acquire "resource:123" --ttl 10
VALUE=$(aws-primitives-tool kvstore get "resource:123")
# Process value safely...
aws-primitives-tool kvstore lock-release "resource:123"''',
        },
    ],
    "failure_modes": [
        "KeyNotFoundException: Key does not exist (exit code 1)",
        "ProvisionedThroughputExceededException: Rate limit exceeded",
        "RequestTimeoutException: Network or DynamoDB timeout",
    ],
    "performance": {
        "Latency": "Single-digit ms (p50), ~10ms (p99)",
        "Throughput": "Unlimited (on-demand mode)",
        "Cost": "$0.25 per million reads (1/5th the cost of writes)",
    },
    "see_also": ["set(1)", "exists(1)", "delete(1)", "list(1)"],
}

# Counter Primitive: inc
INC_DOC = {
    "name": "inc - Atomic Counter Increment",
    "synopsis": "aws-primitives-tool kvstore inc KEY [--by N] [--create] [--table NAME]",
    "description": (
        "Atomically increments counter using DynamoDB's native ADD operation. "
        "Provides lock-free atomic increments safe for concurrent access "
        "from multiple processes/threads."
    ),
    "properties": {
        "Operation": "Atomic Read-Modify-Write (RMW) at storage layer",
        "Complexity": "O(1) time, O(1) space",
        "Atomicity": "Hardware-level atomic ADD (not application-level)",
        "Consistency Model": "Linearizable (strongest consistency guarantee)",
        "Concurrency": "Lock-free, wait-free (no process blocking)",
    },
    "guarantees": [
        "Atomicity: Increment is indivisible (all-or-nothing)",
        "Linearizability: Sequential consistency + real-time ordering",
        "Durability: Persisted to 3 AZs before acknowledgment",
        "No Lost Updates: All concurrent increments succeed",
        "Isolation: Serializable (appears sequential)",
    ],
    "when_to_apply": [
        "Metrics Collection: Count API requests, errors, events",
        "Resource Usage Tracking: Bytes transferred, operations performed",
        "Distributed Counting: Multiple processes incrementing same counter",
        "Rate Limiting: Count requests per time window",
        "Versioning: Increment version numbers atomically",
        "Sequence Generation: Generate monotonically increasing IDs",
    ],
    "examples": [
        {
            "title": "API Request Metrics",
            "code": '''# Count requests per endpoint (non-blocking)
handle_request() {
  aws-primitives-tool kvstore inc "metrics:api:$ENDPOINT:requests" &
  # Process request immediately (don't wait for counter)
  process_request
}''',
        },
        {
            "title": "Distributed Rate Limiter",
            "code": '''# Rate limit: 100 requests/minute per user
WINDOW="$(date +%Y-%m-%d-%H-%M)"
COUNT=$(aws-primitives-tool kvstore inc "ratelimit:$USER_ID:$WINDOW" --create | jq '.value')
if [ "$COUNT" -gt 100 ]; then
  echo "Rate limit exceeded"
  exit 429
fi''',
        },
        {
            "title": "Distributed ID Generation",
            "code": '''# Generate unique sequential IDs across processes
generate_order_id() {
  ID=$(aws-primitives-tool kvstore inc "sequence:order_id" --create | jq '.value')
  echo "ORDER-$(printf '%010d' $ID)"
}

# Usage: ORDER_ID=$(generate_order_id)
# Result: ORDER-0000000042''',
        },
        {
            "title": "Multi-Metric Collection",
            "code": '''# Collect multiple metrics concurrently
aws-primitives-tool kvstore inc "metrics:requests" &
aws-primitives-tool kvstore inc "metrics:bytes_in" --by $BODY_SIZE &
aws-primitives-tool kvstore inc "metrics:cpu_ms" --by $CPU_TIME &
wait  # All increments succeed atomically''',
        },
    ],
    "composability": [
        {
            "title": "Inc + Threshold Alert (Conditional Logic)",
            "code": '''# Alert when counter exceeds threshold
COUNT=$(aws-primitives-tool kvstore inc "errors:critical" | jq '.value')
if [ "$COUNT" -gt 100 ]; then
  send_alert "Critical errors exceeded 100: current=$COUNT"
fi''',
        },
        {
            "title": "Inc + Transaction (Atomic Multi-Counter Update)",
            "code": '''# Atomically update multiple counters
cat > metrics.json <<EOF
{
  "operations": [
    {"action": "Update", "type": "counter", "key": "requests", "operation": "inc", "value": 1},
    {"action": "Update", "type": "counter", "key": "bytes", "operation": "inc", "value": 1024}
  ]
}
EOF
aws-primitives-tool kvstore transaction --file metrics.json''',
            "note": "Transaction provides atomicity across multiple counters",
        },
        {
            "title": "Inc + Get-Counter (Read After Increment)",
            "code": '''# Increment and check total
aws-primitives-tool kvstore inc "daily:logins"
TOTAL=$(aws-primitives-tool kvstore get-counter "daily:logins" | jq '.value')
echo "Total logins today: $TOTAL"''',
        },
    ],
    "failure_modes": [
        "CounterNotFoundException: Counter missing and --create not specified",
        "NumberFormatException: Counter value is not numeric",
        "ProvisionedThroughputExceededException: Rate limit exceeded",
    ],
    "performance": {
        "Latency": "Single-digit ms (p50), ~15ms (p99)",
        "Throughput": "Unlimited concurrent increments",
        "Scalability": "Horizontal scaling across DynamoDB partitions",
        "Cost": "$1.25 per million increments",
    },
    "see_also": ["dec(1)", "get-counter(1)", "set(1)", "transaction(1)"],
}

# Add stub documentation for remaining primitives
# (Full implementation would include all primitives)

PRIMITIVES_DOCS = {
    "set": SET_DOC,
    "get": GET_DOC,
    "inc": INC_DOC,
    # Add all other primitives here...
}


def get_doc_data(command: str) -> dict[str, Any] | None:
    """
    Retrieve documentation data for a command.

    Args:
        command: Command name (e.g., "set", "inc", "lock-acquire")

    Returns:
        Documentation data dictionary or None if not found
    """
    return PRIMITIVES_DOCS.get(command)
