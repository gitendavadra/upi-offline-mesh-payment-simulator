import test from 'node:test';
import assert from 'node:assert/strict';
import { generateUpiQrUri, generateMeshReceiptPayload, QrTransactionData } from './qr.ts';

test('generateUpiQrUri formats standard NPCI UPI Intent URI', () => {
  const tx: QrTransactionData = {
    id: 'TX-9021',
    senderVpa: 'alice@sim.upi',
    receiverVpa: 'bob@sim.upi',
    amount: 250.5,
    packetHash: 'abcdef0123456789fedcba9876543210',
  };

  const uri = generateUpiQrUri(tx);
  assert.ok(uri.startsWith('upi://pay?'));
  assert.ok(uri.includes('pa=bob%40sim.upi'));
  assert.ok(uri.includes('pn=bob'));
  assert.ok(uri.includes('am=250.50'));
  assert.ok(uri.includes('tr=TX-9021'));
  assert.ok(uri.includes('tn=OfflineMesh_abcdef01'));
  assert.ok(uri.includes('cu=INR'));
});

test('generateUpiQrUri handles fallback note and integer amounts', () => {
  const tx: QrTransactionData = {
    id: 104,
    senderVpa: 'carol@sim.upi',
    receiverVpa: 'store@upi',
    amount: '150',
  };

  const uri = generateUpiQrUri(tx);
  assert.ok(uri.includes('am=150.00'));
  assert.ok(uri.includes('tn=Offline_UPI_Transfer'));
});

test('generateMeshReceiptPayload outputs structured offline cryptographic JSON', () => {
  const tx: QrTransactionData = {
    id: 'TX-100',
    senderVpa: 'alice@sim.upi',
    receiverVpa: 'bob@sim.upi',
    amount: 50,
    packetHash: '9876543210abcdef0123456789',
    status: 'SETTLED',
    isMeshRelayed: true,
    hopCount: 3,
  };

  const jsonStr = generateMeshReceiptPayload(tx);
  const parsed = JSON.parse(jsonStr);
  assert.equal(parsed.scheme, 'UPI-OFFLINE-MESH-V1');
  assert.equal(parsed.txId, 'TX-100');
  assert.equal(parsed.from, 'alice@sim.upi');
  assert.equal(parsed.to, 'bob@sim.upi');
  assert.equal(parsed.amount, 50);
  assert.equal(parsed.relayed, true);
  assert.equal(parsed.hops, 3);
  assert.equal(parsed.tamperCheck, '9876543210abcdef');
});
