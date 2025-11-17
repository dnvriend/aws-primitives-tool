# Integration Tests

Comprehensive integration tests for aws-primitives-tool kvstore operations.

## Overview

These tests verify end-to-end functionality of all kvstore primitives against a real DynamoDB table.

## Test Structure

- `test_helpers.sh` - Shared test utilities and assertions
- `test_kv_operations.sh` - Key-value operations (set, get, delete, exists, list)
- `test_counter_operations.sh` - Counter operations (inc, dec, get-counter)
- `test_list_operations.sh` - List operations (lpush, rpush, lpop, rpop, lrange)
- `test_lock_operations.sh` - Distributed locks (acquire, release, extend, check)
- `test_queue_set_leader.sh` - Queue, Set, and Leader operations
- `run_all_tests.sh` - Master test runner

## Running Tests

### Run all tests:
```bash
./tests/integration/run_all_tests.sh
```

### Run specific test suite:
```bash
./tests/integration/test_kv_operations.sh
./tests/integration/test_counter_operations.sh
./tests/integration/test_list_operations.sh
./tests/integration/test_lock_operations.sh
./tests/integration/test_queue_set_leader.sh
```

## Prerequisites

1. **AWS Credentials**: Valid AWS credentials configured
2. **DynamoDB Access**: Permissions to create/delete tables
3. **Test Table**: Uses `aws-primitives-tool-kvstore-test` by default

## Environment Variables

- `KVSTORE_TABLE` - Override test table name (default: `aws-primitives-tool-kvstore-test`)
- `AWS_REGION` - AWS region for testing
- `AWS_PROFILE` - AWS profile to use

## Test Assertions

The test framework provides:

- `assert_success` - Command must succeed
- `assert_failure` - Command must fail
- `assert_contains` - Output contains string
- `assert_json_equals` - JSON field equals value

## CI/CD Integration

Add to your CI pipeline:
```bash
make test-integration
```

Or directly:
```bash
cd tests/integration && ./run_all_tests.sh
```

## Coverage

Tests cover:
- ✅ Basic CRUD operations
- ✅ Conditional operations
- ✅ TTL and expiration
- ✅ Atomic operations
- ✅ Concurrency (locks, leaders)
- ✅ Data structures (lists, sets, queues)
- ✅ Edge cases (empty collections, missing keys)
- ✅ Idempotency
- ✅ Error handling

## Cleanup

Tests automatically:
1. Create fresh test table before running
2. Clean up test table after completion

Manual cleanup if needed:
```bash
aws-primitives-tool kvstore drop-table --table aws-primitives-tool-kvstore-test --approve
```
