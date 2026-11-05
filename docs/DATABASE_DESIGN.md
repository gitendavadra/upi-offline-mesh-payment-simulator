# Database Design & Schema Documentation
## Relational Schema Specifications

### 1. Entity-Relationship Diagram (Conceptual)

```
   ┌───────────────────┐               ┌───────────────────┐
   │       users       │ 1           1 │     accounts      │
   ├───────────────────┼───────────────┼───────────────────┤
   │ id (PK)           │               │ vpa (PK)          │
   │ username (UQ)     │               │ holder_name       │
   │ email (UQ)        │               │ balance (DECIMAL) │
   │ password_hash     │               │ version (INT)     │
   │ role              │               │ user_id (FK)      │
   │ vpa (UQ)          │               │ updated_at        │
   │ public_key_pem    │               └───────────────────┘
   │ private_key_pem   │
   └───────────────────┘
             │
             │ creates
             ▼
   ┌────────────────────────┐          ┌───────────────────┐
   │     offline_queue      │          │   transactions    │
   ├────────────────────────┼──────────┼───────────────────┤
   │ id (PK)                │ settles  │ id (PK)           │
   │ queue_id (UQ)          │ ───────► │ packet_hash (UQ)  │
   │ packet_id (UQ)         │          │ idempotency_key   │
   │ sender_vpa             │          │ sender_vpa        │
   │ receiver_vpa           │          │ receiver_vpa      │
   │ amount (DECIMAL)       │          │ amount (DECIMAL)  │
   │ pin_hash               │          │ status            │
   │ nonce (UQ)             │          │ bridge_node_id    │
   │ ciphertext             │          │ hop_count         │
   │ signature              │          │ signature_valid   │
   │ status                 │          │ signed_at         │
   │ attempts               │          │ settled_at        │
   └────────────────────────┘          └───────────────────┘
```

---

### 2. Table Schemas & Constraints

#### Table: `accounts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `vpa` | VARCHAR(100) | PRIMARY KEY | Virtual Payment Address (e.g. `alice@demo`) |
| `holder_name` | VARCHAR(100) | NOT NULL | User account holder name |
| `balance` | NUMERIC(19, 2) | NOT NULL, DEFAULT 0.00 | Authoritative balance in INR |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Optimistic concurrency control lock |
| `user_id` | INTEGER | FOREIGN KEY(users.id), NULLABLE | Associated registered user ID |
| `updated_at` | TIMESTAMP | DEFAULT UTC | Last balance mutation timestamp |

#### Table: `transactions`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique transaction reference |
| `packet_hash` | VARCHAR(64) | UNIQUE, NOT NULL, INDEX | SHA-256 hex digest of ciphertext |
| `idempotency_key`| VARCHAR(64) | UNIQUE, INDEX | Unique payment intent UUID nonce |
| `sender_vpa` | VARCHAR(100) | NOT NULL, INDEX | Originating account address |
| `receiver_vpa` | VARCHAR(100) | NOT NULL, INDEX | Beneficiary account address |
| `amount` | NUMERIC(19, 2) | NOT NULL | Transaction transfer amount |
| `signed_at` | TIMESTAMP | NOT NULL | Client offline signature timestamp |
| `settled_at` | TIMESTAMP | NOT NULL | Central bank settlement timestamp |
| `bridge_node_id` | VARCHAR(100) | NOT NULL | Ingesting gateway bridge identifier |
| `hop_count` | INTEGER | NOT NULL, DEFAULT 0 | Count of peer-to-peer mesh hops |
| `status` | VARCHAR(30) | NOT NULL | `SETTLED`, `REJECTED`, `REQUIRES_REVIEW` |
| `signature_valid`| BOOLEAN | DEFAULT TRUE | RSA-PSS verification result |

#### Table: `offline_queue`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Local queue index |
| `queue_id` | VARCHAR(36) | UNIQUE, NOT NULL | Client queue entry UUID |
| `packet_id` | VARCHAR(36) | UNIQUE, NOT NULL | Wire mesh packet UUID |
| `sender_vpa` | VARCHAR(100) | NOT NULL | Sender VPA |
| `receiver_vpa` | VARCHAR(100) | NOT NULL | Recipient VPA |
| `amount` | NUMERIC(19, 2) | NOT NULL | Payment amount |
| `nonce` | VARCHAR(64) | UNIQUE, NOT NULL | Replay-prevention nonce |
| `ciphertext` | TEXT | NOT NULL | Hybrid-encrypted payload blob |
| `signature` | TEXT | NULLABLE | Base64 digital signature |
| `status` | VARCHAR(30) | NOT NULL | `PENDING_OFFLINE`, `SYNCING`, etc. |
| `attempts` | INTEGER | NOT NULL, DEFAULT 0 | Number of synchronization attempts |
