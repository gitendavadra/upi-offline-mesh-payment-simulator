# UPI Without Internet — Mesh Payment & Deferred Settlement Simulator

> **An advanced academic fintech and cybersecurity simulation demonstrating peer-to-peer offline payment routing over ad-hoc mesh networks with hybrid RSA/AES cryptography, durable offline transaction queues, and idempotent ledger reconciliation.**

---

> ### ⚠️ ACADEMIC SIMULATION DISCLAIMER
> **This software is strictly an educational research simulation developed for Computer Engineering demonstrations, university capstone presentations, and technical portfolios.**
> - It **does NOT connect to NPCI** (National Payments Corporation of India) production switches.
> - It **does NOT interface with real bank accounts**, core banking systems (CBS), or real fiat currency.
> - All accounts, balances, keys, and device identities in this demonstration are **cryptographically simulated entities**.

---

## Badges & Status

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?style=flat&logo=flask&logoColor=white)
![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=flat&logo=vite&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-19%20Passed%20(100%25)-brightgreen?style=flat&logo=pytest&logoColor=white)
![Node Tests](https://img.shields.io/badge/Node%20Tests-6%20Passed%20(100%25)-brightgreen?style=flat&logo=node.js&logoColor=white)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

---

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [High-Level Architecture Overview](#2-high-level-architecture-overview)
3. [Key Cryptographic & Security Mechanisms](#3-key-cryptographic--security-mechanisms)
4. [Mesh Network & Gossip Routing Simulation](#4-mesh-network--gossip-routing-simulation)
5. [Offline Transaction Lifecycle & State Machine](#5-offline-transaction-lifecycle--state-machine)
6. [Double-Spending Mitigation & Conflict Resolution](#6-double-spending-mitigation--conflict-resolution)
7. [Offline QR Code Generation & Scanning](#7-offline-qr-code-generation--scanning)
8. [Repository Directory Structure](#8-repository-directory-structure)
9. [Prerequisites & System Requirements](#9-prerequisites--system-requirements)
10. [Backend Installation & Setup](#10-backend-installation--setup)
11. [Frontend Installation & Setup](#11-frontend-installation--setup)
12. [Unified Development Server Guide](#12-unified-development-server-guide)
13. [Automated Testing Guide](#13-automated-testing-guide)
14. [Security Audit & Hardening](#14-security-audit--hardening)
15. [Comparison with Original Java Implementation](#15-comparison-with-original-java-implementation)
16. [Real-World Industry Context (RBI / NPCI UPI Lite)](#16-real-world-industry-context-rbi--npci-upi-lite)
17. [Project Documentation Index](#17-project-documentation-index)
18. [Contributing & Code of Conduct](#18-contributing--code-of-conduct)
19. [License & Acknowledgements](#19-license--acknowledgements)

---

## 1. Executive Summary & Problem Statement

Standard Unified Payments Interface (UPI) protocols rely unconditionally on **synchronous, round-trip client-to-server TLS connections** between the sender's mobile handset, the payment service provider (PSP), NPCI, and the issuing/acquiring Core Banking Systems (CBS). 

When cellular connectivity fails—during natural disasters, subterranean transit, rural blackouts, or network congestion—traditional digital payments halt completely.

### Fundamental Engineering Challenges in Disconnected Environments:
1. **Zero Direct Connectivity**: Senders cannot communicate with banking authorization servers.
2. **Untrusted Intermediaries**: If payment packets travel via multi-hop peer devices (strangers' phones), intermediaries must not be capable of reading transaction amounts, extracting payer credentials, or tampering with recipient VPAs.
3. **The Bridge Storm Problem (Duplicate Delivery)**: When multiple bystander devices subsequently walk into cellular range (4G/5G) and simultaneously ingest identical packets into the banking gateway, the ledger must guarantee **strictly exactly-once execution**.
4. **Offline Double-Spending**: Without an online balance check, a rogue user could sign multiple conflicting offline payment promises exceeding their available liquid funds.

This project delivers a **full-stack, production-modeled software architecture** solving these challenges through authenticated hybrid cryptography, deterministic SHA-256 deduplication gates, gossip-based mesh forwarding, and deferred multi-pass ledger settlement.

---

## 2. High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OFFLINE SENDER HANDSET                            │
│                                                                             │
│  [1. Canonical Payload] ──► [2. RSA-PSS Signature]                          │
│                                      │                                      │
│  [3. Ephemeral AES-256 Key] ──► [4. AES-GCM Encrypt] ──► [5. RSA-OAEP Wrap]│
│                                      │                                      │
│                       [Encrypted Mesh Packet]                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                      BLE / Wi-Fi Direct Mesh Gossip
                                       ▼
        ┌─────────────┐       Hop       ┌─────────────┐       Hop       ┌─────────────┐
        │  stranger1  │ ──────────────► │  stranger2  │ ──────────────► │    bridge   │
        └─────────────┘                 └─────────────┘                 └──────┬──────┘
                                                                               │ Cellular
                                                                               │ 4G/5G
                                                                    HTTPS POST │ /api/bridge/ingest
                                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CENTRALIZED BANK BACKEND                           │
│                                                                             │
│   Gate 1: SHA-256 Ciphertext Hash Calculation                               │
│           └─► Checked against Idempotency Gate (In-Memory + DB Unique)      │
│               Duplicate? ──► DROP IMMEDIATELY (DUPLICATE_DROPPED)           │
│                                                                             │
│   Gate 2: Authenticated AES-256-GCM Decryption (Tag Check)                  │
│           Tampered? ──► REJECT AS TAMPERED (INVALID)                        │
│                                                                             │
│   Gate 3: Freshness Window Check (< 24 Hours)                               │
│           Expired? ──► REJECT AS REPLAY (INVALID)                           │
│                                                                             │
│   Gate 4: Sender RSA-PSS Digital Signature Verification                     │
│           Invalid Signature? ──► REJECT AS FORGED (INVALID)                 │
│                                                                             │
│   Gate 5: Authoritative Ledger Settlement                                   │
│           Sufficient Balance?                                               │
│           ├── YES ──► Atomic Debit/Credit ──► Status: SETTLED               │
│           └── NO  ──► Balance Overdraft   ──► Status: REJECTED              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Cryptographic & Security Mechanisms

### Hybrid Encryption Envelope
To preserve data privacy and cryptographic integrity while traversing untrusted mesh nodes, transactions are sealed inside a dual-layer cryptographic envelope:
1. **Symmetric Layer (AES-256-GCM)**:
   - Each transaction generates a cryptographically secure 256-bit ephemeral key and a 12-byte random Initialization Vector (IV).
   - Payload is encrypted with Galois/Counter Mode (GCM), generating a 16-byte authentication tag ensuring ciphertext integrity.
2. **Asymmetric Layer (RSA-OAEP)**:
   - The ephemeral AES key is wrapped with the Central Bank Server's 2048-bit RSA public key using Optimal Asymmetric Encryption Padding (OAEP) parameterized with SHA-256.
   - Intermediary nodes cannot decrypt or inspect transaction data.
3. **Digital Signatures (RSA-PSS with SHA-256)**:
   - The sender signs the canonical transaction data with their local private key.
   - Guarantees **non-repudiation**; the sender cannot later claim they did not authorize the debit.
4. **Deterministic Idempotency Hash**:
   - `SHA-256(ciphertext)` is computed immediately upon ingestion.
   - If two or more bridges deliver the identical packet, the second and subsequent packets are intercepted and dropped before decryption or database modification.
5. **Credential Security**:
   - User credentials use **Argon2id** password hashing (`argon2-cffi`), the winner of the Password Hashing Competition.

---

## 4. Mesh Network & Gossip Routing Simulation

The application implements a gossip-based ad-hoc mesh network:
- **Node Topologies**: Pre-configured nodes including `phone-alice`, `phone-stranger1`, `phone-stranger2`, `phone-stranger3`, and `phone-bridge`.
- **Hop Count & Time-To-Live (TTL)**: Packets carry a TTL field (default: 5 hops). Each hop decrements TTL. When TTL reaches 0, the packet is discarded to prevent infinite mesh congestion.
- **Loop Prevention**: Nodes maintain a memory of recently forwarded packet IDs; looped packets are ignored.
- **Bridge Gateway**: When designated bridge nodes establish network connectivity, they collect packets stored in their local buffers and flush them to the server ingestion endpoint (`/api/bridge/ingest`).

---

## 5. Offline Transaction Lifecycle & State Machine

Transactions advance through a deterministic state machine:

```
  [CREATED]
      │
      ▼ (Offline Payment Stored Locally)
  [PENDING_OFFLINE]
      │
      ▼ (Device Prepares for Network Link)
  [READY_TO_SYNC]
      │
      ▼ (Bridge Flush / Direct Upload Initiated)
  [SYNCING]
      │
      ├──────────────────────┬──────────────────────┐
      ▼                      ▼                      ▼
  [SETTLED]              [REJECTED]        [REQUIRES_REVIEW]
  (Ledger Debited        (Insufficient      (Double-Spend Attempt /
   & Credited)            Funds)             Concurrent Conflict)
```

---

## 6. Double-Spending Mitigation & Conflict Resolution

In pure offline environments without trusted secure hardware, a malicious actor could sign two distinct payments totaling more than their account balance. 

### Educational Conflict Demonstration:
- The simulator demonstrates both:
  1. **Online Authoritative Rejection**: The ledger settles whichever valid transaction arrives first. Subsequent conflicting transactions are marked `REJECTED (insufficient_balance)` or `REQUIRES_REVIEW`.
  2. **Hardware Security Architecture (UPI Lite Model)**: In real-world offline payments, transactions are restricted to an on-device **Secure Element (SE) / eSIM applet** maintaining a strict offline ledger cap (e.g. ₹500 per transaction, ₹2000 total wallet balance) that physically prevents signing conflicting requests.

---

## 7. Offline QR Code Generation & Scanning

The simulator features full offline QR code generation:
- **Standard NPCI UPI Intent URI**: Generates interoperable URIs:
  `upi://pay?pa=receiver@bank&pn=ReceiverName&am=500.00&cu=INR&tn=OfflineRef`
- **Offline Mesh Cryptographic Payload**: Encodes structured JSON containing the signed packet ID, ciphertext hash, timestamp, and digital signature, allowing optical peer-to-peer transmission between devices without Bluetooth or Wi-Fi.

---

## 8. Repository Directory Structure

```
UPI_Without_Internet/
│
├── README.md                      # Master 22-section comprehensive documentation
├── LICENSE                        # Apache 2.0 Open Source License
├── CONTRIBUTING.md                # Contribution guidelines and code standards
├── .gitignore                     # Comprehensive ignore rules (Python, Node, SQLite, OS)
├── .gitattributes                 # Cross-platform LF line-ending normalization
├── .env.example                   # Environment configuration template
│
├── backend/                       # Python Flask Banking & Cryptographic Engine
│   ├── app/
│   │   ├── models/                # SQLAlchemy Models (Account, Transaction, User, Device, AuditLog)
│   │   ├── routes/                # Blueprint Controllers (payments, sync, mesh, auth, dashboard)
│   │   ├── services/              # Core Services (crypto_service, security_service, ledger, mesh)
│   │   ├── templates/             # Server-rendered Jinja2 UI (Bootstrap 5 + Chart.js)
│   │   ├── static/                # Static assets, CSS, and client JavaScript
│   │   ├── extensions.py          # SQLAlchemy & Flask-Login instances
│   │   └── __init__.py            # Flask Application Factory
│   ├── tests/                     # Pytest automated test suite (19 integration tests)
│   ├── instance/                  # Local runtime data directory (.gitkeep)
│   ├── config.py                  # Environment configurations (Dev, Test, Prod)
│   ├── run.py                     # Backend executable entry point (Port 5001)
│   ├── requirements.txt           # Python pinned dependencies
│   └── .env.example               # Backend environment variables
│
├── frontend/                      # Standalone React + TypeScript Dashboard & Simulator
│   ├── src/
│   │   ├── utils/                 # Utility functions (formatters, offline QR generator)
│   │   │   ├── formatters.ts      # Currency & hash truncator logic
│   │   │   ├── formatters.test.ts # Node.js unit tests for formatters
│   │   │   ├── qr.ts              # NPCI intent & offline payload builders
│   │   │   └── qr.test.ts         # Node.js unit tests for QR generators
│   │   ├── App.tsx                # Main interactive simulator and ledger dashboard
│   │   ├── main.tsx               # React 19 entry point
│   │   └── index.css              # Tailwind CSS styles
│   ├── public/                    # Static public assets
│   ├── index.html                 # HTML5 entry point
│   ├── package.json               # Frontend dependencies & npm test scripts
│   ├── tsconfig.json              # TypeScript compiler configuration
│   └── vite.config.ts             # Vite build & proxy configuration
│
├── docs/                          # In-depth architectural & academic documentation
│   ├── ARCHITECTURE.md            # Detailed system design & component diagrams
│   ├── SRS.md                     # Software Requirements Specification
│   ├── DATABASE_DESIGN.md         # Schema diagrams & relational tables
│   ├── API_DOCUMENTATION.md       # Comprehensive REST API specifications
│   ├── SECURITY.md                # Threat model, attack vectors & mitigations
│   ├── OFFLINE_SYNC.md            # Queue state transitions & reconciliation rules
│   ├── MESH_NETWORK.md            # Gossip propagation & bridge ingestion mechanics
│   ├── TESTING_REPORT.md          # Automated test execution report (25 passing tests)
│   ├── VIVA_QUESTIONS.md          # 20 Academic viva examination Q&As with answers
│   └── PROJECT_REPORT_OUTLINE.md  # Formal university capstone report chapter outline
│
├── original-java-repo/            # Preserved Spring Boot 3 / Java 17 reference project
│   ├── src/                       # Original Java source code
│   ├── pom.xml                    # Maven configuration
│   └── README.md                  # Original repository documentation
│
└── .github/
    └── workflows/
        └── tests.yml              # GitHub Actions CI matrix (Python 3.11/3.12 + Node 18/20)
```

---

## 9. Prerequisites & System Requirements

- **Operating System**: Linux, macOS, or Windows 10/11 (WSL2 recommended on Windows)
- **Python**: Version `3.11.x` or `3.12.x`
- **Node.js**: Version `18.x`, `20.x`, or higher
- **Package Managers**: `pip` and `npm`

---

## 10. Backend Installation & Setup

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables (optional, defaults provided):
   ```bash
   cp .env.example .env
   ```
5. Launch the Flask backend:
   ```bash
   python run.py
   ```
   The backend server initializes on `http://127.0.0.1:5001`.

---

## 11. Frontend Installation & Setup

1. Open a terminal and navigate to the root or `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Launch the Vite development server:
   ```bash
   npm run dev
   ```
   The interactive React application starts on `http://localhost:3000`.

---

## 12. Unified Development Server Guide

In this repository, the root configuration orchestrates seamless development. API calls made from the React frontend (`/api/*` and `/auth/*`) are automatically reverse-proxied to `http://127.0.0.1:5001`.

To run both concurrently:
- **Terminal 1**: `cd backend && python run.py`
- **Terminal 2**: `npm run dev`

Open your browser at `http://localhost:3000` to interact with the full-stack visualizer and payment engine.

---

## 13. Automated Testing Guide

The codebase enforces strict test-driven reliability with **25 automated tests** across both backend and frontend.

### Running All Tests in One Command
```bash
npm run test:all
```

### Running Backend Pytest Suite
```bash
pytest backend/tests -v
```
**Test Suite Coverage (19 tests)**:
- Authentication & Argon2id password hashing
- Hybrid RSA-OAEP + AES-256-GCM encryption round-trip
- 1-bit tampering detection via AES-GCM authentication tags
- Idempotency gate duplicate packet drop (concurrent thread execution)
- Gossip mesh propagation and TTL decrement
- Durable offline transaction queue state machine
- Double-spending conflict resolution demonstration

### Running Frontend Unit Tests
```bash
npm test
```
**Test Suite Coverage (6 tests)**:
- Currency formatting & integer boundary handling
- SHA-256 cryptographic hash truncation
- NPCI UPI Intent URI generation
- Offline QR payload formatting

### TypeScript Static Typecheck
```bash
npm run lint
```

---

## 14. Security Audit & Hardening

- **Zero Hardcoded Secrets**: All cryptographic keys and database paths are generated dynamically at runtime or loaded from environment variables.
- **Strict `.gitignore`**: Database files (`*.db`), private keys (`*.pem`), and environment files (`.env`) are excluded from version control.
- **Cross-Site Request Forgery (CSRF)**: Enforced via `Flask-WTF` on all state-altering POST/PUT requests.
- **Secure Cookie Flags**: Session cookies set `HttpOnly=True` and `SameSite=Lax`.
- **Timing Attack Resilience**: Key comparisons and signature checks use constant-time operations provided by the Python `cryptography` library.

---

## 15. Comparison with Original Java Implementation

| Architectural Component | Original Java Repo (`original-java-repo/`) | Modern Python / React Architecture |
|---|---|---|
| **Language & Runtime** | Java 17 / Spring Boot 3.3.5 | Python 3.11+ (Flask) + React 19 (TypeScript) |
| **Cryptography** | Java `javax.crypto` + `java.security` | Python `cryptography` (OpenSSL backend) |
| **Password Security** | Standard Spring Security BCrypt | **Argon2id** (`argon2-cffi`) |
| **UI Presentation** | Server-rendered Thymeleaf HTML | High-performance React SPA + Live SVG Mesh |
| **Offline QR Codes** | None | Real-time NPCI Intent & Offline Payload QR Generator |
| **Test Concurrency** | Basic JUnit | ThreadPool concurrent bridge storm simulation |

---

## 16. Real-World Industry Context (RBI / NPCI UPI Lite)

This academic simulation models concepts actively used in real-world offline payments:
- **UPI Lite (RBI / NPCI)**: On-device offline balance wallet designed for small-value transactions without querying the core banking server.
- **UPI 123PAY**: Interactive Voice Response (IVR) and sound-wave based offline payments for feature phones.
- **Central Bank Digital Currency (CBDC / Digital Rupee)**: Reserve Bank of India offline digital token transfer over NFC and Bluetooth mesh networks.

---

## 17. Project Documentation Index

Detailed documentation files are available in the [`docs/`](./docs/) directory:

- 📖 [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — Comprehensive technical architecture & message flow diagrams.
- 📋 [`docs/SRS.md`](./docs/SRS.md) — Formal Software Requirements Specification (IEEE 830 compliant).
- 🗄️ [`docs/DATABASE_DESIGN.md`](./docs/DATABASE_DESIGN.md) — Entity-relationship diagrams and table schemas.
- 🔌 [`docs/API_DOCUMENTATION.md`](./docs/API_DOCUMENTATION.md) — Complete REST API reference with payload schemas.
- 🔒 [`docs/SECURITY.md`](./docs/SECURITY.md) — Threat model (STRIDE), attack vectors, and cryptographic proofs.
- 🔄 [`docs/OFFLINE_SYNC.md`](./docs/OFFLINE_SYNC.md) — Transaction queue synchronization and conflict resolution logic.
- 📡 [`docs/MESH_NETWORK.md`](./docs/MESH_NETWORK.md) — Peer-to-peer gossip routing, TTL, and bridge mechanics.
- 🧪 [`docs/TESTING_REPORT.md`](./docs/TESTING_REPORT.md) — Full automated testing results and test matrix.
- 🎓 [`docs/VIVA_QUESTIONS.md`](./docs/VIVA_QUESTIONS.md) — 20 academic viva questions with detailed answers.
- 📑 [`docs/PROJECT_REPORT_OUTLINE.md`](./docs/PROJECT_REPORT_OUTLINE.md) — University engineering project report chapter outline.

---

## 18. Contributing & Code of Conduct

Contributions, issues, and feature proposals are welcome! Please review [CONTRIBUTING.md](./CONTRIBUTING.md) for style guidelines, branch naming conventions, and testing requirements.

---

## 19. License & Acknowledgements

- **License**: Licensed under the **Apache License, Version 2.0**. See [LICENSE](./LICENSE) for full details.
- **Original Project**: Built upon research inspired by the original `UPI_Without_Internet` repository by [perryvegehan](https://github.com/perryvegehan/UPI_Without_Internet).
- **Academic Context**: Designed for Computer Science and Engineering students, fintech enthusiasts, and security researchers exploring resilient financial protocols.
