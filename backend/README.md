# UPI Without Internet — Mesh Payment & Deferred Settlement Simulator

An advanced academic fintech research and engineering simulation demonstrating **offline digital payment routing over peer-to-peer mesh networks with hybrid cryptography, durable offline transaction queues, and idempotent ledger settlement**.

---

## 1. Project Introduction & Problem Statement

In situations of zero cellular and internet connectivity (such as natural disasters, subterranean environments, remote regions, or cellular outages), traditional digital payment protocols like UPI fail completely because they rely on synchronous, round-trip client-to-server TLS connections to authorize transactions.

### The Problem
- **No Direct Internet**: The sender's phone cannot reach the bank's core banking system (CBS).
- **Untrusted Intermediaries**: In an ad-hoc peer-to-peer mesh, packets hop through strangers' devices. How do you prevent intermediates from reading transaction amounts or tampering with parameters?
- **The Duplicate-Storm**: When multiple bridge nodes walk into cellular range (4G/5G) and simultaneously upload identical packets, how does the ledger guarantee exactly-once debit and credit?
- **Double-Spending & Stale Balance**: Without online verification, what stops a user with ₹1,000 from signing ₹800 to Alice and ₹700 to Bob on disconnected devices?

### Proposed Architecture Solution
This project transforms the original Spring Boot / Java demo into a **production-structured Python fintech engine** implementing:
1. **Hybrid Cryptography**: RSA-OAEP (SHA-256) wrapping an ephemeral AES-256-GCM authenticated session key.
2. **Digital Signatures**: RSA-PSS with SHA-256 for non-repudiation and origin verification.
3. **Idempotency Gate**: SHA-256 ciphertext hash compare-and-set (simulating Redis `SET NX EX`) backed by a database unique constraint.
4. **Durable Client Offline Queue**: State machine (`CREATED` ➔ `PENDING_OFFLINE` ➔ `READY_TO_SYNC` ➔ `SYNCING` ➔ `COMPLETED_SIMULATION` / `REQUIRES_REVIEW`).
5. **Gossip Mesh Simulator**: Multi-hop peer-to-peer propagation with TTL decrement, hop count tracking, loop prevention, and configurable packet loss.
6. **Double-Spending Conflict Demonstration**: Transparent educational simulation demonstrating why true offline prevention requires secure hardware wallets (e.g. UPI Lite Secure Element), and how deferred reconcilers protect ledger integrity.

> **CRITICAL ACADEMIC DISCLAIMER**: This application is an educational simulation of offline payment concepts. It does not connect to real NPCI infrastructure, execute real bank account transfers, or handle real fiat currency.

---

## 2. Technology Stack

- **Backend**: Python 3.11+ / Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- **Database**: SQLite (local) / PostgreSQL-ready SQLAlchemy ORM
- **Cryptography**: `cryptography` library (RSA-2048, OAEP, PSS, AES-256-GCM, SHA-256)
- **Password Security**: Argon2id via `argon2-cffi`
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js, SVG Mesh Visualizer
- **Testing**: `pytest`, ThreadPool concurrency tests, atomic integrity verification

---

## 3. Directory Structure

```
upi-offline-python/
├── app/
│   ├── __init__.py           # Application factory & seeding
│   ├── extensions.py         # SQLAlchemy, LoginManager, CSRF, Argon2
│   ├── models/               # Domain ORM models
│   │   ├── user.py           # Argon2id, roles (USER, ADMIN), RSA keys
│   │   ├── account.py        # Optimistic locking (@version) & balances
│   │   ├── transaction.py    # Idempotent ledger with packet_hash
│   │   ├── offline_queue.py  # Durable state machine for offline queue
│   │   ├── device.py         # Virtual mesh nodes
│   │   └── audit_log.py      # Immutable security audit trail
│   ├── routes/               # Modular blueprints
│   │   ├── auth.py           # Register, login, logout, me
│   │   ├── dashboard.py      # Overview metrics
│   │   ├── payments.py       # Inject, create, server-key, bridge ingest
│   │   ├── transactions.py   # Searchable & filterable ledger
│   │   ├── network.py        # Gossip, bridge flush, topology, packet loss
│   │   ├── sync.py           # Offline queue sync & double-spend demo
│   │   └── admin.py          # Users, audit logs, reset
│   ├── services/             # Core business logic
│   │   ├── crypto_service.py # RSA-OAEP + AES-256-GCM + RSA-PSS + SHA-256
│   │   ├── ledger_service.py # ACID debit/credit with optimistic locking
│   │   ├── payment_service.py# Instruction preparation & packet packaging
│   │   ├── mesh_service.py   # Multi-hop gossip & loop prevention
│   │   ├── security_service.py# Idempotency cache & ingestion pipeline
│   │   └── sync_service.py   # Reconnection & double-spend simulation
│   ├── templates/            # Jinja2 templates (Bootstrap 5)
│   └── static/               # CSS, JS, visualizer assets
├── tests/                    # 19 automated pytest unit & concurrency tests
├── docs/                     # Comprehensive technical documentation
├── config.py                 # Development, Testing, Production configs
├── run.py                    # Server entrypoint
└── requirements.txt
```

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10+ and `pip`

```bash
# 1. Clone repository
git clone https://github.com/perryvegehan/UPI_Without_Internet.git
cd upi-offline-python

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated test suite
PYTHONPATH=. pytest tests -v

# 4. Start the application
python run.py
```

The application will start on **`http://localhost:5001`**.

---

## 5. Demo Credentials

| Role | Username | Password | Assigned VPA | Initial Balance |
|---|---|---|---|---|
| User | `alice` | `alice123` | `alice@demo` | ₹5,000.00 |
| Admin | `admin` | `admin123` | `admin@demo` | N/A |
| Demo User | `bob` | N/A | `bob@demo` | ₹1,000.00 |
| Demo User | `carol` | N/A | `carol@demo` | ₹2,500.00 |
| Demo User | `dave` | N/A | `dave@demo` | ₹500.00 |

---

## 6. End-to-End Walkthrough

1. **Compose & Inject**: Select Alice, Bob, ₹500, PIN 1234. The sender generates a nonce, signs with RSA-PSS, encrypts with RSA-OAEP + AES-GCM, and injects into `phone-alice`.
2. **Hop (Gossip)**: Run 2 gossip rounds. Packets propagate across `phone-stranger1`, `phone-stranger2`, `phone-stranger3`, and `phone-bridge`. TTL decrements from 5 to 3.
3. **Bridge Flush**: `phone-bridge` hits 4G and POSTs to `/api/bridge/ingest`. The backend:
   - Claims SHA-256 ciphertext hash in idempotency cache.
   - Decrypts AES key with RSA-OAEP and decrypts payload with AES-GCM.
   - Verifies freshness window (under 24h).
   - Atomically updates ledger balances in a single database transaction.
4. **Duplicate Storm Defense**: Reset mesh, inject 1 packet, gossip twice, and flush multiple bridge nodes simultaneously. Exactly one packet settles; all others are dropped with `DUPLICATE_DROPPED`.
5. **Double-Spending Demonstration**: Navigate to the Double-Spend Demo tab to observe how conflicting offline requests against stale balances are detected and flagged as `REQUIRES_REVIEW` without corrupting ledger balances.

---

## 7. Automated Test Suite

Run all unit, integration, security, and concurrency tests:

```bash
PYTHONPATH=. pytest tests -v
```

Tests included:
- `test_user_registration` & `test_duplicate_registration_prevented`
- `test_login_and_logout` (Argon2id verification)
- `test_hybrid_crypto_round_trip` (RSA-OAEP + AES-256-GCM)
- `test_tampered_ciphertext_fails_decryption` (GCM authentication tag)
- `test_digital_signature_generation_and_verification` (RSA-PSS / SHA-256)
- `test_single_packet_delivered_by_multiple_bridges_settles_exactly_once` (Concurrent idempotency)
- `test_packet_injection_and_gossip` (TTL decrement & loop prevention)
- `test_offline_queue_creation_and_persistence` & state transitions
- `test_double_spending_demonstration_scenario` (Conflict detection & consistency)
- `test_stale_packet_is_rejected` (Replay protection)
