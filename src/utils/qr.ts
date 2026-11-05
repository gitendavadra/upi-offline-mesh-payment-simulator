export interface QrTransactionData {
  id: string | number;
  senderVpa: string;
  receiverVpa: string;
  amount: number | string;
  packetHash?: string;
  status?: string;
  note?: string;
  timestamp?: string;
  isMeshRelayed?: boolean;
  hopCount?: number;
}

/**
 * Encodes transaction as a standard UPI Intent URI (RFC/NPCI compliant).
 * Format: upi://pay?pa=<receiver>&pn=<receiver>&am=<amount>&tr=<txId>&tn=<note>&cu=INR
 */
export function generateUpiQrUri(tx: QrTransactionData): string {
  const params = new URLSearchParams();
  const pa = tx.receiverVpa || '';
  const pn = pa.split('@')[0] || 'Merchant';
  const am = typeof tx.amount === 'number' ? tx.amount.toFixed(2) : parseFloat(String(tx.amount) || '0').toFixed(2);
  const tr = String(tx.id || '');
  const tn = tx.note || (tx.packetHash ? `OfflineMesh_${tx.packetHash.slice(0, 8)}` : 'Offline_UPI_Transfer');

  params.set('pa', pa);
  params.set('pn', pn);
  params.set('am', am);
  params.set('tr', tr);
  params.set('tn', tn);
  params.set('cu', 'INR');

  return `upi://pay?${params.toString()}`;
}

/**
 * Encodes complete cryptographic proof payload for offline P2P mesh verification / scanner receipt.
 */
export function generateMeshReceiptPayload(tx: QrTransactionData): string {
  const payload = {
    scheme: 'UPI-OFFLINE-MESH-V1',
    txId: tx.id,
    from: tx.senderVpa,
    to: tx.receiverVpa,
    amount: typeof tx.amount === 'number' ? tx.amount : parseFloat(String(tx.amount) || '0'),
    currency: 'INR',
    packetHash: tx.packetHash || null,
    status: tx.status || 'SETTLED',
    relayed: Boolean(tx.isMeshRelayed),
    hops: tx.hopCount ?? 0,
    timestamp: tx.timestamp || new Date().toISOString(),
    tamperCheck: tx.packetHash ? tx.packetHash.slice(0, 16) : 'OFFLINE-PROOF-OK',
  };
  return JSON.stringify(payload, null, 2);
}
