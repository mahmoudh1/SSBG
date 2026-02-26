# SSBG — System Architecture Document

> **Secure Sovereign Backup Gateway**
> Complete Technical Architecture Reference

**Document Version:** 2.0  
**Date:** February 2025  
**Classification:** INTERNAL  
**Status:** Final  
**Audience:** Development Team, Evaluators, Technical Reviewers

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Design Principles](#2-design-principles)
3. [System Context & Boundaries](#3-system-context--boundaries)
4. [Container Architecture](#4-container-architecture)
5. [Network Architecture](#5-network-architecture)
6. [Application Architecture (Gateway)](#6-application-architecture-gateway)
7. [Layered Architecture & Dependency Flow](#7-layered-architecture--dependency-flow)
8. [Cryptographic Architecture](#8-cryptographic-architecture)
   - 8.1 [Cryptographic Primitives](#81-cryptographic-primitives)
   - 8.2 [Key Hierarchy & Lifecycle](#82-key-hierarchy--lifecycle)
   - 8.3 [ECIES Key Wrapping — Deep Dive](#83-ecies-key-wrapping--deep-dive)
   - 8.4 [AES-256-GCM Encryption — Deep Dive](#84-aes-256-gcm-encryption--deep-dive)
   - 8.5 [Streaming Encryption for Large Files](#85-streaming-encryption-for-large-files)
   - 8.6 [SHA-512 Hashing Strategy](#86-sha-512-hashing-strategy)
   - 8.7 [Crypto-Shredding — Mathematical Guarantee](#87-crypto-shredding--mathematical-guarantee)
9. [Data Architecture](#9-data-architecture)
   - 9.1 [Entity-Relationship Model](#91-entity-relationship-model)
   - 9.2 [Table Definitions & Indexing Strategy](#92-table-definitions--indexing-strategy)
   - 9.3 [Enumeration Types](#93-enumeration-types)
   - 9.4 [Data Flow Through Tables](#94-data-flow-through-tables)
10. [API Architecture](#10-api-architecture)
    - 10.1 [REST API Design](#101-rest-api-design)
    - 10.2 [Endpoint Catalog](#102-endpoint-catalog)
    - 10.3 [Request/Response Schemas](#103-requestresponse-schemas)
    - 10.4 [Error Handling Contract](#104-error-handling-contract)
11. [Security Architecture](#11-security-architecture)
    - 11.1 [Authentication System](#111-authentication-system)
    - 11.2 [Authorization & RBAC](#112-authorization--rbac)
    - 11.3 [Policy Engine Architecture](#113-policy-engine-architecture)
    - 11.4 [Defense-in-Depth Layers](#114-defense-in-depth-layers)
12. [Audit & Compliance Architecture](#12-audit--compliance-architecture)
    - 12.1 [Hash Chain Design](#121-hash-chain-design)
    - 12.2 [Chain Validation Algorithm](#122-chain-validation-algorithm)
    - 12.3 [Checkpoint System](#123-checkpoint-system)
    - 12.4 [Audited Events Catalog](#124-audited-events-catalog)
13. [Threat Detection & Monitoring Architecture](#13-threat-detection--monitoring-architecture)
    - 13.1 [Rule Engine Design](#131-rule-engine-design)
    - 13.2 [Detection Rules Catalog](#132-detection-rules-catalog)
    - 13.3 [Alert Lifecycle](#133-alert-lifecycle)
14. [Incident Response Architecture](#14-incident-response-architecture)
    - 14.1 [Four-Level Escalation Model](#141-four-level-escalation-model)
    - 14.2 [Escalation State Machine](#142-escalation-state-machine)
    - 14.3 [Per-Level System Behavior](#143-per-level-system-behavior)
15. [Storage Architecture](#15-storage-architecture)
    - 15.1 [MinIO Object Storage Design](#151-minio-object-storage-design)
    - 15.2 [Object Layout & Naming](#152-object-layout--naming)
    - 15.3 [ECC Key Filesystem Layout](#153-ecc-key-filesystem-layout)
16. [Workflow Architecture](#16-workflow-architecture)
    - 16.1 [Backup Workflow — Complete Flow](#161-backup-workflow--complete-flow)
    - 16.2 [Restore Workflow — Complete Flow](#162-restore-workflow--complete-flow)
    - 16.3 [Crypto-Shredding Workflow — Complete Flow](#163-crypto-shredding-workflow--complete-flow)
    - 16.4 [Key Rotation Workflow](#164-key-rotation-workflow)
    - 16.5 [Authentication Workflow](#165-authentication-workflow)
17. [Configuration Architecture](#17-configuration-architecture)
18. [Deployment Architecture](#18-deployment-architecture)
    - 18.1 [Docker Compose Topology](#181-docker-compose-topology)
    - 18.2 [Container Specifications](#182-container-specifications)
    - 18.3 [Volume Management](#183-volume-management)
    - 18.4 [Health Check Strategy](#184-health-check-strategy)
    - 18.5 [Startup & Dependency Ordering](#185-startup--dependency-ordering)
19. [Resilience & Failure Handling](#19-resilience--failure-handling)
20. [Threat Model](#20-threat-model)
21. [Technology Decisions & Rationale](#21-technology-decisions--rationale)
22. [Future Architecture Evolution](#22-future-architecture-evolution)

---

## 1. Architecture Overview

SSBG is a self-hosted, sovereign-grade encrypted backup gateway that implements a defense-in-depth security architecture. The system provides seven core capabilities:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SSBG Core Capabilities                          │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Client-Side │  │    HYOK     │  │   Tamper-   │                │
│  │  Encryption  │  │    Key Mgmt │  │   Evident   │                │
│  │  (AES-256-  │  │  (ECIES +   │  │   Audit Log │                │
│  │   GCM)      │  │  SECP384R1) │  │  (SHA-512   │                │
│  │             │  │             │  │   chain)    │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐│
│  │  Policy     │  │   Threat    │  │  Incident   │  │  Crypto-  ││
│  │  Engine     │  │  Detection  │  │  Response   │  │  Shredding││
│  │  (RBAC +    │  │  (10 Rules, │  │  (4 Levels, │  │  (Key     ││
│  │  classific.)│  │  real-time) │  │  automated) │  │  destroy) ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

The system follows a monolithic gateway architecture where a single FastAPI application orchestrates all business logic, communicating with PostgreSQL for metadata/state and MinIO for encrypted object storage. All three components are containerized and orchestrated via Docker Compose.

---

## 2. Design Principles

The architecture is governed by the following principles, listed in priority order:

**DP1 — Zero-Trust Key Management:** No component, service, or administrator should be able to access plaintext backup data without explicitly holding the correct private key AND passing policy evaluation. The system assumes every actor is potentially compromised.

**DP2 — Encryption Before Storage:** Plaintext data must never exist on persistent storage. Data is encrypted in the gateway's memory before being written to MinIO. The DEK exists in memory only during the encrypt/decrypt operation and is immediately zeroed afterward.

**DP3 — Cryptographic Auditability:** Every state-changing operation must be recorded in the tamper-evident audit log. The hash chain provides a mathematical proof that the log has not been modified since creation. Any single bit change in any entry invalidates the entire chain from that point forward.

**DP4 — Least Privilege Access:** The policy engine enforces the principle that every operation requires the minimum set of credentials. Restore requires strictly higher trust than backup. SECRET data requires the highest role plus MFA. Crypto-shredding requires the highest role, MFA, and explicit confirmation.

**DP5 — Fail-Secure:** When any component fails or an anomaly is detected, the system restricts access rather than permitting it. Unknown states default to deny. Monitoring alerts escalate the incident level, which reduces system capability rather than expanding it.

**DP6 — Irreversible Destruction:** Crypto-shredding is a one-way operation. Once a key is destroyed, no mechanism exists to recover it. This is by design — the system must guarantee that "destroyed" means "permanently irrecoverable" with mathematical certainty.

**DP7 — Simplicity Over Complexity:** The MVP uses the minimum number of components needed to demonstrate all security properties. A single MinIO instance proves the encryption and crypto-shredding model without the operational complexity of replication.

---

## 3. System Context & Boundaries

### System Context Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           External Environment                           │
│                                                                          │
│  ┌──────────────────┐         ┌──────────────────┐                      │
│  │  Government       │         │  Admin User       │                      │
│  │  Source System     │         │  (Browser / CLI)  │                      │
│  │                    │         │                    │                      │
│  │  Runs Backup      │         │  Manages policies, │                      │
│  │  Agent CLI         │         │  keys, alerts,     │                      │
│  │                    │         │  crypto-shred       │                      │
│  └────────┬───────────┘         └────────┬───────────┘                      │
│           │ HTTPS :8000                   │ HTTPS :8000                      │
│           │ X-API-Key                     │ X-API-Key + X-MFA-Token          │
│           ▼                               ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     SSBG System Boundary                            │    │
│  │                     (Docker Compose)                                 │    │
│  │                                                                      │    │
│  │  ┌────────────────────────────────────────────────────────────────┐ │    │
│  │  │                      ssbg-gateway                               │ │    │
│  │  │                      FastAPI :8000                               │ │    │
│  │  │                                                                  │ │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐ │ │    │
│  │  │  │ Encrypt  │ │ Key Mgr  │ │ Policy   │ │ Audit + Monitor + │ │ │    │
│  │  │  │ Service  │ │ (ECIES)  │ │ Engine   │ │ Response Ctrl     │ │ │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘ │ │    │
│  │  └──────────────────┬────────────────┬────────────────────────────┘ │    │
│  │                     │                │                               │    │
│  │              ┌──────▼──────┐  ┌──────▼──────┐                       │    │
│  │              │  PostgreSQL │  │    MinIO     │                       │    │
│  │              │    :5432    │  │   :9000      │                       │    │
│  │              │             │  │              │                       │    │
│  │              │ Metadata,   │  │ Encrypted    │                       │    │
│  │              │ Audit Logs, │  │ blobs +      │                       │    │
│  │              │ Policies,   │  │ Wrapped DEKs │                       │    │
│  │              │ Alerts      │  │              │                       │    │
│  │              └─────────────┘  └──────────────┘                       │    │
│  │                                                                      │    │
│  │  ┌─────────────────────────────────────────────────┐                │    │
│  │  │  keys/primary/                                   │                │    │
│  │  │  P-001.private.pem  (password-encrypted)         │                │    │
│  │  │  P-001.public.pem                                │                │    │
│  │  │  (Host filesystem, mounted via Docker volume)    │                │    │
│  │  └─────────────────────────────────────────────────┘                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Trust Boundaries

**Boundary 1 — External Network → Gateway:** All external communication enters through port 8000. Every request must carry a valid API key. This is the primary attack surface.

**Boundary 2 — Gateway → PostgreSQL:** Internal Docker network only. No external access. The gateway uses parameterized queries via SQLAlchemy ORM to prevent SQL injection.

**Boundary 3 — Gateway → MinIO:** Internal Docker network only. No external access. Only encrypted data (ciphertext + wrapped DEKs) crosses this boundary. Plaintext never touches MinIO.

**Boundary 4 — Gateway → Filesystem (Keys):** The ECC private keys are the most sensitive assets. They are stored on the host filesystem, mounted read/write into the gateway container. Private keys are encrypted with a password via PKCS8/PBKDF2.

### What SSBG Is NOT

SSBG is not a general-purpose file storage system — it is purpose-built for sovereign backup with cryptographic lifecycle control. It does not handle user authentication federation (no LDAP/SAML) in the MVP, does not provide a web UI in the MVP, and does not manage network security beyond Docker network isolation.

---

## 4. Container Architecture

### Container Inventory

```
┌─────────────────────────────────────────────────────────┐
│                  Docker Compose Stack                     │
│                  Network: ssbg-network                    │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  ssbg-gateway                                        │ │
│  │  Image: Custom (Python 3.11-slim)                    │ │
│  │  Port: 8000 → host                                   │ │
│  │  Volumes: ./keys:/app/keys                           │ │
│  │  Depends: postgres (healthy), minio (healthy)        │ │
│  │  Restart: unless-stopped                              │ │
│  │  Memory: ~256 MB base + upload buffer                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  ssbg-postgres                                       │ │
│  │  Image: postgres:16-alpine                           │ │
│  │  Port: 5432 (internal only)                          │ │
│  │  Volumes: pgdata:/var/lib/postgresql/data            │ │
│  │  Healthcheck: pg_isready -U ssbg (5s interval)      │ │
│  │  Restart: unless-stopped                              │ │
│  │  Memory: ~128 MB                                      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  ssbg-minio                                          │ │
│  │  Image: minio/minio:latest                           │ │
│  │  Ports: 9000 (API), 9001 (Console)                   │ │
│  │  Volumes: minio-data:/data                           │ │
│  │  Healthcheck: mc ready local (10s interval)          │ │
│  │  Restart: unless-stopped                              │ │
│  │  Memory: ~256 MB                                      │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  Volumes: pgdata, minio-data (Docker managed)           │
└─────────────────────────────────────────────────────────┘
```

### Container Responsibilities

| Container | Stores | Processes | Exposes |
|-----------|--------|-----------|---------|
| ssbg-gateway | Nothing persistent (stateless) | Encryption, key wrapping, policy eval, monitoring | REST API on :8000 |
| ssbg-postgres | Metadata, audit logs, policies, alerts, system state | SQL queries, transactions | Nothing external |
| ssbg-minio | Encrypted ciphertext blobs, wrapped DEK blobs | S3-compatible object operations | Console on :9001 (optional) |

### Data Residency

| Data Type | Resides In | Format | Encrypted |
|-----------|-----------|--------|-----------|
| Plaintext backup data | Gateway memory ONLY (transient) | Raw bytes | No (in-memory only) |
| Ciphertext | MinIO | AES-256-GCM encrypted | Yes |
| Wrapped DEK | MinIO | ECIES-encrypted blob | Yes |
| DEK (unwrapped) | Gateway memory ONLY (transient) | 32 raw bytes | No (in-memory only) |
| ECC private key | Host filesystem (Docker volume) | PEM, password-encrypted | Yes (PKCS8+PBKDF2) |
| ECC public key | Host filesystem + PostgreSQL | PEM plaintext | No (public by design) |
| API key (raw) | Shown once to user, never stored | `ssbg_{hex}` | N/A |
| API key (hash) | PostgreSQL | SHA-512 hex string | Hashed (one-way) |
| Backup metadata | PostgreSQL | Structured rows | No (metadata only) |
| Audit log entries | PostgreSQL | Structured rows + SHA-512 hashes | Hash-chained |
| Nonce (GCM) | PostgreSQL (backup_metadata.nonce) | 12 bytes (BYTEA) | No (safe to store publicly) |

---

## 5. Network Architecture

### Network Topology

```
                    Host Machine
                    ┌─────────────────────────────────────────────────┐
                    │                                                  │
                    │   External Network                               │
                    │   ┌───────────────────────────────────┐         │
 Client ────────────┼──▶│ Port 8000 (Gateway API)            │         │
                    │   │ Port 9001 (MinIO Console, optional)│         │
                    │   └────────────────┬──────────────────┘         │
                    │                    │                              │
                    │   Docker Bridge: ssbg-network (172.x.0.0/16)    │
                    │   ┌────────────────┴──────────────────────────┐  │
                    │   │                                           │  │
                    │   │  gateway ◄──────► postgres               │  │
                    │   │  172.x.0.2       172.x.0.3               │  │
                    │   │     │                                     │  │
                    │   │     └────────────► minio                 │  │
                    │   │                   172.x.0.4               │  │
                    │   │                                           │  │
                    │   └───────────────────────────────────────────┘  │
                    │                                                  │
                    └─────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Internal Port | Host Port | Protocol | Access |
|---------|--------------|-----------|----------|--------|
| ssbg-gateway | 8000 | 8000 | HTTP (REST) | External — client-facing |
| ssbg-postgres | 5432 | Not exposed | TCP (PostgreSQL) | Internal only |
| ssbg-minio API | 9000 | Not exposed (production) | HTTP (S3) | Internal only |
| ssbg-minio Console | 9001 | 9001 (dev only) | HTTP (Web UI) | Optional — debug |

### Network Security Properties

**Isolation:** PostgreSQL and MinIO are only reachable from within the Docker bridge network. An external attacker who compromises the host network cannot directly connect to the database or object store.

**Encrypted Data in Transit (Internal):** While internal Docker network traffic is unencrypted (HTTP), only ciphertext flows between the gateway and MinIO. An attacker who captures internal traffic sees encrypted blobs, not plaintext.

**No Plaintext on Wire:** The backup plaintext exists only in the gateway's process memory. It enters the gateway via the client's HTTP POST, is encrypted in memory, and the ciphertext is sent to MinIO. The plaintext never traverses the Docker network.

**Single Entry Point:** Port 8000 is the only external-facing entry point. All access control, authentication, authorization, rate limiting, and monitoring happen at this single point.

---

## 6. Application Architecture (Gateway)

### Full Directory Structure

```
gateway/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── alembic/
│   └── versions/                    # Database migration scripts
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry, lifespan, router mounts
│   ├── config.py                    # Pydantic Settings (env-based config)
│   ├── dependencies.py              # Auth dependency injection
│   │
│   ├── api/                         # HTTP route handlers (thin controllers)
│   │   ├── __init__.py
│   │   ├── health.py                # GET /health, GET /health/detailed
│   │   ├── backup.py                # POST /backup, GET /backup/{id}, GET /backups
│   │   ├── restore.py               # POST /restore, GET /restore/{id}/status, download
│   │   └── admin.py                 # Policies, keys, audit, alerts, crypto-shred
│   │
│   ├── models/                      # SQLAlchemy ORM models (1:1 with tables)
│   │   ├── __init__.py
│   │   ├── api_key.py               # ApiKey model
│   │   ├── backup_metadata.py       # BackupMetadata model
│   │   ├── key_version.py           # KeyVersion model
│   │   ├── audit_log.py             # AuditLog + AuditCheckpoint models
│   │   ├── policy.py                # Policy model
│   │   ├── alert.py                 # Alert model
│   │   ├── restore_request.py       # RestoreRequest model
│   │   └── system_state.py          # SystemState model
│   │
│   ├── schemas/                     # Pydantic request/response validation
│   │   ├── __init__.py
│   │   ├── common.py                # Enums, envelopes, pagination
│   │   ├── backup.py                # BackupCreate, BackupResponse
│   │   ├── restore.py               # RestoreRequest, RestoreResponse
│   │   ├── admin.py                 # Policy, key, alert schemas
│   │   └── audit.py                 # AuditLog query/response schemas
│   │
│   ├── services/                    # Business logic layer (core domain)
│   │   ├── __init__.py
│   │   ├── encryption_service.py    # AES-256-GCM encrypt/decrypt + streaming
│   │   ├── key_manager.py           # ECC key generation, ECIES wrap/unwrap, destroy
│   │   ├── storage_service.py       # MinIO upload/download via S3 API
│   │   ├── policy_engine.py         # Policy Decision Point (PDP)
│   │   ├── audit_service.py         # Hash chain append + validation
│   │   ├── monitoring_service.py    # Rule evaluation + alert creation
│   │   ├── response_controller.py   # Incident level escalation/de-escalation
│   │   └── backup_service.py        # Orchestrator: coordinates full backup/restore
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py               # Async engine, session factory, get_db()
│   │   └── base.py                  # SQLAlchemy declarative base
│   │
│   └── utils/
│       ├── __init__.py
│       ├── hashing.py               # SHA-512 helper functions
│       ├── streaming.py             # Chunked file I/O utilities
│       └── errors.py                # SSBGError, error codes, response builders
│
└── tests/
    ├── conftest.py                  # Test fixtures: DB, client, keys
    ├── test_backup.py
    ├── test_restore.py
    ├── test_encryption.py
    ├── test_key_manager.py
    ├── test_policy_engine.py
    ├── test_audit_log.py
    ├── test_monitoring.py
    ├── test_response_controller.py
    └── test_integration.py          # End-to-end workflow tests
```

### Backup Agent (Separate Component)

```
agent/
├── Dockerfile                       # Optional — can run on host
├── requirements.txt
├── ssbg_agent.py                    # CLI entry point (click-based)
├── config.yaml.example              # Sample configuration
└── tests/
    └── test_agent.py
```

---

## 7. Layered Architecture & Dependency Flow

The gateway follows a strict layered architecture where each layer only depends on the layer directly below it:

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: API Layer (app/api/)                                       │
│  Thin controllers — HTTP routing, request parsing, response building │
│  Depends on: Services, Schemas, Dependencies                         │
│  Files: health.py, backup.py, restore.py, admin.py                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ calls
┌─────────────────────────────────▼───────────────────────────────────┐
│  LAYER 2: Service Layer (app/services/)                              │
│  Core business logic — encryption, key ops, policy, audit, monitor   │
│  Depends on: Models, DB Session, Config                              │
│  Files: encryption_service.py, key_manager.py, policy_engine.py,    │
│         audit_service.py, monitoring_service.py, response_controller │
│         storage_service.py, backup_service.py                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ reads/writes
┌─────────────────────────────────▼───────────────────────────────────┐
│  LAYER 3: Data Layer (app/models/ + app/db/)                         │
│  ORM models + async database sessions                                │
│  Depends on: SQLAlchemy, asyncpg, PostgreSQL                         │
│  Files: All model files, session.py, base.py                         │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ connects to
┌─────────────────────────────────▼───────────────────────────────────┐
│  LAYER 4: Infrastructure (Docker containers)                         │
│  PostgreSQL, MinIO, Host Filesystem (keys)                           │
│  Managed by: Docker Compose                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Service Dependency Graph

```
backup_service.py (orchestrator)
├── encryption_service.py          # Encrypt/decrypt data
├── key_manager.py                 # Wrap/unwrap DEK, generate/destroy keys
├── storage_service.py             # Upload/download to MinIO
├── policy_engine.py               # Evaluate access policies
├── audit_service.py               # Log events to hash chain
├── monitoring_service.py          # Check detection rules
│   └── audit_service.py           # Queries audit log for pattern detection
└── response_controller.py         # Manage incident levels
    └── audit_service.py           # Log escalation events
```

### Request Processing Pipeline

Every incoming request passes through a consistent pipeline:

```
HTTP Request
    │
    ▼
┌──────────────────┐
│ 1. FastAPI Router │  Route matching, request parsing
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. Dependency     │  API key authentication (SHA-512 hash lookup)
│    Injection      │  MFA validation (if required)
│                   │  IP whitelist check
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 3. Policy Engine  │  RBAC check, classification check, rate limit,
│                   │  time window, incident level
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. Business Logic │  Encryption, key operations, storage operations
│    (Services)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 5. Audit Logging  │  Hash chain entry for the operation
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 6. Monitoring     │  Check if operation triggers any detection rules
│    Evaluation     │  Create alerts if thresholds exceeded
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 7. Response       │  Standard JSON envelope with request_id
│    Building       │
└──────────────────┘
```

---

## 8. Cryptographic Architecture

### 8.1 Cryptographic Primitives

| Primitive | Algorithm | Standard | Key/Output Size | Usage in SSBG |
|-----------|-----------|----------|-----------------|----------------|
| Symmetric Encryption | AES-256-GCM | NIST SP 800-38D | 256-bit key, 128-bit tag, 96-bit nonce | Backup data encryption |
| Asymmetric Encryption | ECIES | IEEE 1363a | SECP384R1 (384-bit curve) | DEK wrapping/unwrapping |
| Key Agreement | ECDH | NIST SP 800-56A | Shared secret from curve | Part of ECIES wrapping |
| Key Derivation | HKDF-SHA256 | RFC 5869 | 256-bit output | ECDH shared secret → AES key |
| Cryptographic Hash | SHA-512 | FIPS 180-4 | 512-bit / 128 hex chars | Audit chain, checksums, key hashing |
| Random Generation | os.urandom() | System CSPRNG | Variable | DEK, nonce, API key generation |

### 8.2 Key Hierarchy & Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    KEY HIERARCHY                                  │
│                                                                   │
│  Level 0: ECC Master Key Pair (long-lived)                       │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Version: P-001  │  Curve: SECP384R1  │  Status: ACTIVE  │    │
│  │                                                           │    │
│  │  Private Key: /keys/primary/P-001.private.pem             │    │
│  │    → Encrypted with PKCS8 + PBKDF2 (password-protected)  │    │
│  │    → File permissions: 0600 (owner only)                  │    │
│  │    → THIS IS THE MOST SENSITIVE ASSET IN THE SYSTEM       │    │
│  │                                                           │    │
│  │  Public Key: /keys/primary/P-001.public.pem               │    │
│  │    → Also stored in key_versions.public_key_pem           │    │
│  │    → Safe to distribute (used only for wrapping)          │    │
│  └──────────────────────────────────────────────────────────┘    │
│       │                                                           │
│       │ ECIES wraps (public key) / unwraps (private key)         │
│       ▼                                                           │
│  Level 1: Data Encryption Key — DEK (per-object, ephemeral)     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Size: 32 bytes (256 bits)                                │    │
│  │  Generated: os.urandom(32) per backup                     │    │
│  │  Lifetime: Exists in memory ONLY during encrypt/decrypt   │    │
│  │  Storage: NEVER stored in plaintext                       │    │
│  │           Stored as ECIES-wrapped blob in MinIO            │    │
│  └──────────────────────────────────────────────────────────┘    │
│       │                                                           │
│       │ AES-256-GCM encrypts (DEK + nonce → ciphertext + tag)   │
│       ▼                                                           │
│  Level 2: Encrypted Backup Data (persistent)                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Format: AES-256-GCM ciphertext + 16-byte auth tag       │    │
│  │  Storage: MinIO at backups/{object_id}/data.enc           │    │
│  │  Nonce: Stored in PostgreSQL backup_metadata.nonce        │    │
│  │         (12 bytes, safe to store alongside ciphertext)    │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Key Lifecycle State Machine

```
                generate_key_pair()
                       │
                       ▼
                ┌──────────────┐
                │    ACTIVE    │ ◄── Current key for new backups
                └──────┬───────┘
                       │ rotate_key()
                       ▼
                ┌──────────────┐
                │   RETIRED    │ ◄── Still available for unwrapping
                │              │     existing DEKs, but not used
                └──────┬───────┘     for new wrapping operations
                       │ destroy_key() [IRREVERSIBLE]
                       ▼
                ┌──────────────┐
                │  DESTROYED   │ ◄── Private key file securely deleted
                │              │     All associated backups are now
                └──────────────┘     PERMANENTLY IRRECOVERABLE
```

### 8.3 ECIES Key Wrapping — Deep Dive

ECIES (Elliptic Curve Integrated Encryption Scheme) wraps the DEK using the recipient's public key. The process is:

```
WRAP (encrypt DEK with public key):
═══════════════════════════════════

Input: DEK (32 bytes), Recipient Public Key (P-001)

Step 1: Generate ephemeral key pair
  ephemeral_private = random EC key on SECP384R1
  ephemeral_public  = ephemeral_private.public_key()

Step 2: ECDH key agreement
  shared_secret = ECDH(ephemeral_private, recipient_public_key)
  // shared_secret is a point on the curve, ~48 bytes

Step 3: Key derivation (HKDF)
  derived_key = HKDF-SHA256(
    ikm    = shared_secret,
    salt   = None,
    info   = b"SSBG-DEK-WRAP-v1",
    length = 32  // AES-256
  )

Step 4: Encrypt DEK
  nonce = os.urandom(12)  // 96-bit GCM nonce
  encrypted_dek = AES-256-GCM.encrypt(derived_key, nonce, DEK)
  // encrypted_dek includes 16-byte auth tag

Step 5: Serialize
  ephemeral_pub_bytes = ephemeral_public.to_X962_uncompressed()
  wrapped_dek = [2-byte len(ephemeral_pub_bytes)]
              + [ephemeral_pub_bytes]  // ~97 bytes for P-384
              + [12-byte nonce]
              + [encrypted_dek]        // 32 + 16 = 48 bytes

Output: wrapped_dek (~159 bytes)


UNWRAP (decrypt DEK with private key):
═══════════════════════════════════════

Input: wrapped_dek, Recipient Private Key (P-001)

Step 1: Deserialize
  Parse pubkey_len, ephemeral_pub_bytes, nonce, encrypted_dek

Step 2: Reconstruct ephemeral public key
  ephemeral_public = EC.from_encoded_point(SECP384R1, ephemeral_pub_bytes)

Step 3: ECDH key agreement
  shared_secret = ECDH(recipient_private_key, ephemeral_public)

Step 4: Key derivation (same HKDF parameters)
  derived_key = HKDF-SHA256(shared_secret, None, b"SSBG-DEK-WRAP-v1", 32)

Step 5: Decrypt DEK
  DEK = AES-256-GCM.decrypt(derived_key, nonce, encrypted_dek)
  // GCM automatically verifies auth tag

Output: DEK (32 bytes)
```

### 8.4 AES-256-GCM Encryption — Deep Dive

GCM (Galois/Counter Mode) provides both confidentiality and authenticity in a single operation:

**Properties:**
- Encryption: AES-256 in CTR mode (confidentiality)
- Authentication: GHASH over ciphertext (integrity + authenticity)
- Output: ciphertext (same length as plaintext) + 16-byte authentication tag
- Nonce: 12 bytes (96 bits), must be unique per DEK usage

**Why GCM over CTR:** CTR mode provides encryption only — an attacker can flip bits in the ciphertext and the corresponding bits in the plaintext will flip (malleability attack). GCM adds a 16-byte authentication tag that detects any modification to the ciphertext. If even one bit is changed, `AESGCM.decrypt()` raises `InvalidTag` and refuses to output any plaintext.

**Nonce uniqueness guarantee:** Since each backup object gets a unique DEK generated with `os.urandom(32)`, nonce reuse across different objects is not a security concern (different key = different keystream regardless of nonce). Within a single object's streaming encryption, nonce uniqueness is guaranteed by XOR-ing the base nonce with a chunk counter.

### 8.5 Streaming Encryption for Large Files

For files larger than available memory, SSBG uses chunked encryption:

```
Input File (e.g., 500 MB)
    │
    │ read in 64 MB chunks
    ▼
┌─────────────────────────────────────────────────┐
│ Chunk 0: base_nonce XOR 0 → nonce_0             │
│   encrypted_chunk_0 = AES-GCM(DEK, nonce_0, chunk_0) │
│                                                       │
│ Chunk 1: base_nonce XOR 1 → nonce_1             │
│   encrypted_chunk_1 = AES-GCM(DEK, nonce_1, chunk_1) │
│                                                       │
│ ...                                              │
│                                                       │
│ Chunk N: base_nonce XOR N → nonce_N             │
│   encrypted_chunk_N = AES-GCM(DEK, nonce_N, chunk_N) │
└─────────────────────────────────────────────────┘
    │
    ▼
Output Format:
  [4-byte chunk_0 length][encrypted_chunk_0]
  [4-byte chunk_1 length][encrypted_chunk_1]
  ...
  [4-byte chunk_N length][encrypted_chunk_N]
  [4-byte zero]  ← terminator
```

The per-chunk nonce derivation ensures unique nonces while sharing a single DEK across all chunks:

```python
def _derive_chunk_nonce(base_nonce: bytes, chunk_index: int) -> bytes:
    index_bytes = chunk_index.to_bytes(12, "big")
    return bytes(a ^ b for a, b in zip(base_nonce, index_bytes))
```

### 8.6 SHA-512 Hashing Strategy

SHA-512 is used uniformly across the entire system:

| Usage | Input | Output | Stored In |
|-------|-------|--------|-----------|
| Audit hash chain | `event_id \|\| timestamp \|\| sequence_number \|\| actor \|\| action \|\| resource \|\| result \|\| details \|\| prev_hash` | 128 hex chars | audit_log.curr_hash |
| API key hashing | Raw API key string (`ssbg_...`) | 128 hex chars | api_keys.key_hash |
| Plaintext checksum | Raw plaintext bytes | 128 hex chars | backup_metadata.checksum_plaintext |
| Ciphertext checksum | Encrypted ciphertext bytes | 128 hex chars | backup_metadata.checksum_ciphertext |
| Genesis hash | String `"GENESIS"` | 128 hex chars | First audit entry's prev_hash |

**Why SHA-512 over SHA-256:**

- 256-bit collision resistance (vs SHA-256's 128-bit)
- Faster on 64-bit processors (operates on 64-bit words natively)
- Single algorithm across entire system eliminates confusion
- All VARCHAR fields use 128 characters consistently

### 8.7 Crypto-Shredding — Mathematical Guarantee

Crypto-shredding achieves permanent data destruction through key destruction:

```
BEFORE crypto-shredding:
  Data recovery path exists:
    P-001.private.pem → ECDH → derive key → unwrap DEK → decrypt data ✓

DURING crypto-shredding (3-step secure deletion):
  1. Overwrite P-001.private.pem with os.urandom(file_size)
  2. Flush to disk: os.fsync(fd)
  3. Delete file: os.unlink(path)

AFTER crypto-shredding:
  Data recovery path is BROKEN:
    P-001.private.pem → FILE DOES NOT EXIST
      → Cannot perform ECDH
        → Cannot derive wrapping key
          → Cannot unwrap DEK
            → Cannot decrypt ciphertext
              → Data is PERMANENTLY IRRECOVERABLE ✗

  The ciphertext in MinIO is now indistinguishable from random noise.
  Without the DEK, a brute-force attack on AES-256 requires 2^256 operations
  (estimated heat death of the universe × 10^40 at current computational capacity).
```

---

## 9. Data Architecture

### 9.1 Entity-Relationship Model

```
                                 ┌────────────────┐
                                 │  system_state   │
                                 │  (incident lvl) │
                                 └────────────────┘

┌────────────┐     creates     ┌──────────────────┐     encrypts with    ┌────────────────┐
│  api_keys   │───────────────▶│ backup_metadata   │◄───────────────────▶│  key_versions   │
│             │                │                    │                     │                  │
│  key_hash   │                │  object_id         │                     │  version_id      │
│  role       │                │  classification    │                     │  key_type        │
│  department │                │  checksum_*        │                     │  status          │
│  is_active  │                │  storage_path      │                     │  public_key_pem  │
└──────┬──────┘                │  key_version ──────┼────────────────────▶│  private_key_path│
       │                       └──────────┬─────────┘                     └────────────────┘
       │ performs                          │
       │                                  │ target of
       ▼                                  ▼
┌──────────────────┐           ┌──────────────────┐
│   audit_log       │           │ restore_requests  │
│                    │           │                    │
│  event_id          │           │  restore_id        │
│  sequence_number   │           │  backup_id         │
│  action            │           │  requested_by      │
│  prev_hash ────────┼──chain──▶│  justification     │
│  curr_hash         │           │  status            │
└──────────┬─────────┘           │  download_token    │
           │                     └──────────────────┘
           │ checkpoint every 1000
           ▼
┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│ audit_checkpoints │           │    policies       │           │     alerts        │
│                    │           │                    │           │                    │
│  sequence_number   │           │  policy_id         │           │  alert_id          │
│  curr_hash         │           │  name              │           │  rule_id           │
└──────────────────┘           │  rule_json         │           │  severity          │
                                │  priority          │           │  incident_level    │
                                └──────────────────┘           │  status            │
                                                                └──────────────────┘
                                                    ┌──────────────────┐
                                                    │  rate_counters    │
                                                    │                    │
                                                    │  api_key_id        │
                                                    │  action_type       │
                                                    │  window_start      │
                                                    │  count             │
                                                    └──────────────────┘
```

### 9.2 Table Definitions & Indexing Strategy

#### api_keys

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | Unique identifier |
| key_hash | VARCHAR(128) UNIQUE | SHA-512 hash of raw key |
| key_prefix | VARCHAR(8) | First 8 chars for identification |
| role | user_role ENUM | operator / admin / super_admin |
| department | VARCHAR(100) | Organizational unit |
| description | VARCHAR(255) | Human-readable label |
| created_at | TIMESTAMPTZ | Creation time |
| expires_at | TIMESTAMPTZ | Expiration (NULL = never) |
| is_active | BOOLEAN | Revocation flag |
| allowed_ips | INET[] | IP whitelist (NULL = any) |
| last_used_at | TIMESTAMPTZ | Last usage time |
| last_used_ip | INET | Last usage IP |

**Indexes:** `idx_api_keys_hash` on key_hash (lookup), `idx_api_keys_active` on is_active WHERE TRUE (filtered).

#### backup_metadata

| Column | Type | Description |
|--------|------|-------------|
| object_id | UUID PK | Backup identifier |
| classification | classification_level | PUBLIC / INTERNAL / CONFIDENTIAL / SECRET |
| source_system | VARCHAR(200) | Origin system |
| original_filename | VARCHAR(500) | Original file name |
| description | TEXT | Human description |
| original_size | BIGINT | Plaintext bytes |
| encrypted_size | BIGINT | Ciphertext bytes |
| checksum_plaintext | VARCHAR(128) | SHA-512 of plaintext |
| checksum_ciphertext | VARCHAR(128) | SHA-512 of ciphertext |
| storage_path | VARCHAR(500) | MinIO object key |
| wrapped_dek_path | VARCHAR(500) | MinIO DEK key |
| key_version | VARCHAR(50) FK | ECC key used |
| nonce | BYTEA | 12-byte GCM nonce |
| created_by | UUID FK | API key that created |
| created_at | TIMESTAMPTZ | Creation time |
| status | backup_status | PROCESSING / ACTIVE / DELETED / CRYPTO_SHREDDED |

**Indexes:** status, classification, created_at DESC, created_by, key_version.

#### key_versions

| Column | Type | Description |
|--------|------|-------------|
| version_id | VARCHAR(50) PK | e.g., "P-001" |
| key_type | key_type | PRIMARY / SECONDARY |
| curve | VARCHAR(20) | SECP384R1 |
| public_key_pem | TEXT | PEM-encoded public key |
| private_key_path | VARCHAR(500) | Filesystem path |
| created_at | TIMESTAMPTZ | Generation time |
| rotated_from | VARCHAR(50) FK | Previous version |
| status | key_status | ACTIVE / RETIRED / DESTROYED |
| destroyed_at | TIMESTAMPTZ | Destruction time |
| destroyed_by | UUID FK | Who authorized |
| destruction_reason | TEXT | Reason for destruction |

**Indexes:** status, key_type.

#### audit_log

| Column | Type | Description |
|--------|------|-------------|
| event_id | UUID PK | Unique event ID |
| sequence_number | BIGSERIAL UNIQUE | Chain ordering |
| timestamp | TIMESTAMPTZ | Event time |
| actor | UUID FK | API key (NULL = system) |
| actor_role | user_role | Role at time of action |
| action | audit_action | Action type |
| resource | VARCHAR(200) | Affected resource |
| result | audit_result | SUCCESS / DENIED / FAILED / ERROR |
| details | JSONB | Flexible context |
| source_ip | INET | Client IP |
| prev_hash | VARCHAR(128) | SHA-512 link to previous |
| curr_hash | VARCHAR(128) UNIQUE | SHA-512 of this entry |

**Indexes:** timestamp DESC, action, actor, resource, sequence_number.

**Critical constraint:** sequence_number uses BIGSERIAL (no gaps). Hash chain integrity depends on unbroken sequence.

#### Additional Tables

**audit_checkpoints:** checkpoint_id (SERIAL PK), sequence_number (FK), curr_hash, created_at. Created every 1,000 entries.

**policies:** policy_id (UUID PK), name (UNIQUE), description, rule_json (JSONB), is_active, priority (lower = higher), created_at, updated_at, created_by.

**alerts:** alert_id (UUID PK), rule_id (M1–M10), severity, status, incident_level (0–3), triggered_at, acknowledged_at/by, resolved_at/by, details (JSONB), related_actor, related_resource.

**restore_requests:** restore_id (UUID PK), backup_id (FK), requested_by (FK), justification, status, requested_at, approved_at/by, completed_at, download_token, download_expires_at, source_ip.

**rate_counters:** id (SERIAL PK), api_key_id (FK), action_type, window_start, count. Unique on (api_key_id, action_type, window_start).

**system_state:** key (VARCHAR PK), value (JSONB), updated_at. Stores incident_level and system_version.

### 9.3 Enumeration Types

| Enum | Values | Usage |
|------|--------|-------|
| classification_level | PUBLIC, INTERNAL, CONFIDENTIAL, SECRET | Data sensitivity |
| user_role | operator, admin, super_admin | Access level |
| backup_status | PROCESSING, ACTIVE, DELETED, CRYPTO_SHREDDED | Backup lifecycle |
| key_status | ACTIVE, RETIRED, DESTROYED | Key lifecycle |
| key_type | PRIMARY, SECONDARY | Key lineage |
| audit_action | 27 values (see PRD §8) | Event categorization |
| audit_result | SUCCESS, DENIED, FAILED, ERROR | Outcome tracking |
| alert_severity | MEDIUM, HIGH, CRITICAL | Threat level |
| alert_status | NEW, ACKNOWLEDGED, INVESTIGATING, RESOLVED, ESCALATED | Alert lifecycle |

### 9.4 Data Flow Through Tables

**During Backup:**

```
api_keys ──(authenticate)──▶ policy check
                                │
                                ▼
                          backup_metadata ──(INSERT, status=PROCESSING)
                                │
                          key_versions ──(read active P-xxx public key)
                                │
                          backup_metadata ──(UPDATE, status=ACTIVE)
                                │
                          audit_log ──(INSERT BACKUP_COMPLETE)
                                │
                          rate_counters ──(INCREMENT backup count)
```

**During Restore:**

```
api_keys ──(authenticate + MFA)──▶ policy check ──▶ system_state (check incident level)
                                                         │
                                                   restore_requests ──(INSERT, status=PENDING/APPROVED)
                                                         │
                                                   backup_metadata ──(read storage_path, key_version, nonce)
                                                         │
                                                   key_versions ──(read private key path)
                                                         │
                                                   restore_requests ──(UPDATE, status=COMPLETE)
                                                         │
                                                   audit_log ──(INSERT RESTORE_COMPLETE)
                                                         │
                                                   monitoring check ──▶ alerts? ──▶ system_state escalation?
```

---

## 10. API Architecture

### 10.1 REST API Design

All endpoints follow these conventions:

- Base path: `/api/v1`
- Content type: `application/json` (except file upload: `multipart/form-data`)
- Authentication: `X-API-Key` header on all endpoints except `GET /health`
- MFA: `X-MFA-Token` header on restore and crypto-shred endpoints
- Pagination: `page` (1-based) and `limit` (max 100) query parameters
- Every response includes `request_id` (UUID) and `timestamp` (ISO-8601)

### 10.2 Endpoint Catalog

#### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/v1/health | None | Basic liveness check |
| GET | /api/v1/health/detailed | Admin | Component health: DB, MinIO, keys |

#### Backup Operations

| Method | Endpoint | Auth | Request | Response |
|--------|----------|------|---------|----------|
| POST | /api/v1/backup | API Key | Multipart: file + classification + source_system + description | BackupResponse |
| GET | /api/v1/backup/{backup_id} | API Key | — | BackupResponse |
| GET | /api/v1/backup/{backup_id}/status | API Key | — | BackupStatusResponse |
| GET | /api/v1/backups | API Key | Query: classification, source_system, status, date_from, date_to, page, limit | PaginatedResponse |

#### Restore Operations

| Method | Endpoint | Auth | Request | Response |
|--------|----------|------|---------|----------|
| POST | /api/v1/restore | API Key + MFA | backup_id, justification (min 10 chars) | RestoreResponse |
| GET | /api/v1/restore/{restore_id}/status | API Key | — | RestoreStatusResponse |
| GET | /api/v1/restore/{restore_id}/download | API Key + MFA | — | Binary file stream |

#### Admin Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/v1/admin/policies | Admin | Create policy |
| GET | /api/v1/admin/policies | Admin | List policies |
| POST | /api/v1/admin/api-keys | Super Admin | Generate API key (raw shown once) |
| DELETE | /api/v1/admin/api-keys/{key_id} | Super Admin | Revoke API key |
| GET | /api/v1/admin/audit-logs | Admin | Query audit log (filtered, paginated) |
| POST | /api/v1/admin/audit-logs/validate | Admin | Validate hash chain integrity |
| GET | /api/v1/admin/alerts | Admin | List alerts (filtered by status) |
| POST | /api/v1/admin/alerts/{alert_id}/acknowledge | Admin | Acknowledge alert |
| POST | /api/v1/admin/incident/crypto-shred | Super Admin + MFA | IRREVERSIBLE: destroy key |

### 10.3 Request/Response Schemas

**Standard Success Envelope:**
```json
{
    "status": "success",
    "data": { ... },
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-02-15T10:30:00.000Z"
}
```

**Standard Error Envelope:**
```json
{
    "status": "error",
    "error": {
        "code": "POLICY_DENIED",
        "message": "Role 'operator' not authorized for restore"
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "timestamp": "2025-02-15T10:30:00.000Z"
}
```

**BackupResponse:**
```json
{
    "object_id": "uuid",
    "classification": "CONFIDENTIAL",
    "source_system": "gov-records-01",
    "original_filename": "report.pdf",
    "original_size": 1048576,
    "encrypted_size": 1048608,
    "checksum_plaintext": "sha512hex...",
    "key_version": "P-001",
    "status": "ACTIVE",
    "created_at": "2025-02-15T10:30:00Z"
}
```

### 10.4 Error Handling Contract

| Error Code | HTTP | When |
|------------|------|------|
| AUTH_INVALID_KEY | 401 | Missing, invalid, expired, or revoked API key |
| AUTH_MFA_REQUIRED | 401 | Operation requires MFA but header missing |
| POLICY_DENIED | 403 | Policy engine denied the operation |
| BACKUP_NOT_FOUND | 404 | Backup object_id not found |
| RESTORE_NOT_FOUND | 404 | Restore request not found |
| RESTORE_QUARANTINED | 423 | Level 2 incident — restores quarantined |
| RATE_LIMITED | 429 | Per-key or system rate limit exceeded |
| CRYPTO_SHREDDED | 410 | Keys destroyed — data permanently gone |
| KEY_UNAVAILABLE | 503 | Key file missing or decryption failed |
| INTEGRITY_FAILURE | 500 | Checksum or GCM tag mismatch |
| UPLOAD_FAILED | 500 | MinIO upload or encryption error |
| INTERNAL_ERROR | 500 | Unexpected server error |

---

## 11. Security Architecture

### 11.1 Authentication System

```
Client Request
    │
    │  Header: X-API-Key: ssbg_a1b2c3d4e5f6...
    │
    ▼
┌────────────────────────────────────────────────┐
│  Step 1: Extract key from X-API-Key header      │
│          Missing? → 401 AUTH_INVALID_KEY         │
└───────────────────────┬────────────────────────┘
                        ▼
┌────────────────────────────────────────────────┐
│  Step 2: Compute SHA-512(raw_key)               │
│          Look up hash in api_keys table          │
│          Not found? → 401 AUTH_INVALID_KEY       │
└───────────────────────┬────────────────────────┘
                        ▼
┌────────────────────────────────────────────────┐
│  Step 3: Check is_active = TRUE                  │
│          Revoked? → 401 AUTH_INVALID_KEY         │
└───────────────────────┬────────────────────────┘
                        ▼
┌────────────────────────────────────────────────┐
│  Step 4: Check expires_at > NOW()               │
│          Expired? → 401 AUTH_INVALID_KEY         │
└───────────────────────┬────────────────────────┘
                        ▼
┌────────────────────────────────────────────────┐
│  Step 5: Check allowed_ips contains client IP    │
│          (skip if allowed_ips is NULL)           │
│          Not in list? → 401 AUTH_INVALID_KEY     │
└───────────────────────┬────────────────────────┘
                        ▼
┌────────────────────────────────────────────────┐
│  Step 6: Update last_used_at, last_used_ip      │
│          Return {id, role, department, source_ip}│
└────────────────────────────────────────────────┘
```

**API Key Format:** `ssbg_{32 hex chars}` generated via `secrets.token_hex(16)`. Total length: 37 characters.

**Key Storage:** Only the SHA-512 hash is persisted. A database compromise reveals hashes, not usable keys. Brute-forcing a 128-bit random key from its SHA-512 hash is computationally infeasible.

### 11.2 Authorization & RBAC

Three roles with hierarchical permissions:

```
super_admin ⊃ admin ⊃ operator

┌────────────────────────────────────────────────────┐
│  super_admin                                        │
│  ├── Everything admin can do, PLUS:                 │
│  ├── Create/revoke API keys                         │
│  ├── Execute crypto-shredding (+ MFA + confirm)     │
│  └── Restore SECRET data (+ MFA)                    │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  admin                                        │   │
│  │  ├── Everything operator can do, PLUS:         │   │
│  │  ├── Restore PUBLIC/INTERNAL data              │   │
│  │  ├── Restore CONFIDENTIAL data (+ MFA)         │   │
│  │  ├── View/query audit logs                     │   │
│  │  ├── Manage policies                           │   │
│  │  ├── View/acknowledge alerts                   │   │
│  │  └── View detailed health                      │   │
│  │                                                │   │
│  │  ┌──────────────────────────────────────────┐ │   │
│  │  │  operator                                 │ │   │
│  │  │  ├── Create backups (all classifications) │ │   │
│  │  │  ├── View backup metadata                 │ │   │
│  │  │  ├── List own backups                     │ │   │
│  │  │  └── Check backup status                  │ │   │
│  │  └──────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

### 11.3 Policy Engine Architecture

The policy engine is a stateless evaluator. It receives the operation context and returns an allow/deny decision:

```
PolicyEngine.evaluate_restore(
    role = admin,
    classification = CONFIDENTIAL,
    incident_level = 0,
    has_mfa = True,
    current_hour = 14,
    restore_count_this_hour = 3,
    system_restore_count_this_hour = 12,
)
    │
    │ Evaluate rules in order (first deny wins):
    │
    ├── P9: incident_level >= 3? → No  → Continue
    ├── P2: role in {admin, super_admin}? → Yes → Continue
    ├── P3: SECRET + super_admin + MFA? → N/A (CONFIDENTIAL) → Continue
    ├── P3b: CONFIDENTIAL + MFA? → has_mfa=True → Continue
    ├── P4: 8 ≤ 14 < 18? → Yes (business hours) → Continue
    ├── P5: 3 < 10 per-key limit? → Yes → Continue
    ├── P6: 12 < 50 system limit? → Yes → Continue
    │
    └── Result: PolicyDecision(allowed=True, reason="Restore allowed")
```

### 11.4 Defense-in-Depth Layers

```
Layer 7: Crypto-Shredding
    │  Ultimate guarantee — destroy key = destroy data forever
Layer 6: Incident Response (4 levels)
    │  Automated restriction escalation
Layer 5: Monitoring & Detection (10 rules)
    │  Real-time anomaly detection
Layer 4: Policy Engine (9 rules)
    │  Classification-aware, role-based, time-bound access control
Layer 3: Authentication (API Key + MFA + IP whitelist)
    │  Identity verification
Layer 2: Encryption (AES-256-GCM + ECIES)
    │  Data confidentiality + integrity
Layer 1: Network Isolation (Docker bridge)
    │  Component isolation, single entry point
Layer 0: Physical Infrastructure (self-hosted)
    │  Sovereign control — no external dependencies
```

---

## 12. Audit & Compliance Architecture

### 12.1 Hash Chain Design

```
GENESIS                Entry 1                  Entry 2                  Entry N
┌──────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│SHA-512(  │          │ event_id     │          │ event_id     │          │ event_id     │
│"GENESIS")│───prev──▶│ timestamp    │───prev──▶│ timestamp    │  ···  ──▶│ timestamp    │
│          │   hash   │ seq: 1       │   hash   │ seq: 2       │          │ seq: N       │
│= e3b0c44.│          │ action       │          │ action       │          │ action       │
│          │          │ prev_hash: ──┤          │ prev_hash: ──┤          │ prev_hash: ──┤
└──────────┘          │  e3b0c44...  │          │  a1b2c3d...  │          │  x9y8z7w...  │
                      │ curr_hash: ──┤          │ curr_hash: ──┤          │ curr_hash: ──┤
                      │  a1b2c3d...  │          │  d4e5f6g...  │          │  final...    │
                      └──────────────┘          └──────────────┘          └──────────────┘

Hash computation for each entry:
  curr_hash = SHA-512(
      event_id
    + "|" + timestamp.isoformat()
    + "|" + str(sequence_number)
    + "|" + str(actor or "SYSTEM")
    + "|" + action
    + "|" + (resource or "")
    + "|" + result
    + "|" + json.dumps(details, sort_keys=True)
    + "|" + prev_hash
  )
```

### 12.2 Chain Validation Algorithm

```
function validate_chain():
    entries = SELECT * FROM audit_log ORDER BY sequence_number ASC
    expected_prev = SHA-512("GENESIS")

    for each entry in entries:
        if entry.prev_hash ≠ expected_prev:
            return {valid: false, broken_at: entry.sequence_number,
                    error: "prev_hash chain break"}

        recomputed = SHA-512(entry.event_id || ... || entry.prev_hash)
        if entry.curr_hash ≠ recomputed:
            return {valid: false, broken_at: entry.sequence_number,
                    error: "entry content tampered"}

        expected_prev = entry.curr_hash

    return {valid: true, entries_checked: len(entries)}
```

**Tamper detection guarantee:** If an attacker modifies any field of any entry, the recomputed curr_hash will differ from the stored curr_hash. If an attacker tries to fix the curr_hash, the next entry's prev_hash will no longer match. The only way to forge the chain is to recompute every subsequent entry's hash, which requires rewriting the entire chain from the tampered point forward — and the system detects this because the chain tip's hash will differ from any externally anchored checkpoint.

### 12.3 Checkpoint System

Every 1,000 entries, a checkpoint is created:

```
audit_log:        seq 1 ─── seq 2 ─── ... ─── seq 1000 ─── seq 1001 ─── ... ─── seq 2000
                                                  │                                    │
audit_checkpoints:                           checkpoint 1                         checkpoint 2
                                          (seq=1000, hash=...)                (seq=2000, hash=...)
```

Checkpoints enable partial validation (start from last checkpoint) and external anchoring (export checkpoint hashes to an external system for independent verification).

### 12.4 Audited Events Catalog

Every significant operation generates an audit entry:

| Category | Events |
|----------|--------|
| Backup | BACKUP_START, BACKUP_COMPLETE, BACKUP_FAILED |
| Restore | RESTORE_REQUEST, RESTORE_APPROVED, RESTORE_DENIED, RESTORE_COMPLETE, RESTORE_FAILED |
| Policy | POLICY_CHECK_ALLOW, POLICY_CHECK_DENY |
| Key Management | KEY_WRAP, KEY_UNWRAP, KEY_ROTATE, KEY_DESTROY |
| Alerts | ALERT_TRIGGER, ALERT_ACK, ALERT_RESOLVE, ALERT_ESCALATE |
| Incident | INCIDENT_LEVEL_CHANGE |
| Configuration | CONFIG_CHANGE, POLICY_CHANGE |
| Authentication | AUTH_SUCCESS, AUTH_FAILURE |
| Crypto-Shredding | CRYPTO_SHRED_START, CRYPTO_SHRED_COMPLETE |
| System | SYSTEM_START, SYSTEM_HEALTH_CHECK |

---

## 13. Threat Detection & Monitoring Architecture

### 13.1 Rule Engine Design

The monitoring service uses a pattern-matching architecture:

```
┌─────────────┐     ┌──────────────────────────────────┐
│ Audit Event  │────▶│  Rule Evaluator                   │
│ (trigger)    │     │                                    │
└─────────────┘     │  For each rule in RULES:           │
                    │    if rule.type == "threshold":     │
                    │      count = query audit_log        │
                    │        WHERE action = rule.action   │
                    │        AND time > now - window      │
                    │      if count >= threshold:         │
                    │        → CREATE ALERT               │
                    │                                      │
                    │    if rule.type == "event":          │
                    │      → Check specific conditions     │
                    │      → CREATE ALERT if matched       │
                    └──────────────────┬───────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────┐
                    │  Alert Created                     │
                    │  → Insert into alerts table        │
                    │  → Check incident_level            │
                    │  → Escalate if needed              │
                    └──────────────────────────────────┘
```

### 13.2 Detection Rules Catalog

| Rule | Type | Trigger | Window | Threshold | Severity | Level |
|------|------|---------|--------|-----------|----------|-------|
| M1 | Threshold | AUTH_FAILURE | 5 min | 5 | HIGH | 1 |
| M2 | Threshold | RESTORE_COMPLETE | 60 min | 10 (per key) | HIGH | 1 |
| M3 | Statistical | RESTORE volume | 24 hr | 3× avg | HIGH | 2 |
| M4 | Event | New IP for restore | — | — | MEDIUM | 1 |
| M5 | Event | KEY_UNWRAP outside 08–18 | — | — | MEDIUM | 1 |
| M6 | Event | Audit tampering attempt | — | — | CRITICAL | 2 |
| M7 | Threshold | RESTORE_FAILED | 10 min | 3 | HIGH | 2 |
| M8 | Threshold | BACKUP_DELETE | 60 min | 5 | CRITICAL | 2 |
| M9 | Event | POLICY_CHANGE | — | — | MEDIUM | 1 |
| M10 | Event | Hash chain validation failure | — | — | CRITICAL | 3 |

### 13.3 Alert Lifecycle

```
┌───────┐   auto-create    ┌───────────────┐   admin action   ┌──────────────────┐
│  Rule  │ ───────────────▶ │     NEW       │ ───────────────▶ │   ACKNOWLEDGED   │
│ match  │                  │               │                  │                  │
└────────┘                  └───────┬───────┘                  └────────┬─────────┘
                                    │                                   │
                            15 min timeout                        investigation
                                    │                                   │
                                    ▼                                   ▼
                            ┌───────────────┐                  ┌──────────────────┐
                            │   ESCALATED   │                  │  INVESTIGATING   │
                            │               │                  │                  │
                            └───────────────┘                  └────────┬─────────┘
                                                                       │
                                                                 resolution
                                                                       │
                                                                       ▼
                                                               ┌──────────────────┐
                                                               │    RESOLVED      │
                                                               └──────────────────┘
```

---

## 14. Incident Response Architecture

### 14.1 Four-Level Escalation Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INCIDENT LEVEL ESCALATION                                 │
│                                                                              │
│  Level 0 ──────▶ Level 1 ──────▶ Level 2 ──────▶ Level 3                   │
│  NORMAL          ALERT           QUARANTINE       LOCKDOWN                   │
│                                                                              │
│  All systems     Rate limits ↓   Restores →       CRYPTO-SHRED              │
│  operational     MFA for all     PENDING           All keys destroyed        │
│                  Enhanced log    Manual approval    System sealed             │
│                                  Unwrap frozen      IRREVERSIBLE             │
│                                                                              │
│  ◄── auto-revert (30 min) ──┤   ◄── manual ──┤   ╳ NO REVERT              │
│                              │   de-escalation│                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.2 Escalation State Machine

```
         ┌──────────────────────────────────────────────────────┐
         │                                                       │
         ▼                                                       │
    ┌─────────┐     M1/M2/M4/M5/M9     ┌─────────┐            │
    │ Level 0 │ ───────────────────────▶ │ Level 1 │ ──30min──▶│ (auto-revert)
    │ Normal  │                          │ Alert   │            │
    └────┬────┘                          └────┬────┘            │
         │                                    │                  │
         │     M3/M6/M7/M8                    │ M3/M6/M7/M8    │
         │                                    │                  │
         ▼                                    ▼                  │
    ┌─────────┐                          ┌─────────┐            │
    │ Level 2 │ ◄────────────────────────│ Level 2 │            │
    │Quarantin│                          │Quarantin│ ──admin──▶│ (de-escalate)
    └────┬────┘                          └────┬────┘
         │                                    │
         │     M10 / manual                   │ M10 / manual
         ▼                                    ▼
    ┌─────────┐                          ┌─────────┐
    │ Level 3 │                          │ Level 3 │
    │LOCKDOWN │    NO RETURN             │LOCKDOWN │    NO RETURN
    │PERMANENT│                          │PERMANENT│
    └─────────┘                          └─────────┘
```

### 14.3 Per-Level System Behavior

| Behavior | Level 0 | Level 1 | Level 2 | Level 3 |
|----------|---------|---------|---------|---------|
| Backup operations | ✅ Normal | ✅ Normal | ✅ Normal | ❌ Blocked |
| Restore operations | ✅ Normal | ✅ MFA required for ALL | ⏸ PENDING (manual approval) | ❌ Blocked |
| DEK unwrap | ✅ Normal | ✅ Normal | ❌ Frozen | ❌ Destroyed |
| Rate limits | Normal | 50% reduction | 50% reduction | N/A |
| Logging | Standard | Enhanced | Enhanced | N/A |
| Notification | None | Log entry | Super admin notified | N/A |
| Duration | Indefinite | 30 min auto-revert | Until manual de-escalation | **Permanent** |
| Revertible | — | Yes (auto) | Yes (manual) | **No** |

---

## 15. Storage Architecture

### 15.1 MinIO Object Storage Design

MinIO provides S3-compatible object storage within the Docker environment:

| Property | Value |
|----------|-------|
| Protocol | S3 v4 signature |
| Endpoint | http://minio:9000 (internal) |
| Bucket | ssbg-backups |
| Versioning | Enabled (accidental overwrite protection) |
| Region | us-east-1 (MinIO requirement) |
| Authentication | Access key + Secret key (shared credentials) |
| SSL | Disabled (internal Docker network) |

### 15.2 Object Layout & Naming

```
ssbg-backups/                          ← Single bucket
└── backups/
    ├── {uuid-1}/
    │   ├── data.enc                   ← AES-256-GCM ciphertext + 16-byte tag
    │   └── dek.wrapped                ← ECIES-wrapped DEK (~159 bytes)
    ├── {uuid-2}/
    │   ├── data.enc
    │   └── dek.wrapped
    └── {uuid-N}/
        ├── data.enc
        └── dek.wrapped
```

**Naming convention:** Each backup object_id (UUID) gets its own "directory" in MinIO. This provides clean namespace isolation and makes crypto-shredding verification straightforward — after key destruction, every `data.enc` under the affected key version's backups is mathematically unreadable.

### 15.3 ECC Key Filesystem Layout

```
keys/                                   ← Mounted as Docker volume
└── primary/
    ├── P-001.private.pem              ← PKCS8 + PBKDF2 encrypted
    │                                     File mode: 0600
    │                                     ~3.2 KB for SECP384R1
    ├── P-001.public.pem               ← Plaintext PEM
    │                                     File mode: 0644
    │                                     ~350 bytes for SECP384R1
    ├── P-002.private.pem              ← Rotated key (if rotation occurred)
    └── P-002.public.pem
```

---

## 16. Workflow Architecture

### 16.1 Backup Workflow — Complete Flow

```
 Client                       Gateway                          MinIO           PostgreSQL
   │                            │                                │                 │
   │  POST /api/v1/backup       │                                │                 │
   │  Headers:                  │                                │                 │
   │    X-API-Key: ssbg_...     │                                │                 │
   │  Body (multipart):         │                                │                 │
   │    file: <binary>          │                                │                 │
   │    classification: SECRET  │                                │                 │
   │    source_system: gov-01   │                                │                 │
   ├───────────────────────────▶│                                │                 │
   │                            │                                │                 │
   │                            │─── 1. SHA-512(api_key) ────────────────────────▶│
   │                            │    SELECT * FROM api_keys      │                 │
   │                            │    WHERE key_hash = ?          │                 │
   │                            │◀───── api_key record ──────────────────────────│
   │                            │                                │                 │
   │                            │─── 2. PolicyEngine.evaluate_backup() ──────────│
   │                            │    Check role, classification, │                 │
   │                            │    incident level              │                 │
   │                            │◀── PolicyDecision(allowed=True)│                 │
   │                            │                                │                 │
   │                            │─── 3. Read file from request   │                 │
   │                            │    Compute SHA-512(plaintext)  │                 │
   │                            │                                │                 │
   │                            │─── 4. Generate DEK             │                 │
   │                            │    dek = os.urandom(32)        │                 │
   │                            │    nonce = os.urandom(12)      │                 │
   │                            │                                │                 │
   │                            │─── 5. AES-256-GCM encrypt      │                 │
   │                            │    ciphertext = encrypt(dek,   │                 │
   │                            │                  nonce, plain) │                 │
   │                            │                                │                 │
   │                            │─── 6. SHA-512(ciphertext)      │                 │
   │                            │                                │                 │
   │                            │─── 7. ECIES wrap DEK ──────────────────────────▶│
   │                            │    Read P-001 public key       │                 │
   │                            │    wrapped = ecies_wrap(dek)   │                 │
   │                            │    Zero DEK from memory        │                 │
   │                            │                                │                 │
   │                            │─── 8. Upload to MinIO ────────▶│                 │
   │                            │    PUT backups/{id}/data.enc   │                 │
   │                            │    PUT backups/{id}/dek.wrapped│                 │
   │                            │◀───── 200 OK ─────────────────│                 │
   │                            │                                │                 │
   │                            │─── 9. Store metadata ──────────────────────────▶│
   │                            │    INSERT INTO backup_metadata │                 │
   │                            │    (checksums, paths, key_ver) │                 │
   │                            │                                │                 │
   │                            │─── 10. Audit log ──────────────────────────────▶│
   │                            │    INSERT INTO audit_log       │                 │
   │                            │    (BACKUP_COMPLETE, hash chain)│                │
   │                            │                                │                 │
   │◀── 200 {object_id, ...} ──│                                │                 │
```

### 16.2 Restore Workflow — Complete Flow

```
 Client                       Gateway                          MinIO           PostgreSQL
   │                            │                                │                 │
   │  POST /api/v1/restore      │                                │                 │
   │  Headers:                  │                                │                 │
   │    X-API-Key: ssbg_...     │                                │                 │
   │    X-MFA-Token: 123456     │                                │                 │
   │  Body:                     │                                │                 │
   │    backup_id: uuid         │                                │                 │
   │    justification: "..."    │                                │                 │
   ├───────────────────────────▶│                                │                 │
   │                            │                                │                 │
   │                            │─── 1. Authenticate (API key + MFA) ────────────│
   │                            │                                │                 │
   │                            │─── 2. Fetch backup metadata ───────────────────▶│
   │                            │    SELECT * FROM backup_metadata               │
   │                            │    WHERE object_id = ?                          │
   │                            │◀── metadata (classification, key_ver, nonce) ──│
   │                            │                                │                 │
   │                            │─── 3. Policy evaluation ───────────────────────│
   │                            │    Check role, classification, │                 │
   │                            │    MFA, business hours,        │                 │
   │                            │    rate limits, incident level │                 │
   │                            │                                │                 │
   │                            │    [If Level 2: status=PENDING,│await approval] │
   │                            │                                │                 │
   │                            │─── 4. Download from MinIO ────▶│                 │
   │                            │    GET backups/{id}/data.enc   │                 │
   │                            │    GET backups/{id}/dek.wrapped│                 │
   │                            │◀── ciphertext + wrapped_dek ──│                 │
   │                            │                                │                 │
   │                            │─── 5. Unwrap DEK ──────────────────────────────│
   │                            │    Load P-001 private key      │    (filesystem) │
   │                            │    dek = ecies_unwrap(wrapped) │                 │
   │                            │    [If key DESTROYED → 410]    │                 │
   │                            │                                │                 │
   │                            │─── 6. AES-256-GCM decrypt      │                 │
   │                            │    plaintext = decrypt(dek,    │                 │
   │                            │                 nonce, cipher) │                 │
   │                            │    [If InvalidTag → 500        │                 │
   │                            │     INTEGRITY_FAILURE]         │                 │
   │                            │                                │                 │
   │                            │─── 7. Verify SHA-512 checksum  │                 │
   │                            │    SHA-512(plaintext) ==       │                 │
   │                            │    metadata.checksum_plaintext?│                 │
   │                            │                                │                 │
   │                            │─── 8. Generate download token ─────────────────▶│
   │                            │    INSERT INTO restore_requests│                 │
   │                            │    (status=COMPLETE, token=...)│                 │
   │                            │                                │                 │
   │                            │─── 9. Audit log + monitoring ──────────────────▶│
   │                            │                                │                 │
   │◀── 200 {restore_id, url} ─│                                │                 │
```

### 16.3 Crypto-Shredding Workflow — Complete Flow

```
 Admin Client                  Gateway                   Filesystem      PostgreSQL
   │                            │                            │                │
   │  POST /admin/incident/     │                            │                │
   │       crypto-shred         │                            │                │
   │  Headers:                  │                            │                │
   │    X-API-Key: super_admin  │                            │                │
   │    X-MFA-Token: 123456     │                            │                │
   │  Body:                     │                            │                │
   │    key_version: "P-001"    │                            │                │
   │    confirmation: "DESTROY- │                            │                │
   │                  P001"     │                            │                │
   ├───────────────────────────▶│                            │                │
   │                            │                            │                │
   │                            │─── 1. Triple auth check    │                │
   │                            │    Role: super_admin ✓     │                │
   │                            │    MFA: valid ✓            │                │
   │                            │    Confirm: matches ✓      │                │
   │                            │                            │                │
   │                            │─── 2. Audit: CRYPTO_SHRED_START ──────────▶│
   │                            │                            │                │
   │                            │─── 3. Destroy private key ▶│                │
   │                            │    Overwrite with random   │                │
   │                            │    fsync() to disk         │                │
   │                            │    unlink() file           │                │
   │                            │◀── destruction_record ─────│                │
   │                            │                            │                │
   │                            │─── 4. Update key_versions ─────────────────▶│
   │                            │    SET status=DESTROYED    │                │
   │                            │                            │                │
   │                            │─── 5. Mark affected backups ───────────────▶│
   │                            │    UPDATE backup_metadata  │                │
   │                            │    SET status=CRYPTO_SHREDDED              │
   │                            │    WHERE key_version='P-001'               │
   │                            │                            │                │
   │                            │─── 6. Set Level 3 (permanent) ─────────────▶│
   │                            │    UPDATE system_state     │                │
   │                            │    SET level=3             │                │
   │                            │                            │                │
   │                            │─── 7. Audit: CRYPTO_SHRED_COMPLETE ────────▶│
   │                            │                            │                │
   │◀── 200 {affected: N,      │                            │                │
   │         status: DESTROYED, │                            │                │
   │         irreversible: true}│                            │                │
```

### 16.4 Key Rotation Workflow

```
1. Generate new key pair (P-002)
2. Register P-002 in key_versions (status=ACTIVE)
3. Update P-001 in key_versions (status=RETIRED)
4. All NEW backups use P-002 for wrapping
5. Existing backups still use P-001 for unwrapping (private key still exists)
6. Audit log: KEY_ROTATE event

Note: Key rotation does NOT require re-encrypting existing backups.
      The old key remains available for unwrapping until explicitly destroyed.
```

### 16.5 Authentication Workflow

```
Request arrives
    │
    ▼
Extract X-API-Key header → missing? → 401
    │
    ▼
Compute SHA-512(raw_key)
    │
    ▼
SELECT FROM api_keys WHERE key_hash = ? → not found? → 401
    │                                      (log AUTH_FAILURE)
    ▼
Check is_active = TRUE → revoked? → 401
    │
    ▼
Check expires_at > NOW() → expired? → 401
    │
    ▼
Check allowed_ips contains client IP → blocked? → 401
    │
    ▼
Update last_used_at, last_used_ip
    │
    ▼
Log AUTH_SUCCESS to audit
    │
    ▼
[If MFA required for this operation]
    │
    ▼
Extract X-MFA-Token → missing? → 401 AUTH_MFA_REQUIRED
    │
    ▼
Validate token → invalid? → 401
    │
    ▼
Authentication complete → proceed to policy evaluation
```

---

## 17. Configuration Architecture

Configuration is managed through Pydantic Settings with environment variable overrides:

| Category | Setting | Default (Dev) | Production | Description |
|----------|---------|---------------|------------|-------------|
| Database | DATABASE_URL | postgresql+asyncpg://ssbg:password@postgres:5432/ssbg | Strong password | Async connection string |
| MinIO | MINIO_ENDPOINT | minio:9000 | minio:9000 | S3 endpoint |
| MinIO | MINIO_ACCESS_KEY | minioadmin | Strong random | S3 access key |
| MinIO | MINIO_SECRET_KEY | minioadmin | Strong random | S3 secret key |
| MinIO | MINIO_BUCKET | ssbg-backups | ssbg-backups | Storage bucket |
| Keys | ECC_PRIMARY_KEY_DIR | /app/keys/primary | /app/keys/primary | Key directory |
| Keys | ECC_KEY_PASSWORD | changeme | Strong random | Private key password |
| Security | API_KEY_HEADER | X-API-Key | X-API-Key | Auth header name |
| Security | MFA_HEADER | X-MFA-Token | X-MFA-Token | MFA header name |
| Rate Limits | MAX_RESTORES_PER_KEY_PER_HOUR | 100 | 10 | Per-key limit |
| Rate Limits | MAX_RESTORES_SYSTEM_PER_HOUR | — | 50 | System-wide limit |
| Rate Limits | MAX_AUTH_FAILURES_PER_5MIN | — | 5 | Brute force threshold |
| Policy | BUSINESS_HOURS_START | 0 | 8 | Business hours start |
| Policy | BUSINESS_HOURS_END | 24 | 18 | Business hours end |
| Monitoring | ALERT_AUTO_ESCALATE_MINUTES | 60 | 15 | Unack escalation timer |
| Monitoring | AUDIT_CHECKPOINT_INTERVAL | 1000 | 1000 | Checkpoint frequency |
| Streaming | UPLOAD_CHUNK_SIZE | 67108864 | 67108864 | 64 MB chunks |
| Restore | RESTORE_DOWNLOAD_TTL_SECONDS | 3600 | 3600 | 1 hour download window |
| Logging | LOG_LEVEL | DEBUG | INFO | Application log level |

---

## 18. Deployment Architecture

### 18.1 Docker Compose Topology

```yaml
version: "3.9"
services:
  ssbg-gateway:
    build: ./gateway
    ports: ["8000:8000"]
    volumes: ["./keys:/app/keys"]
    depends_on:
      postgres: { condition: service_healthy }
      minio: { condition: service_healthy }
    networks: [ssbg-network]
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: { test: "pg_isready -U ssbg", interval: 5s }
    networks: [ssbg-network]
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    volumes: [minio-data:/data]
    command: server /data --console-address ":9001"
    healthcheck: { test: "mc ready local", interval: 10s }
    networks: [ssbg-network]
    restart: unless-stopped

volumes: { pgdata: {}, minio-data: {} }
networks: { ssbg-network: { driver: bridge } }
```

### 18.2 Container Specifications

| Container | Base Image | Size | Python | Key Packages |
|-----------|-----------|------|--------|--------------|
| gateway | python:3.11-slim | ~250 MB | 3.11 | fastapi, sqlalchemy, cryptography, boto3 |
| postgres | postgres:16-alpine | ~80 MB | — | PostgreSQL 16 |
| minio | minio/minio:latest | ~120 MB | — | MinIO server |

### 18.3 Volume Management

| Volume | Type | Mounted To | Purpose | Backup Required |
|--------|------|-----------|---------|-----------------|
| pgdata | Docker named | postgres:/var/lib/postgresql/data | Database persistence | Yes (metadata, audit logs) |
| minio-data | Docker named | minio:/data | Encrypted blob storage | Optional (data is encrypted) |
| ./keys | Bind mount | gateway:/app/keys | ECC key storage | **CRITICAL** (loss = data loss) |

### 18.4 Health Check Strategy

| Container | Check | Interval | Timeout | Retries | Failure Action |
|-----------|-------|----------|---------|---------|----------------|
| postgres | `pg_isready -U ssbg` | 5s | 5s | 5 | Block gateway startup |
| minio | `mc ready local` | 10s | 5s | 5 | Block gateway startup |
| gateway | `GET /api/v1/health` | — | — | — | External monitoring |

### 18.5 Startup & Dependency Ordering

```
1. PostgreSQL starts → healthcheck passes (pg_isready)
2. MinIO starts → healthcheck passes (mc ready local)
3. Gateway starts (depends_on both healthy)
   a. SQLAlchemy creates tables (dev) or Alembic runs migrations (prod)
   b. MinIO bucket created if not exists (ensure_buckets())
   c. ECC keys verified on filesystem
   d. Uvicorn begins accepting requests on :8000
```

---

## 19. Resilience & Failure Handling

| Failure Scenario | Impact | Handling |
|-----------------|--------|----------|
| PostgreSQL down | Cannot authenticate, log, or query | Gateway returns 503; restart policy: unless-stopped |
| MinIO down | Cannot upload/download backups | Gateway returns 503 for backup/restore ops; other endpoints unaffected |
| Gateway crash | No API access | Docker restart policy: unless-stopped; stateless design = clean restart |
| ECC key file corrupted | Cannot wrap/unwrap DEK | Gateway logs error; backup/restore fail with KEY_UNAVAILABLE |
| ECC key file deleted (accidental) | Same as crypto-shredding | All backups for that key version become irrecoverable |
| Disk full (PostgreSQL) | Cannot write audit logs or metadata | Operations fail; system remains secure (fail-closed) |
| Disk full (MinIO) | Cannot store new backups | Backup operations fail; existing data unaffected |
| Network partition (internal) | Gateway loses DB or MinIO connectivity | Operations fail with 503; reconnects automatically |
| Concurrent hash chain writes | Race condition on prev_hash | Use SELECT ... FOR UPDATE or application lock on last entry |

---

## 20. Threat Model

### Attack Surfaces

| Surface | Threat | Mitigation |
|---------|--------|------------|
| Port 8000 (API) | Brute force API keys | SHA-512 hashing, rate limiting (M1), IP whitelisting |
| Port 8000 (API) | Mass data exfiltration via restore | MFA requirement, rate limiting (M2), business hours (P4), monitoring (M3) |
| Port 8000 (API) | Unauthorized access escalation | RBAC enforcement, policy engine, audit logging |
| PostgreSQL data | Direct database tampering | Docker network isolation, hash chain tamper detection (M10) |
| MinIO data | Unauthorized direct access | Docker network isolation; data is encrypted (useless without keys) |
| Host filesystem | ECC key theft | File permissions (0600), password encryption (PKCS8+PBKDF2) |
| Host filesystem | Key deletion (DoS) | Docker volume isolation; key backup procedures (operational) |
| Gateway memory | DEK extraction from process memory | DEK exists only during encrypt/decrypt; zeroed immediately after |
| Supply chain | Compromised dependencies | Pinned dependency versions, minimal base image |

### Threat Actors

| Actor | Capability | Goal | Primary Defense |
|-------|------------|------|-----------------|
| External attacker | Network access to port 8000 | Data exfiltration | Auth + Policy + Monitoring |
| Compromised operator | Valid API key (operator role) | Unauthorized restore | RBAC (operator cannot restore) |
| Compromised admin | Valid API key (admin role) | Mass exfiltration | Rate limits + monitoring + MFA |
| Rogue insider (IT) | Host access | Key theft or tampering | Key encryption + audit chain + Level 3 |
| Database attacker | SQL access | Audit log tampering | SHA-512 hash chain (M10 → Level 3) |

### Security Properties vs. Attacks

| Property | Attack | Defense | Guarantee |
|----------|--------|---------|-----------|
| Confidentiality | Read ciphertext without key | AES-256-GCM; key required | Computationally infeasible (2^256) |
| Integrity | Modify ciphertext | GCM auth tag detects any change | Cryptographic (128-bit tag) |
| Authenticity | Forge backup data | SHA-512 checksums + GCM tag | Cryptographic |
| Non-repudiation | Deny performing action | Hash-chained audit log | Mathematical (chain breaks on tamper) |
| Destruction | Recover destroyed data | Private key file securely deleted | Physical (overwrite + fsync + delete) |

---

## 21. Technology Decisions & Rationale

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| Language | Python 3.11 | Go, Rust, Java | Team expertise; rich crypto library; rapid development |
| Framework | FastAPI | Flask, Django, Express | Async native; auto-generated docs; Pydantic validation |
| Database | PostgreSQL 16 | MySQL, SQLite, MongoDB | JSONB support; INET type; array types; async driver |
| ORM | SQLAlchemy 2.0 (async) | Tortoise, raw SQL | Industry standard; excellent async support |
| Object Storage | MinIO | LocalFS, Ceph, Cloud S3 | S3-compatible; self-hosted; single binary; Docker-native |
| Symmetric Cipher | AES-256-GCM | ChaCha20-Poly1305, AES-CTR | NIST standard; hardware acceleration; authenticated |
| Asymmetric Cipher | ECIES (SECP384R1) | RSA-2048, RSA-4096, X25519 | Shorter keys; equivalent security; standard curve |
| Hash Function | SHA-512 | SHA-256, SHA-3, BLAKE2 | 256-bit collision resistance; faster on 64-bit; standard |
| Containerization | Docker Compose | Kubernetes, bare metal | Appropriate for MVP; simple; portable |
| Key Format | PEM (PKCS8) | JWK, DER, raw bytes | Human-readable; well-supported; standard tooling |

---

## 22. Future Architecture Evolution

### Phase 2: Secondary MinIO Disaster Recovery

Add a fourth container (`ssbg-minio-secondary`) with independent ECC key lineage (S-001, S-002). During backup, the DEK is wrapped twice — once with P-xxx and once with S-xxx. Each wrapped copy stored in respective MinIO. Crypto-shredding P-xxx leaves S-xxx recoverable as a safety net.

### Phase 3: Web Dashboard

React-based admin interface for monitoring, policy management, audit log visualization, and alert handling. Communicates with the existing REST API. No new backend required.

### Phase 4: External Audit Anchoring

Publish hash chain checkpoints to an external immutable ledger (blockchain or append-only log service). Enables independent third-party verification that the audit log has not been tampered with.

### Phase 5: Certificate-Based Authentication

Replace API keys with mutual TLS (mTLS) client certificates issued by the organization's PKI. Eliminates shared-secret-based authentication.

### Phase 6: Backup Agent Enhancements

Incremental backups, compression, parallel multi-threaded uploads, scheduled backups via cron/systemd, and integration with government records management systems.

---

*End of Document — SSBG System Architecture v2.0*
