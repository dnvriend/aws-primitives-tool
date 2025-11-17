# PubSub Primitives Design (SNS Topics)

**Document Version**: 2.0
**Last Updated**: 2025-11-15
**Status**: DESIGN SPECIFICATION

---

## Executive Summary

This document specifies the design for **pubsub primitives** built on Amazon SNS (Simple Notification Service). Topics provide **1-to-many communication** via fan-out, where a single message published to a topic is delivered to multiple subscriber queues.

**Critical Architecture Pattern**: SNS+SQS
- **SNS Topics** (this document): Fan-out messaging (1-to-many)
- **SQS Queues** (see queue-primitives-design.md): Individual subscriber consumption (1-to-1)

**Key Design Principles**:
- **FIFO by Default**: Guaranteed ordering with FIFO topics + FIFO queues
- **SNS+SQS Pattern**: Primary architecture for reliable message delivery
- **Fan-Out**: Single publish → multiple subscriber queues
- **Message Filtering**: Subscriber-side filtering with JSON policies
- **CLI Composable**: Simple, pipeable commands for AI agents

**Communication Model**:
```
Publisher → Topic (SNS) → Queue 1 (SQS) → Subscriber 1
                       → Queue 2 (SQS) → Subscriber 2
                       → Queue 3 (SQS) → Subscriber 3
```

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [SNS+SQS Pattern](#snssqs-pattern)
3. [Primitive Operations](#primitive-operations)
4. [CLI Specification](#cli-specification)
5. [Implementation Architecture](#implementation-architecture)
6. [Error Handling](#error-handling)
7. [Use Cases](#use-cases)
8. [Cost Model](#cost-model)
9. [Testing Strategy](#testing-strategy)

---

## 1. Architecture Overview

### 1.1 Communication Patterns

| Pattern | Technology | Use Case |
|---------|-----------|----------|
| **1-to-Many (Fan-out)** | SNS Topics | Broadcast messages to multiple subscribers |
| **1-to-1 (Buffering)** | SQS Queues | Individual consumer processing with retry |

**Design Principle**:
- **Topics (SNS)**: For broadcasting events to multiple subscribers
- **Queues (SQS)**: For individual subscriber consumption with buffering

### 1.2 SNS+SQS Pattern (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                    SNS FIFO Topic                           │
│                   events.fifo                               │
│                   (1-to-Many)                               │
└───────────────────┬─────────────────┬───────────────────────┘
                    │                 │
                    │ Fan-out         │
                    ▼                 ▼
        ┌───────────────────┐ ┌───────────────────┐
        │  SQS FIFO Queue   │ │  SQS FIFO Queue   │
        │  agent-1.fifo     │ │  agent-2.fifo     │
        │  (1-to-1)         │ │  (1-to-1)         │
        └─────────┬─────────┘ └─────────┬─────────┘
                  │                     │
                  │                     │
                  ▼                     ▼
        ┌───────────────────┐ ┌───────────────────┐
        │   Agent 1         │ │   Agent 2         │
        │   (Consumer)      │ │   (Consumer)      │
        └───────────────────┘ └───────────────────┘
```

**Why SNS+SQS?**

| Benefit | Description |
|---------|-------------|
| **Buffering** | SQS queues buffer messages if consumer is down or slow |
| **Retry** | Automatic retry with exponential backoff |
| **Throttling Protection** | Queue absorbs bursts, consumer polls at own pace |
| **Visibility Timeout** | Prevent duplicate processing during execution |
| **Dead Letter Queue** | Failed messages automatically moved to DLQ |
| **Ordering** | FIFO queues guarantee message order |

**AWS Documentation Quote**:
> "By subscribing an Amazon SQS queue to an Amazon SNS topic, messages can be delivered to applications requiring immediate notification and also persisted in an Amazon SQS queue for later processing."

> "Amazon SNS FIFO topics cannot deliver messages to customer-managed endpoints like Lambda functions. To fan out messages from SNS FIFO topics to Lambda, SQS FIFO queues must first be subscribed to the topic."

### 1.3 Topic Types

| Feature | FIFO Topic (Default) | Standard Topic |
|---------|---------------------|----------------|
| **Ordering** | Guaranteed FIFO per group | Best-effort ordering |
| **Delivery** | Exactly-once | At-least-once (duplicates possible) |
| **Throughput** | 300 TPS (3,000 with batching) | Unlimited |
| **Subscriptions** | 100 per topic | 12.5 million per topic |
| **Direct Lambda** | ❌ NOT SUPPORTED | ✅ Supported (not recommended) |
| **Must Use SQS** | ✅ REQUIRED | Optional (but recommended) |
| **Suffix** | `.fifo` required | No suffix |
| **Use Case** | Ordered workflows, transactions | High-throughput, order-insensitive |

**Design Decision**: FIFO topics are the **default** for all pubsub operations. Standard topics are opt-in with `--standard` flag.

**CRITICAL**: FIFO topics **CANNOT** deliver directly to Lambda. Must use SQS FIFO queue.

---

## 2. SNS+SQS Pattern

### 2.1 Pattern Overview

**Correct Pattern** (Recommended):
```
Publisher → SNS Topic → SQS Queue 1 → Lambda 1 / Consumer 1
                    ↓
                    → SQS Queue 2 → Lambda 2 / Consumer 2
                    ↓
                    → SQS Queue 3 → Lambda 3 / Consumer 3
```

**Incorrect Pattern** (NOT Recommended):
```
Publisher → SNS Topic → Lambda 1 (direct, no buffering, no retry)
                    ↓
                    → Lambda 2 (direct, no buffering, no retry)
                    ↓
                    → Lambda 3 (direct, no buffering, no retry)
```

### 2.2 Why SNS → Lambda Direct is Problematic

| Issue | Impact | Solution with SQS |
|-------|--------|-------------------|
| **No Buffering** | Lambda throttled → messages lost | SQS buffers messages |
| **No Retry** | Lambda fails → message lost | SQS auto-retries with backoff |
| **No Throttling Protection** | Bursts overwhelm Lambda | SQS absorbs bursts |
| **No Visibility Timeout** | Duplicate processing | SQS prevents duplicates |
| **No DLQ** | Failed messages disappear | SQS moves to DLQ after max retries |
| **FIFO Unsupported** | ❌ Cannot use FIFO topics | ✅ SQS FIFO required for FIFO topics |

### 2.3 Workflow: Creating SNS+SQS Fan-Out

**Step 1: Create FIFO Topic**
```bash
pubsub create-topic events.fifo
```

**Step 2: Create SQS Queues for Each Subscriber**
```bash
queue create agent-1.fifo
queue create agent-2.fifo
queue create agent-3.fifo
```

**Step 3: Subscribe Queues to Topic**
```bash
queue subscribe-to-topic agent-1.fifo events.fifo --raw-message-delivery
queue subscribe-to-topic agent-2.fifo events.fifo --raw-message-delivery
queue subscribe-to-topic agent-3.fifo events.fifo --raw-message-delivery
```

**Step 4: Publish to Topic (Fan-Out)**
```bash
pubsub publish events.fifo '{"type": "task_complete", "agent": "agent-1"}' \
  --message-group-id events \
  --deduplication-id task-001
```

**Step 5: Each Subscriber Receives from Their Own Queue**
```bash
# Agent 1
queue receive agent-1.fifo --delete-after-receive

# Agent 2
queue receive agent-2.fifo --delete-after-receive

# Agent 3
queue receive agent-3.fifo --delete-after-receive
```

### 2.4 Raw Message Delivery

**Without Raw Message Delivery** (SNS Envelope):
```json
{
  "Type": "Notification",
  "MessageId": "abc123",
  "TopicArn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
  "Message": "{\"type\": \"task_complete\", \"agent\": \"agent-1\"}",
  "Timestamp": "2025-11-15T10:30:00.000Z",
  "MessageAttributes": {...}
}
```

**With Raw Message Delivery** (Cleaner):
```json
{"type": "task_complete", "agent": "agent-1"}
```

**Recommendation**: Always use `--raw-message-delivery` for SQS subscriptions to strip SNS metadata.

### 2.5 Message Filtering

**Filter at Subscription Level**:
```bash
# Agent 1: Only ERROR messages
queue subscribe-to-topic agent-1.fifo events.fifo \
  --filter-policy '{"level": ["ERROR"]}' \
  --raw-message-delivery

# Agent 2: Only high priority (>= 8)
queue subscribe-to-topic agent-2.fifo events.fifo \
  --filter-policy '{"priority": [{"numeric": [">=", 8]}]}' \
  --raw-message-delivery

# Agent 3: All messages
queue subscribe-to-topic agent-3.fifo events.fifo \
  --raw-message-delivery
```

**Publish with Attributes for Filtering**:
```bash
pubsub publish events.fifo '{"message": "Error detected"}' \
  --message-group-id events \
  --deduplication-id err-001 \
  --attribute level=ERROR \
  --attribute priority=9:Number
```

**Result**:
- Agent 1: ✅ Receives (level=ERROR matches filter)
- Agent 2: ✅ Receives (priority=9 >= 8)
- Agent 3: ✅ Receives (no filter, receives all)

---

## 3. Primitive Operations

### 3.1 Create Topic

**Purpose**: Create an SNS topic (FIFO by default).

**CLI Command**:
```bash
pubsub create-topic <topic-name> [OPTIONS]
```

**Options**:
- `--standard` - Create Standard topic (default: FIFO)
- `--display-name <name>` - Human-readable name (for email/SMS)
- `--content-deduplication` - Enable content-based deduplication (FIFO only, default: true)
- `--tags <key=value>` - Resource tags (can be specified multiple times)

**Output** (JSON):
```json
{
  "topic_name": "events.fifo",
  "topic_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
  "topic_type": "FIFO",
  "created": true
}
```

**Exit Codes**:
- `0` - Topic created successfully
- `1` - Topic already exists
- `2` - Invalid parameters (missing .fifo suffix for FIFO)
- `3` - AWS service error

**Agent-Friendly Help**:
```
Create an SNS topic for fan-out messaging (FIFO by default).

FIFO topics provide guaranteed ordering and exactly-once delivery.
Standard topics provide unlimited throughput with best-effort ordering.

IMPORTANT: FIFO topics CANNOT deliver directly to Lambda. You must
subscribe SQS FIFO queues to FIFO topics and configure Lambda to poll
from the SQS queue.

Examples:

\b
    # Create FIFO topic (default)
    pubsub create-topic events.fifo

\b
    # Create Standard topic (high throughput)
    pubsub create-topic high-volume-events --standard

\b
    # Create topic with display name (for email/SMS)
    pubsub create-topic alerts.fifo --display-name "Production Alerts"

\b
    # Create topic with tags
    pubsub create-topic events.fifo \\
        --tags project=claude-code \\
        --tags env=production

\b
Output Format:
    Returns JSON with topic metadata:
    {
      "topic_name": "events.fifo",
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
      "topic_type": "FIFO",
      "created": true
    }
```

---

### 3.2 Publish Message

**Purpose**: Publish a message to a topic (fan-out to all subscriber queues).

**CLI Command**:
```bash
pubsub publish <topic-name> <message> [OPTIONS]
```

**Options**:
- `--message-group-id <group-id>` - Message group ID (required for FIFO)
- `--deduplication-id <dedup-id>` - Deduplication ID (FIFO only, optional if content deduplication enabled)
- `--subject <subject>` - Message subject (for email notifications)
- `--attribute <key=value[:type]>` - Message attributes for filtering (can be specified multiple times)
- `--stdin` / `-s` - Read message from stdin

**Output** (JSON):
```json
{
  "message_id": "5fea7756-0ea4-451a-a703-a558b933e274",
  "sequence_number": "18849746239162747",
  "topic_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
  "published": true
}
```

**Exit Codes**:
- `0` - Message published successfully
- `1` - Topic not found
- `2` - Invalid parameters (missing message group ID)
- `3` - AWS service error

**Agent-Friendly Help**:
```
Publish a message to an SNS topic.

The message is fanned out to all subscriber queues. Each subscriber
receives the message in their own SQS queue and consumes it independently.

For FIFO topics, messages with the same MessageGroupId are processed
in order across all subscribers. Messages in different groups can be
processed in parallel.

Examples:

\b
    # Publish to FIFO topic
    pubsub publish events.fifo '{"type": "task_complete", "agent": "agent-1"}' \\
        --message-group-id events \\
        --deduplication-id task-001

\b
    # Publish with attributes for filtering
    pubsub publish events.fifo '{"message": "Error detected"}' \\
        --message-group-id events \\
        --deduplication-id err-001 \\
        --attribute level=ERROR \\
        --attribute priority=9:Number

\b
    # Publish from stdin
    echo '{"event": "test"}' | pubsub publish events.fifo --stdin \\
        --message-group-id events \\
        --deduplication-id test-001

\b
    # Publish with subject (for email subscribers)
    pubsub publish alerts.fifo "Critical error detected" \\
        --message-group-id alerts \\
        --deduplication-id alert-001 \\
        --subject "Production Alert"

\b
Output Format:
    Returns JSON with message metadata:
    {
      "message_id": "5fea7756-0ea4-451a-a703-a558b933e274",
      "sequence_number": "18849746239162747",
      "published": true
    }
```

---

### 3.3 List Topics

**Purpose**: List all SNS topics.

**CLI Command**:
```bash
pubsub list-topics [OPTIONS]
```

**Options**:
- `--format <format>` - Output format: json, json-lines, names-only (default: json)

**Output** (JSON):
```json
{
  "topics": [
    {
      "topic_name": "events.fifo",
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
      "topic_type": "FIFO"
    },
    {
      "topic_name": "alerts.fifo",
      "topic_arn": "arn:aws:sns:us-east-1:123456789012:alerts.fifo",
      "topic_type": "FIFO"
    }
  ],
  "count": 2
}
```

**Agent-Friendly Help**:
```
List all SNS topics.

Examples:

\b
    # List all topics
    pubsub list-topics

\b
    # Output only topic names
    pubsub list-topics --format names-only
```

---

### 3.4 Delete Topic

**Purpose**: Delete an SNS topic and all its subscriptions.

**CLI Command**:
```bash
pubsub delete-topic <topic-name> [OPTIONS]
```

**Options**:
- `--force` / `-f` - Force delete (skip confirmation)

**Output** (JSON):
```json
{
  "topic_name": "events.fifo",
  "deleted": true
}
```

**Exit Codes**:
- `0` - Topic deleted
- `1` - Topic not found
- `2` - User cancelled
- `3` - AWS service error

**Agent-Friendly Help**:
```
Delete an SNS topic and all its subscriptions.

WARNING: This operation is irreversible. Topic and subscriptions cannot be recovered.

Examples:

\b
    # Delete topic (with confirmation)
    pubsub delete-topic events.fifo

\b
    # Force delete without confirmation
    pubsub delete-topic events.fifo --force
```

---

### 3.5 Get Topic Attributes

**Purpose**: Get topic metadata and statistics.

**CLI Command**:
```bash
pubsub get-topic-attrs <topic-name>
```

**Output** (JSON):
```json
{
  "topic_name": "events.fifo",
  "topic_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo",
  "topic_type": "FIFO",
  "owner": "123456789012",
  "subscriptions_confirmed": 3,
  "subscriptions_pending": 0,
  "display_name": "Production Events"
}
```

**Agent-Friendly Help**:
```
Get topic attributes and statistics.

Returns topic configuration and subscription counts.

Examples:

\b
    # Get topic attributes
    pubsub get-topic-attrs events.fifo

\b
    # Check subscription count
    pubsub get-topic-attrs events.fifo | jq -r '.subscriptions_confirmed'
```

---

### 3.6 List Subscriptions

**Purpose**: List all subscriptions to a topic.

**CLI Command**:
```bash
pubsub list-subscriptions <topic-name> [OPTIONS]
```

**Options**:
- `--format <format>` - Output format: json, json-lines, table (default: json)

**Output** (JSON):
```json
{
  "topic_name": "events.fifo",
  "subscriptions": [
    {
      "subscription_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo:abc-123",
      "protocol": "sqs",
      "endpoint": "arn:aws:sqs:us-east-1:123456789012:agent-1.fifo",
      "status": "confirmed",
      "raw_message_delivery": true
    },
    {
      "subscription_arn": "arn:aws:sns:us-east-1:123456789012:events.fifo:def-456",
      "protocol": "sqs",
      "endpoint": "arn:aws:sqs:us-east-1:123456789012:agent-2.fifo",
      "status": "confirmed",
      "raw_message_delivery": true
    }
  ],
  "count": 2
}
```

**Agent-Friendly Help**:
```
List all subscriptions to a topic.

Shows all SQS queues (and other endpoints) subscribed to the topic.

Examples:

\b
    # List subscriptions
    pubsub list-subscriptions events.fifo

\b
    # Count subscriptions
    pubsub list-subscriptions events.fifo | jq -r '.count'
```

---

### 3.7 Set Topic Policy

**Purpose**: Set topic access policy (for cross-account or service access).

**CLI Command**:
```bash
pubsub set-topic-policy <topic-name> <policy-file>
```

**Example Policy** (allow S3 to publish):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3.amazonaws.com"},
    "Action": "SNS:Publish",
    "Resource": "arn:aws:sns:us-east-1:123456789012:events.fifo",
    "Condition": {
      "ArnLike": {"aws:SourceArn": "arn:aws:s3:::my-bucket"}
    }
  }]
}
```

**Agent-Friendly Help**:
```
Set topic access policy.

Allows other AWS services or accounts to publish to the topic.

Examples:

\b
    # Allow S3 to publish
    pubsub set-topic-policy events.fifo s3-policy.json

\b
    # Allow cross-account publishing
    pubsub set-topic-policy events.fifo cross-account-policy.json
```

---

## 4. CLI Specification

### 4.1 Command Structure

```bash
pubsub <operation> [arguments] [options]
```

### 4.2 Commands Summary

**Topic Operations**:
```bash
pubsub create-topic <name>         # Create FIFO topic (default)
pubsub list-topics                 # List all topics
pubsub delete-topic <name>         # Delete topic
pubsub get-topic-attrs <name>      # Get topic details
```

**Publishing Operations**:
```bash
pubsub publish <topic> <message>   # Publish message (fan-out)
```

**Subscription Operations**:
```bash
pubsub list-subscriptions <topic>  # List subscriptions
pubsub set-topic-policy <topic> <policy-file>  # Set access policy
```

**Note**: Queue subscription is handled by `queue subscribe-to-topic` (see queue-primitives-design.md)

### 4.3 Global Options

All commands support:
- `--help` / `-h` - Show help
- `--version` - Show version
- `--verbose` / `-V` - Verbose output
- `--quiet` / `-q` - Suppress output
- `--region <region>` - AWS region (default: from AWS config)
- `--profile <profile>` - AWS profile (default: default)
- `--output <format>` - Output format: json, json-lines, yaml, table

### 4.4 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Resource not found |
| 2 | Invalid parameters |
| 3 | AWS service error |
| 4 | Permission denied |

---

## 5. Implementation Architecture

### 5.1 Project Structure

```
aws_primitives_tool/
├── pubsub/
│   ├── __init__.py
│   ├── cli.py                 # Click CLI commands
│   ├── core/
│   │   ├── __init__.py
│   │   ├── operations.py      # Core topic operations
│   │   ├── publish.py         # Publish logic
│   │   └── utils.py          # Helper functions
│   ├── exceptions.py          # Custom exceptions
│   └── models.py             # Pydantic models
```

### 5.2 Core Operations Module

```python
# pubsub/core/operations.py

"""
Core SNS topic operations.

This module provides topic operations for 1-to-many fan-out messaging.
Use in conjunction with queue operations (SQS) for reliable delivery.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from typing import Dict, Any, Optional
import boto3
import json

class TopicOperations:
    """SNS topic operations."""

    def __init__(self, region: str = 'us-east-1'):
        """Initialize SNS client."""
        self.sns = boto3.client('sns', region_name=region)

    def create_topic(
        self,
        topic_name: str,
        is_fifo: bool = True,
        display_name: Optional[str] = None,
        content_deduplication: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create SNS topic (FIFO by default)."""
        # Validate FIFO suffix
        if is_fifo and not topic_name.endswith('.fifo'):
            raise ValueError(
                f"FIFO topic name must end with .fifo suffix: {topic_name}"
            )

        # Build attributes
        attributes = {}
        if display_name:
            attributes['DisplayName'] = display_name
        if is_fifo:
            attributes['FifoTopic'] = 'true'
            if content_deduplication:
                attributes['ContentBasedDeduplication'] = 'true'

        # Create topic
        response = self.sns.create_topic(
            Name=topic_name,
            Attributes=attributes
        )

        return {
            'topic_name': topic_name,
            'topic_arn': response['TopicArn'],
            'topic_type': 'FIFO' if is_fifo else 'Standard',
            'created': True
        }

    def publish(
        self,
        topic_name: str,
        message: str,
        message_group_id: Optional[str] = None,
        deduplication_id: Optional[str] = None,
        subject: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Publish message to topic."""
        # Get topic ARN
        topic_arn = self._get_topic_arn(topic_name)

        # Validate FIFO requirements
        is_fifo = topic_name.endswith('.fifo')
        if is_fifo and not message_group_id:
            raise ValueError(
                "FIFO topic requires --message-group-id"
            )

        # Build publish parameters
        params = {
            'TopicArn': topic_arn,
            'Message': message
        }

        if subject:
            params['Subject'] = subject

        if is_fifo:
            params['MessageGroupId'] = message_group_id
            if deduplication_id:
                params['MessageDeduplicationId'] = deduplication_id

        if attributes:
            params['MessageAttributes'] = self._format_attributes(attributes)

        # Publish
        response = self.sns.publish(**params)

        result = {
            'message_id': response['MessageId'],
            'topic_arn': topic_arn,
            'published': True
        }

        if 'SequenceNumber' in response:
            result['sequence_number'] = response['SequenceNumber']

        return result
```

---

## 6. Error Handling

### 6.1 Custom Exceptions

```python
# pubsub/exceptions.py

"""
PubSub operation exceptions.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

class PubSubError(Exception):
    """Base exception for pubsub operations."""

    def __init__(self, message: str, solution: str = "", exit_code: int = 3):
        self.message = message
        self.solution = solution
        self.exit_code = exit_code
        super().__init__(self.message)

    def __str__(self):
        if self.solution:
            return f"{self.message}\n\nSolution: {self.solution}"
        return self.message

class TopicNotFoundError(PubSubError):
    """Topic does not exist."""

    def __init__(self, topic_name: str):
        super().__init__(
            f"Topic '{topic_name}' not found",
            f"Create the topic: pubsub create-topic {topic_name}",
            exit_code=1
        )

class TopicAlreadyExistsError(PubSubError):
    """Topic already exists."""

    def __init__(self, topic_name: str):
        super().__init__(
            f"Topic '{topic_name}' already exists",
            "Use a different topic name or delete the existing topic",
            exit_code=1
        )

class InvalidParameterError(PubSubError):
    """Invalid parameters provided."""

    def __init__(self, message: str, solution: str):
        super().__init__(message, solution, exit_code=2)

class MessageTooLargeError(PubSubError):
    """Message exceeds 256 KB limit."""

    def __init__(self, size_mb: float):
        super().__init__(
            f"Message size {size_mb:.2f} MB exceeds 256 KB limit",
            "Store large payloads in S3 and publish reference:\n"
            "  1. blob put large-payload.json s3://bucket/data.json\n"
            "  2. pubsub publish topic '{\"s3_key\": \"s3://bucket/data.json\"}'",
            exit_code=2
        )
```

---

## 7. Use Cases

### 7.1 Agent Coordination (Event Broadcasting)

**Scenario**: Multiple agents need to know when tasks complete.

```bash
# Create topic
pubsub create-topic events.fifo

# Create queues for each agent
queue create agent-1.fifo
queue create agent-2.fifo
queue create agent-3.fifo

# Subscribe queues to topic
queue subscribe-to-topic agent-1.fifo events.fifo --raw-message-delivery
queue subscribe-to-topic agent-2.fifo events.fifo --raw-message-delivery
queue subscribe-to-topic agent-3.fifo events.fifo --raw-message-delivery

# Agent 1 publishes task completion
pubsub publish events.fifo '{"type": "task_complete", "agent": "agent-1"}' \
  --message-group-id events \
  --deduplication-id task-001

# All agents receive the message in their own queues
queue receive agent-1.fifo --delete-after-receive
queue receive agent-2.fifo --delete-after-receive
queue receive agent-3.fifo --delete-after-receive
```

---

### 7.2 Selective Delivery (Message Filtering)

**Scenario**: Different agents want different types of events.

```bash
# Create topic
pubsub create-topic events.fifo

# Create queues
queue create errors.fifo
queue create high-priority.fifo
queue create all-events.fifo

# Subscribe with filters
# Queue 1: Only ERROR messages
queue subscribe-to-topic errors.fifo events.fifo \
  --filter-policy '{"level": ["ERROR"]}' \
  --raw-message-delivery

# Queue 2: Only high priority (>= 8)
queue subscribe-to-topic high-priority.fifo events.fifo \
  --filter-policy '{"priority": [{"numeric": [">=", 8]}]}' \
  --raw-message-delivery

# Queue 3: All messages
queue subscribe-to-topic all-events.fifo events.fifo \
  --raw-message-delivery

# Publish with attributes
pubsub publish events.fifo '{"message": "Error detected"}' \
  --message-group-id events \
  --deduplication-id err-001 \
  --attribute level=ERROR \
  --attribute priority=9:Number

# Result:
# - errors.fifo: Receives (level=ERROR)
# - high-priority.fifo: Receives (priority=9 >= 8)
# - all-events.fifo: Receives (no filter)
```

---

## 8. Cost Model

### 8.1 SNS Pricing (US East 1)

| Item | Price |
|------|-------|
| **Standard Topics** | |
| - Publishes (first 1M/month) | FREE |
| - Publishes (after 1M) | $0.50 per 1M |
| **FIFO Topics** | |
| - Publishes (first 1M/month) | FREE |
| - Publishes (after 1M) | $0.60 per 1M |
| **Deliveries** | |
| - To SQS | FREE |
| - To Lambda | FREE |
| - To HTTP/HTTPS | $0.60 per 1M |
| - To Email | $2.00 per 100K |
| - To SMS | $0.05-0.20 per message (varies by country) |

### 8.2 Cost Examples

**Scenario 1: Development (100K events/month)**

```
100,000 FIFO publishes (within free tier) = $0.00
100,000 deliveries to SQS = $0.00
Total: $0.00/month
```

**Scenario 2: Production (5M events/month, 3 subscribers)**

```
5,000,000 FIFO publishes:
- First 1M: $0.00 (free tier)
- Next 4M: 4 × $0.60 = $2.40

5M publishes × 3 subscribers = 15M SQS deliveries: $0.00

Total: $2.40/month
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/pubsub/test_operations.py

"""
Unit tests for pubsub operations.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

import pytest
from aws_primitives_tool.pubsub.core.operations import TopicOperations
from aws_primitives_tool.pubsub.exceptions import (
    TopicNotFoundError,
    InvalidParameterError
)

@pytest.fixture
def topic_ops():
    """Topic operations fixture."""
    return TopicOperations(region='us-east-1')

def test_create_fifo_topic(topic_ops):
    """Test FIFO topic creation."""
    result = topic_ops.create_topic('test-topic.fifo')
    assert result['topic_name'] == 'test-topic.fifo'
    assert result['topic_type'] == 'FIFO'
    assert result['created'] is True

def test_create_fifo_topic_without_suffix(topic_ops):
    """Test FIFO topic creation fails without .fifo suffix."""
    with pytest.raises(ValueError) as exc:
        topic_ops.create_topic('test-topic', is_fifo=True)
    assert '.fifo suffix' in str(exc.value)

def test_publish_to_fifo_without_group_id(topic_ops):
    """Test publishing to FIFO topic fails without message group ID."""
    with pytest.raises(ValueError) as exc:
        topic_ops.publish('test-topic.fifo', 'test message')
    assert 'message-group-id' in str(exc.value)
```

---

## Summary

This design provides comprehensive SNS topic primitives for **1-to-many communication** with:

### ✅ Core Features
- FIFO topics by default (guaranteed ordering)
- SNS+SQS pattern for reliable delivery
- Fan-out to multiple subscriber queues
- Message filtering at subscriber level
- Raw message delivery for cleaner payloads

### ✅ CLI Operations
- Create, list, delete topics
- Publish messages with fan-out
- List subscriptions
- Set topic access policies

### ✅ Cost-Effective
- Free tier: 1M publishes/month
- FIFO: $0.60 per 1M publishes (after free tier)
- SQS deliveries: FREE

### ✅ Agent-Friendly
- Self-documenting CLI with inline examples
- Composable commands (pipeable)
- JSON output for easy parsing
- Exception-based errors with solutions

### ✅ Production-Ready
- SNS+SQS pattern for buffering and retry
- FIFO topics for guaranteed ordering
- Message filtering for selective delivery
- Dead letter queues (via SQS)

---

**Next Steps**:
1. Create `pubsub-value-proposition.md`
2. Create `queue-value-proposition.md`

---

**Document Status**: ✅ COMPLETE (Revised for SNS+SQS pattern)

This design is ready for implementation.
