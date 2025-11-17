#!/usr/bin/env bash
# Integration tests for KV operations
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

# Source test helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

test_header "KV OPERATIONS TESTS"

# Test: SET and GET
test_section "Basic SET and GET"
assert_success "$CLI set test-key 'test-value' --table $TEST_TABLE" "Set key-value pair"
assert_json_equals "$CLI get test-key --table $TEST_TABLE" ".value" "test-value" "Get returns correct value"
assert_json_equals "$CLI get test-key --table $TEST_TABLE" ".key" "test-key" "Get returns correct key"

# Test: SET with TTL
test_section "SET with TTL"
assert_success "$CLI set ttl-key 'expires-soon' --ttl 3600 --table $TEST_TABLE" "Set with TTL"
assert_contains "$CLI get ttl-key --table $TEST_TABLE" "expires-soon" "Get TTL key"

# Test: SET with --if-not-exists
test_section "SET with --if-not-exists"
assert_success "$CLI set unique-key 'first' --if-not-exists --table $TEST_TABLE" "Set with if-not-exists (first time)"
assert_failure "$CLI set unique-key 'second' --if-not-exists --table $TEST_TABLE" "Set with if-not-exists (should fail on duplicate)"
assert_json_equals "$CLI get unique-key --table $TEST_TABLE" ".value" "first" "Value unchanged after failed if-not-exists"

# Test: GET with default
test_section "GET with default"
assert_json_equals "$CLI get nonexistent-key --default 'fallback' --table $TEST_TABLE" ".value" "fallback" "Get with default returns default"
assert_json_equals "$CLI get nonexistent-key --default 'fallback' --table $TEST_TABLE" ".default" "true" "Get with default sets default flag"

# Test: GET nonexistent (should fail)
test_section "GET nonexistent key"
assert_failure "$CLI get missing-key --table $TEST_TABLE" "Get nonexistent key fails"

# Test: EXISTS
test_section "EXISTS"
assert_success "$CLI exists test-key --table $TEST_TABLE" "Exists returns true for existing key"
assert_failure "$CLI exists nonexistent-key --table $TEST_TABLE" "Exists returns false for missing key"

# Test: DELETE
test_section "DELETE"
assert_success "$CLI delete test-key --table $TEST_TABLE" "Delete existing key"
assert_failure "$CLI exists test-key --table $TEST_TABLE" "Key no longer exists after delete"
assert_success "$CLI delete test-key --table $TEST_TABLE" "Delete is idempotent"

# Test: DELETE with --if-value
test_section "DELETE with conditional"
assert_success "$CLI set conditional-key 'correct-value' --table $TEST_TABLE" "Set conditional key"
assert_failure "$CLI delete conditional-key --if-value 'wrong-value' --table $TEST_TABLE" "Delete fails with wrong value"
assert_success "$CLI exists conditional-key --table $TEST_TABLE" "Key still exists after failed conditional delete"
assert_success "$CLI delete conditional-key --if-value 'correct-value' --table $TEST_TABLE" "Delete succeeds with correct value"

# Test: LIST keys
test_section "LIST keys"
assert_success "$CLI set config/db-url 'postgres://...' --table $TEST_TABLE" "Set first config key"
assert_success "$CLI set config/api-key 'secret123' --table $TEST_TABLE" "Set second config key"
assert_success "$CLI set other-key 'value' --table $TEST_TABLE" "Set non-config key"
assert_contains "$CLI list config/ --table $TEST_TABLE" "config/db-url" "List finds prefix keys"
assert_contains "$CLI list config/ --table $TEST_TABLE" "config/api-key" "List finds all prefix keys"
assert_json_equals "$CLI list config/ --table $TEST_TABLE" ".count" "2" "List count correct"

# Test: LIST with limit
test_section "LIST with limit"
assert_json_equals "$CLI list --limit 2 --table $TEST_TABLE" '.keys | length' "2" "List respects limit"

# Test: LIST with --format keys
test_section "LIST format keys"
assert_contains "$CLI list config/ --format keys --table $TEST_TABLE" "config/db-url" "Format keys outputs only keys"

test_summary
