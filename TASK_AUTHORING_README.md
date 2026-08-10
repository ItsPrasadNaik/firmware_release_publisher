# Firmware Release Publisher - Task Authoring Assessment

This is a **complete task authoring submission** for the Hurix Devchallenge platform. It contains a full challenge package for solvers to implement a firmware release publishing system.

## Submission Structure (6-Part Authoring Package)

Per Handbook Section 2, this repository contains all required components:

### 1. **instruction.md** (Root)
Complete task description for solvers:
- Overview of the firmware release publishing pipeline
- 6-part implementation requirements:
  1. CSV manifest reconciliation with DuckDB CTEs
  2. Canonical JSON descriptor creation
  3. OpenSSL CMS cryptographic signing
  4. HTTP publication to distribution gateway
  5. Idempotent state tracking in DuckDB
  6. Output format specification
- Technical constraints (DuckDB callback API, Windows paths, JSON canonicalization)
- Grading criteria

### 2. **solution/** (Reference Implementation)
The working reference solution:
- `release-publisher.mjs` - Complete implementation (301 lines)
- `publish.sh` - Shell wrapper script
- Demonstrates correct orchestration of all 6 parts
- Includes detailed code comments for architecture

### 3. **tests/** (Automated Validation)
- `test.sh` - Bash test harness
  - Validates file structure, syntax, CSV, output format
  - Quick validation before Docker testing
- `test_outputs.py` - Python validator
  - Comprehensive testing with JSON reporting
  - Validates golden output structure
  - Produces CI/CD integration reports

### 4. **task.toml** (Task Metadata)
TOML configuration:
- Reward structure: empty_run=0, full_run=1
- Component descriptions (reconciliation, signing, publication, persistence)
- Environment paths and configurations
- Difficulty level and estimated implementation time

### 5. **AUTHOR_NOTES.md** (Implementation Walkthrough)
Detailed author explanation:
- Architecture decisions and rationale
- Promise-wrapped DuckDB API pattern
- SQL 4-part CTE reconciliation pipeline
- Canonical JSON for deterministic signing
- OpenSSL CMS integration details
- HTTP publication and idempotency
- Known pitfalls and debugging guidance
- Recommended solver implementation order

### 6. **environment/** (Grading Infrastructure)
Complete Docker environment isolated from solver code:
- `Dockerfile` - Full build environment with dependencies
- `package.json` - npm dependencies (duckdb v1.1.3, express v4.19.2)
- `distribution-gateway/` - Mock HTTP gateway server for testing
- `fixtures/build_manifest.csv` - Test data (40 records, 3 duplicates)
- `keys/` - Self-signed certificates generated at build time
- `reports/publications.expected.txt` - Golden reference output
- **publisher/** - EMPTY (solver implements here)

## Proof Validation

The `proofs.sh` script demonstrates both reward scenarios:

### Proof A: Empty Environment (Reward 0)
```bash
./proofs.sh
```
Shows:
- `environment/publisher/` directory is empty
- `npm run report` fails to find implementation file
- No valid output produced
- **Grader awards: 0 points**

### Proof B: With Reference Solution (Reward 1)
```bash
./proofs.sh
```
Shows:
- `solution/release-publisher.mjs` deployed to `environment/publisher/`
- `npm run report` executes complete pipeline
- Output exactly matches `publications.expected.txt` (6 lines, 3 bundles)
- **Grader awards: 1 point**

## Task Overview for Solvers

A solver implementing this task would need to create `environment/publisher/release-publisher.mjs` that:

1. **Loads and reconciles** the build manifest CSV
2. **Identifies publishable bundles** after deduplication and withdrawal processing
3. **Creates canonical JSON descriptors** with sorted keys
4. **Signs each bundle** using OpenSSL CMS with provided certificate
5. **Submits to HTTP gateway** with proper request/response handling
6. **Maintains idempotent state** so retries don't duplicate submissions
7. **Produces exact output format** (6 lines matching golden file)

### Expected Solution Characteristics

- Language: Node.js v20+
- Dependencies: duckdb npm package, Node.js built-ins
- Complexity: Intermediate (3+ hour implementation)
- Core challenges:
  - SQL CTEs for complex data reconciliation
  - Promise-based wrapper around callback API
  - Cryptographic signing integration
  - HTTP request/response handling
  - State management for idempotency

### Key Implementation Steps (Recommended Order)

1. CSV loading and SQL reconciliation (verify 3 bundles identified)
2. Canonical JSON descriptor creation (verify deterministic output)
3. OpenSSL CMS signing in isolation (verify PEM signatures)
4. HTTP publication loop wiring (test with mock gateway)
5. Idempotent state tracking (test first and second runs)
6. Output formatting (match golden file exactly)

## Running Tests

Validate the complete package:

```bash
# Quick structural validation
bash tests/test.sh

# Comprehensive Python validation
python3 tests/test_outputs.py

# Demonstrate both reward scenarios
bash proofs.sh
```

## Technical Constraints Documented

1. **DuckDB API**: Callback-based (not Promises) → requires wrapper functions
2. **Windows Compatibility**: File paths with spaces need double quotes in shell commands
3. **JSON Canonicalization**: Keys must be alphabetically sorted, no whitespace
4. **Connection Lifecycle**: Explicit close() calls required for cleanup
5. **HTTP Integration**: Gateway at 127.0.0.1:7070 with specific endpoint contracts
6. **Deterministic Signing**: Identical inputs must always produce identical signatures

## Grading Workflow

When graders evaluate a solver's submission:

1. Clone the solver's repository
2. Extract `environment/` directory
3. Build Docker image from Dockerfile
4. Generate signing certificates at build time
5. Start distribution gateway container
6. Run `npm run report`
7. Capture stdout
8. Compare line-by-line against `publications.expected.txt`
9. Award 1 point if exact match, 0 if any mismatch
10. Validate idempotency (second run produces same output)

## File Organization

```
.
├── instruction.md              ← Task description for solvers
├── task.toml                   ← Metadata
├── AUTHOR_NOTES.md             ← Implementation walkthrough
├── proofs.sh                   ← Proof validation script
├── README.md                   ← This file
├── solution/                   ← Reference implementation
│   ├── release-publisher.mjs   ← Complete working solution
│   └── publish.sh              ← Shell wrapper
├── tests/                      ← Validation tests
│   ├── test.sh                 ← Bash test harness
│   └── test_outputs.py         ← Python validator
└── environment/                ← Docker grading environment
    ├── Dockerfile              ← Complete build
    ├── package.json            ← Dependencies
    ├── publisher/              ← EMPTY (solver fills in)
    ├── distribution-gateway/   ← Mock server for testing
    ├── fixtures/               ← Test data
    │   └── build_manifest.csv
    ├── keys/                   ← Generated certificates
    └── reports/
        └── publications.expected.txt ← Golden output
```

## Validation Checklist

Before final submission, verify:

- ✅ instruction.md provides clear requirements
- ✅ solution/release-publisher.mjs works correctly
- ✅ tests/ include bash and Python validators
- ✅ task.toml has complete metadata
- ✅ AUTHOR_NOTES.md documents architecture
- ✅ environment/publisher/ is empty (Proof A)
- ✅ solution produces golden output (Proof B)
- ✅ All 6 parts present per Handbook Section 2
- ✅ proofs.sh demonstrates both reward scenarios
