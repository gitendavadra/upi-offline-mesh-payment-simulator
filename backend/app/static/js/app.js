// UPI Offline Mesh Simulator — Client Controller

function logConsole(message, type = 'info') {
    const el = document.getElementById('activity-log');
    if (!el) return;
    const time = new Date().toLocaleTimeString();
    const prefix = type === 'error' ? '❌ ' : type === 'success' ? '✅ ' : '📡 ';
    el.textContent = `[${time}] ${prefix}${message}\n` + el.textContent;
}

async function refreshAll() {
    try {
        // 1. Fetch dashboard metrics
        const statsRes = await fetch('/api/dashboard/stats');
        if (statsRes.ok) {
            const stats = await statsRes.json();
            updateStat('stat-balance', `₹${parseFloat(stats.simulatedBalance).toFixed(2)}`);
            updateStat('stat-total-tx', stats.totalTransactions);
            updateStat('stat-settled', stats.settledCount);
            updateStat('stat-pending', stats.pendingQueueCount);
            updateStat('stat-cache-size', stats.idempotencyCacheSize);
            updateStat('stat-mesh-packets', stats.packetsInMesh);
            const userPill = document.getElementById('nav-user-vpa');
            if (userPill) userPill.textContent = stats.userVpa;
        }

        // 2. Fetch Accounts
        const accRes = await fetch('/api/accounts');
        if (accRes.ok) {
            const accounts = await accRes.json();
            const tbody = document.querySelector('#accounts-table tbody');
            if (tbody) {
                tbody.innerHTML = accounts.map(a => `
                    <tr>
                        <td class="font-mono text-teal">${a.vpa}</td>
                        <td>${a.holderName}</td>
                        <td class="font-mono fw-bold text-green">₹${parseFloat(a.balance).toFixed(2)}</td>
                        <td class="font-mono text-xs text-slate-400">v${a.version}</td>
                    </tr>
                `).join('');
            }
        }

        // 3. Fetch Transactions
        const txRes = await fetch('/api/transactions?limit=15');
        if (txRes.ok) {
            const txData = await txRes.json();
            const tbody = document.querySelector('#tx-table tbody');
            if (tbody) {
                tbody.innerHTML = txData.transactions.map(t => {
                    const badgeClass =
                        t.status === 'SETTLED' ? 'badge-status-settled' :
                        t.status === 'REJECTED' ? 'badge-status-rejected' :
                        t.status === 'DUPLICATE_DROPPED' ? 'badge-status-duplicate' : 'badge-status-pending';
                    return `
                        <tr>
                            <td class="font-mono text-xs">#${t.id}</td>
                            <td class="font-mono text-xs">${t.senderVpa}</td>
                            <td class="font-mono text-xs">${t.receiverVpa}</td>
                            <td class="font-mono fw-bold">₹${parseFloat(t.amount).toFixed(2)}</td>
                            <td><span class="badge ${badgeClass}">${t.status}</span></td>
                            <td class="font-mono text-xs">${t.bridgeNodeId || 'direct'}</td>
                            <td class="text-center">${t.hopCount}</td>
                            <td class="text-xs text-slate-400 font-mono">${t.settledAt ? new Date(t.settledAt).toLocaleTimeString() : '-'}</td>
                        </tr>
                    `;
                }).join('');
            }
        }

        // 4. Fetch Mesh Device State
        const meshRes = await fetch('/api/mesh/state');
        if (meshRes.ok) {
            const m = await meshRes.json();
            const devicesDiv = document.getElementById('mesh-devices-container');
            if (devicesDiv) {
                devicesDiv.innerHTML = m.devices.map(d => `
                    <div class="card-fintech p-3 mb-2 ${d.hasInternet ? 'border-success' : ''}">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-white">${d.name}</strong>
                            <span class="badge ${d.hasInternet ? 'bg-success' : 'bg-secondary'} font-mono">
                                ${d.hasInternet ? '🌐 4G Gateway' : '🚫 OFFLINE'}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between text-xs text-slate-400 font-mono">
                            <span>ID: ${d.deviceId}</span>
                            <span>Holding: ${d.packetCount} pkt(s)</span>
                        </div>
                        ${d.packetIds.length > 0 ? `
                            <div class="mt-2 d-flex flex-wrap gap-1">
                                ${d.packetIds.map(id => `<span class="badge bg-navy-accent font-mono text-teal">${id}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            }
        }

    } catch (err) {
        console.error("Dashboard refresh error:", err);
    }
}

function updateStat(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = value;
}

// Action: Demo Send
async function injectPayment() {
    const senderVpa = document.getElementById('demo-sender')?.value || 'alice@demo';
    const receiverVpa = document.getElementById('demo-receiver')?.value || 'bob@demo';
    const amount = parseFloat(document.getElementById('demo-amount')?.value || '500');
    const pin = document.getElementById('demo-pin')?.value || '1234';

    try {
        const res = await fetch('/api/demo/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ senderVpa, receiverVpa, amount, pin, ttl: 5, startDevice: 'phone-alice' })
        });
        const data = await res.json();
        if (res.ok) {
            logConsole(`Packet ${data.packetId.substring(0,8)} encrypted & injected at ${data.injectedAt} (TTL 5)`);
            logConsole(`Ciphertext: ${data.ciphertextPreview}`);
            refreshAll();
        } else {
            logConsole(`Error: ${data.error}`, 'error');
        }
    } catch (e) {
        logConsole(`Network error: ${e.message}`, 'error');
    }
}

// Action: Gossip Round
async function runGossip() {
    try {
        const res = await fetch('/api/mesh/gossip', { method: 'POST' });
        const data = await res.json();
        logConsole(`Gossip Round: ${data.transfers} packet transfer(s) across peers (Dropped: ${data.packetLossDropped})`);
        refreshAll();
    } catch (e) {
        logConsole(`Gossip failed: ${e.message}`, 'error');
    }
}

// Action: Bridge Flush
async function flushBridges() {
    try {
        const res = await fetch('/api/mesh/flush', { method: 'POST' });
        const data = await res.json();
        logConsole(`Bridge Flush: ${data.uploadsAttempted} upload(s) attempted:`);
        data.results.forEach(r => {
            logConsole(`   ${r.bridgeNode} pkt ${r.packetId} → ${r.outcome} ${r.reason ? `(${r.reason})` : ''}`, r.outcome === 'SETTLED' ? 'success' : 'info');
        });
        refreshAll();
    } catch (e) {
        logConsole(`Flush failed: ${e.message}`, 'error');
    }
}

// Action: Reset Mesh
async function resetMesh() {
    try {
        await fetch('/api/mesh/reset', { method: 'POST' });
        logConsole(`Mesh buffers and idempotency cache cleared.`);
        refreshAll();
    } catch (e) {
        logConsole(`Reset failed: ${e.message}`, 'error');
    }
}

// Periodic auto-refresh
document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
    setInterval(refreshAll, 4000);
});
