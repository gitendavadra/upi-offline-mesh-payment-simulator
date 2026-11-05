# Software Requirements Specification (SRS)
## UPI Without Internet — Mesh Payment & Deferred Settlement Simulation

### 1. Introduction
#### 1.1 Purpose
This document specifies the software requirements for the UPI Offline Mesh Payment Simulator. It details the functional and non-functional requirements for an academic simulation demonstrating deferred digital payment settlement across untrusted peer-to-peer mesh networks.

#### 1.2 Scope
The application simulates an offline ecosystem where smartphones without internet connectivity generate encrypted, digitally signed payment instructions, gossip them across nearby devices over a simulated Bluetooth mesh, and hand them off to internet-connected bridge devices for server-side verification and atomic ledger settlement.

#### 1.3 Intended Audience
- Software Engineering evaluators and viva examiners
- Computer Science / Information Technology faculty
- Cybersecurity & FinTech students and researchers

---

### 2. Overall Description
#### 2.1 Product Perspective
In traditional UPI (Unified Payments Interface), the sender, payee, and banks communicate in real-time over cellular/broadband networks. In this project, the network layer is decoupled from real-time internet availability using asynchronous mesh routing.

#### 2.2 User Characteristics
- **Standard User (e.g., Alice, Bob)**: Can view simulated balances, compose online or offline payments, review ledger history, and inspect held packets.
- **System Administrator**: Can inspect global audit logs, review system performance, manage user roles, and trigger system factory resets.

---

### 3. Functional Requirements

#### FR-01: User Authentication & Role Management
- The system shall hash user passwords using Argon2id with recommended memory and time cost parameters.
- The system shall enforce role-based access control (USER, ADMIN).
- Upon registration, the system shall generate a dedicated RSA-2048 signing keypair for the client device.

#### FR-02: Payment Instruction Generation
- The sender device shall generate a unique cryptographic nonce (UUID) per transaction intent.
- The instruction shall record a high-resolution epoch timestamp (`signedAt`) for freshness verification.
- The payment amount must be strictly greater than zero and formatted with 2 decimal places.

#### FR-03: Hybrid Cryptography & Non-Repudiation
- The client shall encrypt cleartext instructions using an ephemeral AES-256 key with AES-GCM.
- The client shall wrap the AES key using RSA-OAEP with SHA-256 and MGF1 padding using the server's public key.
- The client shall sign the canonical instruction payload using RSA-PSS with SHA-256 for non-repudiation.

#### FR-04: Multi-Hop Mesh Simulation
- The simulator shall model at least 5 nodes (`phone-alice`, `phone-stranger1`, `phone-stranger2`, `phone-stranger3`, `phone-bridge`).
- Packets shall have a Time-To-Live (TTL) field decremented on each gossip hop.
- Devices shall reject duplicate packet IDs to prevent routing loops.
- Configurable packet loss (0% to 50%) shall be supported.

#### FR-05: Idempotency & Duplicate-Storm Gate
- The server shall compute the SHA-256 hash of inbound ciphertext prior to decryption.
- The server shall atomically claim the hash in an idempotency cache.
- Duplicate deliveries of the same ciphertext shall be immediately dropped with `DUPLICATE_DROPPED`.

#### FR-06: Atomic Ledger Settlement
- The core banking ledger shall execute debit and credit operations within an atomic database transaction.
- If sender balance is insufficient, the system shall record a `REJECTED` transaction without balance modification.
- Optimistic locking (version increment) shall protect accounts against concurrent update corruption.

#### FR-07: Durable Offline Transaction Queue
- Offline payments shall persist across server restarts in an SQLite database.
- Queue items shall follow strict state transitions:
  `CREATED` ➔ `PENDING_OFFLINE` ➔ `READY_TO_SYNC` ➔ `SYNCING` ➔ `COMPLETED_SIMULATION` / `FAILED` / `REQUIRES_REVIEW`.

#### FR-08: Double-Spending Conflict Demonstration
- The system shall provide an academic demonstration of two disconnected devices signing competing payments against stale balances.
- The first arriving transaction shall settle; the second shall be flagged as `REQUIRES_REVIEW` and rejected, preserving final ledger consistency.

---

### 4. Non-Functional Requirements
- **Performance**: Cryptographic packet ingestion must complete in under 50ms per transaction.
- **Security**: AES-GCM must detect single-bit tampering and throw authentication exceptions.
- **Maintainability**: Modular Python architecture adhering to PEP 8 standards.
- **Compatibility**: Responsive web interface compatible with modern browsers.
