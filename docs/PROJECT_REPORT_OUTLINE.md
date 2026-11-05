# Final Year B.Tech / M.Tech Project Report Outline
## Offline Mesh Digital Payment & Deferred Settlement System

### Chapter 1: Introduction
- 1.1 Motivation & Background
- 1.2 Digital Payment Adoption in Developing Nations (UPI in India)
- 1.3 Challenges of Connectivity Blackouts and Disconnected Zones
- 1.4 Objectives of the Research Project
- 1.5 Organization of the Report

### Chapter 2: Literature Review & Existing Systems
- 2.1 Survey of Existing Offline Payment Standards (UPI Lite, Apple Pay Cash, Visa Offline)
- 2.2 Peer-to-Peer Ad-Hoc Mesh Networking Protocols (BLE GATT, Wi-Fi Direct, B.A.T.M.A.N.)
- 2.3 Store-and-Forward Delay Tolerant Networks (DTN)
- 2.4 Cryptographic Standards in Banking: Hybrid Encryption and Authenticated Ciphers
- 2.5 Gap Analysis of the Existing Spring Boot Demonstration

### Chapter 3: System Requirements & Mathematical Modeling
- 3.1 Functional & Non-Functional Specifications
- 3.2 Formal Security Model & Adversarial Assumptions
- 3.3 Cryptographic Primitives:
  - RSA-OAEP with SHA-256 and Optimal Asymmetric Encryption Padding
  - AES-256 in Galois/Counter Mode (GCM)
  - RSA Probabilistic Signature Scheme (PSS)
- 3.4 Gossip Propagation Mathematical Model (Epidemic Spreading & TTL Limits)

### Chapter 4: Architecture & Detailed Design
- 4.1 Multi-Tier Modular Python Architecture
- 4.2 Entity-Relationship & Relational Database Design
- 4.3 Client-Side Durable Offline Queue State Machine
- 4.4 Bridge Ingestion Pipeline & Idempotency Filter
- 4.5 ACID Core Banking Ledger with Optimistic Locking

### Chapter 5: Implementation Details
- 5.1 Python Backend & Flask Application Factory
- 5.2 Cryptography Implementation with Python `cryptography`
- 5.3 Mesh Simulator & Gossip Propagation Engine
- 5.4 Double-Spending Simulation & Conflict Handling Module
- 5.5 High-Performance FinTech UI & Interactive SVG Visualizer

### Chapter 6: Testing, Concurrency Verification & Results
- 6.1 Automated Unit & Integration Testing using `pytest`
- 6.2 Multi-Threaded Concurrency Testing (Simultaneous Duplicate Storm)
- 6.3 Security Testing (Ciphertext Bit-Flipping, Replay Attacks, Tamper Detection)
- 6.4 Double-Spending Reconciliation Empirical Results

### Chapter 7: Honest Limitations & Future Scope
- 7.1 CAP Theorem Implications on Offline Settlements
- 7.2 Hardware Security Module (HSM) and Secure Element (eSE) Integration
- 7.3 Android Kotlin Port with Native Android BLE GATT Central/Peripheral Stack
- 7.4 Zero-Knowledge Proofs (ZKP) for Stale Balance Verification

### Chapter 8: Conclusion
- Summary of Contributions and Final Remarks
- References & Appendix
