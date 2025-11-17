# --doc Flag Implementation Guide

## Overview

The --doc flag provides AI agent-optimized documentation for all kvstore primitives. This guide explains how to add the flag to all remaining commands.

## Architecture

### Files Created

1. **aws_primitives_tool/kvstore/doc_generator.py** - Generates markdown documentation from structured data
2. **aws_primitives_tool/kvstore/doc_data.py** - Contains documentation data for all primitives

### Documentation Structure

Each primitive includes:
- **Computer Science Properties**: Complexity, consistency model, atomicity
- **Guarantees**: ACID properties, idempotency, durability
- **When to Apply**: Use cases and scenarios
- **Practical Examples**: Real-world code examples
- **Composability**: How to combine primitives (key differentiator!)
- **Failure Modes**: Possible errors and exit codes
- **Performance Characteristics**: Latency, throughput, cost

## Reference Implementation

The `set` command in `kv_commands.py` serves as the reference implementation.

### Step 1: Add Imports

```python
from ..doc_data import get_doc_data
from ..doc_generator import display_doc, generate_doc
```

### Step 2: Add --doc Option

```python
@click.command("your-command")
@click.argument("arg1", required=False)  # Make arguments optional
@click.option(
    "--doc",
    is_flag=True,
    help="Show AI agent-optimized documentation (CS semantics, guarantees, composability)",  # noqa: E501
)
def your_command(ctx, arg1, ..., doc):
```

### Step 3: Add Documentation Handler

```python
def your_command(ctx, arg1, ..., doc):
    """Your help text."""

    # Handle --doc flag (add at beginning of function)
    if doc:
        doc_data = get_doc_data("your-command")
        if doc_data:
            doc_content = generate_doc(**doc_data)
            display_doc(doc_content)
        else:
            click.echo("Documentation not available for: your-command", err=True)
            ctx.exit(1)

    # Validate required arguments when not using --doc
    if arg1 is None:
        click.echo("Error: Missing required argument ARG1", err=True)
        ctx.exit(2)

    # Rest of command logic...
```

### Step 4: Add Documentation Data

In `doc_data.py`, add documentation for your command:

```python
YOUR_COMMAND_DOC = {
    "name": "your-command - Brief Description",
    "synopsis": "aws-primitives-tool kvstore your-command ARGS [OPTIONS]",
    "description": "Detailed description...",
    "properties": {
        "Operation": "CS operation type",
        "Complexity": "Time and space complexity",
        "Atomicity": "Atomicity guarantees",
        "Consistency": "Consistency model",
    },
    "guarantees": [
        "Atomicity: ...",
        "Durability: ...",
        "Consistency: ...",
    ],
    "when_to_apply": [
        "Use Case 1: Description",
        "Use Case 2: Description",
    ],
    "examples": [
        {
            "title": "Example Title",
            "code": '''# Example code
aws-primitives-tool kvstore your-command arg''',
        },
    ],
    "composability": [
        {
            "title": "Composition Pattern Name",
            "code": '''# How to compose with other primitives
aws-primitives-tool kvstore cmd1
aws-primitives-tool kvstore cmd2''',
            "note": "Optional explanatory note",
        },
    ],
    "failure_modes": [
        "ExceptionType: Description",
    ],
    "performance": {
        "Latency": "Typical latency",
        "Throughput": "Throughput characteristics",
        "Cost": "AWS pricing info",
    },
    "see_also": ["related-cmd1(1)", "related-cmd2(1)"],
}

# Add to PRIMITIVES_DOCS dictionary
PRIMITIVES_DOCS = {
    ...
    "your-command": YOUR_COMMAND_DOC,
}
```

## Commands Requiring --doc Flag

### Phase 1: Table Management (2 commands)
- [ ] create-table
- [ ] drop-table

### Phase 2: KV Operations (4 commands)
- [x] set ✅ (reference implementation)
- [ ] get
- [ ] delete
- [ ] exists
- [ ] list

### Phase 3: Counter Operations (3 commands)
- [ ] inc
- [ ] dec
- [ ] get-counter

### Phase 4: Lock Operations (4 commands)
- [ ] lock-acquire
- [ ] lock-release
- [ ] lock-check
- [ ] lock-extend

### Phase 5: Queue Operations (5 commands)
- [ ] queue-push
- [ ] queue-pop
- [ ] queue-peek
- [ ] queue-size
- [ ] queue-ack

### Phase 6: Leader Operations (4 commands)
- [ ] leader-elect
- [ ] leader-heartbeat
- [ ] leader-check
- [ ] leader-resign

### Phase 7: Set Operations (5 commands)
- [ ] sadd
- [ ] srem
- [ ] sismember
- [ ] smembers
- [ ] scard

### Phase 8: List Operations (5 commands)
- [ ] lpush
- [ ] rpush
- [ ] lpop
- [ ] rpop
- [ ] lrange

### Phase 9: Transaction Operations (1 command)
- [ ] transaction

**Total**: 32 commands, 1 completed (3%)

## Testing

```bash
# Test documentation display
aws-primitives-tool kvstore set --doc

# Verify it exits cleanly
echo $?  # Should be 0

# Test with other commands after implementation
aws-primitives-tool kvstore inc --doc
aws-primitives-tool kvstore lock-acquire --doc
```

## Key Design Decisions

### 1. AI Agent Optimization
- **Computer science terminology** (linearizability, serializability, atomicity)
- **Explicit guarantees** (ACID properties clearly stated)
- **Complexity analysis** (O(1), O(n) notation)
- **Composability examples** (how to combine primitives)

### 2. Composability Focus
Composability is the **unique value proposition**. Each primitive shows:
- How it combines with other primitives
- Real-world composition patterns
- Note that examples are not exhaustive (infinite combinations possible)

### 3. Practical Examples
- Progression from simple to complex
- Real bash code (copy-paste ready)
- Use cases from actual scenarios

### 4. Failure Modes
- Explicit exception types
- Exit codes documented
- Actionable error information

## Implementation Priority

Recommend implementing in this order:

1. **High-traffic primitives**: set, get, inc, dec (most used)
2. **Synchronization primitives**: lock-acquire, lock-release (critical for correctness)
3. **Collection primitives**: queue-push, queue-pop, lpush, rpop
4. **Advanced primitives**: transaction, leader-elect
5. **Utility commands**: exists, list, check commands

## Notes

- All code passes `make check` (ruff, mypy, pytest)
- Documentation displays to stderr for AI agent parsing
- Exit code 0 on success, 1 on doc not found
- Arguments are optional when --doc is used
- Line length limited to 100 characters (use `# noqa: E501` if needed)
