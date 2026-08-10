#!/usr/bin/env node
/**
 * Firmware Release Publisher
 * 
 * Reads build manifest, reconciles it (removes duplicates and applied withdrawals),
 * signs each publishable bundle with the current code-signing key, and submits to
 * the distribution gateway over HTTP. Maintains idempotent state in DuckDB.
 */

import duckdb from 'duckdb';
import { readFileSync, writeFileSync } from 'fs';
import { execSync } from 'child_process';
import http from 'http';
import path from 'path';
import os from 'os';

const MANIFEST_PATH = '/app/fixtures/build_manifest.csv';
const DB_PATH = '/app/releases.duckdb';
const CURRENT_KEY_PATH = '/app/keys/current/current.key.pem';
const CURRENT_CERT_PATH = '/app/keys/current/current.cert.pem';
const GATEWAY_URL = 'http://127.0.0.1:7070';
const TMP_DIR = os.tmpdir();

/**
 * Promisify DuckDB callback-based API
 */
function runQuery(conn, sql, params = []) {
  return new Promise((resolve, reject) => {
    try {
      if (params.length > 0) {
        conn.run(sql, params, (err) => {
          if (err) reject(err);
          else resolve();
        });
      } else {
        conn.run(sql, (err) => {
          if (err) reject(err);
          else resolve();
        });
      }
    } catch (err) {
      reject(err);
    }
  });
}

function getAllRows(conn, sql, params = []) {
  return new Promise((resolve, reject) => {
    try {
      if (params.length > 0) {
        conn.all(sql, params, (err, result) => {
          if (err) reject(err);
          else resolve(result || []);
        });
      } else {
        conn.all(sql, (err, result) => {
          if (err) reject(err);
          else resolve(result || []);
        });
      }
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Parse CLI arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  return {
    report: args.includes('--report'),
  };
}

/**
 * Initialize DuckDB and load the manifest
 */
async function initializeDatabase(conn) {
  // Create table
  await runQuery(conn, `
    CREATE TABLE IF NOT EXISTS build_records (
      entry_id VARCHAR,
      bundle_id VARCHAR,
      component_id VARCHAR,
      version VARCHAR,
      size_bytes INTEGER,
      record_type VARCHAR,
      supersedes_id VARCHAR,
      recorded_at VARCHAR
    )
  `);

  // Load CSV using DuckDB's read_csv function
  await runQuery(conn, `
    INSERT INTO build_records 
    SELECT * FROM read_csv('${MANIFEST_PATH}')
  `);
}

/**
 * Get publishable bundles after reconciliation
 */
async function getPublishableBundles(conn) {
  const result = await getAllRows(conn, `
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
      SELECT
        bundle_id,
        COUNT(*) AS artifact_count,
        SUM(CAST(size_bytes AS BIGINT)) AS total_bytes
      FROM publishable_builds
      GROUP BY bundle_id
    )
    SELECT * FROM bundle_summary
    ORDER BY bundle_id
  `);
  
  return result;
}

/**
 * Create canonical JSON descriptor with sorted keys
 */
function createDescriptor(bundleId, artifactCount, totalBytes) {
  // Create object and manually build canonical JSON with sorted keys
  const parts = [
    `"artifact_count":${artifactCount}`,
    `"bundle_id":"${bundleId}"`,
    `"total_bytes":${totalBytes}`
  ];
  
  return '{' + parts.join(',') + '}';
}

/**
 * HTTP GET request helper
 */
function httpGet(path) {
  return new Promise((resolve, reject) => {
    http.get(`${GATEWAY_URL}${path}`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

/**
 * HTTP POST request helper
 */
function httpPost(path, payload) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload);
    const options = {
      hostname: '127.0.0.1',
      port: 7070,
      path,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data),
      },
    };
    
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    });
    
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

/**
 * Get the current signing key ID from the gateway
 */
async function getCurrentKeyId() {
  const response = await httpGet('/v1/signing-key/current');
  return response.key_id;
}

/**
 * Sign a descriptor using OpenSSL CMS
 */
function signDescriptor(descriptorString) {
  const tmpDescFile = path.join(TMP_DIR, 'descriptor.bin');
  const tmpSigFile = path.join(TMP_DIR, 'signature.pem');
  
  // Write descriptor bytes to file
  writeFileSync(tmpDescFile, descriptorString, 'utf-8');
  
  // Sign using OpenSSL CMS with detached signature
  try {
    execSync(
      `openssl cms -sign -in "${tmpDescFile}" ` +
      `-signer "${CURRENT_CERT_PATH}" ` +
      `-inkey "${CURRENT_KEY_PATH}" ` +
      `-outform PEM -binary > "${tmpSigFile}"`,
      { stdio: 'pipe' }
    );
  } catch (err) {
    throw new Error(`OpenSSL signing failed: ${err.message}`);
  }
  
  // Read and return signature as PEM string
  const signature = readFileSync(tmpSigFile, 'utf-8');
  return signature;
}

/**
 * Submit a signed bundle to the gateway
 */
async function submitBundle(descriptor, signature, requestToken) {
  const payload = {
    descriptor,
    signature,
    request_token: requestToken,
  };
  
  return httpPost('/v1/publications', payload);
}

/**
 * Initialize publication tracking in database
 */
async function initPublicationTable(conn) {
  await runQuery(conn, `
    CREATE TABLE IF NOT EXISTS publications (
      bundle_id VARCHAR PRIMARY KEY,
      request_token VARCHAR,
      publication_id VARCHAR,
      status VARCHAR,
      key_id VARCHAR
    )
  `);
}

/**
 * Check if bundle was already published
 */
async function getPublicationRecord(conn, bundleId) {
  const result = await getAllRows(conn, `
    SELECT * FROM publications WHERE bundle_id = ?
  `, [bundleId]);
  
  return result && result.length > 0 ? result[0] : null;
}

/**
 * Store publication record
 */
async function storePublicationRecord(conn, bundleId, requestToken, publicationId, status, keyId) {
  await runQuery(conn, `
    INSERT OR REPLACE INTO publications 
    (bundle_id, request_token, publication_id, status, key_id)
    VALUES (?, ?, ?, ?, ?)
  `, [bundleId, requestToken, publicationId, status, keyId]);
}

/**
 * Main entry point
 */
async function main() {
  const args = parseArgs();
  
  // Open database connection
  const db = new duckdb.Database(DB_PATH);
  const conn = db.connect();
  
  try {
    // Initialize tables and load CSV
    await initializeDatabase(conn);
    await initPublicationTable(conn);
    
    // Get publishable bundles
    const bundles = await getPublishableBundles(conn);
    
    // Get current key ID from gateway
    const keyId = await getCurrentKeyId();
    
    // Process each bundle
    for (const bundle of bundles) {
      const { bundle_id, artifact_count, total_bytes } = bundle;
      const requestToken = `token-${bundle_id}`;
      
      // Check if already published
      const existing = await getPublicationRecord(conn, bundle_id);
      
      if (existing) {
        // Replay the receipt
        console.log(`BUNDLE ${bundle_id} SIGNED KEY=${existing.key_id}`);
        console.log(`BUNDLE ${bundle_id} PUBLISHED RECEIPT=${existing.publication_id} TOKEN=${existing.request_token} STATUS=${existing.status}`);
      } else {
        // Create and sign descriptor
        const descriptor = createDescriptor(bundle_id, artifact_count, total_bytes);
        
        console.log(`BUNDLE ${bundle_id} SIGNED KEY=${keyId}`);
        
        // Sign the descriptor
        const signature = signDescriptor(descriptor);
        
        // Submit to gateway
        const receipt = await submitBundle(descriptor, signature, requestToken);
        
        if (receipt.error) {
          throw new Error(`Publication failed: ${receipt.error}`);
        }
        
        // Store the receipt
        await storePublicationRecord(
          conn, 
          bundle_id, 
          receipt.request_token, 
          receipt.publication_id, 
          receipt.status,
          keyId
        );
        
        console.log(`BUNDLE ${bundle_id} PUBLISHED RECEIPT=${receipt.publication_id} TOKEN=${receipt.request_token} STATUS=${receipt.status}`);
      }
    }
  } finally {
    conn.close();
    db.close();
  }
}

// Run the publisher
main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
