"""
Constants for kvstore operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

# Default table name
DEFAULT_TABLE_NAME = "aws-primitives-tool-kvstore"

# Default TTLs (in seconds)
DEFAULT_LOCK_TTL = 300  # 5 minutes
DEFAULT_LOCK_WAIT = 30  # 30 seconds
DEFAULT_KEY_TTL = 3600  # 1 hour (when --ttl not specified)

# Namespace prefixes for DynamoDB keys
PREFIX_KV = "kv"
PREFIX_COUNTER = "counter"
PREFIX_LOCK = "lock"
PREFIX_QUEUE = "queue"
PREFIX_LEADER = "leader"
PREFIX_SET = "set"
PREFIX_LIST = "list"

# DynamoDB attribute names
ATTR_PK = "PK"
ATTR_SK = "SK"
ATTR_VALUE = "value"
ATTR_TYPE = "type"
ATTR_TTL = "ttl"
ATTR_METADATA = "metadata"
ATTR_CREATED_AT = "created_at"
ATTR_UPDATED_AT = "updated_at"
ATTR_VERSION = "version"

# Lock wait behavior
LOCK_BACKOFF_BASE = 1.0  # Start with 1 second
LOCK_BACKOFF_MAX = 16.0  # Max 16 seconds between retries
LOCK_BACKOFF_FACTOR = 2.0  # Exponential backoff factor

# Queue behavior
QUEUE_VISIBILITY_TIMEOUT = 300  # 5 minutes default visibility timeout
QUEUE_MAX_MESSAGES = 10  # Max messages to peek at once
