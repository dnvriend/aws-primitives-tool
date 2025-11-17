#!/usr/bin/env bash
# Integration tests for Counter operations
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

test_header "COUNTER OPERATIONS TESTS"

# Test: INC with --create
test_section "INC with --create"
assert_success "$CLI inc new-counter --create --table $TEST_TABLE" "Create counter with inc"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".value" "1" "Counter starts at 1"

# Test: INC existing counter
test_section "INC existing counter"
assert_success "$CLI inc new-counter --table $TEST_TABLE" "Increment counter"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".value" "2" "Counter incremented to 2"

# Test: INC with custom amount
test_section "INC with custom amount"
assert_success "$CLI inc new-counter --by 10 --table $TEST_TABLE" "Increment by 10"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".value" "12" "Counter incremented by 10"

# Test: INC nonexistent (should fail without --create)
test_section "INC nonexistent without --create"
assert_failure "$CLI inc missing-counter --table $TEST_TABLE" "INC fails on nonexistent counter"

# Test: DEC
test_section "DEC"
assert_success "$CLI dec new-counter --table $TEST_TABLE" "Decrement counter"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".value" "11" "Counter decremented"

# Test: DEC with custom amount
test_section "DEC with custom amount"
assert_success "$CLI dec new-counter --by 5 --table $TEST_TABLE" "Decrement by 5"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".value" "6" "Counter decremented by 5"

# Test: DEC nonexistent (should fail)
test_section "DEC nonexistent"
assert_failure "$CLI dec missing-counter --table $TEST_TABLE" "DEC fails on nonexistent counter"

# Test: GET-COUNTER
test_section "GET-COUNTER"
assert_json_equals "$CLI get-counter new-counter --table $TEST_TABLE" ".type" "counter" "Counter has correct type"
assert_contains "$CLI get-counter new-counter --table $TEST_TABLE" "created_at" "Counter has creation timestamp"

# Test: GET-COUNTER nonexistent
test_section "GET-COUNTER nonexistent"
assert_failure "$CLI get-counter nonexistent-counter --table $TEST_TABLE" "GET-COUNTER fails on missing counter"

# Test: Multiple counters
test_section "Multiple independent counters"
assert_success "$CLI inc requests --create --table $TEST_TABLE" "Create requests counter"
assert_success "$CLI inc errors --create --table $TEST_TABLE" "Create errors counter"
assert_success "$CLI inc requests --by 100 --table $TEST_TABLE" "Increment requests"
assert_success "$CLI inc errors --by 5 --table $TEST_TABLE" "Increment errors"
assert_json_equals "$CLI get-counter requests --table $TEST_TABLE" ".value" "101" "Requests counter correct"
assert_json_equals "$CLI get-counter errors --table $TEST_TABLE" ".value" "6" "Errors counter correct"

test_summary
