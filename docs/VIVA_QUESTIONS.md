# Comprehensive Viva Voce Questions & Answers
## UPI Without Internet (Offline Mesh Payment Simulation)

### Q1: Why is hybrid encryption necessary instead of pure RSA?
**Answer**: RSA asymmetric encryption has a strict mathematical payload limit determined by its key size minus padding overhead. For an RSA-2048 key using OAEP with SHA-256, the maximum encryptable plaintext is only 190 bytes (`256 - 2*32 - 2 = 190 bytes`). A JSON payment instruction containing sender, receiver, amount, PIN hash, timestamp, and signature exceeds this limit. Hybrid encryption solves this by using fast, authenticated symmetric AES-256-GCM to encrypt arbitrarily sized JSON payloads, and then using RSA-OAEP strictly to encrypt the 32-byte AES key.

### Q2: Why is the ciphertext hashed for idempotency rather than hashing the cleartext or using the packet ID?
**Answer**:
1. **Malicious Intermediaries**: Untrusted mesh devices can rewrite or forge the unencrypted `packetId` header.
2. **Denial-of-Service Defense**: Hashing the cleartext requires the server to perform expensive RSA decryption on every incoming packet before knowing if it's a duplicate. An attacker could flood the bridge with duplicate ciphertexts and exhaust CPU resources.
3. **Deterministic AES-GCM**: For identical plaintext, nonce, and key, the ciphertext is byte-identical. Hashing the ciphertext with SHA-256 allows an instant, O(1) atomic check-and-set *prior* to decryption.

### Q3: How does the system defend against replay attacks?
**Answer**:
1. **Freshness Window (`signedAt`)**: Inside the authenticated AES-GCM payload, the sender embeds an epoch millisecond timestamp. The backend rejects any packet where `signedAt` is older than 24 hours (86,400 seconds).
2. **Cryptographic Nonce**: Every payment instruction includes a unique UUID nonce. Even if the same user sends identical amounts to the same payee repeatedly, the different nonces yield completely different ciphertexts and hashes.

### Q4: What is the fundamental limitation of offline payments without an online connection?
**Answer**: The CAP theorem applies. In a partitioned offline network, devices cannot synchronously verify whether the sender's bank balance has been depleted elsewhere. Therefore, an offline payment receipt is an "IOU / promissory instruction," not instantaneous financial settlement. True zero-risk offline payments in real-world systems require a tamper-resistant hardware Secure Element (eSE) pre-loaded with a dedicated balance wallet (such as UPI Lite).

### Q5: What is the role of optimistic locking on the Account entity?
**Answer**: The `version` column acts as an optimistic lock. If two concurrent threads attempt to debit or credit the same account simultaneously, the database checks that the version has not mutated between read and commit. If a conflict occurs, an exception is thrown, rolling back the transaction and preventing lost updates or corrupted balances.
