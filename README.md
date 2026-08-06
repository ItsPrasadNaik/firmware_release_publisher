# Firmware Release Publisher

Publisher for firmware release bundles. Reads build manifest CSV, reconciles records (deduplication + withdrawal processing), signs bundles with OpenSSL, and submits to distribution gateway.

## Architecture

### CSV Reconciliation
- Parses build manifest with BUILD and WITHDRAWAL record types
- Deduplicates records via `SELECT DISTINCT`
- Filters withdrawn builds using 4-part CTE pipeline
- Orders by bundle_id for consistent output

### Signing & Publication
- Generates canonical JSON descriptor (sorted keys, no whitespace) for deterministic signing
- Signs with OpenSSL CMS using PKCS#7 format
- Submits to `/v1/publications` endpoint with descriptor + signature + request token

### Idempotency
- Tracks publication state in DuckDB `publication_log` table
- Checks if bundle already published before signing
- Replays stored receipt on retry (no duplicate submissions)

### Key Components
- `release-publisher.mjs` - Main orchestrator (301 lines)
  - CSV loading and SQL reconciliation
  - OpenSSL integration
  - HTTP gateway communication
  - State management via DuckDB

## Implementation Notes

**DuckDB Promise Handling**
- npm v1.1.3 uses callback-based API, not Promises
- Wrapped `db.run()` in Promise handlers for async/await compatibility

**Cross-Platform Paths**
- Used `os.tmpdir()` + `path.join()` for Windows/Unix portability
- Quoted all paths in OpenSSL shell commands (Windows spaces handling)

**Connection Lifecycle**
- Explicit `db.connect()` → use connection → `conn.close()` → `db.close()`
- Finally block ensures cleanup on errors

## Docker Build & Run

```bash
cd environment
docker build -t fw-release-publisher .
docker run fw-release-publisher npm run report
```

Expected output: 6 lines (3 bundles, 2 lines each)
- Bundle ID, signing key ID
- Receipt ID, token, status

## Dependencies
- duckdb (npm) - data reconciliation
- Node.js built-ins: fs, child_process, http, path, os
- OpenSSL CLI - CMS signing
- Python 3.11 - key generation (Dockerfile)
