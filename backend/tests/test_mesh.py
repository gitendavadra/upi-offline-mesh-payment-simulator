import pytest
from decimal import Decimal
from app.services.mesh_service import mesh_service
from app.services.payment_service import payment_service

def test_packet_injection_and_gossip(app):
    with app.app_context():
        packet = payment_service.create_mesh_packet(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('150.00'),
            pin='1234',
            ttl=3
        )

        # Inject at Alice's device
        success = mesh_service.inject('phone-alice', packet)
        assert success is True

        alice_dev = mesh_service.get_device('phone-alice')
        assert alice_dev.packet_count() == 1

        # Run 1st gossip round
        r1 = mesh_service.gossip_once()
        assert r1['transfers'] > 0

        # Devices in the mesh should now hold the packet with decremented TTL
        stranger1 = mesh_service.get_device('phone-stranger1')
        assert stranger1.packet_count() == 1
        held_pkt = stranger1.get_packets()[0]
        assert held_pkt['ttl'] == 2 # 3 - 1

        # Run 2nd gossip round: devices shouldn't duplicate existing packet
        r2 = mesh_service.gossip_once()
        # All devices hold 1 packet each
        for d in mesh_service.get_devices():
            assert d.packet_count() == 1

def test_bridge_upload_collection(app):
    with app.app_context():
        mesh_service.reset_mesh()
        packet = payment_service.create_mesh_packet(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('50.00'),
            pin='1234',
            ttl=2
        )

        mesh_service.inject('phone-alice', packet)
        mesh_service.gossip_once() # propagates to bridge

        uploads = mesh_service.collect_bridge_uploads()
        assert len(uploads) >= 1
        assert uploads[0]['bridgeNodeId'] == 'phone-bridge'

def test_mesh_reset(app):
    with app.app_context():
        mesh_service.seed_default_devices()
        packet = payment_service.create_mesh_packet(
            sender_vpa='alice@demo',
            receiver_vpa='bob@demo',
            amount=Decimal('10.00'),
            pin='1234'
        )
        mesh_service.inject('phone-alice', packet)
        assert mesh_service.get_device('phone-alice').packet_count() == 1

        mesh_service.reset_mesh()
        for d in mesh_service.get_devices():
            assert d.packet_count() == 0
