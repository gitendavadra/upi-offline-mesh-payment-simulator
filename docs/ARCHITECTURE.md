# System Architecture Documentation
## UPI Without Internet — Mesh Payment & Deferred Settlement

### 1. Architectural Overview

The application utilizes an asynchronous, store-and-forward mesh routing architecture coupled with a centralized authoritative ledger settlement pipeline:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        OFFLINE SENDER CLIENT                           │
│  PaymentInstruction: { sender, receiver, amount, pinHash, nonce, time }│
│                        │                                               │
│                        ├─► 1. Sign canonical payload with RSA-PSS      │
│                        │                                               │
│                        └─► 2. Encrypt with Server RSA-OAEP + AES-GCM   │
│                                                                        │
│   MeshPacket: { packetId, ttl, createdAt, ciphertext, signature }      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                       BLE / Wi-Fi Direct Mesh Gossip
                                    ▼
       ┌───────────┐    Hop    ┌───────────┐    Hop    ┌───────────┐
       │ stranger1 │ ────────► │ stranger2 │ ────────► │  bridge   │
       └───────────┘           └───────────┘           └─────┬─────┘
                                                             │ Walks into 4G
                                                             │
                                                  HTTPS POST │ /api/bridge/ingest
                                                             ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      CENTRALIZED BANK BACKEND                          │
│                                                                        │
│   [1] SHA-256 Ciphertext Hash                                          │
│        │                                                               │
│   [2] Idempotency Gate (Atomic compare-and-set SETNX)                  │
│        │ ──► If duplicate: Drop packet (DUPLICATE_DROPPED)             │
│        │                                                               │
│   [3] Authenticated AES-GCM Decryption                                 │
│        │ ──► If tag invalid: Reject as tampered (INVALID)              │
│        │                                                               │
│   [4] Freshness Window Verification (under 24h replay protection)      │
│        │ ──► If stale: Reject (INVALID)                                │
│        │                                                               │
│   [5] RSA-PSS Signature Verification against Sender Public Key         │
│        │ ──► If invalid: Reject forged origin                          │
│        │                                                               │
│   [6] Core Ledger Settlement                                           │
│        │ ──► Verify sender balance >= amount                           │
│        │ ──► Atomic debit sender & credit receiver in DB transaction   │
│        │ ──► Version increment (optimistic locking)                    │
│        └ ──► Write immutable transaction log                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Architectural Layers

#### 2.1 Domain Layer (`app/models/`)
- Pure SQLAlchemy declarative entities representing Core Banking Accounts, Transactions, Offline Queues, Virtual Devices, Users, and Audit Logs.
- Enforces relational constraints (unique `packet_hash`, unique `idempotency_key`, positive balance constraints).

#### 2.2 Security & Cryptography Layer (`app/services/crypto_service.py`, `security_service.py`)
- Independent cryptographic service managing RSA-2048 key pairs, OAEP padding, AES-256-GCM authenticated encryption, and PSS digital signatures.
- Replay and tamper mitigation: ensures intermediaries can never forge or alter transactions.

#### 2.3 Network Simulation Layer (`app/services/mesh_service.py`)
- Models hop-by-hop gossip broadcast, TTL expiration, loop prevention, and configurable packet loss.
- Independent of actual BLE hardware, allowing end-to-end demonstrations on any host machine.

#### 2.4 Persistence & Sync Layer (`app/services/sync_service.py`, `ledger_service.py`)
- Durable offline queue maintaining state transitions.
- Atomic ACID ledger execution with optimistic locking to defend against concurrent balance mutations.

#### 2.5 Presentation Layer
- Jinja2 + Bootstrap 5 + SVG Mesh Visualizer for Python standalone mode.
- REST API layer providing seamless JSON endpoints for web and mobile clients.
