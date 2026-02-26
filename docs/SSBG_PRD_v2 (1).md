# SSBG — Secure Sovereign Backup Gateway
## Product Requirements Document (PRD) — Version 2.0

**Document Version:** 2.0  
**Date:** February 2025  
**Classification:** INTERNAL  
**Authors:** SSBG Development Team  
**Status:** Final

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Problem Statement](#3-problem-statement)
4. [Goals & Objectives](#4-goals--objectives)
5. [System Architecture](#5-system-architecture)
6. [Technology Stack](#6-technology-stack)
7. [Cryptographic Architecture](#7-cryptographic-architecture)
8. [Database Schema](#8-database-schema)
9. [API Contract](#9-api-contract)
10. [Policy Engine](#10-policy-engine)
11. [Audit Log & Hash Chain](#11-audit-log--hash-chain)
12. [Monitoring & Detection Engine](#12-monitoring--detection-engine)
13. [Incident Response Controller](#13-incident-response-controller)
14. [Backup Workflow](#14-backup-workflow)
15. [Restore Workflow](#15-restore-workflow)
16. [Crypto-Shredding Workflow](#16-crypto-shredding-workflow)
17. [Authentication & Authorization](#17-authentication--authorization)
18. [Storage Architecture](#18-storage-architecture)
19. [Error Handling](#19-error-handling)
20. [Testing Strategy](#20-testing-strategy)
21. [Deployment & Configuration](#21-deployment--configuration)
22. [Future Work](#22-future-work)

---

## 1. Executive Summary

The Secure Sovereign Backup Gateway (SSBG) is a self-hosted, sovereign-grade backup system designed to provide government-level data protection through client-side encryption, Hold Your Own Key (HYOK) key management, and cryptographic data lifecycle control. The system ensures that sensitive government data is encrypted before leaving the source environment, stored securely in S3-compatible object storage (MinIO), and can be permanently destroyed through irreversible crypto-shredding when required.

SSBG implements a defense-in-depth security model combining AES-256-GCM symmetric encryption with ECIES (Elliptic Curve Integrated Encryption Scheme) key wrapping, SHA-512 tamper-evident audit logging, a rule-based policy engine, real-time threat monitoring, and a staged incident response system with four escalation levels (Level 0 through Level 3).

This PRD v2 reflects the streamlined MVP architecture with a single MinIO instance, SHA-512 hashing throughout the system, and the secondary MinIO disaster recovery feature documented as planned future work.

---

## 2. Project Overview

**Project Name:** Secure Sovereign Backup Gateway (SSBG)  
**Project Type:** University Graduation Project  
**Team Size:** 5+ members  
**Primary Language:** Python 3.11+  
**Deployment Model:** Docker Compose (self-hosted)  
**API Framework:** FastAPI  
**Database:** PostgreSQL 16  
**Object Storage:** MinIO (S3-compatible)

SSBG addresses the critical requirement for sovereign nations and government institutions to maintain full control over their backup data, encryption keys, and data lifecycle. Unlike commercial cloud backup services where the provider holds the encryption keys, SSBG ensures the data owner holds all keys and can independently verify data integrity and enforce destruction.

---

## 3. Problem Statement

Government and sovereign institutions face several critical challenges with conventional backup solutions:

**Data Sovereignty Concerns:** Commercial cloud backup providers store encryption keys on their infrastructure. In the event of a foreign government subpoena, legal dispute, or provider compromise, the data owner has no independent guarantee of data confidentiality. The institution must trust the provider's key management, which violates the principle of sovereign data control.

**Lack of Verifiable Audit Trails:** Existing backup solutions provide audit logs, but these logs are typically stored in the same system they audit. An attacker who compromises the backup system can modify the audit trail to conceal unauthorized access. There is no cryptographic guarantee that the audit log has not been tampered with.

**No Guaranteed Data Destruction:** When a data retention period expires, or when a security breach demands immediate data destruction, conventional backup systems offer "delete" operations that may leave recoverable data fragments on disk. There is no cryptographic guarantee that destroyed data is irrecoverable.

**Insufficient Access Control Granularity:** Government data classifications (PUBLIC, INTERNAL, CONFIDENTIAL, SECRET) require different access controls, encryption strengths, and handling procedures. Most backup systems treat all data equally, lacking classification-aware policy enforcement.

**No Real-Time Threat Detection:** Backup systems are high-value targets for data exfiltration attacks. An attacker who gains access to the restore mechanism can silently exfiltrate data without detection. Existing solutions lack real-time monitoring of access patterns and automated incident response.

---

## 4. Goals & Objectives

### Primary Goals

**G1 — Client-Side Encryption:** All data must be encrypted before leaving the source environment. The backup gateway encrypts data using AES-256-GCM with per-object Data Encryption Keys (DEKs). Plaintext data never exists on the storage medium.

**G2 — Hold Your Own Key (HYOK):** The data owner generates, stores, and controls all cryptographic keys. No external party (including the system developer) can decrypt backup data. ECC key pairs (SECP384R1) are generated locally and private keys are password-protected and stored on the owner's infrastructure.

**G3 — Tamper-Evident Audit Logging:** Every operation is logged in a SHA-512 hash chain. Each log entry's hash depends on all previous entries. Any modification to a single entry breaks the chain, making tampering mathematically detectable.

**G4 — Classification-Aware Policy Engine:** Access control policies are enforced based on data classification level, user role, time of day, request rate, and system incident level. Restore operations require strictly higher trust than backup operations.

**G5 — Crypto-Shredding:** Permanent, irreversible data destruction by destroying the ECC private key. Without the private key, the wrapped DEK cannot be unwrapped, the DEK cannot decrypt the ciphertext, and the data is mathematically irrecoverable.

**G6 — Real-Time Threat Detection:** A rule-based monitoring engine detects suspicious patterns (brute force, mass exfiltration, off-hours access) and triggers automated incident responses.

**G7 — Staged Incident Response:** Four escalation levels (0–3) with progressively restrictive responses, from enhanced logging (Level 1) to complete system lockdown and crypto-shredding (Level 3).

### Success Metrics

| Metric | Target |
|--------|--------|
| Encryption coverage | 100% of stored data encrypted at rest |
| Key sovereignty | Zero external key dependencies |
| Audit chain integrity | 100% tamper detection rate |
| Policy enforcement | Zero unauthorized restores |
| Crypto-shred effectiveness | 0% data recovery after key destruction |
| Threat detection latency | < 60 seconds from anomaly to alert |
| System uptime | 99.5% (development/demo environment) |

---

## 5. System Architecture

### Container Architecture

The MVP deployment consists of 3 Docker containers orchestrated via Docker Compose:

| Container | Image | Ports | Purpose |
|-----------|-------|-------|---------|
| `ssbg-gateway` | Custom (Python 3.11) | 8000 | FastAPI application server |
| `ssbg-postgres` | postgres:16-alpine | 5432 | Metadata, audit logs, policies |
| `ssbg-minio` | minio/minio:latest | 9000 (API), 9001 (Console) | Encrypted object storage |

### Network Architecture

All containers communicate over an internal Docker bridge network (`ssbg-network`). Only the gateway exposes its port (8000) to the host. PostgreSQL and MinIO are accessible only from within the Docker network, providing network-level isolation.

```
                          ┌─────────────────────────────────┐
                          │         Docker Network           │
                          │         (ssbg-network)           │
                          │                                  │
 Client ──── :8000 ──────▶│  ┌──────────────────┐           │
                          │  │  ssbg-gateway     │           │
                          │  │  (FastAPI)         │           │
                          │  └────┬─────────┬────┘           │
                          │       │         │                │
                          │       ▼         ▼                │
                          │  ┌─────────┐ ┌────────┐          │
                          │  │postgres │ │ minio  │          │
                          │  │ :5432   │ │ :9000  │          │
                          │  └─────────┘ └────────┘          │
                          └─────────────────────────────────┘
```

### Application Architecture (Gateway)

```
gateway/app/
├── main.py                  # FastAPI entry point & lifespan
├── config.py                # Pydantic settings management
├── dependencies.py          # Auth & dependency injection
├── api/                     # Route handlers
│   ├── backup.py            # POST /backup, GET /backup/{id}
│   ├── restore.py           # POST /restore, GET /restore/{id}
│   ├── admin.py             # Policies, keys, audit, alerts, crypto-shred
│   └── health.py            # GET /health, GET /health/detailed
├── models/                  # SQLAlchemy ORM models
│   ├── backup_metadata.py
│   ├── audit_log.py
│   ├── key_version.py
│   ├── api_key.py
│   ├── policy.py
│   └── alert.py
├── schemas/                 # Pydantic request/response schemas
│   ├── backup.py
│   ├── restore.py
│   ├── admin.py
│   └── common.py            # Enums, envelopes, pagination
├── services/                # Business logic layer
│   ├── encryption_service.py
│   ├── key_manager.py
│   ├── storage_service.py
│   ├── policy_engine.py
│   ├── audit_service.py
│   ├── monitoring_service.py
│   ├── response_controller.py
│   └── backup_service.py
├── db/
│   ├── session.py           # Async engine + session factory
│   └── base.py              # SQLAlchemy declarative base
└── utils/
    ├── hashing.py           # SHA-512 helpers
    ├── streaming.py         # Chunked file streaming
    └── errors.py            # Centralized error handling
```

---

## 6. Technology Stack

### Core Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.11+ | Primary development language |
| Web Framework | FastAPI | 0.109.2 | Async REST API framework |
| ASGI Server | Uvicorn | 0.27.1 | High-performance async server |
| Database | PostgreSQL | 16 (Alpine) | Relational metadata store |
| ORM | SQLAlchemy | 2.0.27 (async) | Database abstraction layer |
| DB Migrations | Alembic | 1.13.1 | Schema version control |
| DB Driver | asyncpg | 0.29.0 | Async PostgreSQL driver |
| Object Storage | MinIO | Latest | S3-compatible encrypted storage |
| S3 Client | boto3 / aioboto3 | 1.34.34 / 12.3.0 | S3 API client |
| Cryptography | cryptography | 42.0.2 | AES-GCM, ECC, HKDF |
| Validation | Pydantic | 2.6.1 | Request/response validation |
| Settings | pydantic-settings | 2.1.0 | Environment configuration |
| Containerization | Docker Compose | 3.9 | Container orchestration |

### Agent CLI Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| HTTP Client | httpx | 0.27.0 | Async HTTP requests |
| CLI Framework | click | 8.1.7 | Command-line interface |
| Terminal UI | rich | 13.7.0 | Pretty terminal output |
| Configuration | pyyaml | 6.0.1 | YAML config parsing |

---

## 7. Cryptographic Architecture

### Cryptographic Primitives

| Primitive | Algorithm | Key Size | Purpose |
|-----------|-----------|----------|---------|
| Symmetric Encryption | AES-256-GCM | 256-bit | Backup data encryption |
| Asymmetric Key Wrapping | ECIES (SECP384R1) | 384-bit curve | DEK wrapping/unwrapping |
| Key Derivation | HKDF-SHA256 | 256-bit output | ECDH shared secret → AES key |
| Hash Function (System-wide) | SHA-512 | 512-bit output | Audit chain, checksums, API key hashing |

### Why SHA-512

SSBG v2 standardizes on SHA-512 for all hashing operations throughout the system. The rationale:

**256-bit collision resistance:** SHA-512 provides 256-bit collision resistance compared to SHA-256's 128-bit collision resistance. For a tamper-evident audit log where collision resistance is the primary security property, this represents a significant security margin.

**Faster on 64-bit processors:** SHA-512 operates on 64-bit words natively, making it faster than SHA-256 on modern 64-bit server hardware (which is the target deployment platform).

**Consistency:** Using a single hash function across the entire system (audit chain, API key hashing, plaintext checksums, ciphertext checksums) eliminates confusion and reduces implementation errors.

### Key Hierarchy

```
┌─────────────────────────────────────────────┐
│          ECC Master Key Pair                │
│          (SECP384R1 / P-384)                │
│          Version: P-001, P-002, ...         │
│                                             │
│   Private Key: Password-protected PEM       │
│   Public Key: PEM (can be distributed)      │
└──────────────────┬──────────────────────────┘
                   │ ECIES wraps/unwraps
                   ▼
┌─────────────────────────────────────────────┐
│           Data Encryption Key (DEK)         │
│           (AES-256, 32 random bytes)        │
│           Unique per backup object          │
│                                             │
│   Plaintext: Only exists in memory          │
│   Wrapped: Stored in MinIO alongside data   │
└──────────────────┬──────────────────────────┘
                   │ AES-256-GCM encrypts
                   ▼
┌─────────────────────────────────────────────┐
│           Backup Ciphertext                 │
│           (AES-256-GCM encrypted data)      │
│           + 16-byte authentication tag      │
│           + 12-byte nonce                   │
│                                             │
│   Stored in MinIO as .enc file              │
└─────────────────────────────────────────────┘
```

### ECIES Key Wrapping Process

The DEK is wrapped using Elliptic Curve Integrated Encryption Scheme (ECIES):

**Step 1 — Ephemeral Key Generation:** Generate a random ephemeral ECC key pair on SECP384R1.

**Step 2 — ECDH Key Agreement:** Compute a shared secret using ECDH between the ephemeral private key and the recipient's (master) public key.

**Step 3 — Key Derivation:** Derive a 256-bit AES key from the shared secret using HKDF-SHA256 with info label `SSBG-DEK-WRAP-v1`.

**Step 4 — DEK Encryption:** Encrypt the 32-byte DEK using AES-256-GCM with the derived key and a random 12-byte nonce.

**Step 5 — Serialization:** Output the wrapped DEK as: `[2-byte pubkey length][ephemeral public key (X9.62 uncompressed)][12-byte nonce][encrypted DEK + 16-byte GCM tag]`.

### Crypto-Shredding Chain

The mathematical guarantee of crypto-shredding works as follows:

```
Destroy P-001.private.pem
    → Cannot perform ECDH with ephemeral public keys
        → Cannot derive AES wrapping key
            → Cannot unwrap DEK
                → Cannot decrypt ciphertext
                    → Data is PERMANENTLY IRRECOVERABLE
```

The private key file is securely destroyed by: (1) overwriting with random bytes of the same size, (2) flushing to disk with `fsync`, and (3) deleting the file. This three-step process ensures the key material is not recoverable from disk.

---

## 8. Database Schema

### Enumerations

```sql
CREATE TYPE classification_level AS ENUM ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'SECRET');
CREATE TYPE user_role AS ENUM ('operator', 'admin', 'super_admin');
CREATE TYPE backup_status AS ENUM ('PROCESSING', 'ACTIVE', 'DELETED', 'CRYPTO_SHREDDED');
CREATE TYPE key_status AS ENUM ('ACTIVE', 'RETIRED', 'DESTROYED');
CREATE TYPE key_type AS ENUM ('PRIMARY', 'SECONDARY');
CREATE TYPE audit_action AS ENUM (
    'BACKUP_START', 'BACKUP_COMPLETE', 'BACKUP_FAILED',
    'RESTORE_REQUEST', 'RESTORE_APPROVED', 'RESTORE_DENIED',
    'RESTORE_COMPLETE', 'RESTORE_FAILED',
    'POLICY_CHECK_ALLOW', 'POLICY_CHECK_DENY',
    'KEY_WRAP', 'KEY_UNWRAP', 'KEY_ROTATE', 'KEY_DESTROY',
    'ALERT_TRIGGER', 'ALERT_ACK', 'ALERT_RESOLVE', 'ALERT_ESCALATE',
    'INCIDENT_LEVEL_CHANGE', 'CONFIG_CHANGE', 'POLICY_CHANGE',
    'AUTH_SUCCESS', 'AUTH_FAILURE',
    'CRYPTO_SHRED_START', 'CRYPTO_SHRED_COMPLETE',
    'SYSTEM_START', 'SYSTEM_HEALTH_CHECK'
);
CREATE TYPE audit_result AS ENUM ('SUCCESS', 'DENIED', 'FAILED', 'ERROR');
CREATE TYPE alert_severity AS ENUM ('MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE alert_status AS ENUM ('NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'ESCALATED');
```

### Tables

#### api_keys

Stores SHA-512 hashed API keys. The raw key is shown once on creation and never stored.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Unique identifier |
| key_hash | VARCHAR(128) | NOT NULL, UNIQUE | SHA-512 hash of the raw API key |
| key_prefix | VARCHAR(8) | NOT NULL | First 8 chars for identification |
| role | user_role | NOT NULL | operator, admin, super_admin |
| department | VARCHAR(100) | NOT NULL | Organizational department |
| description | VARCHAR(255) | | Human-readable description |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |
| expires_at | TIMESTAMPTZ | | NULL = never expires |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Revocation flag |
| allowed_ips | INET[] | | IP whitelist (NULL = any) |
| last_used_at | TIMESTAMPTZ | | Last usage timestamp |
| last_used_ip | INET | | Last usage IP address |

#### backup_metadata

Stores metadata for each encrypted backup object.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| object_id | UUID | PK, DEFAULT gen_random_uuid() | Unique backup identifier |
| classification | classification_level | NOT NULL | Data classification level |
| source_system | VARCHAR(200) | NOT NULL | Origin system identifier |
| original_filename | VARCHAR(500) | | Original file name |
| description | TEXT | | Human-readable description |
| original_size | BIGINT | NOT NULL | Plaintext size in bytes |
| encrypted_size | BIGINT | NOT NULL | Ciphertext size in bytes |
| checksum_plaintext | VARCHAR(128) | NOT NULL | SHA-512 hex of plaintext |
| checksum_ciphertext | VARCHAR(128) | NOT NULL | SHA-512 hex of ciphertext |
| storage_path | VARCHAR(500) | NOT NULL | S3 key in MinIO |
| wrapped_dek_path | VARCHAR(500) | NOT NULL | S3 key for wrapped DEK |
| key_version | VARCHAR(50) | NOT NULL, FK → key_versions | ECC key version used |
| nonce | BYTEA | NOT NULL | 12-byte GCM nonce |
| created_by | UUID | NOT NULL, FK → api_keys | API key that created this backup |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |
| status | backup_status | NOT NULL, DEFAULT 'PROCESSING' | Current status |

#### key_versions

Tracks ECC key pair lifecycle including rotation and destruction.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| version_id | VARCHAR(50) | PK | e.g., "P-001", "P-002" |
| key_type | key_type | NOT NULL | PRIMARY or SECONDARY |
| curve | VARCHAR(20) | NOT NULL, DEFAULT 'SECP384R1' | Elliptic curve name |
| public_key_pem | TEXT | NOT NULL | PEM-encoded public key |
| private_key_path | VARCHAR(500) | NOT NULL | Filesystem path to encrypted PEM |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Generation timestamp |
| rotated_from | VARCHAR(50) | FK → key_versions | Previous version (if rotated) |
| status | key_status | NOT NULL, DEFAULT 'ACTIVE' | ACTIVE, RETIRED, or DESTROYED |
| destroyed_at | TIMESTAMPTZ | | When key was destroyed |
| destroyed_by | UUID | FK → api_keys | Who authorized destruction |
| destruction_reason | TEXT | | Why key was destroyed |

#### audit_log

Tamper-evident log with SHA-512 hash chain.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | UUID | PK, DEFAULT gen_random_uuid() | Unique event identifier |
| sequence_number | BIGSERIAL | UNIQUE, NOT NULL | Sequential chain ordering |
| timestamp | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Event timestamp |
| actor | UUID | FK → api_keys | API key that performed action (NULL for system) |
| actor_role | user_role | | Role at time of action |
| action | audit_action | NOT NULL | Action type |
| resource | VARCHAR(200) | | Affected resource ID |
| result | audit_result | NOT NULL | SUCCESS, DENIED, FAILED, ERROR |
| details | JSONB | | Flexible context data |
| source_ip | INET | | Client IP address |
| prev_hash | VARCHAR(128) | NOT NULL | SHA-512 of previous entry's curr_hash |
| curr_hash | VARCHAR(128) | NOT NULL, UNIQUE | SHA-512 of this entry |

#### audit_checkpoints

Periodic snapshots of the hash chain for efficient validation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| checkpoint_id | SERIAL | PK | Auto-incrementing ID |
| sequence_number | BIGINT | NOT NULL, FK → audit_log | Checkpoint position |
| curr_hash | VARCHAR(128) | NOT NULL | SHA-512 hash at checkpoint |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Checkpoint timestamp |

Checkpoints are created every 1,000 audit log entries.

#### policies

Configurable access control policies evaluated by the policy engine.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| policy_id | UUID | PK, DEFAULT gen_random_uuid() | Unique policy identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Policy name |
| description | TEXT | | Policy description |
| rule_json | JSONB | NOT NULL | Policy rules definition |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Enabled flag |
| priority | INTEGER | NOT NULL, DEFAULT 100 | Lower = higher priority |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last modification |
| created_by | UUID | FK → api_keys | Policy creator |

#### alerts

Monitoring alerts generated by the detection engine.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| alert_id | UUID | PK, DEFAULT gen_random_uuid() | Unique alert identifier |
| rule_id | VARCHAR(10) | NOT NULL | Monitoring rule (M1–M10) |
| severity | alert_severity | NOT NULL | MEDIUM, HIGH, CRITICAL |
| status | alert_status | NOT NULL, DEFAULT 'NEW' | Alert lifecycle status |
| incident_level | INTEGER | NOT NULL, CHECK 0–3 | Recommended escalation level |
| triggered_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When alert was created |
| acknowledged_at | TIMESTAMPTZ | | When acknowledged |
| acknowledged_by | UUID | FK → api_keys | Who acknowledged |
| resolved_at | TIMESTAMPTZ | | When resolved |
| resolved_by | UUID | FK → api_keys | Who resolved |
| details | JSONB | NOT NULL | Rule match evidence |
| related_actor | UUID | FK → api_keys | API key that triggered alert |
| related_resource | VARCHAR(200) | | Backup/key involved |

#### restore_requests

Tracks restore request lifecycle separately from audit log.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| restore_id | UUID | PK, DEFAULT gen_random_uuid() | Unique restore identifier |
| backup_id | UUID | NOT NULL, FK → backup_metadata | Target backup |
| requested_by | UUID | NOT NULL, FK → api_keys | Requester |
| justification | TEXT | NOT NULL | Reason for restore |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | PENDING/APPROVED/DENIED/PROCESSING/COMPLETE/FAILED/QUARANTINED |
| requested_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Request timestamp |
| approved_at | TIMESTAMPTZ | | Approval timestamp |
| approved_by | UUID | FK → api_keys | Approver (Level 2) |
| completed_at | TIMESTAMPTZ | | Completion timestamp |
| download_token | VARCHAR(64) | | Time-limited download token |
| download_expires_at | TIMESTAMPTZ | | Token expiry |
| source_ip | INET | | Request source IP |

#### rate_counters

Sliding window counters for rate limiting enforcement.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Auto-incrementing ID |
| api_key_id | UUID | NOT NULL, FK → api_keys | Associated API key |
| action_type | VARCHAR(30) | NOT NULL | restore, backup, auth_failure |
| window_start | TIMESTAMPTZ | NOT NULL | Window start time |
| count | INTEGER | NOT NULL, DEFAULT 1 | Counter value |

#### system_state

Global system state including current incident level.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | VARCHAR(50) | PK | State key |
| value | JSONB | NOT NULL | State value |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update |

Initial seed values: `incident_level` = `{"level": 0}`, `system_version` = `{"version": "1.0.0"}`.

---

## 9. API Contract

All API endpoints are prefixed with `/api/v1`. Authentication is via the `X-API-Key` header. MFA-protected endpoints additionally require the `X-MFA-Token` header.

### Response Envelope

All responses follow a standard JSON envelope:

```json
{
    "status": "success",
    "data": { ... },
    "request_id": "uuid",
    "timestamp": "ISO-8601"
}
```

Error responses:

```json
{
    "status": "error",
    "error": { "code": "ERROR_CODE", "message": "Human readable message" },
    "request_id": "uuid",
    "timestamp": "ISO-8601"
}
```

### Health Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | None | Basic health check |
| GET | `/api/v1/health/detailed` | Admin | Component-level health (DB, MinIO, keys) |

### Backup Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/backup` | API Key | Upload and encrypt a new backup (multipart form) |
| GET | `/api/v1/backup/{backup_id}` | API Key | Get backup metadata |
| GET | `/api/v1/backup/{backup_id}/status` | API Key | Get processing status |
| GET | `/api/v1/backups` | API Key | List backups (filtered, paginated) |

**POST /backup** accepts multipart form data with fields: `file` (binary), `classification` (enum), `source_system` (string), `description` (optional string).

### Restore Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/restore` | API Key + MFA | Request restore of a backup |
| GET | `/api/v1/restore/{restore_id}/status` | API Key | Check restore job status |
| GET | `/api/v1/restore/{restore_id}/download` | API Key + MFA | Download restored plaintext (time-limited) |

**POST /restore** requires `backup_id` (UUID) and `justification` (string, min 10 chars).

### Admin Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/admin/policies` | Admin | Create a new policy |
| GET | `/api/v1/admin/policies` | Admin | List all policies |
| POST | `/api/v1/admin/api-keys` | Super Admin | Generate a new API key |
| DELETE | `/api/v1/admin/api-keys/{key_id}` | Super Admin | Revoke an API key |
| GET | `/api/v1/admin/audit-logs` | Admin | Query audit logs (filtered, paginated) |
| POST | `/api/v1/admin/audit-logs/validate` | Admin | Validate hash chain integrity |
| GET | `/api/v1/admin/alerts` | Admin | List alerts (filtered by status) |
| POST | `/api/v1/admin/alerts/{alert_id}/acknowledge` | Admin | Acknowledge an alert |
| POST | `/api/v1/admin/incident/crypto-shred` | Super Admin + MFA | Execute crypto-shredding (IRREVERSIBLE) |

---

## 10. Policy Engine

The Policy Decision Point (PDP) evaluates every operation against a set of rules. The fundamental design principle is: **Restore ALWAYS requires higher trust than Backup.**

### Policy Rules

| Rule ID | Policy | Effect |
|---------|--------|--------|
| P1 | Backup requires operator, admin, or super_admin role | Deny backup if role insufficient |
| P2 | Restore requires admin or super_admin role | Deny restore for operators |
| P3 | SECRET restore requires super_admin + MFA | Deny if role or MFA insufficient |
| P3b | CONFIDENTIAL restore requires MFA | Deny if MFA not provided |
| P4 | Restore only during business hours (08:00–18:00) | Deny restore outside hours |
| P5 | Per-key rate limit: max 10 restores/hour | Deny if limit exceeded |
| P6 | System-wide rate limit: max 50 restores/hour | Deny if system limit exceeded |
| P7 | Crypto-shred requires super_admin + MFA + confirmation code | Deny if any requirement missing |
| P8 | Level 2 incident: all restores require manual admin approval | Restore set to PENDING status |
| P9 | Level 3 incident: all operations blocked | Complete system lockdown |

### Evaluation Order

Policies are evaluated in order with a first-deny-wins strategy:

1. Incident level check (P9 → Level 3 blocks everything)
2. Role-based access control (P1, P2)
3. Classification-based access control (P3, P3b)
4. Time window check (P4, restore only)
5. Per-key rate limit (P5)
6. System-wide rate limit (P6)
7. Custom policies from database (priority-ordered)

### Role-Permission Matrix

| Operation | operator | admin | super_admin |
|-----------|----------|-------|-------------|
| Backup (PUBLIC/INTERNAL) | ✅ | ✅ | ✅ |
| Backup (CONFIDENTIAL/SECRET) | ✅ | ✅ | ✅ |
| Restore (PUBLIC/INTERNAL) | ❌ | ✅ | ✅ |
| Restore (CONFIDENTIAL) | ❌ | ✅ + MFA | ✅ + MFA |
| Restore (SECRET) | ❌ | ❌ | ✅ + MFA |
| View Audit Logs | ❌ | ✅ | ✅ |
| Manage Policies | ❌ | ✅ | ✅ |
| Manage API Keys | ❌ | ❌ | ✅ |
| Crypto-Shredding | ❌ | ❌ | ✅ + MFA + Confirm |

---

## 11. Audit Log & Hash Chain

### Hash Chain Mechanism

Every audit log entry includes a cryptographic link to all previous entries via SHA-512 hashing:

**Hash computation:**

```
curr_hash = SHA-512(event_id || timestamp || sequence_number || actor || action || resource || result || details || prev_hash)
```

The first entry uses `prev_hash = SHA-512("GENESIS")`.

Each subsequent entry's `prev_hash` is the `curr_hash` of the immediately preceding entry, forming an unbroken chain. If any entry is modified, its `curr_hash` changes, which breaks the link to the next entry, making tampering detectable by walking the chain forward.

### Tamper Detection

The audit service provides a `validate_chain()` method that walks the entire chain from genesis, recomputing each entry's hash and verifying it matches the stored `curr_hash`. If any mismatch is found, the system reports the exact sequence number of the first tampered entry.

### Checkpoints

Every 1,000 entries, a checkpoint is stored in the `audit_checkpoints` table. Checkpoints enable partial validation (validate from last checkpoint instead of genesis) and provide external anchoring points for third-party verification.

### Logged Events

Every significant operation generates an audit entry, including: backup creation, restore requests and completions, policy evaluations, key operations (wrap, unwrap, rotate, destroy), authentication successes and failures, alert lifecycle events, incident level changes, configuration changes, and system health checks.

---

## 12. Monitoring & Detection Engine

### Monitoring Rules

| Rule | Name | Trigger | Severity | Incident Level |
|------|------|---------|----------|----------------|
| M1 | Failed Auth Brute Force | 5+ failed auth attempts from same source in 5 minutes | HIGH | 1 |
| M2 | Excessive Restore Rate | 10+ restores per API key per hour | HIGH | 1 |
| M3 | Restore Volume Spike | Restore volume 3× daily average | HIGH | 2 |
| M4 | Restore from New IP | Restore from IP never seen for this API key | MEDIUM | 1 |
| M5 | Key Unwrap Outside Business Hours | DEK unwrap request outside 08:00–18:00 | MEDIUM | 1 |
| M6 | Audit Log Tampering Attempt | Any attempt to modify or disable audit logging | CRITICAL | 2 |
| M7 | Failed Restore Attempts | 3+ failed restores in 10 minutes | HIGH | 2 |
| M8 | Bulk Backup Deletion | 5+ delete requests in 1 hour | CRITICAL | 2 |
| M9 | Policy Configuration Change | Any policy or role change | MEDIUM | 1 |
| M10 | Hash Chain Validation Failure | Audit log integrity check failed | CRITICAL | 3 |

### Alert Lifecycle

Alerts follow the lifecycle: **NEW → ACKNOWLEDGED → INVESTIGATING → RESOLVED** (or **ESCALATED** if auto-escalation triggers). Unacknowledged alerts auto-escalate after 15 minutes (configurable).

### Detection Mechanism

The monitoring service runs either periodically or is triggered on each audit event. It evaluates threshold-based rules (M1, M2, M7, M8) by counting matching events within sliding time windows, and event-based rules (M4, M5, M6, M9, M10) by analyzing individual events in context.

---

## 13. Incident Response Controller

### Incident Levels

| Level | Name | Trigger | Actions | Reversible |
|-------|------|---------|---------|------------|
| 0 | Normal | Default state | All operations normal | N/A |
| 1 | Alert | M1, M2, M4, M5, M9 alerts | Rate limits reduced to 50%; MFA required for ALL restores; enhanced logging | Yes (auto-reverts after 30 min) |
| 2 | Quarantine | M3, M6, M7, M8 alerts | All restores go to PENDING (require manual admin approval); DEK unwrap frozen; super_admins notified | Yes (manual de-escalation by admin) |
| 3 | Lockdown | M10 alert or manual crypto-shred | Crypto-shredding executed; all sessions blocked; system sealed | **No (IRREVERSIBLE)** |

### Escalation Flow

```
Level 0 (Normal)
    │
    ├── M1/M2/M4/M5/M9 → Level 1 (auto-revert 30 min)
    │                           │
    │                           ├── Additional M3/M6/M7/M8 → Level 2
    │                           │
    │                           └── Timeout → Level 0
    │
    ├── M3/M6/M7/M8 → Level 2 (manual de-escalation required)
    │                       │
    │                       ├── Admin de-escalates → Level 1 or 0
    │                       │
    │                       └── M10 or manual → Level 3 (PERMANENT)
    │
    └── M10 → Level 3 (PERMANENT — crypto-shredding executed)
```

### De-escalation Rules

Level 1 auto-reverts to Level 0 after 30 minutes if no additional alerts trigger. Level 2 requires explicit admin action to de-escalate. Level 3 cannot be de-escalated — it is permanent and irreversible.

---

## 14. Backup Workflow

### Step-by-Step Flow

**Step 1 — Authentication:** Client sends request with `X-API-Key` header. Gateway hashes the key with SHA-512 and looks up the hash in `api_keys` table. Verify the key is active, not expired, and IP is in allowed list.

**Step 2 — Policy Evaluation:** Policy engine evaluates backup permission based on caller's role, data classification, and current incident level (P1, P9).

**Step 3 — File Reception:** Gateway receives the file via multipart upload. For large files, the file is streamed in chunks (64 MB default).

**Step 4 — Checksum Computation:** Compute SHA-512 hash of the plaintext data.

**Step 5 — DEK Generation:** Generate a cryptographically secure random 32-byte DEK using `os.urandom(32)`.

**Step 6 — Encryption:** Encrypt the plaintext using AES-256-GCM with the DEK and a random 12-byte nonce. GCM mode produces ciphertext with an appended 16-byte authentication tag.

**Step 7 — Ciphertext Checksum:** Compute SHA-512 hash of the ciphertext.

**Step 8 — DEK Wrapping:** Wrap the DEK using ECIES with the active ECC public key (e.g., P-001). The DEK is encrypted and the plaintext DEK is immediately zeroed from memory.

**Step 9 — Upload to MinIO:** Upload two objects to the MinIO bucket: the ciphertext as `backups/{object_id}/data.enc` and the wrapped DEK as `backups/{object_id}/dek.wrapped`.

**Step 10 — Metadata Storage:** Store backup metadata in PostgreSQL including object_id, classification, checksums (SHA-512), storage path, key version, nonce, and status.

**Step 11 — Audit Logging:** Log `BACKUP_COMPLETE` event in the audit log with hash chain entry.

**Step 12 — Response:** Return backup_id, encrypted_size, checksums, and status to the client.

### Backup Flow Diagram

```
Client                    Gateway                   MinIO         PostgreSQL
  │                          │                        │               │
  │── POST /backup ─────────▶│                        │               │
  │   (file + metadata)      │                        │               │
  │                          │── SHA-512(plaintext) ──▶│               │
  │                          │── Generate DEK ────────▶│               │
  │                          │── AES-256-GCM encrypt ─▶│               │
  │                          │── SHA-512(ciphertext) ─▶│               │
  │                          │── ECIES wrap DEK ──────▶│               │
  │                          │                        │               │
  │                          │── PUT data.enc ────────▶│               │
  │                          │── PUT dek.wrapped ─────▶│               │
  │                          │                        │               │
  │                          │── INSERT metadata ─────────────────────▶│
  │                          │── INSERT audit_log ────────────────────▶│
  │                          │                        │               │
  │◀── 200 { backup_id } ───│                        │               │
```

---

## 15. Restore Workflow

### Step-by-Step Flow

**Step 1 — Authentication + MFA:** Client sends request with `X-API-Key` and `X-MFA-Token` headers. Both are validated. MFA is required for all restore operations; for CONFIDENTIAL and SECRET data, MFA is mandatory by policy.

**Step 2 — Policy Evaluation:** Policy engine evaluates restore permission based on role, classification, MFA status, business hours, per-key rate limit, system rate limit, and incident level (P2–P9).

**Step 3 — Incident Level Check:** If incident level is 2, the restore is set to PENDING and requires manual admin approval. If level is 3, the restore is denied outright.

**Step 4 — Fetch from MinIO:** Download the ciphertext (`data.enc`) and wrapped DEK (`dek.wrapped`) from the MinIO bucket.

**Step 5 — DEK Unwrapping:** Unwrap the DEK using ECIES with the ECC private key. This requires the private key to exist (not destroyed) and the correct password to decrypt the PEM file.

**Step 6 — Decryption:** Decrypt the ciphertext using AES-256-GCM with the unwrapped DEK and stored nonce. GCM automatically verifies the 16-byte authentication tag — if the ciphertext has been tampered with, decryption fails with `InvalidTag`.

**Step 7 — Integrity Verification:** Compute SHA-512 of the decrypted plaintext and compare with the stored `checksum_plaintext`. A mismatch indicates data corruption or tampering.

**Step 8 — Download Token:** Generate a time-limited download token (1 hour TTL) for the restored plaintext.

**Step 9 — Audit Logging:** Log `RESTORE_COMPLETE` event with hash chain entry.

**Step 10 — Response:** Return restore_id, status, and download URL to the client.

---

## 16. Crypto-Shredding Workflow

### Prerequisites

Crypto-shredding requires three simultaneous authorizations: super_admin role, valid MFA token, and a confirmation code matching the pattern `DESTROY-{key_version}`.

### Step-by-Step Flow

**Step 1 — Triple Authorization:** Verify super_admin role, MFA token, and confirmation code.

**Step 2 — Log Intent:** Audit log entry `CRYPTO_SHRED_START` with hash chain.

**Step 3 — Destroy Private Key:** Execute three-step secure deletion of the ECC private key file: overwrite with random bytes, flush to disk with fsync, then delete the file.

**Step 4 — Update Key Database:** Set key_versions.status = DESTROYED, record destroyed_at and destroyed_by.

**Step 5 — Mark Affected Backups:** Update all backup_metadata records where key_version matches the destroyed key to status = CRYPTO_SHREDDED.

**Step 6 — Escalate to Level 3:** Set system incident level to 3 (permanent lockdown).

**Step 7 — Final Audit:** Log `CRYPTO_SHRED_COMPLETE` with the list of affected backup IDs and destruction record.

### Post-Shredding State

After crypto-shredding, any attempt to restore an affected backup returns HTTP 410 with error code `CRYPTO_SHREDDED` and message "Backup keys destroyed — data permanently unrecoverable." The system remains in Level 3 permanently. The ciphertext remains in MinIO but is mathematically useless without the DEK, which cannot be unwrapped without the destroyed private key.

---

## 17. Authentication & Authorization

### API Key System

API keys follow the format `ssbg_{32 random hex chars}` (example: `ssbg_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`). Keys are generated using `secrets.token_hex(16)` for cryptographic randomness.

**Storage:** Only the SHA-512 hash of the key is stored in the database. The raw key is displayed once on creation and never stored or logged.

**Authentication flow:** Client provides key in `X-API-Key` header → Gateway computes `SHA-512(raw_key)` → Look up hash in `api_keys` table → Verify `is_active`, `expires_at`, `allowed_ips` → Update `last_used_at` and `last_used_ip`.

### MFA System

For operations requiring MFA (restore, crypto-shred), the client provides a token in the `X-MFA-Token` header. In the MVP, any non-empty token is accepted as valid. Production deployments should integrate TOTP verification (e.g., via `pyotp`).

### IP Whitelisting

API keys can optionally specify an `allowed_ips` array (PostgreSQL INET[] type). If set, only requests from listed IPs are accepted.

---

## 18. Storage Architecture

### MinIO Configuration

The MVP uses a single MinIO instance for all encrypted object storage:

| Setting | Value |
|---------|-------|
| Endpoint | minio:9000 (internal) |
| Console | minio:9001 (internal) |
| Bucket | ssbg-backups |
| Versioning | Enabled |
| Region | us-east-1 |
| SSL | Disabled (Docker internal network) |

### Object Layout

Each backup stores two objects in MinIO:

```
ssbg-backups/
└── backups/
    └── {object_id}/
        ├── data.enc          # AES-256-GCM ciphertext + auth tag
        └── dek.wrapped       # ECIES-wrapped DEK
```

### ECC Key Storage

ECC key pairs are stored on the gateway's filesystem (mounted via Docker volume):

```
keys/
└── primary/
    ├── P-001.private.pem     # Password-encrypted (PKCS8 + PBKDF2)
    ├── P-001.public.pem      # Plaintext PEM
    ├── P-002.private.pem     # Rotated key
    └── P-002.public.pem
```

Private key files are set to mode `0600` (owner read/write only).

---

## 19. Error Handling

### Error Code Registry

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| AUTH_INVALID_KEY | 401 | API key missing, invalid, expired, or revoked |
| AUTH_MFA_REQUIRED | 401 | Operation requires MFA verification |
| POLICY_DENIED | 403 | Policy engine denied the operation |
| BACKUP_NOT_FOUND | 404 | Backup object not found |
| RESTORE_NOT_FOUND | 404 | Restore request not found |
| RESTORE_QUARANTINED | 423 | Restores quarantined due to active incident |
| RATE_LIMITED | 429 | Rate limit exceeded |
| CRYPTO_SHREDDED | 410 | Backup keys destroyed — data permanently unrecoverable |
| KEY_UNAVAILABLE | 503 | Key manager unavailable or key destroyed |
| INTEGRITY_FAILURE | 500 | Data integrity verification failed |
| UPLOAD_FAILED | 500 | Encryption or storage upload failed |
| INTERNAL_ERROR | 500 | Internal server error |

---

## 20. Testing Strategy

### Security Test Cases

**ST1 — Unauthorized Restore:** Operator role attempts restore → Expected: 403 POLICY_DENIED.

**ST2 — Restore Without MFA on CONFIDENTIAL:** Admin attempts CONFIDENTIAL restore without MFA → Expected: 401 AUTH_MFA_REQUIRED.

**ST3 — Mass Restore Detection:** Send 15 rapid restore requests → Expected: Alert M2 triggers after 10th request, incident Level 1 activated.

**ST4 — Audit Log Tampering:** Directly modify a row in audit_log table, then call validate → Expected: `{"valid": false, "first_invalid_sequence": N}`.

**ST5 — No Plaintext in Transit:** Capture network traffic on Docker bridge during backup → Expected: No plaintext data visible in capture (only ciphertext flows to MinIO).

**ST6 — Crypto-Shred Execution:** Execute crypto-shred on key P-001 → Expected: Key file deleted, affected backups marked CRYPTO_SHREDDED, system Level 3.

**ST7 — Restore After Crypto-Shred:** Attempt restore of shredded backup → Expected: 410 CRYPTO_SHREDDED.

**ST8 — Hash Chain Integrity:** Create 100 audit entries, validate chain → Expected: `{"valid": true, "entries_checked": 100}`.

**ST9 — Rate Limiting:** Exceed per-key restore limit → Expected: 429 RATE_LIMITED.

**ST10 — Business Hours Enforcement:** Attempt restore at 03:00 → Expected: POLICY_DENIED with business hours message.

### Test Execution

```bash
# All tests
cd gateway && pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Integration tests
pytest tests/test_integration.py -v --timeout=120
```

---

## 21. Deployment & Configuration

### Docker Compose Deployment

```yaml
version: "3.9"
services:
  ssbg-gateway:
    build: ./gateway
    container_name: ssbg-gateway
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://ssbg:${POSTGRES_PASSWORD}@postgres:5432/ssbg
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - MINIO_BUCKET=ssbg-backups
      - ECC_PRIMARY_KEY_DIR=/app/keys/primary
      - ECC_KEY_PASSWORD=${ECC_KEY_PASSWORD}
    volumes:
      - ./keys:/app/keys
    depends_on:
      postgres: { condition: service_healthy }
      minio: { condition: service_healthy }
    networks: [ssbg-network]

  postgres:
    image: postgres:16-alpine
    container_name: ssbg-postgres
    environment:
      - POSTGRES_DB=ssbg
      - POSTGRES_USER=ssbg
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ssbg"]
      interval: 5s
    networks: [ssbg-network]

  minio:
    image: minio/minio:latest
    container_name: ssbg-minio
    ports: ["9000:9000", "9001:9001"]
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY}
    volumes: [minio-data:/data]
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
    networks: [ssbg-network]

volumes:
  pgdata:
  minio-data:

networks:
  ssbg-network:
    driver: bridge
```

### Environment Configuration

| Setting | Development | Production |
|---------|-------------|------------|
| LOG_LEVEL | DEBUG | INFO |
| ECC_KEY_PASSWORD | dev-password | Strong random (Docker secret) |
| POSTGRES_PASSWORD | devpassword | Strong random (Docker secret) |
| MINIO_SECRET_KEY | minioadmin | Strong random |
| business_hours_start | 0 (always open) | 8 |
| business_hours_end | 24 (always open) | 18 |
| max_restores_per_key_per_hour | 100 | 10 |
| alert_auto_escalate_minutes | 60 | 15 |
| audit_checkpoint_interval | 1000 | 1000 |

### Quick Start

```bash
# 1. Setup
cp .env.example .env    # Edit with strong passwords

# 2. Generate ECC keys
python scripts/generate_keys.py --primary P-001 --password "$ECC_KEY_PASSWORD"

# 3. Start
docker-compose up -d

# 4. Initialize
docker exec ssbg-gateway python scripts/init_db.py
docker exec ssbg-gateway python scripts/create_api_key.py --role super_admin --department "IT Security"

# 5. Test
curl http://localhost:8000/api/v1/health
```

---

## 22. Future Work

### Phase 2: Secondary MinIO Disaster Recovery

The current MVP uses a single MinIO instance. In a production deployment, a secondary MinIO instance with an independent ECC key lineage would provide disaster recovery capability, ensuring data remains recoverable even after crypto-shredding of the primary key.

**Architecture:** The secondary MinIO would run as a separate Docker container (`ssbg-minio-secondary`, ports 9002/9003) with its own data volume and independent ECC key lineage (S-001, S-002, etc.).

**Key Wrapping:** During backup, the same DEK would be wrapped twice — once with the primary ECC public key (P-xxx) and once with the secondary ECC public key (S-xxx). Both wrapped DEKs and the ciphertext would be uploaded to the respective MinIO instances.

**Crypto-Shredding Behavior:** When crypto-shredding destroys the primary key (P-xxx), the primary copy becomes unrecoverable. However, the secondary copy remains recoverable via the secondary key (S-xxx), providing a safety net for accidental key destruction or disaster recovery scenarios.

**Database Changes:** The `backup_metadata` table would add columns: `storage_path_secondary`, `wrapped_dek_path_secondary`, `key_version_secondary`, and `is_replicated`. The `key_type` enum already supports SECONDARY values.

**Implementation Estimate:** 3–5 days of additional development. The current architecture is designed to accommodate this extension through the `storage_service` abstraction layer, Alembic migration path, and Docker Compose extensibility.

### Additional Future Work

**TOTP MFA Integration:** Replace the MVP's any-non-empty-token MFA with proper TOTP verification using `pyotp`, supporting hardware tokens and authenticator apps.

**Web Dashboard:** A React-based admin dashboard for monitoring alerts, managing policies, viewing audit logs, and performing administrative actions without using curl commands.

**External Audit Chain Anchoring:** Periodically publish audit chain checkpoints to an external blockchain or public ledger for independent third-party verification.

**Certificate-Based Authentication:** Replace API key authentication with mutual TLS (mTLS) using client certificates issued by the organization's PKI.

**Backup Agent Enhancements:** Add support for incremental backups, compression, parallel uploads, scheduled automatic backups, and integration with system schedulers (cron, systemd timers).

---

*End of Document*
