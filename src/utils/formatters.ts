export function formatCurrency(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '₹0.00';
  if (num < 0) {
    return `-₹${Math.abs(num).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
  return `₹${num.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function truncateHash(hash: string, start = 8, end = 6): string {
  if (!hash) return '-';
  if (hash.length <= start + end) return hash;
  return `${hash.slice(0, start)}...${hash.slice(-end)}`;
}

export function calculateNetDelta(initial: number, final: number): {
  text: string;
  isPositive: boolean;
  isZero: boolean;
} {
  const diff = final - initial;
  if (Math.abs(diff) < 0.001) {
    return { text: '₹0.00', isPositive: false, isZero: true };
  }
  const prefix = diff > 0 ? '+' : '';
  return {
    text: `${prefix}${formatCurrency(diff)}`,
    isPositive: diff > 0,
    isZero: false,
  };
}
