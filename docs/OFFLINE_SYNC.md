# Offline Synchronization & Reconciliation Engine

### 1. The Offline Queue Lifecycle
The client-side offline queue maintains payment requests in persistent storage through network outages.

```
[ CREATED ]
     │
     ▼
[ PENDING_OFFLINE ]  (Encrypted packet stored on device)
     │
     ▼
[ READY_TO_SYNC ]    (Peer or bridge connectivity detected)
     │
     ▼
[ SYNCING ]          (Transmission to gateway in flight)
     │
     ├──► [ COMPLETED_SIMULATION ]  (Successfully settled on core ledger)
     │
     ├──► [ REQUIRES_REVIEW ]       (Conflicting or insufficient funds)
     │
     └──► [ FAILED ]                (Corrupted or cryptographic error)
```

---

### 2. Double-Spending & Reconciliation Analysis
Without a centralized global lock, two disconnected devices can independently sign payment requests exceeding available balance.

#### The Reconciliation Policy
1. **FIFO Ingestion Order**: The first transaction received by the authoritative server is processed and settled.
2. **Conflict Flagging (`REQUIRES_REVIEW`)**: Subsequent transactions from the same account with insufficient remaining funds are not allowed to overdraft. They are flagged for human review or rejected.
3. **Hardware Wallet Alternative (UPI Lite Model)**: In commercial deployments, true offline zero-risk spending requires a tamper-proof hardware Secure Element (eSE) where balance is deducted locally before a signature is generated.
