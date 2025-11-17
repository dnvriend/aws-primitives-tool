#!/usr/bin/env bash
# Integration tests for Lock operations
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

test_header "LOCK OPERATIONS TESTS"

# Test: LOCK-ACQUIRE
test_section "LOCK-ACQUIRE"
assert_success "$CLI lock-acquire deploy-lock --ttl 300 --owner agent-1 --table $TEST_TABLE" "Acquire lock"
assert_json_equals "$CLI lock-acquire deploy-lock --ttl 300 --owner agent-1 --table $TEST_TABLE" '.owner' "agent-1" "Lock owner correct"

# Test: LOCK-ACQUIRE duplicate (should fail)
test_section "LOCK-ACQUIRE duplicate"
assert_failure "$CLI lock-acquire deploy-lock --ttl 300 --owner agent-2 --table $TEST_TABLE" "Cannot acquire held lock"

# Test: LOCK-CHECK
test_section "LOCK-CHECK"
assert_success "$CLI lock-check deploy-lock --table $TEST_TABLE" "Lock check succeeds for held lock"
assert_contains "$CLI lock-check deploy-lock --table $TEST_TABLE" "agent-1" "Lock check shows owner"

# Test: LOCK-EXTEND
test_section "LOCK-EXTEND"
assert_success "$CLI lock-extend deploy-lock --ttl 600 --owner agent-1 --table $TEST_TABLE" "Extend lock TTL"
assert_failure "$CLI lock-extend deploy-lock --ttl 600 --owner agent-2 --table $TEST_TABLE" "Cannot extend lock owned by another"

# Test: LOCK-RELEASE
test_section "LOCK-RELEASE"
assert_failure "$CLI lock-release deploy-lock --owner agent-2 --table $TEST_TABLE" "Cannot release lock owned by another"
assert_success "$CLI lock-release deploy-lock --owner agent-1 --table $TEST_TABLE" "Release lock"
assert_failure "$CLI lock-check deploy-lock --table $TEST_TABLE" "Lock no longer held"

# Test: LOCK-RELEASE idempotent
test_section "LOCK-RELEASE idempotent"
assert_success "$CLI lock-release deploy-lock --owner agent-1 --table $TEST_TABLE" "Release is idempotent"

# Test: LOCK-ACQUIRE with wait
test_section "LOCK-ACQUIRE with wait"
assert_success "$CLI lock-acquire test-lock --ttl 2 --owner agent-1 --table $TEST_TABLE" "Acquire lock with short TTL"
assert_success "$CLI lock-acquire test-lock --ttl 300 --owner agent-2 --wait 5 --table $TEST_TABLE" "Acquire with wait succeeds after expiry"

test_summary
