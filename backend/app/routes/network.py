from flask import Blueprint, request, jsonify, render_template, current_app
import logging
from concurrent.futures import ThreadPoolExecutor
from app.services.mesh_service import mesh_service
from app.services.security_service import security_service, idempotency_cache
from app.models.audit_log import AuditLog
from app.extensions import db

logger = logging.getLogger(__name__)
network_bp = Blueprint('network', __name__)

@network_bp.route('/network/simulator')
def simulator_page():
    return render_template('network/simulator.html')

@network_bp.route('/api/mesh/state', methods=['GET'])
def mesh_state():
    """Returns current state of every virtual device in the mesh."""
    devices = mesh_service.get_devices()
    device_data = []
    for d in devices:
        device_data.append({
            'deviceId': d.device_id,
            'name': d.name,
            'hasInternet': d.has_internet,
            'packetCount': d.packet_count(),
            'packetIds': [p.get('packetId', '')[:8] for p in d.get_packets()]
        })

    return jsonify({
        'devices': device_data,
        'idempotencyCacheSize': idempotency_cache.size(),
        'packetLossRate': mesh_service.packet_loss_rate
    })

@network_bp.route('/api/mesh/gossip', methods=['POST'])
def mesh_gossip():
    """Runs one discrete round of gossip forwarding across the mesh."""
    result = mesh_service.gossip_once()
    return jsonify({
        'transfers': result['transfers'],
        'packetLossDropped': result['packetLossDropped'],
        'deviceCounts': result['deviceCounts']
    })

@network_bp.route('/api/mesh/flush', methods=['POST'])
def mesh_flush():
    """
    Bridge nodes with internet upload all held packets in parallel.
    Exercises the concurrent duplicate-storm idempotency gate!
    """
    uploads = mesh_service.collect_bridge_uploads()
    results = []
    app = current_app._get_current_object()


    def process_upload(up):
        with app.app_context():
            packet = up['packet']
            bridge_id = up['bridgeNodeId']
            hop_count = 5 - packet.get('ttl', 5)
            res = security_service.ingest_packet(packet, bridge_node_id=bridge_id, hop_count=hop_count)
            return {
                'bridgeNode': bridge_id,
                'packetId': packet.get('packetId', '')[:8],
                'outcome': res.get('outcome'),
                'reason': res.get('reason') or '',
                'transactionId': res.get('transactionId') or -1
            }


    # Execute concurrent uploads using a thread pool to simulate simultaneous delivery
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_upload, up) for up in uploads]
        for f in futures:
            try:
                results.append(f.result())
            except Exception as e:
                logger.error("Bridge flush worker error: %s", str(e))

    return jsonify({
        'uploadsAttempted': len(uploads),
        'results': results
    })

@network_bp.route('/api/mesh/reset', methods=['POST'])
def mesh_reset():
    """Clears all held packets in the mesh and flushes the idempotency cache."""
    mesh_service.reset_mesh()
    idempotency_cache.clear()
    AuditLog.log(
        event_type='MESH_RESET',
        actor='SIMULATOR',
        details="Mesh devices packet buffers and idempotency cache cleared",
        severity='INFO'
    )
    db.session.commit()
    return jsonify({'status': 'mesh and idempotency cache cleared'})

@network_bp.route('/api/mesh/topology', methods=['GET'])
def mesh_topology():
    return jsonify(mesh_service.get_mesh_topology())

@network_bp.route('/api/mesh/config', methods=['POST'])
def mesh_config():
    data = request.get_json(silent=True) or {}
    loss_rate = float(data.get('packetLossRate', 0.0))
    mesh_service.set_packet_loss_rate(loss_rate)
    return jsonify({
        'status': 'updated',
        'packetLossRate': mesh_service.packet_loss_rate
    })
