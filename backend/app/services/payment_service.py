import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
from app.extensions import db
from app.models.account import Account
from app.models.offline_queue import OfflineQueueItem
from app.models.user import User
from app.services.crypto_service import crypto_service
from app.services.ledger_service import ledger_service

class PaymentService:
    """
    Coordinates payment preparation, packet generation, client signing,
    and offline queuing.
    """

    @staticmethod
    def create_payment_instruction(
        sender_vpa: str,
        receiver_vpa: str,
        amount: Decimal,
        pin: str,
        nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates the cleartext payment payload."""
        if amount <= Decimal('0.00'):
            raise ValueError("Amount must be strictly positive")

        if sender_vpa == receiver_vpa:
            raise ValueError("Cannot send payment to your own account")

        return {
            'senderVpa': sender_vpa,
            'receiverVpa': receiver_vpa,
            'amount': str(amount),
            'pinHash': crypto_service.hash_pin(pin),
            'nonce': nonce or str(uuid.uuid4()),
            'signedAt': int(time.time() * 1000)
        }

    @classmethod
    def create_mesh_packet(
        cls,
        sender_vpa: str,
        receiver_vpa: str,
        amount: Decimal,
        pin: str,
        ttl: int = 5,
        nonce: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulates the sender phone offline creation flow:
        1. Build instruction.
        2. Sign instruction with sender private key (if user exists with keypair).
        3. Encrypt instruction with server's RSA public key using hybrid scheme.
        4. Package into MeshPacket with TTL.
        """
        instruction = cls.create_payment_instruction(
            sender_vpa=sender_vpa,
            receiver_vpa=receiver_vpa,
            amount=amount,
            pin=pin,
            nonce=nonce
        )

        # Try to locate user for signature non-repudiation
        signature = None
        user = User.query.filter_by(vpa=sender_vpa).first()
        if user and user.private_key_pem:
            signature = crypto_service.sign_payload(instruction, user.private_key_pem)

        ciphertext = crypto_service.encrypt(instruction)
        packet_id = str(uuid.uuid4())

        return {
            'packetId': packet_id,
            'ttl': ttl,
            'createdAt': instruction['signedAt'],
            'ciphertext': ciphertext,
            'signature': signature,
            'instruction': instruction # Included for sender local inspection
        }

    @classmethod
    def queue_offline_payment(
        cls,
        sender_vpa: str,
        receiver_vpa: str,
        amount: Decimal,
        pin: str,
        ttl: int = 5
    ) -> OfflineQueueItem:
        """
        Stores an encrypted payment in the persistent local offline queue.
        State: PENDING_OFFLINE
        """
        packet_data = cls.create_mesh_packet(
            sender_vpa=sender_vpa,
            receiver_vpa=receiver_vpa,
            amount=amount,
            pin=pin,
            ttl=ttl
        )

        instruction = packet_data['instruction']
        queue_item = OfflineQueueItem(
            packet_id=packet_data['packetId'],
            sender_vpa=sender_vpa,
            receiver_vpa=receiver_vpa,
            amount=amount,
            pin_hash=instruction['pinHash'],
            nonce=instruction['nonce'],
            signed_at=datetime.fromtimestamp(instruction['signedAt'] / 1000.0, tz=timezone.utc),
            ciphertext=packet_data['ciphertext'],
            signature=packet_data.get('signature'),
            status='PENDING_OFFLINE',
            attempts=0
        )
        db.session.add(queue_item)
        db.session.commit()
        return queue_item

payment_service = PaymentService()
