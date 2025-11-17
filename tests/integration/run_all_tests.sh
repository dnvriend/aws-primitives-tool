#!/usr/bin/env bash
# Master test runner for all integration tests
#
# Note: This code was generated with assistance from AI coding tools
# and has been reviewed and tested by a human.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Track overall results
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║    AWS PRIMITIVES TOOL - INTEGRATION TEST SUITE           ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Setup test environment
echo -e "${YELLOW}Setting up test environment...${NC}"
setup_test_table
echo ""

# Run each test suite
run_test_suite() {
    local test_file="$1"
    local test_name=$(basename "$test_file" .sh)
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Running: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Reset test counters for this suite
    TESTS_RUN=0
    TESTS_PASSED=0
    TESTS_FAILED=0
    
    if bash "$test_file"; then
        PASSED_SUITES=$((PASSED_SUITES + 1))
        echo -e "${GREEN}✓ Suite PASSED${NC}"
    else
        FAILED_SUITES=$((FAILED_SUITES + 1))
        echo -e "${RED}✗ Suite FAILED${NC}"
    fi
    
    echo ""
}

# Run all test suites
run_test_suite "$SCRIPT_DIR/test_kv_operations.sh"
run_test_suite "$SCRIPT_DIR/test_counter_operations.sh"
run_test_suite "$SCRIPT_DIR/test_list_operations.sh"
run_test_suite "$SCRIPT_DIR/test_lock_operations.sh"
run_test_suite "$SCRIPT_DIR/test_queue_set_leader.sh"

# Cleanup
echo -e "${YELLOW}Cleaning up test environment...${NC}"
cleanup_test_data
echo ""

# Final summary
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║                  FINAL TEST SUMMARY                        ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "Total Test Suites: $TOTAL_SUITES"
echo -e "Passed: ${GREEN}$PASSED_SUITES${NC}"
echo -e "Failed: ${RED}$FAILED_SUITES${NC}"
echo ""

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║              ✓ ALL INTEGRATION TESTS PASSED! ✓             ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                            ║${NC}"
    echo -e "${RED}║           ✗ SOME INTEGRATION TESTS FAILED! ✗               ║${NC}"
    echo -e "${RED}║                                                            ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
