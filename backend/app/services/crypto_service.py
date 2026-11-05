import os
import json
import base64
import hashlib
from typing import Tuple, Dict, Any
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidSignature, InvalidTag

class HybridCryptoService:
    """
    Production-grade hybrid encryption and digital signature service.
    Follows RFC standards matching the Java implementation:
    - RSA-2048 with OAEP (SHA-256, MGF1-SHA256)
    - AES-256-GCM (12-byte IV, 16-byte authentication tag)
    - SHA-256 ciphertext hashing for idempotency deduplication
    - RSA-PSS / SHA-256 digital signatures for non-repudiation
    """
    RSA_KEY_SIZE = 2048
    AES_KEY_BYTES = 32 # 256 bits
    GCM_IV_BYTES = 12
    GCM_TAG_BYTES = 16
    RSA_ENCRYPTED_KEY_BYTES = 256 # 2048 bits / 8

    def __init__(self, private_key_pem: bytes = None):
        key_path = os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'server_private_key.pem')
        if private_key_pem:
            self._server_private_key = serialization.load_pem_private_key(
                private_key_pem, password=None
            )
        elif os.path.exists(key_path):
            with open(key_path, 'rb') as f:
                self._server_private_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            self._server_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=self.RSA_KEY_SIZE
            )
            try:
                os.makedirs(os.path.dirname(key_path), exist_ok=True)
                with open(key_path, 'wb') as f:
                    f.write(self._server_private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
            except Exception:
                pass
        self._server_public_key = self._server_private_key.public_key()


    @property
    def server_public_key(self):
        return self._server_public_key

    def get_server_public_key_pem(self) -> str:
        return self._server_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def get_server_public_key_base64(self) -> str:
        der = self._server_public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(der).decode('utf-8')

    def generate_sender_keypair(self) -> Tuple[str, str]:
        """Generates an RSA-2048 keypair for a simulated sender phone."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.RSA_KEY_SIZE
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        return private_pem, public_pem

    def sign_payload(self, payload: Dict[str, Any], sender_private_key_pem: str) -> str:
        """Digitally sign canonical JSON using RSA-PSS with SHA-256."""
        canonical_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        private_key = serialization.load_pem_private_key(
            sender_private_key_pem.encode('utf-8'), password=None
        )
        signature = private_key.sign(
            canonical_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')

    def verify_signature(self, payload: Dict[str, Any], signature_b64: str, sender_public_key_pem: str) -> bool:
        """Verify RSA-PSS signature against sender's registered public key."""
        try:
            canonical_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
            signature = base64.b64decode(signature_b64)
            public_key = serialization.load_pem_public_key(sender_public_key_pem.encode('utf-8'))
            public_key.verify(
                signature,
                canonical_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except (InvalidSignature, Exception):
            return False

    def encrypt(self, instruction_dict: Dict[str, Any], recipient_public_key=None) -> str:
        """
        Encrypt instruction dictionary using hybrid encryption:
        1. Generate ephemeral AES-256 key.
        2. Encrypt plaintext JSON with AES-256-GCM.
        3. Encrypt AES key with RSA-OAEP (SHA-256).
        4. Pack: [256-byte RSA-encrypted key] + [12-byte IV] + [AES-GCM ciphertext + tag]
        5. Return base64 string.
        """
        target_pub_key = recipient_public_key or self._server_public_key
        plaintext = json.dumps(instruction_dict, sort_keys=True).encode('utf-8')

        # 1. Ephemeral AES-256 key
        aes_key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(aes_key)

        # 2. Random 12-byte IV
        iv = os.urandom(self.GCM_IV_BYTES)
        aes_ciphertext_and_tag = aesgcm.encrypt(iv, plaintext, None)

        # 3. RSA-OAEP encrypt the AES key
        oaep_padding = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
        encrypted_aes_key = target_pub_key.encrypt(aes_key, oaep_padding)

        # 4. Pack binary payload
        packed = encrypted_aes_key + iv + aes_ciphertext_and_tag
        return base64.b64encode(packed).decode('utf-8')

    def decrypt(self, base64_ciphertext: str) -> Dict[str, Any]:
        """
        Decrypt hybrid ciphertext:
        - Unpack binary blob
        - Decrypt AES key with server's RSA private key
        - Decrypt and authenticate payload with AES-GCM
        - Throws exception if ciphertext or tag was tampered with!
        """
        raw = base64.b64decode(base64_ciphertext)
        min_len = self.RSA_ENCRYPTED_KEY_BYTES + self.GCM_IV_BYTES + self.GCM_TAG_BYTES
        if len(raw) < min_len:
            raise ValueError(f"Ciphertext too short: {len(raw)} bytes (minimum {min_len})")

        # Unpack slices
        encrypted_aes_key = raw[:self.RSA_ENCRYPTED_KEY_BYTES]
        iv = raw[self.RSA_ENCRYPTED_KEY_BYTES : self.RSA_ENCRYPTED_KEY_BYTES + self.GCM_IV_BYTES]
        aes_ciphertext_and_tag = raw[self.RSA_ENCRYPTED_KEY_BYTES + self.GCM_IV_BYTES :]

        # 1. Decrypt AES key with RSA-OAEP
        oaep_padding = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
        aes_key = self._server_private_key.decrypt(encrypted_aes_key, oaep_padding)

        # 2. Decrypt & verify with AES-GCM (fails with InvalidTag if tampered)
        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(iv, aes_ciphertext_and_tag, None)

        return json.loads(plaintext.decode('utf-8'))

    @staticmethod
    def hash_ciphertext(base64_ciphertext: str) -> str:
        """
        SHA-256 hex digest of the base64 ciphertext string.
        Acts as the primary network idempotency key across all bridge deliveries.
        """
        return hashlib.sha256(base64_ciphertext.encode('utf-8')).hexdigest()

    @staticmethod
    def hash_pin(pin: str) -> str:
        """SHA-256 hash of the 4-6 digit UPI PIN."""
        return hashlib.sha256(pin.encode('utf-8')).hexdigest()

# Singleton instance
crypto_service = HybridCryptoService()
