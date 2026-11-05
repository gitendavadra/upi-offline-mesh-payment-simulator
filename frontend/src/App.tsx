import React, { useState, useEffect, useCallback } from 'react';
import {
  Radio,
  Send,
  RefreshCw,
  TowerControl,
  Trash2,
  ShieldCheck,
  Wallet,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Boxes,
  Database,
  ArrowRight,
  Info,
  Server,
  Lock,
  Search,
  Activity,
  Layers,
  FileText,
  Key,
  Smartphone,
  ExternalLink,
  ChevronRight,
  Copy,
  Check,
  QrCode,
  Download,
  X
} from 'lucide-react';
import QRCode from 'qrcode';
import { formatCurrency, truncateHash } from './utils/formatters.ts';
import { generateUpiQrUri, generateMeshReceiptPayload } from './utils/qr.ts';

// Data Interfaces
interface DashboardStats {
  userVpa: string;
  simulatedBalance: number;
  holderName: string;
  totalTransactions: number;
  settledCount: number;
  rejectedCount: number;
  requiresReviewCount: number;
  pendingQueueCount: number;
  idempotencyCacheSize: number;
  totalDevices: number;
  packetsInMesh: number;
}

interface AccountItem {
  vpa: string;
  holderName: string;
  balance: number;
  version: number;
  updatedAt?: string;
}

interface TransactionItem {
  id: number;
  packetHash: string;
  idempotencyKey?: string;
  senderVpa: string;
  receiverVpa: string;
  amount: number;
  status: string;
  signedAt?: string;
  settledAt?: string;
  bridgeNodeId?: string;
  hopCount: number;
  rejectionReason?: string;
  signatureValid?: boolean;
}

interface MeshDeviceItem {
  deviceId: string;
  name: string;
  hasInternet: boolean;
  packetCount: number;
  packetIds: string[];
  x?: number;
  y?: number;
}

interface QueueItem {
  id: number;
  queueId: string;
  packetId: string;
  senderVpa: string;
  receiverVpa: string;
  amount: number;
  status: string;
  attempts: number;
  signedAt?: string;
  lastAttemptAt?: string;
  errorMessage?: string;
}

interface AuditLogItem {
  id: number;
  timestamp: string;
  eventType: string;
  actor: string;
  severity: string;
  details?: string;
}

interface DoubleSpendResult {
  scenario: string;
  explanation: string;
  initialState: {
    aliceBalance: number;
    bobBalance: number;
    carolBalance: number;
  };
  transactionA: {
    description: string;
    outcome: string;
    reason?: string;
    txId?: number;
  };
  transactionB: {
    description: string;
    outcome: string;
    reason?: string;
    txId?: number;
  };
  finalState: {
    aliceBalance: number;
    bobBalance: number;
    carolBalance: number;
  };
  isConsistent: boolean;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<
    'dashboard' | 'send' | 'ledger' | 'mesh' | 'queue' | 'double-spend' | 'admin' | 'guide'
  >('dashboard');

  // Core Data States
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [accounts, setAccounts] = useState<AccountItem[]>([]);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [devices, setDevices] = useState<MeshDeviceItem[]>([]);
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [serverKey, setServerKey] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [logs, setLogs] = useState<string[]>([]);

  // Send Payment Form State
  const [senderVpa, setSenderVpa] = useState<string>('alice@demo');
  const [receiverVpa, setReceiverVpa] = useState<string>('bob@demo');
  const [amount, setAmount] = useState<string>('500.00');
  const [pin, setPin] = useState<string>('1234');
  const [isOfflineMode, setIsOfflineMode] = useState<boolean>(true);
  const [sendResult, setSendResult] = useState<any>(null);

  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Double-Spend State
  const [doubleSpendData, setDoubleSpendData] = useState<DoubleSpendResult | null>(null);
  const [isSimulatingDS, setIsSimulatingDS] = useState<boolean>(false);

  // Packet Loss Slider State
  const [packetLossRate, setPacketLossRate] = useState<number>(0);

  // QR Code Modal State for Ledger Transactions
  const [selectedQrTx, setSelectedQrTx] = useState<TransactionItem | null>(null);
  const [qrFormat, setQrFormat] = useState<'upi' | 'mesh'>('upi');
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [qrCopied, setQrCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!selectedQrTx) {
      setQrDataUrl('');
      return;
    }
    const payload =
      qrFormat === 'upi'
        ? generateUpiQrUri({
            id: selectedQrTx.id,
            senderVpa: selectedQrTx.senderVpa,
            receiverVpa: selectedQrTx.receiverVpa,
            amount: selectedQrTx.amount,
            packetHash: selectedQrTx.packetHash,
            status: selectedQrTx.status,
          })
        : generateMeshReceiptPayload({
            id: selectedQrTx.id,
            senderVpa: selectedQrTx.senderVpa,
            receiverVpa: selectedQrTx.receiverVpa,
            amount: selectedQrTx.amount,
            packetHash: selectedQrTx.packetHash,
            status: selectedQrTx.status,
            hopCount: selectedQrTx.hopCount,
            isMeshRelayed: selectedQrTx.hopCount > 0,
            timestamp: selectedQrTx.settledAt,
          });

    QRCode.toDataURL(payload, {
      width: 320,
      margin: 2,
      color: {
        dark: '#041d24',
        light: '#e2f9f6',
      },
      errorCorrectionLevel: 'M',
    })
      .then((url) => setQrDataUrl(url))
      .catch((err) => {
        console.error('Failed to generate QR code:', err);
        setQrDataUrl('');
      });
  }, [selectedQrTx, qrFormat]);

  const addLog = useCallback((msg: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${time}] ${msg}`, ...prev.slice(0, 40)]);
  }, []);

  // Fetch all live backend data
  const refreshData = useCallback(async () => {
    try {
      const [sRes, aRes, tRes, mRes, qRes] = await Promise.all([
        fetch('/api/dashboard/stats'),
        fetch('/api/accounts'),
        fetch(`/api/transactions?limit=25${statusFilter ? `&status=${statusFilter}` : ''}${searchTerm ? `&search=${encodeURIComponent(searchTerm)}` : ''}`),
        fetch('/api/mesh/state'),
        fetch('/api/sync/queue')
      ]);

      if (sRes.ok) setStats(await sRes.json());
      if (aRes.ok) setAccounts(await aRes.json());
      if (tRes.ok) {
        const txData = await tRes.json();
        setTransactions(txData.transactions || []);
      }
      if (mRes.ok) {
        const mData = await mRes.json();
        setDevices(mData.devices || []);
        if (typeof mData.packetLossRate === 'number') {
          setPacketLossRate(mData.packetLossRate);
        }
      }
      if (qRes.ok) {
        const qData = await qRes.json();
        setQueueItems(qData.items || []);
      }
    } catch (e: any) {
      console.error('Refresh error:', e);
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, statusFilter]);

  // Initial load
  useEffect(() => {
    refreshData();
    fetch('/api/server-key')
      .then((r) => r.json())
      .then((k) => setServerKey(k))
      .catch((e) => console.error(e));

    addLog('System initialized. Connected to Python Flask fintech engine.');
    const interval = setInterval(refreshData, 3500);
    return () => clearInterval(interval);
  }, [refreshData, addLog]);

  // Actions
  const handleDemoInject = async () => {
    try {
      const res = await fetch('/api/demo/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          senderVpa,
          receiverVpa,
          amount: parseFloat(amount),
          pin,
          ttl: 5,
          startDevice: 'phone-alice'
        })
      });
      const data = await res.json();
      if (res.ok) {
        addLog(`📤 Payment packet ${data.packetId.slice(0, 8)} encrypted (RSA-OAEP+AES-GCM) & injected at ${data.injectedAt}`);
        refreshData();
      } else {
        addLog(`❌ Injection failed: ${data.error}`);
      }
    } catch (e: any) {
      addLog(`❌ Error: ${e.message}`);
    }
  };

  const handleGossipRound = async () => {
    try {
      const res = await fetch('/api/mesh/gossip', { method: 'POST' });
      const data = await res.json();
      addLog(`🔄 Gossip Round: ${data.transfers} transfer(s) across peers (TTL decremented)`);
      refreshData();
    } catch (e: any) {
      addLog(`❌ Gossip failed: ${e.message}`);
    }
  };

  const handleFlushBridges = async () => {
    try {
      const res = await fetch('/api/mesh/flush', { method: 'POST' });
      const data = await res.json();
      addLog(`📡 Bridge Flush: ${data.uploadsAttempted} upload(s) executed concurrently to backend:`);
      data.results?.forEach((r: any) => {
        addLog(`   ${r.bridgeNode} pkt ${r.packetId} ➔ ${r.outcome} ${r.reason ? `(${r.reason})` : ''}`);
      });
      refreshData();
    } catch (e: any) {
      addLog(`❌ Flush failed: ${e.message}`);
    }
  };

  const handleResetMesh = async () => {
    try {
      await fetch('/api/mesh/reset', { method: 'POST' });
      addLog(`🗑 Mesh packet buffers and SHA-256 idempotency cache cleared.`);
      refreshData();
    } catch (e: any) {
      addLog(`❌ Reset failed: ${e.message}`);
    }
  };

  const handleCreatePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/payments/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          senderVpa,
          receiverVpa,
          amount,
          pin,
          offline: isOfflineMode
        })
      });
      const data = await res.json();
      setSendResult({ ok: res.ok, data });
      if (res.ok) {
        if (isOfflineMode) {
          addLog(`📦 Payment ${amount} queued in durable offline storage (ID: ${data.queueId?.slice(0, 8)})`);
        } else {
          addLog(`⚡ Direct Gateway: ₹${amount} ➔ ${data.outcome} (Tx #${data.transactionId || 'none'})`);
        }
        refreshData();
      } else {
        addLog(`❌ Payment Error: ${data.error}`);
      }
    } catch (e: any) {
      setSendResult({ ok: false, data: { error: e.message } });
    }
  };

  const handleTriggerSync = async () => {
    try {
      const res = await fetch('/api/sync/run', { method: 'POST' });
      const data = await res.json();
      addLog(`🔄 Offline Queue Synced: ${data.totalProcessed} processed, ${data.syncedCount} settled, ${data.reviewCount} review`);
      refreshData();
    } catch (e: any) {
      addLog(`❌ Sync failed: ${e.message}`);
    }
  };

  const handleRunDoubleSpend = async () => {
    setIsSimulatingDS(true);
    try {
      const res = await fetch('/api/sync/double-spend-demo', { method: 'POST' });
      const data = await res.json();
      setDoubleSpendData(data);
      addLog(`⚠️ Double-Spending Experiment: Tx A ${data.transactionA.outcome}, Tx B ${data.transactionB.outcome}. Alice end balance: ₹${data.finalState.aliceBalance}`);
      refreshData();
    } catch (e: any) {
      addLog(`❌ Double-spend simulation error: ${e.message}`);
    } finally {
      setIsSimulatingDS(false);
    }
  };

  const handleLoadAdminLogs = async () => {
    try {
      const res = await fetch('/api/admin/audit-logs');
      if (res.ok) {
        setAuditLogs(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleFactoryReset = async () => {
    if (!window.confirm('Reset all balances to default values and clear all transactions?')) return;
    try {
      await fetch('/api/admin/reset-system', { method: 'POST' });
      addLog('⚠️ System state reset to initial factory defaults.');
      refreshData();
    } catch (e: any) {
      addLog(`❌ Factory reset failed: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-slate-950">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight text-white">
                  UPI<span className="text-teal-400">Mesh</span>
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-teal-500/10 text-teal-400 border border-teal-500/20 rounded-full">
                  OFFLINE-SIM
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Mesh-Routed Deferred Payment Settlement
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: Activity },
              { id: 'send', label: 'Send Payment', icon: Send },
              { id: 'ledger', label: 'Ledger', icon: FileText },
              { id: 'mesh', label: 'Mesh Topology', icon: Radio },
              { id: 'queue', label: 'Offline Queue', icon: Boxes },
              { id: 'double-spend', label: 'Double-Spend Demo', icon: AlertTriangle },
              { id: 'admin', label: 'Admin', icon: Lock },
              { id: 'guide', label: 'Architecture', icon: Layers }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id as any);
                    if (tab.id === 'admin') handleLoadAdminLogs();
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                    isActive
                      ? 'bg-teal-500 text-slate-950 font-bold shadow-sm shadow-teal-500/20'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.id === 'queue' && stats && stats.pendingQueueCount > 0 && (
                    <span className="ml-1 px-1.5 py-0.2 rounded-full text-[9px] bg-amber-500 text-slate-950 font-mono font-bold">
                      {stats.pendingQueueCount}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* User Account Pill */}
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-800/80 border border-slate-700/60 rounded-full text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400 animate-ping"></span>
              <span className="text-slate-300">alice@demo</span>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Tab Selector */}
      <div className="md:hidden bg-slate-900 border-b border-slate-800 px-4 py-2 overflow-x-auto flex gap-2">
        {[
          { id: 'dashboard', label: 'Dashboard' },
          { id: 'send', label: 'Send' },
          { id: 'ledger', label: 'Ledger' },
          { id: 'mesh', label: 'Mesh' },
          { id: 'queue', label: 'Queue' },
          { id: 'double-spend', label: 'Double-Spend' },
          { id: 'admin', label: 'Admin' },
          { id: 'guide', label: 'Docs' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => {
              setActiveTab(t.id as any);
              if (t.id === 'admin') handleLoadAdminLogs();
            }}
            className={`px-3 py-1 rounded-md text-xs font-semibold whitespace-nowrap ${
              activeTab === t.id ? 'bg-teal-500 text-slate-950' : 'bg-slate-800 text-slate-300'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Academic Simulation Notice */}
      <div className="bg-slate-900/60 border-b border-slate-800/80 py-1.5 px-4 text-center text-xs text-slate-400">
        <span className="inline-flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-teal-400 flex-shrink-0" />
          <span>
            <strong>Academic Research Simulation:</strong> Demonstrating offline mesh cryptographic payment routing, hybrid RSA-OAEP + AES-256-GCM encryption, idempotency deduplication, and atomic settlement. No real monetary transactions are performed.
          </span>
        </span>
      </div>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
        {/* TAB 1: DASHBOARD & PIPELINE */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm relative overflow-hidden">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <span>Simulated Balance (Alice)</span>
                  <Wallet className="w-4 h-4 text-teal-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-emerald-400">
                  {stats ? formatCurrency(stats.simulatedBalance) : '₹5,000.00'}
                </div>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                  <Database className="w-3 h-3 text-teal-400" />
                  <span>Authoritative Core Ledger Balance</span>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <span>Settled Transactions</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-white">
                  {stats?.settledCount ?? 0}
                </div>
                <div className="text-xs text-slate-400 mt-1">Settled on core banking database</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <span>Offline Queue Items</span>
                  <Clock className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-amber-400">
                  {stats?.pendingQueueCount ?? 0}
                </div>
                <div className="text-xs text-slate-400 mt-1">Durable offline pending packets</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  <span>Idempotency Cache</span>
                  <ShieldCheck className="w-4 h-4 text-teal-400" />
                </div>
                <div className="text-2xl font-bold font-mono text-teal-400">
                  {stats?.idempotencyCacheSize ?? 0}
                </div>
                <div className="text-xs text-slate-400 mt-1">Unique SHA-256 claimed hashes</div>
              </div>
            </div>

            {/* Interactive Step-by-Step Mesh Pipeline */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-teal-500/30 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Radio className="w-5 h-5 text-teal-400" />
                    Interactive Mesh Pipeline (Original 4-Step Flow)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Execute simulated offline payments through the complete cryptographic and gossip lifecycle
                  </p>
                </div>
                <button
                  onClick={handleResetMesh}
                  className="px-3 py-1.5 rounded-lg border border-rose-500/30 hover:bg-rose-500/10 text-rose-400 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Reset Mesh & Cache
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Step 1 */}
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-teal-400">
                    <span className="w-5 h-5 rounded-full bg-teal-500 text-slate-950 flex items-center justify-center font-mono">
                      1
                    </span>
                    <span>Compose & Inject Payment</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="text-slate-400 text-[11px] block mb-1">Recipient VPA</label>
                      <select
                        value={receiverVpa}
                        onChange={(e) => setReceiverVpa(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white font-mono"
                      >
                        <option value="bob@demo">bob@demo (Bob)</option>
                        <option value="carol@demo">carol@demo (Carol)</option>
                        <option value="dave@demo">dave@demo (Dave)</option>
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-slate-400 text-[11px] block mb-1">Amount (₹)</label>
                        <input
                          type="number"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-slate-400 text-[11px] block mb-1">PIN</label>
                        <input
                          type="password"
                          value={pin}
                          maxLength={4}
                          onChange={(e) => setPin(e.target.value)}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-white font-mono"
                        />
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={handleDemoInject}
                    className="w-full mt-2 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all shadow-sm"
                  >
                    <Send className="w-3.5 h-3.5" />
                    Inject into phone-alice
                  </button>
                </div>

                {/* Step 2 */}
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold text-teal-400 mb-2">
                      <span className="w-5 h-5 rounded-full bg-teal-500 text-slate-950 flex items-center justify-center font-mono">
                        2
                      </span>
                      <span>Run Gossip Rounds</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Every device broadcasts held packets to nearby peers over simulated Bluetooth mesh. TTL is decremented per hop until reaching 0.
                    </p>
                  </div>
                  <button
                    onClick={handleGossipRound}
                    className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-teal-400 font-semibold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Execute Gossip Round
                  </button>
                </div>

                {/* Step 3 */}
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold text-teal-400 mb-2">
                      <span className="w-5 h-5 rounded-full bg-teal-500 text-slate-950 flex items-center justify-center font-mono">
                        3
                      </span>
                      <span>Bridge Hits 4G & Uploads</span>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Bridge node connects to 4G and submits packets to <code className="text-teal-400">/api/bridge/ingest</code>. Exercises atomic idempotency & settlement.
                    </p>
                  </div>
                  <button
                    onClick={handleFlushBridges}
                    className="w-full py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all"
                  >
                    <TowerControl className="w-3.5 h-3.5" />
                    Bridges Upload to Gateway
                  </button>
                </div>
              </div>
            </div>

            {/* Split Row: Devices & Balances */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Devices Card */}
              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-teal-400" />
                    Mesh Devices ({devices.length})
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">
                    Total in Mesh: {devices.reduce((acc, d) => acc + d.packetCount, 0)} pkts
                  </span>
                </div>
                <div className="space-y-2.5">
                  {devices.map((d) => (
                    <div
                      key={d.deviceId}
                      className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
                        d.hasInternet
                          ? 'bg-emerald-950/20 border-emerald-500/40'
                          : 'bg-slate-950/60 border-slate-800'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white">{d.name}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                              d.hasInternet
                                ? 'bg-emerald-500/20 text-emerald-400'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {d.hasInternet ? '🌐 4G BRIDGE' : '🚫 OFFLINE'}
                          </span>
                        </div>
                        <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                          ID: {d.deviceId}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="px-2 py-1 rounded bg-slate-800 font-mono text-teal-400 font-bold">
                          {d.packetCount} pkt(s)
                        </span>
                        {d.packetIds.length > 0 && (
                          <div className="text-[10px] font-mono text-slate-400 mt-1">
                            {d.packetIds.map((id) => `#${id}`).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Authoritative Core Bank Balances */}
              <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-teal-400" />
                    Core Bank Ledger Balances
                  </h3>
                  <span className="text-[11px] font-mono text-emerald-400">ACID Storage</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                        <th className="py-2">VPA</th>
                        <th className="py-2">Holder</th>
                        <th className="py-2 text-right">Balance</th>
                        <th className="py-2 text-right">Version</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {accounts.map((a) => (
                        <tr key={a.vpa} className="hover:bg-slate-800/30">
                          <td className="py-2.5 text-teal-400">{a.vpa}</td>
                          <td className="py-2.5 text-slate-300 font-sans">{a.holderName}</td>
                          <td className="py-2.5 text-right font-bold text-emerald-400">
                            {formatCurrency(a.balance)}
                          </td>
                          <td className="py-2.5 text-right text-slate-500">v{a.version}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Console Log */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
                  <Server className="w-3.5 h-3.5 text-teal-400" />
                  Live Event Console (Flask Backend)
                </span>
                <span className="text-[10px] font-mono text-slate-500">Real-Time Telemetry</span>
              </div>
              <div className="font-mono text-xs text-emerald-400/90 h-36 overflow-y-auto space-y-1">
                {logs.map((l, idx) => (
                  <div key={idx} className="leading-relaxed">
                    {l}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SEND PAYMENT */}
        {activeTab === 'send' && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
              <div className="pb-4 border-b border-slate-800 mb-6">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Send className="w-5 h-5 text-teal-400" />
                  Initiate Payment Request
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Signs instruction with client RSA-PSS key and encrypts with server RSA-OAEP + AES-256-GCM
                </p>
              </div>

              <form onSubmit={handleCreatePayment} className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1 uppercase">
                    Sender Account
                  </label>
                  <select
                    value={senderVpa}
                    onChange={(e) => setSenderVpa(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  >
                    {accounts.map((a) => (
                      <option key={a.vpa} value={a.vpa}>
                        {a.vpa} — {a.holderName} ({formatCurrency(a.balance)})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1 uppercase">
                    Recipient VPA
                  </label>
                  <input
                    type="text"
                    value={receiverVpa}
                    onChange={(e) => setReceiverVpa(e.target.value)}
                    placeholder="e.g. bob@demo"
                    required
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-bold text-slate-300 block mb-1 uppercase">
                      Amount (INR)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-2 text-teal-400 font-bold">₹</span>
                      <input
                        type="number"
                        step="0.01"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        required
                        className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-8 pr-3 py-2 text-sm text-white font-mono"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-slate-300 block mb-1 uppercase">
                      UPI PIN
                    </label>
                    <input
                      type="password"
                      value={pin}
                      maxLength={6}
                      onChange={(e) => setPin(e.target.value)}
                      required
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white font-mono"
                    />
                  </div>
                </div>

                {/* Routing Mode Toggle */}
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-2 uppercase">
                    Routing Mechanism
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setIsOfflineMode(true)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                        isOfflineMode
                          ? 'bg-teal-500/10 border-teal-500 text-teal-400'
                          : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5 mb-1">
                        <Boxes className="w-3.5 h-3.5" />
                        Durable Offline Queue
                      </div>
                      <p className="text-[11px] text-slate-400 leading-tight">
                        Store locally in SQLite queue for peer-to-peer mesh gossip.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsOfflineMode(false)}
                      className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${
                        !isOfflineMode
                          ? 'bg-teal-500/10 border-teal-500 text-teal-400'
                          : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5 mb-1">
                        <Send className="w-3.5 h-3.5" />
                        Direct Gateway
                      </div>
                      <p className="text-[11px] text-slate-400 leading-tight">
                        Simulate direct cellular/broadband connection to backend.
                      </p>
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full py-3 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm cursor-pointer shadow-md transition-all mt-4"
                >
                  <Lock className="w-4 h-4 inline mr-2" />
                  Encrypt, Sign & Submit Payment
                </button>
              </form>

              {sendResult && (
                <div
                  className={`mt-6 p-4 rounded-xl border text-xs font-mono ${
                    sendResult.ok
                      ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-400'
                      : 'bg-rose-950/20 border-rose-500/40 text-rose-400'
                  }`}
                >
                  <div className="font-bold mb-1">
                    {sendResult.ok ? '✓ Execution Successful' : '✗ Execution Error'}
                  </div>
                  <pre className="overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(sendResult.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: TRANSACTION LEDGER */}
        {activeTab === 'ledger' && (
          <div className="space-y-4">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 mb-4">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-teal-400" />
                    Permanent Authoritative Ledger
                  </h2>
                  <p className="text-xs text-slate-400">
                    Immutable records protected by SHA-256 ciphertext hash uniqueness
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search VPA or Hash..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white font-mono"
                    />
                  </div>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white"
                  >
                    <option value="">All Statuses</option>
                    <option value="SETTLED">SETTLED</option>
                    <option value="REJECTED">REJECTED</option>
                    <option value="DUPLICATE_DROPPED">DUPLICATE_DROPPED</option>
                    <option value="REQUIRES_REVIEW">REQUIRES_REVIEW</option>
                  </select>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                      <th className="py-2.5">ID</th>
                      <th className="py-2.5">SHA-256 Packet Hash (Idempotency Key)</th>
                      <th className="py-2.5">From</th>
                      <th className="py-2.5">To</th>
                      <th className="py-2.5">Amount</th>
                      <th className="py-2.5">Status</th>
                      <th className="py-2.5">Signature</th>
                      <th className="py-2.5">Gateway</th>
                      <th className="py-2.5">Hops</th>
                      <th className="py-2.5">Settled</th>
                      <th className="py-2.5 text-right">Offline QR</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {transactions.length === 0 ? (
                      <tr>
                        <td colSpan={11} className="py-8 text-center text-slate-500 font-sans">
                          No transactions found in ledger.
                        </td>
                      </tr>
                    ) : (
                      transactions.map((tx) => (
                        <tr key={tx.id} className="hover:bg-slate-800/30">
                          <td className="py-2.5 font-bold text-slate-400">#{tx.id}</td>
                          <td className="py-2.5 text-teal-400" title={tx.packetHash}>
                            {truncateHash(tx.packetHash, 8, 6)}
                          </td>
                          <td className="py-2.5 text-slate-300">{tx.senderVpa}</td>
                          <td className="py-2.5 text-slate-300">{tx.receiverVpa}</td>
                          <td className="py-2.5 font-bold text-white">
                            {formatCurrency(tx.amount)}
                          </td>
                          <td className="py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                tx.status === 'SETTLED'
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                  : tx.status === 'REJECTED'
                                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                  : tx.status === 'DUPLICATE_DROPPED'
                                  ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                  : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                              }`}
                            >
                              {tx.status}
                            </span>
                          </td>
                          <td className="py-2.5 text-[11px]">
                            {tx.signatureValid ? (
                              <span className="text-emerald-400">✓ Valid</span>
                            ) : (
                              <span className="text-slate-500">Unsigned</span>
                            )}
                          </td>
                          <td className="py-2.5 text-slate-400">{tx.bridgeNodeId || 'direct'}</td>
                          <td className="py-2.5 text-center text-slate-400">{tx.hopCount}</td>
                          <td className="py-2.5 text-slate-500 text-[11px]">
                            {tx.settledAt ? new Date(tx.settledAt).toLocaleTimeString() : '-'}
                          </td>
                          <td className="py-2.5 text-right font-sans">
                            <button
                              onClick={() => setSelectedQrTx(tx)}
                              title="Generate offline-readable QR code"
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 text-xs font-semibold cursor-pointer transition-colors"
                            >
                              <QrCode className="w-3.5 h-3.5 text-teal-400" />
                              <span>QR Code</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: MESH TOPOLOGY VISUALIZER */}
        {activeTab === 'mesh' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Radio className="w-5 h-5 text-teal-400" />
                    Multi-Hop Mesh Network Visualizer
                  </h2>
                  <p className="text-xs text-slate-400">
                    Interactive topology map of peer devices propagating encrypted packets to the 4G gateway
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGossipRound}
                    className="px-3 py-1.5 rounded-lg bg-teal-500/10 hover:bg-teal-500/20 text-teal-400 border border-teal-500/30 text-xs font-semibold cursor-pointer"
                  >
                    Run Gossip
                  </button>
                  <button
                    onClick={handleFlushBridges}
                    className="px-3 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs cursor-pointer"
                  >
                    Flush Gateway
                  </button>
                </div>
              </div>

              {/* Graphical Topology Canvas */}
              <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 flex items-center justify-center relative min-h-[320px]">
                <svg viewBox="0 0 800 240" className="w-full max-w-4xl h-auto">
                  {/* Mesh link lines */}
                  <line x1="100" y1="120" x2="250" y2="60" stroke="#334155" strokeWidth="2" strokeDasharray="4" />
                  <line x1="250" y1="60" x2="400" y2="120" stroke="#334155" strokeWidth="2" strokeDasharray="4" />
                  <line x1="400" y1="120" x2="550" y2="60" stroke="#334155" strokeWidth="2" strokeDasharray="4" />
                  <line x1="550" y1="60" x2="700" y2="120" stroke="#334155" strokeWidth="2" strokeDasharray="4" />
                  <line x1="250" y1="60" x2="550" y2="60" stroke="#1e293b" strokeWidth="1.5" strokeDasharray="2" />

                  {/* 5 Mesh Nodes */}
                  {[
                    { id: 'phone-alice', name: 'Alice (Sender)', x: 100, y: 120, isBridge: false },
                    { id: 'phone-stranger1', name: 'Stranger 1', x: 250, y: 60, isBridge: false },
                    { id: 'phone-stranger2', name: 'Stranger 2', x: 400, y: 120, isBridge: false },
                    { id: 'phone-stranger3', name: 'Stranger 3', x: 550, y: 60, isBridge: false },
                    { id: 'phone-bridge', name: '4G Bridge', x: 700, y: 120, isBridge: true }
                  ].map((n) => {
                    const dev = devices.find((d) => d.deviceId === n.id);
                    const count = dev?.packetCount || 0;
                    return (
                      <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
                        <circle
                          r="28"
                          fill="#0f172a"
                          stroke={n.isBridge ? '#10b981' : '#14b8a6'}
                          strokeWidth={n.isBridge ? '3' : '2'}
                        />
                        <circle
                          r="18"
                          fill={n.isBridge ? '#10b981' : '#14b8a6'}
                          opacity={count > 0 ? 0.35 : 0.1}
                        />
                        <text
                          textAnchor="middle"
                          dy="5"
                          fill="#ffffff"
                          fontSize="13"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          {count}
                        </text>
                        <text
                          textAnchor="middle"
                          dy="44"
                          fill="#cbd5e1"
                          fontSize="11"
                          fontWeight="600"
                        >
                          {n.name}
                        </text>
                        <text
                          textAnchor="middle"
                          dy="58"
                          fill={n.isBridge ? '#34d399' : '#64748b'}
                          fontSize="9"
                          fontWeight="bold"
                        >
                          {n.isBridge ? '🌐 4G GATEWAY' : '🚫 OFFLINE PEER'}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Slider for Packet Loss Simulation */}
              <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800 max-w-md">
                <div className="flex justify-between items-center mb-1 text-xs">
                  <span className="font-bold text-slate-300">Simulated Packet Loss Rate</span>
                  <span className="font-mono text-teal-400 font-bold">
                    {Math.round(packetLossRate * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="0.5"
                  step="0.05"
                  value={packetLossRate}
                  onChange={async (e) => {
                    const val = parseFloat(e.target.value);
                    setPacketLossRate(val);
                    await fetch('/api/mesh/config', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ packetLossRate: val })
                    });
                  }}
                  className="w-full accent-teal-400 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                  <span>0% (Ideal BLE)</span>
                  <span>25% (Interference)</span>
                  <span>50% (High Loss)</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: OFFLINE QUEUE */}
        {activeTab === 'queue' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Boxes className="w-5 h-5 text-teal-400" />
                    Durable Offline Transaction Queue
                  </h2>
                  <p className="text-xs text-slate-400">
                    Locally stored, tamper-resistant payment requests awaiting synchronization
                  </p>
                </div>
                <button
                  onClick={handleTriggerSync}
                  className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer shadow-sm transition-all"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Synchronize All Pending ({stats?.pendingQueueCount ?? 0})
                </button>
              </div>

              {/* State Machine Legend */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 mb-6 flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
                <span className="text-slate-400">State Transitions:</span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">CREATED</span>
                <span>➔</span>
                <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">PENDING_OFFLINE</span>
                <span>➔</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">READY_TO_SYNC</span>
                <span>➔</span>
                <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-400">SYNCING</span>
                <span>➔</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">COMPLETED_SIMULATION</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                      <th className="py-2.5">Queue ID</th>
                      <th className="py-2.5">Packet ID</th>
                      <th className="py-2.5">From</th>
                      <th className="py-2.5">To</th>
                      <th className="py-2.5">Amount</th>
                      <th className="py-2.5">Status</th>
                      <th className="py-2.5 text-center">Attempts</th>
                      <th className="py-2.5">Signed At</th>
                      <th className="py-2.5">Last Sync Attempt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {queueItems.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-slate-500 font-sans">
                          Offline queue is currently empty. Use "Send Payment" in offline mode to enqueue transactions.
                        </td>
                      </tr>
                    ) : (
                      queueItems.map((item) => (
                        <tr key={item.id} className="hover:bg-slate-800/30">
                          <td className="py-2.5 text-slate-400">#{item.id}</td>
                          <td className="py-2.5 text-teal-400">{item.packetId.slice(0, 8)}...</td>
                          <td className="py-2.5 text-slate-300">{item.senderVpa}</td>
                          <td className="py-2.5 text-slate-300">{item.receiverVpa}</td>
                          <td className="py-2.5 font-bold text-white">
                            {formatCurrency(item.amount)}
                          </td>
                          <td className="py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                item.status === 'COMPLETED_SIMULATION'
                                  ? 'bg-emerald-500/20 text-emerald-400'
                                  : item.status === 'REQUIRES_REVIEW'
                                  ? 'bg-purple-500/20 text-purple-400'
                                  : item.status === 'FAILED'
                                  ? 'bg-rose-500/20 text-rose-400'
                                  : 'bg-amber-500/20 text-amber-400'
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-2.5 text-center text-slate-400">{item.attempts}</td>
                          <td className="py-2.5 text-slate-500">
                            {item.signedAt ? new Date(item.signedAt).toLocaleTimeString() : '-'}
                          </td>
                          <td className="py-2.5 text-slate-500">
                            {item.lastAttemptAt
                              ? new Date(item.lastAttemptAt).toLocaleTimeString()
                              : '-'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: DOUBLE-SPENDING DEMONSTRATION */}
        {activeTab === 'double-spend' && (
          <div className="space-y-6 max-w-4xl mx-auto">
            <div className="p-6 rounded-2xl bg-slate-900 border border-amber-500/30 shadow-lg">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-amber-400" />
                    Double-Spending Conflict Demonstration
                  </h2>
                  <p className="text-xs text-slate-400">
                    Controlled academic experiment proving offline stale balance conflicts and ledger reconciliation
                  </p>
                </div>
                <button
                  onClick={handleRunDoubleSpend}
                  disabled={isSimulatingDS}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Activity className="w-3.5 h-3.5" />
                  {isSimulatingDS ? 'Simulating...' : 'Run Demonstration'}
                </button>
              </div>

              {/* Scenario Explanation Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider mb-1">
                    Step 1: Stale Balance
                  </div>
                  <h3 className="font-bold text-white text-xs mb-1">Initial Balance ₹1,000</h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Alice enters an underground basement with ₹1,000. Both disconnected phones record ₹1,000.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-[11px] font-bold text-teal-400 uppercase tracking-wider mb-1">
                    Step 2: Competing Requests
                  </div>
                  <h3 className="font-bold text-white text-xs mb-1">₹800 + ₹700 = ₹1,500</h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Device A signs ₹800 to Bob. Device B signs ₹700 to Carol. Total exceeds ₹1,000!
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-1">
                    Step 3: Reconciliation
                  </div>
                  <h3 className="font-bold text-white text-xs mb-1">First-Come Settles</h3>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Upon reconnection, Tx A settles. Tx B triggers conflict detection & is rejected without overdraft.
                  </p>
                </div>
              </div>

              {/* Simulation Result Output */}
              {doubleSpendData && (
                <div className="p-5 rounded-xl bg-slate-950 border border-amber-500/40 space-y-4 mb-6">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    Empirical Reconciliation Results
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
                      <span className="text-[10px] font-bold uppercase text-emerald-400">
                        Arrival 1 (phone-bridge-alpha)
                      </span>
                      <div className="font-bold text-white text-xs mt-1">Alice pays Bob ₹800.00</div>
                      <div className="text-xs font-mono text-emerald-400 mt-1 font-bold">
                        Outcome: {doubleSpendData.transactionA.outcome}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        Alice balance debited from ₹1,000 ➔ ₹200.
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30">
                      <span className="text-[10px] font-bold uppercase text-rose-400">
                        Arrival 2 (phone-bridge-beta)
                      </span>
                      <div className="font-bold text-white text-xs mt-1">Alice pays Carol ₹700.00</div>
                      <div className="text-xs font-mono text-rose-400 mt-1 font-bold">
                        Outcome: {doubleSpendData.transactionB.outcome}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1">
                        {doubleSpendData.transactionB.reason || 'Insufficient available balance (₹200 < ₹700)'}
                      </div>
                    </div>
                  </div>

                  {/* Audit Comparison Table */}
                  <div className="overflow-x-auto border-t border-slate-800 pt-3">
                    <table className="w-full text-xs text-left font-mono">
                      <thead>
                        <tr className="text-slate-400 text-[11px]">
                          <th>Participant</th>
                          <th>Initial Balance</th>
                          <th>Final Balance</th>
                          <th>Net Change</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        <tr>
                          <td className="py-1.5 text-teal-400">alice@demo</td>
                          <td className="py-1.5">{formatCurrency(doubleSpendData.initialState.aliceBalance)}</td>
                          <td className="py-1.5 text-emerald-400 font-bold">{formatCurrency(doubleSpendData.finalState.aliceBalance)}</td>
                          <td className="py-1.5 text-rose-400">-₹800.00</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 text-teal-400">bob@demo</td>
                          <td className="py-1.5">{formatCurrency(doubleSpendData.initialState.bobBalance)}</td>
                          <td className="py-1.5 text-emerald-400 font-bold">{formatCurrency(doubleSpendData.finalState.bobBalance)}</td>
                          <td className="py-1.5 text-emerald-400">+₹800.00</td>
                        </tr>
                        <tr>
                          <td className="py-1.5 text-teal-400">carol@demo</td>
                          <td className="py-1.5">{formatCurrency(doubleSpendData.initialState.carolBalance)}</td>
                          <td className="py-1.5 text-emerald-400 font-bold">{formatCurrency(doubleSpendData.finalState.carolBalance)}</td>
                          <td className="py-1.5 text-slate-500">₹0.00 (Protected)</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Honest Engineering Defense Notes */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 space-y-2">
                <div className="font-bold text-white flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-teal-400" />
                  Engineering Viva Note: CAP Theorem in Offline Payments
                </div>
                <p className="leading-relaxed">
                  In a network partition (P), consistency (C) and availability (A) cannot both be guaranteed across disconnected nodes. Because peer devices cannot communicate with a global consensus lock, offline software payments are <em>asynchronous promissory requests</em>.
                </p>
                <p className="leading-relaxed">
                  <strong>Why real-world UPI Lite uses Secure Elements:</strong> Real-world offline payments require a physical tamper-resistant hardware chip (eSE/UICC) that decrements a locally pre-funded balance securely before signing.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: ADMIN & AUDIT LOGS */}
        {activeTab === 'admin' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800 mb-6">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Lock className="w-5 h-5 text-teal-400" />
                    System Administration & Security Audit Trail
                  </h2>
                  <p className="text-xs text-slate-400">
                    Security event logs, key management, and system baseline controls
                  </p>
                </div>
                <button
                  onClick={handleFactoryReset}
                  className="px-3 py-1.5 rounded-lg border border-rose-500/40 text-rose-400 hover:bg-rose-500/10 text-xs font-semibold cursor-pointer"
                >
                  Factory Reset System
                </button>
              </div>

              {/* Cryptographic Key Information */}
              {serverKey && (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 mb-6 text-xs font-mono space-y-1">
                  <div className="text-slate-400">
                    Algorithm: <span className="text-teal-400">{serverKey.algorithm}</span>
                  </div>
                  <div className="text-slate-400">
                    Scheme: <span className="text-teal-400">{serverKey.hybridScheme}</span>
                  </div>
                  <div className="text-slate-400">
                    Signature: <span className="text-teal-400">{serverKey.signatureAlgorithm}</span>
                  </div>
                </div>
              )}

              {/* Audit Logs Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                      <th className="py-2.5">Timestamp</th>
                      <th className="py-2.5">Event Type</th>
                      <th className="py-2.5">Actor</th>
                      <th className="py-2.5">Severity</th>
                      <th className="py-2.5">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-500 font-sans">
                          No audit events loaded. Click "Refresh" or perform transactions to view logs.
                        </td>
                      </tr>
                    ) : (
                      auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-800/30">
                          <td className="py-2 text-slate-500">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </td>
                          <td className="py-2 font-bold text-teal-400">{log.eventType}</td>
                          <td className="py-2 text-slate-300">{log.actor}</td>
                          <td className="py-2">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                log.severity === 'CRITICAL'
                                  ? 'bg-rose-500/20 text-rose-400'
                                  : log.severity === 'WARNING'
                                  ? 'bg-amber-500/20 text-amber-400'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {log.severity}
                            </span>
                          </td>
                          <td className="py-2 text-slate-400 text-[11px] font-sans">
                            {log.details || '-'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: ARCHITECTURE & VIVA GUIDE */}
        {activeTab === 'guide' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800">
              <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                <Layers className="w-5 h-5 text-teal-400" />
                Technical Architecture & Cryptographic Workflow
              </h2>
              <p className="text-xs text-slate-400 mb-6">
                Comprehensive explanation of hybrid encryption, replay mitigation, and mesh routing
              </p>

              <div className="space-y-4 text-xs text-slate-300 leading-relaxed">
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h3 className="font-bold text-teal-400 text-sm mb-2">1. Hybrid Encryption (RSA-OAEP + AES-256-GCM)</h3>
                  <p>
                    RSA-2048 cannot encrypt arbitrary JSON payloads directly due to its ~190-byte OAEP padding limit. The client generates a fresh, ephemeral 256-bit symmetric AES key, encrypts the payment instruction with authenticated AES-GCM (which appends a 16-byte authentication tag), and then wraps just the 32-byte AES key using RSA-OAEP with SHA-256 and MGF1.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h3 className="font-bold text-teal-400 text-sm mb-2">2. Idempotency Gate (Deduplicating the Duplicate Storm)</h3>
                  <p>
                    When multiple bridge nodes simultaneously walk outside into 4G coverage and upload identical packets, the backend hashes the incoming base64 ciphertext with SHA-256 and tests it against an atomic compare-and-set idempotency gate (simulating Redis <code className="text-teal-400">SET NX EX</code>). Only the first claimer proceeds to decryption and debit/credit execution; all others are short-circuited as <code className="text-amber-400">DUPLICATE_DROPPED</code>.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
                  <h3 className="font-bold text-teal-400 text-sm mb-2">3. Replay Protection & Digital Signatures</h3>
                  <p>
                    Every instruction embeds an epoch timestamp (<code className="text-teal-400">signedAt</code>) and a unique UUID nonce. The server rejects any packet older than 24 hours (86,400s) or future-dated beyond 300s clock skew. In addition, the canonical JSON is signed with the sender's client-side RSA private key (RSA-PSS) for complete origin authenticity and non-repudiation.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* QR Code Inspection Modal */}
      {selectedQrTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative text-slate-100">
            <button
              onClick={() => setSelectedQrTx(null)}
              className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
              <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
                <QrCode className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Offline Payment QR Code</h3>
                <p className="text-xs text-slate-400">
                  Transaction #{selectedQrTx.id} • {selectedQrTx.senderVpa} → {selectedQrTx.receiverVpa}
                </p>
              </div>
            </div>

            {/* Format toggle: NPCI UPI URI vs Cryptographic Mesh Receipt */}
            <div className="mt-4 flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs font-semibold">
              <button
                onClick={() => setQrFormat('upi')}
                className={`flex-1 py-1.5 rounded-md transition-all cursor-pointer ${
                  qrFormat === 'upi'
                    ? 'bg-teal-500 text-slate-950 font-bold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                UPI Standard URI
              </button>
              <button
                onClick={() => setQrFormat('mesh')}
                className={`flex-1 py-1.5 rounded-md transition-all cursor-pointer ${
                  qrFormat === 'mesh'
                    ? 'bg-teal-500 text-slate-950 font-bold shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Offline Mesh Proof (JSON)
              </button>
            </div>

            {/* QR Code Canvas / Image Display */}
            <div className="mt-5 flex flex-col items-center justify-center p-4 bg-slate-950 rounded-xl border border-slate-800">
              {qrDataUrl ? (
                <div className="p-3 bg-[#e2f9f6] rounded-xl shadow-inner border border-teal-500/40">
                  <img
                    src={qrDataUrl}
                    alt="Transaction QR Code"
                    className="w-56 h-56 object-contain block rounded-lg"
                  />
                </div>
              ) : (
                <div className="w-56 h-56 flex items-center justify-center text-slate-500 text-xs">
                  Generating QR code...
                </div>
              )}
              <div className="mt-3 text-center">
                <span className="text-xs font-bold font-mono text-teal-300">
                  {formatCurrency(selectedQrTx.amount)}
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Scan with any UPI camera or offline validator node
                </span>
              </div>
            </div>

            {/* Raw Encoded Payload */}
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span className="font-semibold">
                  {qrFormat === 'upi' ? 'Decoded UPI Intent URI' : 'Mesh Cryptographic Verification Proof'}
                </span>
                <button
                  onClick={() => {
                    const text =
                      qrFormat === 'upi'
                        ? generateUpiQrUri({
                            id: selectedQrTx.id,
                            senderVpa: selectedQrTx.senderVpa,
                            receiverVpa: selectedQrTx.receiverVpa,
                            amount: selectedQrTx.amount,
                            packetHash: selectedQrTx.packetHash,
                          })
                        : generateMeshReceiptPayload({
                            id: selectedQrTx.id,
                            senderVpa: selectedQrTx.senderVpa,
                            receiverVpa: selectedQrTx.receiverVpa,
                            amount: selectedQrTx.amount,
                            packetHash: selectedQrTx.packetHash,
                            status: selectedQrTx.status,
                            hopCount: selectedQrTx.hopCount,
                            isMeshRelayed: selectedQrTx.hopCount > 0,
                            timestamp: selectedQrTx.settledAt,
                          });
                    navigator.clipboard.writeText(text);
                    setQrCopied(true);
                    setTimeout(() => setQrCopied(false), 2000);
                  }}
                  className="inline-flex items-center gap-1 text-[11px] text-teal-400 hover:text-teal-300 cursor-pointer"
                >
                  {qrCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{qrCopied ? 'Copied' : 'Copy Payload'}</span>
                </button>
              </div>
              <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-teal-300/90 overflow-x-auto max-h-24 whitespace-pre-wrap break-all">
                {qrFormat === 'upi'
                  ? generateUpiQrUri({
                      id: selectedQrTx.id,
                      senderVpa: selectedQrTx.senderVpa,
                      receiverVpa: selectedQrTx.receiverVpa,
                      amount: selectedQrTx.amount,
                      packetHash: selectedQrTx.packetHash,
                    })
                  : generateMeshReceiptPayload({
                      id: selectedQrTx.id,
                      senderVpa: selectedQrTx.senderVpa,
                      receiverVpa: selectedQrTx.receiverVpa,
                      amount: selectedQrTx.amount,
                      packetHash: selectedQrTx.packetHash,
                      status: selectedQrTx.status,
                      hopCount: selectedQrTx.hopCount,
                      isMeshRelayed: selectedQrTx.hopCount > 0,
                      timestamp: selectedQrTx.settledAt,
                    })}
              </pre>
            </div>

            {/* Modal Actions */}
            <div className="mt-5 flex items-center justify-between gap-3 pt-3 border-t border-slate-800">
              <a
                href={qrDataUrl}
                download={`upi_tx_${selectedQrTx.id}_qr.png`}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  qrDataUrl
                    ? 'bg-slate-800 hover:bg-slate-700 text-white cursor-pointer'
                    : 'bg-slate-800/40 text-slate-500 pointer-events-none'
                }`}
              >
                <Download className="w-3.5 h-3.5" />
                <span>Save QR Image</span>
              </a>
              <button
                onClick={() => setSelectedQrTx(null)}
                className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold cursor-pointer transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>UPI Without Internet — Academic Mesh Payment Simulation</span>
          <span className="font-mono text-slate-400">Python 3.11 / Flask / SQLAlchemy / Cryptography</span>
        </div>
      </footer>
    </div>
  );
}
