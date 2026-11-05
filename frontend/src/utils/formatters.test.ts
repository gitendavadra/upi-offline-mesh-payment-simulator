import test from 'node:test';
import assert from 'node:assert/strict';
import { formatCurrency, truncateHash, calculateNetDelta } from './formatters.ts';

test('formatCurrency formats standard and zero amounts correctly', () => {
  assert.equal(formatCurrency(5000), '₹5,000.00');
  assert.equal(formatCurrency(0), '₹0.00');
  assert.equal(formatCurrency('1250.5'), '₹1,250.50');
  assert.equal(formatCurrency('invalid'), '₹0.00');
});

test('truncateHash shortens long cryptographic digests', () => {
  const hash = 'a3f8c9b2d4e6f1a8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4b6';
  const truncated = truncateHash(hash, 8, 6);
  assert.equal(truncated, 'a3f8c9b2...f2a4b6');
  assert.equal(truncateHash('short'), 'short');
  assert.equal(truncateHash(''), '-');
});

test('calculateNetDelta calculates positive, negative, and zero deltas', () => {
  const pos = calculateNetDelta(1000, 1800);
  assert.equal(pos.isPositive, true);
  assert.equal(pos.isZero, false);
  assert.equal(pos.text, '+₹800.00');

  const neg = calculateNetDelta(1000, 200);
  assert.equal(neg.isPositive, false);
  assert.equal(neg.isZero, false);
  assert.equal(neg.text, '-₹800.00');

  const zero = calculateNetDelta(2500, 2500);
  assert.equal(zero.isZero, true);
  assert.equal(zero.text, '₹0.00');
});
