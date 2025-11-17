#!/usr/bin/env bash
# Integration tests for List operations
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

test_header "LIST OPERATIONS TESTS"

# Test: LPUSH (prepend)
test_section "LPUSH"
assert_success "$CLI lpush mylist 'item3' --table $TEST_TABLE" "Prepend item3"
assert_success "$CLI lpush mylist 'item2' --table $TEST_TABLE" "Prepend item2"
assert_success "$CLI lpush mylist 'item1' --table $TEST_TABLE" "Prepend item1"

# Test: LRANGE to verify order
test_section "LRANGE after LPUSH"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.items[0]' "item1" "First item correct"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.items[1]' "item2" "Second item correct"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.items[2]' "item3" "Third item correct"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.count' "3" "List count correct"

# Test: RPUSH (append)
test_section "RPUSH"
assert_success "$CLI rpush mylist 'item4' --table $TEST_TABLE" "Append item4"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.items[3]' "item4" "Appended item correct"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.count' "4" "List count after rpush"

# Test: LRANGE with indices
test_section "LRANGE with indices"
assert_json_equals "$CLI lrange mylist 0 2 --table $TEST_TABLE" '.count' "2" "Range 0:2 returns 2 items"
assert_json_equals "$CLI lrange mylist 1 3 --table $TEST_TABLE" '.items[0]' "item2" "Range 1:3 starts at index 1"

# Test: LRANGE negative indices
test_section "LRANGE negative indices"
assert_json_equals "$CLI lrange mylist -2 --table $TEST_TABLE" '.count' "2" "Last 2 items"

# Test: LPOP
test_section "LPOP"
assert_json_equals "$CLI lpop mylist --table $TEST_TABLE" '.value' "item1" "LPOP returns first item"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.count' "3" "List has 3 items after lpop"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.items[0]' "item2" "New first item correct"

# Test: RPOP
test_section "RPOP"
assert_json_equals "$CLI rpop mylist --table $TEST_TABLE" '.value' "item4" "RPOP returns last item"
assert_json_equals "$CLI lrange mylist --table $TEST_TABLE" '.count' "2" "List has 2 items after rpop"

# Test: LPOP empty list
test_section "LPOP until empty"
assert_success "$CLI lpop mylist --table $TEST_TABLE" "Pop remaining items"
assert_success "$CLI lpop mylist --table $TEST_TABLE" "Pop remaining items"
assert_failure "$CLI lpop mylist --table $TEST_TABLE" "LPOP fails on empty list"
assert_json_equals "$CLI lpop mylist --table $TEST_TABLE" '.exists' "false" "Empty list returns exists=false"

# Test: RPOP empty list
test_section "RPOP empty list"
assert_failure "$CLI rpop emptylist --table $TEST_TABLE" "RPOP fails on empty list"

# Test: Build FIFO queue (rpush + lpop)
test_section "FIFO queue pattern"
assert_success "$CLI rpush queue 'task1' --table $TEST_TABLE" "Enqueue task1"
assert_success "$CLI rpush queue 'task2' --table $TEST_TABLE" "Enqueue task2"
assert_success "$CLI rpush queue 'task3' --table $TEST_TABLE" "Enqueue task3"
assert_json_equals "$CLI lpop queue --table $TEST_TABLE" '.value' "task1" "FIFO: first in, first out"
assert_json_equals "$CLI lpop queue --table $TEST_TABLE" '.value' "task2" "FIFO: second dequeue"

# Test: Build LIFO stack (lpush + lpop)
test_section "LIFO stack pattern"
assert_success "$CLI lpush stack 'item1' --table $TEST_TABLE" "Push item1"
assert_success "$CLI lpush stack 'item2' --table $TEST_TABLE" "Push item2"
assert_success "$CLI lpush stack 'item3' --table $TEST_TABLE" "Push item3"
assert_json_equals "$CLI lpop stack --table $TEST_TABLE" '.value' "item3" "LIFO: last in, first out"
assert_json_equals "$CLI lpop stack --table $TEST_TABLE" '.value' "item2" "LIFO: second pop"

test_summary
