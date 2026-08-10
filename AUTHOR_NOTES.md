# Firmware Release Publisher - Implementation Notes

## Author's Approach

This task combines several technical domains into a single integrated pipeline: database SQL (CTEs and aggregation), cryptographic signing (OpenSSL CMS), HTTP client implementation, and state persistence (DuckDB idempotency).

## Architecture

### 1. Promise-Wrapped DuckDB API
The npm duckdb package (v1.1.3) uses a callback-based API, not Promises. The key insight is wrapping callbacks in Promise constructors:

```javascript
function runQuery(conn, sql, params = []) {
  return new Promise((resolve, reject) => {
    if (params.length > 0) {
      conn.run(sql, params, (err) => err ? reject(err) : resolve());
    } else {
      conn.run(sql, (err) => err ? reject(err) : resolve());
    }
  });
}
```

This enables `await` syntax throughout the orchestrator while respecting DuckDB's callback contract.

### 2. SQL Reconciliation Pipeline (4-Part CTE)
The manifest contains 40 records (BUILD + WITHDRAWAL entries) with 3 duplicates. The CTE pipeline:

```sql
WITH deduplicated AS (
  SELECT DISTINCT * FROM build_records
),
withdrawn_builds AS (
  SELECT DISTINCT supersedes_id AS entry_id
  FROM deduplicated
  WHERE record_type = 'WITHDRAWAL'
),
publishable_builds AS (
  SELECT d.*
  FROM deduplicated d
  WHERE d.record_type = 'BUILD'
    AND d.entry_id NOT IN (SELECT entry_id FROM withdrawn_builds)
),
bundle_summary AS (
  SELECT bundle_id, COUNT(*) AS artifact_count, SUM(CAST(size_bytes AS BIGINT)) AS total_bytes
  FROM publishable_builds
  GROUP BY bundle_id
)
SELECT * FROM bundle_summary ORDER BY bundle_id
```

**Reconciliation Steps**:
1. Deduplicate: 40 → 37 unique records
2. Identify withdrawn: Extract supersedes_id values (8 withdrawals)
3. Filter publishable: 37 → 27 publishable builds (8 withdrawn)
4. Aggregate: Group by bundle_id, compute counts and totals

**Final Result**: 3 publishable bundles (BND-101: 9 artifacts/1.2MB, BND-102: 10/2.2MB, BND-103: 8/2.1MB). BND-104 is fully withdrawn.

### 3. Canonical JSON Descriptors
For reproducible cryptographic signing, descriptors must be deterministic:

```javascript
function createDescriptor(bundleId, artifactCount, totalBytes) {
  const parts = [
    `"artifact_count":${artifactCount}`,
    `"bundle_id":"${bundleId}"`,
    `"total_bytes":${totalBytes}`
  ];
  return '{' + parts.join(',') + '}';
}
```

**Key Properties**:
- Sorted keys alphabetically (artifact_count, bundle_id, total_bytes)
- No spaces, no newlines
- Same input → identical output → identical signature

### 4. OpenSSL CMS Signing
Uses detached signatures (signature separate from descriptor):

```bash
openssl cms -sign -in <descriptor> \
  -signer <cert> \
  -inkey <key> \
  -outform PEM -binary > <signature>
```

**Critical Details**:
- `-binary` flag: treat descriptor as binary data
- `-outform PEM`: output signature in PEM format (base64)
- Detached signature: only signs the descriptor, doesn't include it
- Paths may contain spaces (Windows): always quote with `"${path}"`

### 5. HTTP Publication Loop
Iterates over publishable bundles:

1. **Check Idempotency**: Query publications table for existing record
2. **If Exists**: Replay receipt from database (idempotent)
3. **If New**: 
   - Sign descriptor using OpenSSL CMS
   - POST to `/v1/publications` with `{descriptor, signature, request_token}`
   - Store receipt in publications table
4. **Output**: Print SIGNED and PUBLISHED lines

### 6. Idempotent State Management
A simple publications table:

```sql
CREATE TABLE publications (
  bundle_id VARCHAR PRIMARY KEY,
  request_token VARCHAR,
  publication_id VARCHAR,
  status VARCHAR,
  key_id VARCHAR
)
```

**Idempotency Guarantee**: On re-run, the same bundle_id will find an existing record and skip HTTP submission, replaying the original publication_id and status.

## Testing Strategy

The solution is validated through:

1. **Proof A (Reward 0)**: Empty run with no `environment/publisher/release-publisher.mjs`
   - Empty environment should produce minimal output or fail gracefully
   - Grader confirms baseline state (0 reward points)

2. **Proof B (Reward 1)**: With reference solution deployed
   - `npm run report` executed in Docker container
   - Output compared line-by-line against `publications.expected.txt`
   - All 6 lines must match exactly (3 bundles × 2 lines each)
   - Idempotency verified: second run doesn't re-publish

## Known Implementation Pitfalls

1. **DuckDB Promisification**: Forgetting to wrap callbacks causes `await` to hang indefinitely
2. **Path Quoting**: Unquoted paths with spaces in OpenSSL command cause "file not found" errors
3. **JSON Canonicalization**: Non-deterministic key ordering produces different signatures each run
4. **Connection Lifecycle**: Missing `conn.close()` or `db.close()` can leave resources open
5. **HTTP Timeouts**: Gateway timeouts if network is misconfigured (check Docker bridge networking)

## Solver Guidance

Implement in this order (per CANDIDATE_GUIDE Section 4):

1. **CSV Reconciliation**: Load manifest, write dedup + withdrawal CTE, verify 3 bundles
2. **Canonical JSON**: Create descriptors, verify deterministic output
3. **OpenSSL Signing**: Sign a single descriptor in isolation, verify PEM output
4. **HTTP Publication**: Wire submission loop, test against mock gateway responses
5. **Idempotent State**: Add publications table, test re-run scenario (empty 0, full 1)
6. **Output Formatting**: Print lines matching expected format, verify all 6 lines

This phased approach allows validation at each stage before integrating components.

## Grading Process

The grader will:
1. Clone your repository
2. Build Docker image (Dockerfile in environment/)
3. Mount fixtures, generate keys, start gateway container
4. Run `npm run report` and capture stdout
5. Compare against golden output (publications.expected.txt)
6. Score 1 if all 6 lines match, 0 if mismatches found
7. Verify idempotency: re-run should produce same output (no duplicate publications)

Success requires exact output format and correct reconciliation logic.
