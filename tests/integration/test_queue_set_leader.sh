#!/usr/bin/env bash
# Integration tests for Queue, Set, and Leader operations
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

test_header "QUEUE, SET, AND LEADER OPERATIONS TESTS"

# ==================== QUEUE TESTS ====================
test_section "QUEUE: PUSH and POP"
assert_success "$CLI queue-push notifications 'msg1' --table $TEST_TABLE" "Push message"
assert_success "$CLI queue-push notifications 'msg2' --priority 1 --table $TEST_TABLE" "Push with priority"
assert_json_equals "$CLI queue-pop notifications --table $TEST_TABLE" '.message' "msg2" "Higher priority pops first"

test_section "QUEUE: SIZE and PEEK"
assert_success "$CLI queue-push notifications 'msg3' --table $TEST_TABLE" "Push message"
assert_success "$CLI queue-push notifications 'msg4' --table $TEST_TABLE" "Push message"
assert_json_equals "$CLI queue-size notifications --table $TEST_TABLE" '.size' "3" "Queue size correct"
assert_contains "$CLI queue-peek notifications --table $TEST_TABLE" "msg1" "Peek shows messages"

test_section "QUEUE: ACK"
RECEIPT=$(${CLI} queue-pop notifications --table ${TEST_TABLE} | jq -r '.receipt')
assert_success "$CLI queue-ack notifications '$RECEIPT' --table $TEST_TABLE" "Acknowledge message"

test_section "QUEUE: Deduplication"
assert_success "$CLI queue-push dedupqueue 'msg1' --dedup-id 'unique-1' --table $TEST_TABLE" "Push with dedup ID"
assert_failure "$CLI queue-push dedupqueue 'msg1' --dedup-id 'unique-1' --table $TEST_TABLE" "Duplicate dedup ID fails"

# ==================== SET TESTS ====================
test_section "SET: ADD and MEMBERS"
assert_success "$CLI sadd tags 'python' --table $TEST_TABLE" "Add member to set"
assert_success "$CLI sadd tags 'aws' --table $TEST_TABLE" "Add member to set"
assert_success "$CLI sadd tags 'cli' --table $TEST_TABLE" "Add member to set"
assert_json_equals "$CLI scard tags --table $TEST_TABLE" '.size' "3" "Set cardinality correct"
assert_contains "$CLI smembers tags --table $TEST_TABLE" "python" "Members contains python"

test_section "SET: ISMEMBER"
assert_success "$CLI sismember tags 'python' --table $TEST_TABLE" "Member exists in set"
assert_failure "$CLI sismember tags 'java' --table $TEST_TABLE" "Non-member not in set"

test_section "SET: REMOVE"
assert_success "$CLI srem tags 'aws' --table $TEST_TABLE" "Remove member"
assert_json_equals "$CLI scard tags --table $TEST_TABLE" '.size' "2" "Set size after remove"
assert_failure "$CLI sismember tags 'aws' --table $TEST_TABLE" "Removed member no longer exists"

test_section "SET: Idempotency"
assert_success "$CLI sadd tags 'python' --table $TEST_TABLE" "Add existing member (idempotent)"
assert_json_equals "$CLI scard tags --table $TEST_TABLE" '.size' "2" "Size unchanged after duplicate add"

# ==================== LEADER TESTS ====================
test_section "LEADER: ELECT"
assert_success "$CLI leader-elect deploy-pool --ttl 30 --id node-1 --table $TEST_TABLE" "Elect leader"
assert_json_equals "$CLI leader-elect deploy-pool --ttl 30 --id node-1 --table $TEST_TABLE" '.node_id' "node-1" "Leader is node-1"

test_section "LEADER: Election conflict"
assert_failure "$CLI leader-elect deploy-pool --ttl 30 --id node-2 --table $TEST_TABLE" "Cannot elect when leader exists"

test_section "LEADER: CHECK"
assert_success "$CLI leader-check deploy-pool --table $TEST_TABLE" "Check leader status"
assert_contains "$CLI leader-check deploy-pool --table $TEST_TABLE" "node-1" "Leader check shows correct node"

test_section "LEADER: HEARTBEAT"
assert_success "$CLI leader-heartbeat deploy-pool --ttl 30 --id node-1 --table $TEST_TABLE" "Send heartbeat"
assert_failure "$CLI leader-heartbeat deploy-pool --ttl 30 --id node-2 --table $TEST_TABLE" "Cannot heartbeat as non-leader"

test_section "LEADER: RESIGN"
assert_failure "$CLI leader-resign deploy-pool --id node-2 --table $TEST_TABLE" "Cannot resign as non-leader"
assert_success "$CLI leader-resign deploy-pool --id node-1 --table $TEST_TABLE" "Resign as leader"
assert_failure "$CLI leader-check deploy-pool --table $TEST_TABLE" "No leader after resignation"

test_section "LEADER: Re-election"
assert_success "$CLI leader-elect deploy-pool --ttl 30 --id node-2 --table $TEST_TABLE" "New leader can be elected"

test_summary
