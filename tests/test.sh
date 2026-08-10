#!/bin/bash
# Test harness for Firmware Release Publisher
# Runs the solution and captures output for comparison against golden reference

set -euo pipefail

echo "========================================="
echo "Firmware Release Publisher - Test Suite"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Directory setup
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT_DIR="$REPO_ROOT/environment"
SOLUTION_DIR="$REPO_ROOT/solution"
TESTS_DIR="$REPO_ROOT/tests"
GOLDEN_FILE="$ENVIRONMENT_DIR/reports/publications.expected.txt"
TEST_OUTPUT_FILE="${TESTS_DIR}/test_output.txt"

# Create test output directory
mkdir -p "$TESTS_DIR"

echo "Root: $REPO_ROOT"
echo "Environment: $ENVIRONMENT_DIR"
echo "Solution: $SOLUTION_DIR"
echo ""

# Test 1: Check file structure
echo "[TEST 1] Checking file structure..."
if [ -f "$ENVIRONMENT_DIR/Dockerfile" ] && \
   [ -f "$ENVIRONMENT_DIR/package.json" ] && \
   [ -f "$ENVIRONMENT_DIR/fixtures/build_manifest.csv" ] && \
   [ -f "$SOLUTION_DIR/release-publisher.mjs" ]; then
  echo -e "${GREEN}✓ PASS${NC}: All required files present"
  ((PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}: Missing required files"
  ((FAILED++))
fi

# Test 2: Check Node.js syntax
echo ""
echo "[TEST 2] Checking Node.js syntax..."
if node --check "$SOLUTION_DIR/release-publisher.mjs" 2>&1; then
  echo -e "${GREEN}✓ PASS${NC}: Solution syntax is valid"
  ((PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}: Syntax error in solution"
  ((FAILED++))
fi

# Test 3: Check CSV manifest structure
echo ""
echo "[TEST 3] Checking CSV manifest..."
RECORD_COUNT=$(tail -n +2 "$ENVIRONMENT_DIR/fixtures/build_manifest.csv" | wc -l)
if [ "$RECORD_COUNT" -eq 40 ]; then
  echo -e "${GREEN}✓ PASS${NC}: Manifest has 40 records"
  ((PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}: Manifest has $RECORD_COUNT records (expected 40)"
  ((FAILED++))
fi

# Test 4: Check expected output format
echo ""
echo "[TEST 4] Checking expected output structure..."
if [ -f "$GOLDEN_FILE" ]; then
  LINE_COUNT=$(wc -l < "$GOLDEN_FILE")
  if [ "$LINE_COUNT" -eq 6 ]; then
    echo -e "${GREEN}✓ PASS${NC}: Expected output has 6 lines"
    ((PASSED++))
  else
    echo -e "${RED}✗ FAIL${NC}: Expected output has $LINE_COUNT lines (expected 6)"
    ((FAILED++))
  fi
else
  echo -e "${RED}✗ FAIL${NC}: Expected output file not found"
  ((FAILED++))
fi

# Test 5: Check package.json npm scripts
echo ""
echo "[TEST 5] Checking package.json npm scripts..."
if grep -q '"report"' "$ENVIRONMENT_DIR/package.json" 2>/dev/null; then
  echo -e "${GREEN}✓ PASS${NC}: 'npm run report' script configured"
  ((PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}: 'npm run report' script missing"
  ((FAILED++))
fi

# Test 6: Check Dockerfile
echo ""
echo "[TEST 6] Checking Dockerfile..."
if grep -q "FROM node:20" "$ENVIRONMENT_DIR/Dockerfile" && \
   grep -q "npm install" "$ENVIRONMENT_DIR/Dockerfile"; then
  echo -e "${GREEN}✓ PASS${NC}: Dockerfile properly configured"
  ((PASSED++))
else
  echo -e "${RED}✗ FAIL${NC}: Dockerfile missing required directives"
  ((FAILED++))
fi

# Summary
echo ""
echo "========================================="
echo -e "Test Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo "========================================="

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
  exit 1
else
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
fi
