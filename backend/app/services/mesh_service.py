import random
import logging
from typing import List, Dict, Any, Tuple
from app.extensions import db
from app.models.device import Device
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

class MeshSimulatorService:
    """
    Simulates a multi-hop Bluetooth / Wi-Fi Direct mesh network.
    Devices can pass encrypted packets peer-to-peer without internet access.
    """

    DEFAULT_DEVICES = [
        {'device_id': 'phone-alice', 'name': 'Alice (Sender Phone)', 'has_internet': False, 'x': 80, 'y': 150},
        {'device_id': 'phone-stranger1', 'name': 'Stranger 1 (Relay)', 'has_internet': False, 'x': 250, 'y': 80},
        {'device_id': 'phone-stranger2', 'name': 'Stranger 2 (Relay)', 'has_internet': False, 'x': 420, 'y': 150},
        {'device_id': 'phone-stranger3', 'name': 'Stranger 3 (Relay)', 'has_internet': False, 'x': 590, 'y': 80},
        {'device_id': 'phone-bridge', 'name': 'Bridge Node (4G / Gateway)', 'has_internet': True, 'x': 750, 'y': 150},
    ]

    def __init__(self):
        self.packet_loss_rate = 0.0 # 0.0 to 1.0

    def set_packet_loss_rate(self, rate: float):
        self.packet_loss_rate = max(0.0, min(1.0, rate))

    def seed_default_devices(self):
        """Ensures default simulation devices exist in the database."""
        for d_info in self.DEFAULT_DEVICES:
            existing = Device.query.filter_by(device_id=d_info['device_id']).first()
            if not existing:
                dev = Device(
                    device_id=d_info['device_id'],
                    name=d_info['name'],
                    has_internet=d_info['has_internet'],
                    battery_percent=90,
                    bluetooth_enabled=True,
                    is_active=True,
                    held_packets_json='[]',
                    x_coord=d_info['x'],
                    y_coord=d_info['y']
                )
                db.session.add(dev)
        db.session.commit()

    def get_devices(self) -> List[Device]:
        self.seed_default_devices()
        return Device.query.order_by(Device.id).all()

    def get_device(self, device_id: str) -> Device:
        self.seed_default_devices()
        return Device.query.filter_by(device_id=device_id).first()

    def inject(self, device_id: str, packet: Dict[str, Any]) -> bool:
        """Sender injects an encrypted packet into their local phone device."""
        device = self.get_device(device_id)
        if not device:
            raise ValueError(f"Target device {device_id} not found")

        # Standardize packet format
        clean_packet = {
            'packetId': packet.get('packetId'),
            'ttl': packet.get('ttl', 5),
            'createdAt': packet.get('createdAt'),
            'ciphertext': packet.get('ciphertext'),
            'signature': packet.get('signature'),
            'initialHopCount': 0
        }

        success = device.hold_packet(clean_packet)
        if success:
            db.session.commit()
            AuditLog.log(
                event_type='PACKET_INJECTED',
                actor=device_id,
                details=f"Packet {clean_packet['packetId'][:8]} injected into {device.name} (TTL={clean_packet['ttl']})",
                severity='INFO'
            )
        return success

    def gossip_once(self) -> Dict[str, Any]:
        """
        Executes one discrete round of gossip protocol forwarding.
        Packets hop between in-range devices. TTL is decremented.
        Respects simulated packet loss and prevents duplicate transmission.
        """
        devices = self.get_devices()
        transfers = 0
        dropped_loss = 0

        # Snapshot held packets at the start of the round
        snapshot = {d.device_id: d.get_packets() for d in devices}

        for src in devices:
            src_packets = snapshot.get(src.device_id, [])
            for pkt in src_packets:
                current_ttl = pkt.get('ttl', 0)
                if current_ttl <= 0:
                    continue # Expired hop count

                for dst in devices:
                    if dst.device_id == src.device_id:
                        continue

                    # Check if dst already holds this packet (loop prevention)
                    if any(p.get('packetId') == pkt.get('packetId') for p in dst.get_packets()):
                        continue

                    # Simulate packet loss
                    if self.packet_loss_rate > 0.0 and random.random() < self.packet_loss_rate:
                        dropped_loss += 1
                        continue

                    # Transfer copy with decremented TTL
                    new_pkt = dict(pkt)
                    new_pkt['ttl'] = current_ttl - 1
                    new_pkt['initialHopCount'] = pkt.get('initialHopCount', 0) + 1

                    if dst.hold_packet(new_pkt):
                        transfers += 1

        db.session.commit()

        counts = {d.device_id: d.packet_count() for d in self.get_devices()}
        return {
            'transfers': transfers,
            'packetLossDropped': dropped_loss,
            'deviceCounts': counts
        }

    def collect_bridge_uploads(self) -> List[Dict[str, Any]]:
        """Collects all packets from devices that currently possess internet connectivity."""
        devices = self.get_devices()
        uploads = []
        for d in devices:
            if not d.has_internet:
                continue
            for pkt in d.get_packets():
                uploads.append({
                    'bridgeNodeId': d.device_id,
                    'packet': pkt
                })
        return uploads

    def reset_mesh(self):
        """Clears all packet buffers across all devices."""
        for d in self.get_devices():
            d.clear_packets()
        db.session.commit()

    def get_mesh_topology(self) -> Dict[str, Any]:
        """Returns node list and link connections for interactive frontend visualization."""
        devices = self.get_devices()
        nodes = []
        for d in devices:
            nodes.append({
                'id': d.device_id,
                'name': d.name,
                'hasInternet': d.has_internet,
                'packetCount': d.packet_count(),
                'packetIds': [p.get('packetId', '')[:8] for p in d.get_packets()],
                'x': d.x_coord,
                'y': d.y_coord
            })

        # Physical / Bluetooth proximity edges for visualization
        edges = [
            {'source': 'phone-alice', 'target': 'phone-stranger1'},
            {'source': 'phone-stranger1', 'target': 'phone-stranger2'},
            {'source': 'phone-stranger2', 'target': 'phone-stranger3'},
            {'source': 'phone-stranger3', 'target': 'phone-bridge'},
            {'source': 'phone-stranger1', 'target': 'phone-stranger3'},
        ]

        return {
            'nodes': nodes,
            'edges': edges,
            'packetLossRate': self.packet_loss_rate
        }

mesh_service = MeshSimulatorService()
