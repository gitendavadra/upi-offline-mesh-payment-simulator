import json
from datetime import datetime, timezone
from app.extensions import db

class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    has_internet = db.Column(db.Boolean, default=False, nullable=False)
    battery_percent = db.Column(db.Integer, default=90)
    bluetooth_enabled = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    held_packets_json = db.Column(db.Text, default='[]', nullable=False) # JSON list of packets
    x_coord = db.Column(db.Integer, default=100)
    y_coord = db.Column(db.Integer, default=100)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def get_packets(self):
        try:
            return json.loads(self.held_packets_json or '[]')
        except Exception:
            return []

    def set_packets(self, packets):
        self.held_packets_json = json.dumps(packets)

    def hold_packet(self, packet_dict):
        packets = self.get_packets()
        # Don't add duplicate packet_id to the same device
        for p in packets:
            if p.get('packetId') == packet_dict.get('packetId'):
                return False
        packets.append(packet_dict)
        self.set_packets(packets)
        return True

    def clear_packets(self):
        self.held_packets_json = '[]'

    def packet_count(self):
        return len(self.get_packets())

    def to_dict(self):
        packets = self.get_packets()
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'name': self.name,
            'hasInternet': self.has_internet,
            'batteryPercent': self.battery_percent,
            'bluetoothEnabled': self.bluetooth_enabled,
            'isActive': self.is_active,
            'packetCount': len(packets),
            'packetIds': [p.get('packetId', '')[:8] for p in packets],
            'x': self.x_coord,
            'y': self.y_coord
        }
