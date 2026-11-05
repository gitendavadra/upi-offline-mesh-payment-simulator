# Threat Modeling & Security Architecture

### 1. Threat Model & Mitigations

| Threat | Attack Scenario | Implemented Defense Mechanism |
|---|---|---|
| **Eavesdropping by Intermediaries** | Untrusted stranger phone reads payment amount or PIN | **Hybrid RSA-OAEP + AES-GCM**: Payload is opaque ciphertext; only central bank holds private key. |
| **Payload Tampering** | Intermediary flips bits to alter amount from ₹100 to ₹10,000 | **AES-256-GCM Auth Tag**: Any 1-bit alteration causes authenticated decryption to throw `InvalidTag`. |
| **Replay Attacks** | Attacker captures valid ciphertext and submits it weeks later | **Dual-Layer Defense**: 1) `signedAt` epoch timestamp rejected if > 24 hours old. 2) Unique UUID nonces. |
| **Duplicate Storms** | 3 bridge nodes simultaneously deliver the same packet | **Atomic Idempotency Gate**: SHA-256 hash claimed atomically via compare-and-set prior to decryption. |
| **Credential Theft** | Offline rainbow tables or brute force on passwords | **Argon2id Hashing**: Time cost 3, 64 MB memory cost, 4 parallel lanes. |
| **Origin Impersonation** | Rogue client submits payment on behalf of another user | **RSA-PSS Digital Signatures**: Sender signs canonical JSON with device private key verified by server. |

---

### 2. Cryptographic Scheme Details

#### Wire Format
```
[ 256 bytes RSA-OAEP encrypted AES Key ][ 12 bytes GCM IV ][ Variable Ciphertext + 16-byte Tag ]
```
1. **AES-256-GCM**: Provides both confidentiality and integrity in a single authenticated pass.
2. **RSA-OAEP with SHA-256 & MGF1**: Protects against chosen-ciphertext attacks (CCA2) on the symmetric session key.
3. **SHA-256 Ciphertext Hash**: Deduplicates packets *before* performing expensive RSA decryption, neutralizing denial-of-service (DoS) attempts.
