import time
import threading
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.extensions import db
from app.models.transaction import Transaction
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.crypto_service import crypto_service
from app.services.ledger_service import ledger_service

logger = logging.getLogger(__name__)

class IdempotencyCache:
    """
    Thread-safe in-memory idempotency cache simulating Redis SET NX EX.
    Backed by database unique constraint for defense-in-depth.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._seen: Dict[str, float] = {} # hash -> timestamp

    def claim(self, packet_hash: str) -> bool:
        """
        Atomic test-and-set. Returns True if this is the first claimer,
        False if the hash has already been seen (duplicate).
        """
        with self._lock:
            # 1. Memory check
            now = time.time()
            if packet_hash in self._seen:
                return False

            # 2. Database check (defense-in-depth)
            existing = Transaction.query.filter_by(packet_hash=packet_hash).first()
            if existing:
                self._seen[packet_hash] = now
                return False

            self._seen[packet_hash] = now
            return True

    def clear(self):
        with self._lock:
            self._seen.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._seen)

idempotency_cache = IdempotencyCache()

class SecurityService:
    """
    Orchestrates the secure bridge ingestion pipeline:
    1. SHA-256 hashing of ciphertext
    2. Idempotency gate (duplicate drop)
    3. Authenticated AES-GCM decryption & tamper detection
    4. Freshness window validation (replay protection)
    5. Sender digital signature verification (non-repudiation)
    6. Ledger settlement handoff
    """

    MAX_AGE_SECONDS = 86400 # 24 hours
    _ingest_lock = threading.Lock()

    @classmethod
    def ingest_packet(
        cls,
        packet: Dict[str, Any],
        bridge_node_id: str = "direct-bridge",
        hop_count: int = 0
    ) -> Dict[str, Any]:
        with cls._ingest_lock:
            ciphertext = packet.get('ciphertext')
            if not ciphertext:
                return {
                    'outcome': 'INVALID',
                    'packetHash': 'none',
                    'reason': 'missing_ciphertext',
                    'transactionId': None
                }

            try:
                packet_hash = crypto_service.hash_ciphertext(ciphertext)

                # ---- Step 1: Idempotency Gate ----
                if not idempotency_cache.claim(packet_hash):
                    logger.info("DUPLICATE packet %s from bridge %s — dropped", packet_hash[:12], bridge_node_id)
                    try:
                        AuditLog.log(
                            event_type='DUPLICATE_PACKET_DROPPED',
                            actor=bridge_node_id,
                            details=f"Packet hash {packet_hash[:16]}... dropped as duplicate",
                            severity='WARNING'
                        )
                        db.session.commit()
                    except Exception as audit_err:
                        db.session.rollback()
                        logger.debug("Duplicate audit logging skipped: %s", audit_err)
                    return {
                        'outcome': 'DUPLICATE_DROPPED',
                        'packetHash': packet_hash,
                        'reason': 'duplicate_ciphertext_hash',
                        'transactionId': None
                    }

                # ---- Step 2: Decryption & Tamper Detection ----
                try:
                    instruction = crypto_service.decrypt(ciphertext)
                except Exception as e:
                    logger.warning("Decryption failed for packet %s: %s", packet_hash[:12], str(e))
                    AuditLog.log(
                        event_type='TAMPER_DETECTED',
                        actor=bridge_node_id,
                        details=f"Decryption failed for packet {packet_hash[:16]}: {str(e)}",
                        severity='CRITICAL'
                    )
                    db.session.commit()
                    return {
                        'outcome': 'INVALID',
                        'packetHash': packet_hash,
                        'reason': f"decryption_failed: {type(e).__name__}",
                        'transactionId': None
                    }

                # ---- Step 3: Freshness Window (Replay Attack Prevention) ----
                signed_at_ms = instruction.get('signedAt', 0)
                now_ms = int(time.time() * 1000)
                age_seconds = (now_ms - signed_at_ms) / 1000.0

                if age_seconds > cls.MAX_AGE_SECONDS:
                    logger.warning("Packet %s too old (%.1fs), rejected", packet_hash[:12], age_seconds)
                    AuditLog.log(
                        event_type='REPLAY_ATTACK_REJECTED',
                        actor=bridge_node_id,
                        details=f"Packet expired: signed {age_seconds:.1f}s ago",
                        severity='WARNING'
                    )
                    db.session.commit()
                    return {
                        'outcome': 'INVALID',
                        'packetHash': packet_hash,
                        'reason': 'stale_packet',
                        'transactionId': None
                    }

                if age_seconds < -300: # Clock skew tolerance > 5 mins into future
                    return {
                        'outcome': 'INVALID',
                        'packetHash': packet_hash,
                        'reason': 'future_dated_packet',
                        'transactionId': None
                    }

                # ---- Step 4: Digital Signature Verification ----
                signature = packet.get('signature')
                signature_valid = True
                sender_vpa = instruction.get('senderVpa')
                user = User.query.filter_by(vpa=sender_vpa).first()

                if signature and user and user.public_key_pem:
                    signature_valid = crypto_service.verify_signature(
                        instruction, signature, user.public_key_pem
                    )
                    if not signature_valid:
                        logger.warning("Signature validation failed for sender %s", sender_vpa)
                        AuditLog.log(
                            event_type='INVALID_SIGNATURE',
                            actor=sender_vpa,
                            details="Digital signature verification failed",
                            severity='CRITICAL'
                        )
                        db.session.commit()
                        return {
                            'outcome': 'INVALID',
                            'packetHash': packet_hash,
                            'reason': 'invalid_digital_signature',
                            'transactionId': None
                        }

                # ---- Step 5: Settle in Ledger ----
                tx = ledger_service.settle(
                    instruction=instruction,
                    packet_hash=packet_hash,
                    bridge_node_id=bridge_node_id,
                    hop_count=hop_count,
                    signature=signature,
                    signature_valid=signature_valid
                )

                outcome = tx.status # SETTLED or REJECTED
                return {
                    'outcome': outcome,
                    'packetHash': packet_hash,
                    'reason': tx.rejection_reason,
                    'transactionId': tx.id
                }

            except Exception as e:
                logger.error("Ingestion error: %s", str(e), exc_info=True)
                db.session.rollback()
                return {
                    'outcome': 'INVALID',
                    'packetHash': 'error',
                    'reason': f"internal_error: {str(e)}",
                    'transactionId': None
                }

security_service = SecurityService()
