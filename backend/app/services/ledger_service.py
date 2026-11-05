from datetime import datetime, timezone
from decimal import Decimal
import logging
from app.extensions import db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

class LedgerService:
    """
    Simulated core banking ledger service.
    Guarantees ACID transactions with optimistic locking on account balances.
    """

    @staticmethod
    def settle(
        instruction: dict,
        packet_hash: str,
        bridge_node_id: str = "direct",
        hop_count: int = 0,
        signature: str = None,
        signature_valid: bool = True
    ) -> Transaction:
        """
        Processes debit and credit atomically.
        If sender lacks sufficient funds, records a REJECTED transaction.
        If successful, updates balances and writes a SETTLED transaction.
        """
        sender_vpa = instruction.get('senderVpa')
        receiver_vpa = instruction.get('receiverVpa')
        amount_val = instruction.get('amount')
        nonce = instruction.get('nonce')
        signed_at_ms = instruction.get('signedAt', 0)
        signed_at = datetime.fromtimestamp(signed_at_ms / 1000.0, tz=timezone.utc) if signed_at_ms else datetime.now(timezone.utc)

        amount = Decimal(str(amount_val))
        if amount <= Decimal('0.00'):
            raise ValueError("Payment amount must be greater than zero")

        sender = Account.query.filter_by(vpa=sender_vpa).first()
        if not sender:
            raise ValueError(f"Sender account not found: {sender_vpa}")

        receiver = Account.query.filter_by(vpa=receiver_vpa).first()
        if not receiver:
            raise ValueError(f"Receiver account not found: {receiver_vpa}")

        # Defense-in-depth: Check if packet_hash is already settled in database
        existing = Transaction.query.filter_by(packet_hash=packet_hash).first()
        if existing:
            logger.info("Database uniqueness check: packet_hash %s already exists", packet_hash[:12])
            return existing

        # Insufficient funds check
        if sender.balance < amount:
            logger.warning(
                "Insufficient balance: %s has ₹%s, attempted ₹%s",
                sender.vpa, sender.balance, amount
            )
            rejected_tx = Transaction(
                packet_hash=packet_hash,
                idempotency_key=nonce,
                sender_vpa=sender_vpa,
                receiver_vpa=receiver_vpa,
                amount=amount,
                signed_at=signed_at,
                settled_at=datetime.now(timezone.utc),
                bridge_node_id=bridge_node_id,
                hop_count=hop_count,
                status='REJECTED',
                rejection_reason=f"Insufficient balance: Available ₹{sender.balance}, requested ₹{amount}",
                signature=signature,
                signature_valid=signature_valid,
                is_offline_origin=True
            )
            db.session.add(rejected_tx)
            AuditLog.log(
                event_type='PAYMENT_REJECTED_FUNDS',
                actor=sender_vpa,
                details=f"Insufficient funds for ₹{amount} to {receiver_vpa}",
                severity='WARNING'
            )
            db.session.commit()
            return rejected_tx

        # Atomic debit and credit
        sender.debit(amount)
        receiver.credit(amount)

        settled_tx = Transaction(
            packet_hash=packet_hash,
            idempotency_key=nonce,
            sender_vpa=sender_vpa,
            receiver_vpa=receiver_vpa,
            amount=amount,
            signed_at=signed_at,
            settled_at=datetime.now(timezone.utc),
            bridge_node_id=bridge_node_id,
            hop_count=hop_count,
            status='SETTLED',
            rejection_reason=None,
            signature=signature,
            signature_valid=signature_valid,
            is_offline_origin=True
        )
        db.session.add(settled_tx)

        AuditLog.log(
            event_type='PAYMENT_SETTLED',
            actor=sender_vpa,
            details=f"Settled ₹{amount} to {receiver_vpa} via {bridge_node_id} (hops={hop_count})",
            severity='INFO'
        )

        db.session.commit()
        logger.info(
            "SETTLED ₹%s from %s to %s (hash=%s..., bridge=%s)",
            amount, sender_vpa, receiver_vpa, packet_hash[:12], bridge_node_id
        )
        return settled_tx

ledger_service = LedgerService()
