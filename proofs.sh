#!/bin/bash
# Proof validation script for task authoring assessment
# Demonstrates Proof A (empty run -> reward 0) and Proof B (solution -> reward 1)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT_DIR="$REPO_ROOT/environment"
SOLUTION_DIR="$REPO_ROOT/solution"
GOLDEN_FILE="$ENVIRONMENT_DIR/reports/publications.expected.txt"

echo "=========================================="
echo "PROOF VALIDATION - Firmware Release Publisher"
echo "=========================================="
echo ""

# Proof A: Empty Run
echo "[PROOF A] Empty environment/publisher/ run"
echo "-------------------------------------------"

# Temporarily remove implementation if it exists
if [ -f "$ENVIRONMENT_DIR/publisher/release-publisher.mjs" ]; then
  echo "Found existing implementation, backing up..."
  mv "$ENVIRONMENT_DIR/publisher/release-publisher.mjs" "$ENVIRONMENT_DIR/publisher/release-publisher.mjs.backup"
fi

echo "Running: npm run report (with empty environment/publisher/)"
echo ""

# Try to run - should fail or produce no output
OUTPUT_A=$(cd "$ENVIRONMENT_DIR" && npm run report 2>&1 || true)

if [ -z "$OUTPUT_A" ] || echo "$OUTPUT_A" | grep -q "ENOENT\|not found\|No such"; then
  echo "✓ Empty environment produces minimal output (Proof A: REWARD 0)"
  PROOF_A_PASS=1
else
  echo "⚠ Empty environment produced unexpected output:"
  echo "$OUTPUT_A"
  PROOF_A_PASS=0
fi

echo ""
echo ""

# Proof B: With Solution
echo "[PROOF B] With solution deployed"
echo "--------------------------------"

echo "Deploying solution/release-publisher.mjs to environment/publisher/"
cp "$SOLUTION_DIR/release-publisher.mjs" "$ENVIRONMENT_DIR/publisher/release-publisher.mjs"

echo "Running: npm run report (with solution)"
echo ""

# Run the solution
OUTPUT_B=$(cd "$ENVIRONMENT_DIR" && npm run report 2>&1 || true)

echo "Output from npm run report:"
echo "$OUTPUT_B"
echo ""

# Compare against golden
GOLDEN=$(cat "$GOLDEN_FILE" 2>/dev/null || echo "")

if [ "$OUTPUT_B" = "$GOLDEN" ]; then
  echo "✓ Solution output EXACTLY matches golden file (Proof B: REWARD 1)"
  PROOF_B_PASS=1
else
  echo "✗ Solution output does NOT match golden file"
  echo ""
  echo "Expected:"
  echo "$GOLDEN"
  echo ""
  echo "Got:"
  echo "$OUTPUT_B"
  PROOF_B_PASS=0
fi

echo ""
echo "=========================================="
echo "PROOF VALIDATION SUMMARY"
echo "=========================================="

if [ "$PROOF_A_PASS" -eq 1 ] && [ "$PROOF_B_PASS" -eq 1 ]; then
  echo "✓ Both proofs passed!"
  echo "  - Proof A (empty): Reward 0 ✓"
  echo "  - Proof B (solution): Reward 1 ✓"
  EXIT_CODE=0
else
  echo "✗ Proof validation failed"
  [ "$PROOF_A_PASS" -eq 0 ] && echo "  - Proof A (empty): FAILED"
  [ "$PROOF_B_PASS" -eq 0 ] && echo "  - Proof B (solution): FAILED"
  EXIT_CODE=1
fi

echo "=========================================="

exit $EXIT_CODE
