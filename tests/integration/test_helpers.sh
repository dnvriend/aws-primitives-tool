#!/usr/bin/env bash
# Integration test helper functions
# 
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test configuration
TEST_TABLE="${KVSTORE_TABLE:-aws-primitives-tool-kvstore-test}"
CLI="uv run aws-primitives-tool kvstore"

# Print test header
test_header() {
    echo ""
    echo "=================================================="
    echo "  $1"
    echo "=================================================="
}

# Print test section
test_section() {
    echo ""
    echo "--- $1 ---"
}

# Assert command succeeds
assert_success() {
    local cmd="$1"
    local description="${2:-Command should succeed}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} PASS: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} FAIL: $description"
        echo "  Command: $cmd"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Assert command fails
assert_failure() {
    local cmd="$1"
    local description="${2:-Command should fail}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${RED}✗${NC} FAIL: $description (command succeeded when it should fail)"
        echo "  Command: $cmd"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    else
        echo -e "${GREEN}✓${NC} PASS: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    fi
}

# Assert output contains string
assert_contains() {
    local cmd="$1"
    local expected="$2"
    local description="${3:-Output should contain '$expected'}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    local output
    output=$(eval "$cmd" 2>&1 || true)
    
    if echo "$output" | grep -q "$expected"; then
        echo -e "${GREEN}✓${NC} PASS: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} FAIL: $description"
        echo "  Command: $cmd"
        echo "  Expected to contain: $expected"
        echo "  Got: $output"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Assert JSON field equals value
assert_json_equals() {
    local cmd="$1"
    local jq_filter="$2"
    local expected="$3"
    local description="${4:-JSON field $jq_filter should equal $expected}"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    local output
    output=$(eval "$cmd" 2>&1 || true)
    
    local actual
    actual=$(echo "$output" | jq -r "$jq_filter" 2>/dev/null || echo "")
    
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} PASS: $description"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} FAIL: $description"
        echo "  Command: $cmd"
        echo "  Expected: $expected"
        echo "  Got: $actual"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Print test summary
test_summary() {
    echo ""
    echo "=================================================="
    echo "  TEST SUMMARY"
    echo "=================================================="
    echo "Total tests: $TESTS_RUN"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}ALL TESTS PASSED!${NC}"
        return 0
    else
        echo -e "\n${RED}SOME TESTS FAILED!${NC}"
        return 1
    fi
}

# Cleanup test data
cleanup_test_data() {
    echo "Cleaning up test data..."
    # Drop test table if it exists
    $CLI drop-table --table "$TEST_TABLE" --approve > /dev/null 2>&1 || true
}

# Setup test table
setup_test_table() {
    echo "Setting up test table: $TEST_TABLE"
    
    # Drop existing test table
    cleanup_test_data
    
    # Create fresh test table
    $CLI create-table --table "$TEST_TABLE" > /dev/null 2>&1
    
    # Wait for table to be active
    sleep 2
}

# Export functions
export -f test_header
export -f test_section
export -f assert_success
export -f assert_failure
export -f assert_contains
export -f assert_json_equals
export -f test_summary
export -f cleanup_test_data
export -f setup_test_table
