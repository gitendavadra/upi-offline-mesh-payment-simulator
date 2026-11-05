# REST API Specification
## UPI Offline Mesh Payment Simulator

All request and response payloads use JSON unless otherwise stated.

---

### 1. Cryptographic Key Distribution

#### `GET /api/server-key`
Returns the centralized server's public key for offline client caching.

**Response (200 OK):**
```json
{
  "publicKey": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...",
  "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBg...",
  "algorithm": "RSA-2048 / OAEP-SHA256",
  "hybridScheme": "RSA-OAEP encrypts an ephemeral AES-256-GCM session key",
  "signatureAlgorithm": "RSA-PSS with SHA-256 for sender non-repudiation"
}
```

---

### 2. Mesh Simulation Endpoints

#### `POST /api/demo/send`
Simulates a sender phone creating an encrypted payment instruction and dropping it into the mesh.

**Request:**
```json
{
  "senderVpa": "alice@demo",
  "receiverVpa": "bob@demo",
  "amount": 500.00,
  "pin": "1234",
  "ttl": 5,
  "startDevice": "phone-alice"
}
```

**Response (200 OK):**
```json
{
  "packetId": "d9e8f7a6-1234-5678-9abc-def012345678",
  "injectedAt": "phone-alice",
  "ttl": 5,
  "ciphertextPreview": "VGVzdFJhbmRvbUNpcGhlcnRleHRQYXlsb2Fk...",
  "signature": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNAD..."
}
```

#### `GET /api/mesh/state`
Returns the real-time buffer state of all virtual devices in the mesh.

#### `POST /api/mesh/gossip`
Executes one round of gossip broadcast forwarding across peer devices. TTL is decremented.

#### `POST /api/mesh/flush`
Simulates all devices with `hasInternet=true` walking into cellular coverage and concurrently uploading held packets to `/api/bridge/ingest`.

#### `POST /api/mesh/reset`
Flushes held packets on all devices and clears the in-memory idempotency cache.

---

### 3. Gateway Ingestion (The Production Contract)

#### `POST /api/bridge/ingest`
The primary production-shaped endpoint invoked by any bridge node with internet connectivity.

**Headers:**
- `X-Bridge-Node-Id`: `phone-bridge-01`
- `X-Hop-Count`: `3`

**Request:**
```json
{
  "packetId": "d9e8f7a6-1234-5678-9abc-def012345678",
  "ciphertext": "packed-base64-rsa-aes-gcm-blob",
  "signature": "optional-base64-sender-rsa-pss-signature"
}
```

**Outcomes:**
- `SETTLED`: Payment decrypted, validated, freshness verified, and ledger updated.
- `DUPLICATE_DROPPED`: Ciphertext hash already processed; dropped before decryption.
- `REJECTED`: Sender balance insufficient.
- `INVALID`: Tampered ciphertext, bad auth tag, or expired timestamp (> 24h).

---

### 4. Offline Queue & Synchronization

#### `GET /api/sync/queue`
Lists all durable offline queued transactions.

#### `POST /api/sync/run`
Executes the synchronization engine across all pending offline items.

#### `POST /api/sync/double-spend-demo`
Executes the controlled academic demonstration of competing offline transactions.

---

### 5. Accounts & Ledger

#### `GET /api/accounts`
Lists all bank accounts, VPAs, balances, and optimistic lock versions.

#### `GET /api/transactions`
Query parameters: `search`, `status`, `limit`, `offset`.
Returns filtered, searchable ledger records.
