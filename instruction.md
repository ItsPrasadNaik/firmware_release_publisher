# Firmware Release Publisher

## Task Overview

You are implementing a **firmware release publishing system** that orchestrates a multi-stage pipeline:

1. **Manifest Reconciliation**: Read a CSV build manifest, deduplicate records, and apply withdrawal logic to identify publishable firmware bundles
2. **Cryptographic Signing**: Sign each publishable bundle descriptor using OpenSSL CMS with a code-signing certificate
3. **HTTP Publication**: Submit signed bundles to a distribution gateway over HTTP
4. **Idempotent State**: Maintain persistent state in DuckDB so duplicate submissions are detected and not re-published

## Implementation Requirements

### Part 1: CSV Manifest Reconciliation (DuckDB)

**Input**: `fixtures/build_manifest.csv` (40 records containing BUILD and WITHDRAWAL entries)

**Process**:
- Load the CSV into a DuckDB table
- Deduplicate all records (some are duplicated at the end of the CSV)
- Identify withdrawn builds using a CTE pipeline:
  - Extract BUILD records (type = "BUILD")
  - Extract WITHDRAWAL records (type = "WITHDRAWAL") and collect their `supersedes_id` values
  - Filter out any BUILD whose `entry_id` is in the supersedes list
- Group publishable builds by `bundle_id` and compute:
  - `artifact_count`: number of artifacts in bundle
  - `total_bytes`: sum of `size_bytes`
- Return bundles in sorted order by bundle_id

**Expected Output** (after reconciliation):
- 3 publishable bundles: BND-101, BND-102, BND-103
- BND-104 is fully withdrawn (all 2 artifacts superseded)

### Part 2: Canonical Descriptor Creation

**Process**:
- Create a JSON descriptor for each bundle with this structure:
  ```json
  {"artifact_count":9,"bundle_id":"BND-101","total_bytes":1201575}
  ```
- **Critical**: Keys must be sorted alphabetically, no spaces or newlines
- This ensures deterministic output for reproducible signing

### Part 3: OpenSSL CMS Signing

**Process**:
- For each bundle descriptor, sign using OpenSSL CMS:
  ```bash
  openssl cms -sign -in <descriptor_file> \
    -signer /app/keys/current/current.cert.pem \
    -inkey /app/keys/current/current.key.pem \
    -outform PEM -binary > <signature_file>
  ```
- Use **detached signatures** (signature separate from data)
- Key paths contain spaces, so always quote them with double quotes in shell commands
- Return the signature as a PEM-formatted string

### Part 4: HTTP Publication

**Process**:
1. Query the gateway for the current signing key ID:
   ```
   GET http://127.0.0.1:7070/v1/signing-key/current
   Response: {"key_id":"fw-signing-2026-current"}
   ```
2. For each bundle, POST to the gateway:
   ```
   POST http://127.0.0.1:7070/v1/publications
   Payload: {"descriptor":"...", "signature":"...", "request_token":"token-<bundle_id>"}
   Response: {"publication_id":"pub-<bundle_id>", "status":"PUBLISHED", "request_token":"..."}
   ```

### Part 5: Idempotent State Tracking

**Process**:
- Create a `publications` table in DuckDB to track published bundles
- Before submitting a bundle, check if it already exists in this table
- If already published:
  - Skip HTTP submission (idempotency)
  - Replay the original receipt from database
- If new:
  - Submit to gateway
  - Store the receipt in the database
- This ensures that re-running the publisher (e.g., on retry) doesn't duplicate submissions

### Part 6: Output Format

**Process**:
- Print one line per bundle per stage:
  1. `BUNDLE <bundle_id> SIGNED KEY=<key_id>`
  2. `BUNDLE <bundle_id> PUBLISHED RECEIPT=<publication_id> TOKEN=<request_token> STATUS=<status>`
- Expected output (6 lines for 3 bundles):
  ```
  BUNDLE BND-101 SIGNED KEY=fw-signing-2026-current
  BUNDLE BND-101 PUBLISHED RECEIPT=pub-BND-101 TOKEN=token-BND-101 STATUS=PUBLISHED
  BUNDLE BND-102 SIGNED KEY=fw-signing-2026-current
  BUNDLE BND-102 PUBLISHED RECEIPT=pub-BND-102 TOKEN=token-BND-102 STATUS=PUBLISHED
  BUNDLE BND-103 SIGNED KEY=fw-signing-2026-current
  BUNDLE BND-103 PUBLISHED RECEIPT=pub-BND-103 TOKEN=token-BND-103 STATUS=PUBLISHED
  ```

## Deliverables

1. **Implementation**: Write `environment/publisher/release-publisher.mjs` to implement the complete pipeline above
2. **Languages**: Node.js v20+ (duckdb, built-in modules: fs, http, path, os, child_process)
3. **Entry Point**: `npm run report` should execute your implementation
4. **Testing**: Your output will be compared line-by-line against the golden output

## Technical Constraints

- **DuckDB**: Uses callback-based API (not Promises). Wrap callbacks in Promises for async/await.
- **Windows Paths**: If running on Windows, wrap file paths in double quotes for shell commands
- **JSON Canonicalization**: Sorted keys, no whitespace, for deterministic signing
- **Error Handling**: Gracefully handle exceptions; exit with clear error messages

## Grading Criteria

✅ CSV reconciliation: Correct record deduplication and withdrawal processing  
✅ DuckDB SQL: Proper CTE structure for filtered and aggregated results  
✅ OpenSSL signing: Valid PEM detached signatures for each bundle  
✅ HTTP integration: Correct payload format and response handling  
✅ Idempotency: Duplicate submissions are detected and skipped  
✅ Output format: Exact match with golden output (6 lines, 3 bundles)
