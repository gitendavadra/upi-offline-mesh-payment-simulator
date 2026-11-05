from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import List, Dict, Any
from app.extensions import db
from app.models.offline_queue import OfflineQueueItem
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.services.security_service import security_service
from app.services.payment_service import payment_service

logger = logging.getLogger(__name__)

class SyncService:
    """
    Handles synchronization of durable offline queues upon network restoration.
    Performs conflict detection, stale balance mitigation, and ledger reconciliation.
    """

    @classmethod
    def sync_pending_queue(cls, limit: int = 50) -> Dict[str, Any]:
        """
        Synchronizes all eligible offline queue transactions.
        Transitions state from PENDING_OFFLINE -> READY_TO_SYNC -> SYNCING -> COMPLETED_SIMULATION / FAILED.
        """
        pending_items = OfflineQueueItem.query.filter(
            OfflineQueueItem.status.in_(['PENDING_OFFLINE', 'READY_TO_SYNC'])
        ).order_by(OfflineQueueItem.signed_at.asc()).limit(limit).all()

        results = []
        synced_count = 0
        failed_count = 0
        review_count = 0

        for item in pending_items:
            try:
                item.transition_to('SYNCING')
                item.attempts += 1
                item.last_attempt_at = datetime.now(timezone.utc)
                db.session.commit()

                # Package for ingestion
                packet = {
                    'packetId': item.packet_id,
                    'ciphertext': item.ciphertext,
                    'signature': item.signature
                }

                ingest_res = security_service.ingest_packet(
                    packet=packet,
                    bridge_node_id='sync-engine',
                    hop_count=1
                )

                outcome = ingest_res.get('outcome')
                if outcome == 'SETTLED':
                    item.transition_to('COMPLETED_SIMULATION')
                    synced_count += 1
                elif outcome == 'REJECTED':
                    # Conflicting or insufficient funds after offline period
                    item.transition_to('REQUIRES_REVIEW', reason=ingest_res.get('reason'))
                    review_count += 1
                elif outcome == 'DUPLICATE_DROPPED':
                    item.transition_to('COMPLETED_SIMULATION', reason="Duplicate already settled via mesh")
                    synced_count += 1
                else:
                    item.transition_to('FAILED', reason=ingest_res.get('reason'))
                    failed_count += 1

                results.append({
                    'queueId': item.queue_id,
                    'packetId': item.packet_id,
                    'senderVpa': item.sender_vpa,
                    'receiverVpa': item.receiver_vpa,
                    'amount': float(item.amount),
                    'outcome': outcome,
                    'status': item.status,
                    'reason': item.error_message
                })

            except Exception as e:
                logger.error("Error syncing queue item %s: %s", item.queue_id, str(e))
                item.status = 'FAILED'
                item.error_message = str(e)
                failed_count += 1
                results.append({
                    'queueId': item.queue_id,
                    'status': 'FAILED',
                    'error': str(e)
                })

        db.session.commit()

        AuditLog.log(
            event_type='QUEUE_SYNC_RUN',
            actor='SYNC_SERVICE',
            details=f"Synced: {synced_count}, Review: {review_count}, Failed: {failed_count}",
            severity='INFO'
        )
        db.session.commit()

        return {
            'totalProcessed': len(results),
            'syncedCount': synced_count,
            'reviewCount': review_count,
            'failedCount': failed_count,
            'results': results
        }

    @classmethod
    def simulate_double_spending(cls) -> Dict[str, Any]:
        """
        Academic demonstration of the double-spending problem across disconnected devices:
        - Alice's account starts with ₹1,000.
        - Two offline transactions are crafted concurrently on disconnected devices:
            * Request A: Alice pays Bob ₹800 (signed offline against stale ₹1,000 balance).
            * Request B: Alice pays Carol ₹700 (signed offline against stale ₹1,000 balance).
        - Total requested = ₹1,500 > ₹1,000 available.
        - Reconnection occurs:
            * Tx A arrives and settles: Alice balance = ₹200, Bob balance +₹800.
            * Tx B arrives and triggers conflict detection: Insufficient balance (available ₹200 < ₹700).
            * Tx B is flagged as REQUIRES_REVIEW and rejected from ledger execution.
            * Final balance is preserved without overdraft or inconsistency!
        """
        alice_vpa = 'alice@demo'
        bob_vpa = 'bob@demo'
        carol_vpa = 'carol@demo'

        alice_acc = Account.query.filter_by(vpa=alice_vpa).first()
        bob_acc = Account.query.filter_by(vpa=bob_vpa).first()
        carol_acc = Account.query.filter_by(vpa=carol_vpa).first()

        # Set known starting balances
        if not alice_acc:
            alice_acc = Account(vpa=alice_vpa, holder_name="Alice", balance=Decimal('1000.00'))
            db.session.add(alice_acc)
        else:
            alice_acc.balance = Decimal('1000.00')

        if not bob_acc:
            bob_acc = Account(vpa=bob_vpa, holder_name="Bob", balance=Decimal('1000.00'))
            db.session.add(bob_acc)

        if not carol_acc:
            carol_acc = Account(vpa=carol_vpa, holder_name="Carol", balance=Decimal('1000.00'))
            db.session.add(carol_acc)

        db.session.commit()

        initial_state = {
            'aliceBalance': float(alice_acc.balance),
            'bobBalance': float(bob_acc.balance),
            'carolBalance': float(carol_acc.balance)
        }

        # Create two competing offline packets
        packet_a = payment_service.create_mesh_packet(
            sender_vpa=alice_vpa,
            receiver_vpa=bob_vpa,
            amount=Decimal('800.00'),
            pin='1234'
        )

        packet_b = payment_service.create_mesh_packet(
            sender_vpa=alice_vpa,
            receiver_vpa=carol_vpa,
            amount=Decimal('700.00'),
            pin='1234'
        )

        # Ingestion of Tx A (simulating Device A reconnecting first)
        res_a = security_service.ingest_packet(packet_a, bridge_node_id='phone-bridge-alpha', hop_count=2)

        # Ingestion of Tx B (simulating Device B reconnecting second)
        res_b = security_service.ingest_packet(packet_b, bridge_node_id='phone-bridge-beta', hop_count=3)

        # Refresh state from database
        db.session.refresh(alice_acc)
        db.session.refresh(bob_acc)
        db.session.refresh(carol_acc)

        final_state = {
            'aliceBalance': float(alice_acc.balance),
            'bobBalance': float(bob_acc.balance),
            'carolBalance': float(carol_acc.balance)
        }

        AuditLog.log(
            event_type='DOUBLE_SPEND_SIMULATION',
            actor='SIMULATOR',
            details=f"Tx A ({res_a['outcome']}), Tx B ({res_b['outcome']}). Alice end balance: ₹{alice_acc.balance}",
            severity='WARNING'
        )
        db.session.commit()

        return {
            'scenario': 'Offline Double-Spending Contention',
            'explanation': (
                "Both transactions were signed offline when Alice held ₹1,000. "
                "Tx A claimed ₹800 first and settled. When Tx B arrived requesting ₹700, "
                "the backend detected that Alice's available balance was only ₹200. "
                "The ledger rejected Tx B, preventing unauthorized overdraft while maintaining consistency."
            ),
            'initialState': initial_state,
            'transactionA': {
                'description': 'Alice pays Bob ₹800.00',
                'outcome': res_a['outcome'],
                'reason': res_a.get('reason'),
                'txId': res_a.get('transactionId')
            },
            'transactionB': {
                'description': 'Alice pays Carol ₹700.00',
                'outcome': res_b['outcome'],
                'reason': res_b.get('reason'),
                'txId': res_b.get('transactionId')
            },
            'finalState': final_state,
            'isConsistent': alice_acc.balance >= 0
        }

sync_service = SyncService()
