import pytest
import base64
from app.services.crypto_service import HybridCryptoService

def test_hybrid_crypto_round_trip():
    crypto = HybridCryptoService()
    instruction = {
        'senderVpa': 'alice@demo',
        'receiverVpa': 'bob@demo',
        'amount': '250.00',
        'pinHash': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'nonce': '123e4567-e89b-12d3-a456-426614174000',
        'signedAt': 1730000000000
    }

    ciphertext_b64 = crypto.encrypt(instruction)
    assert isinstance(ciphertext_b64, str)
    assert len(ciphertext_b64) > 256

    decrypted = crypto.decrypt(ciphertext_b64)
    assert decrypted['senderVpa'] == 'alice@demo'
    assert decrypted['receiverVpa'] == 'bob@demo'
    assert decrypted['amount'] == '250.00'
    assert decrypted['nonce'] == '123e4567-e89b-12d3-a456-426614174000'

def test_tampered_ciphertext_fails_decryption():
    crypto = HybridCryptoService()
    instruction = {'senderVpa': 'alice@demo', 'amount': '500.00'}
    ciphertext_b64 = crypto.encrypt(instruction)

    # Decode and flip one byte in the AES ciphertext/tag payload
    raw = bytearray(base64.b64decode(ciphertext_b64))
    raw[-5] ^= 0xFF # Flip bits in the GCM tag area
    tampered_b64 = base64.b64encode(raw).decode('utf-8')

    with pytest.raises(Exception):
        crypto.decrypt(tampered_b64)

def test_ciphertext_hashing_is_deterministic():
    crypto = HybridCryptoService()
    ct1 = "VGVzdENpcGhlcnRleHRQYWNraW5n"
    h1 = crypto.hash_ciphertext(ct1)
    h2 = crypto.hash_ciphertext(ct1)
    assert h1 == h2
    assert len(h1) == 64 # SHA-256 hex length

def test_digital_signature_generation_and_verification():
    crypto = HybridCryptoService()
    priv_pem, pub_pem = crypto.generate_sender_keypair()

    payload = {
        'senderVpa': 'alice@demo',
        'receiverVpa': 'bob@demo',
        'amount': '100.00',
        'nonce': 'random-nonce-99'
    }

    sig = crypto.sign_payload(payload, priv_pem)
    assert isinstance(sig, str)

    # Valid signature
    assert crypto.verify_signature(payload, sig, pub_pem) is True

    # Tampered payload fails verification
    tampered = dict(payload)
    tampered['amount'] = '9999.00'
    assert crypto.verify_signature(tampered, sig, pub_pem) is False

    # Wrong public key fails verification
    _, other_pub = crypto.generate_sender_keypair()
    assert crypto.verify_signature(payload, sig, other_pub) is False
