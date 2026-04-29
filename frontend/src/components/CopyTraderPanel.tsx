import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Users, Plus, Trash2, RefreshCw, Check, X, Clock } from 'lucide-react';

interface Wallet {
  id: string;
  wallet_address: string;
  label: string;
  weight: number;
  active: boolean;
  created_at: string;
}

interface PendingTrade {
  id: string;
  wallet_id: string;
  wallet_address: string;
  condition_id: string;
  title: string;
  outcome: string;
  avg_price: number;
  odds: number;
  initial_value: number;
  realized_pnl: number;
  is_open: boolean;
  ai_probability: number | null;
  ai_confidence: number | null;
  ai_reasoning: string | null;
  edge: number;
  agent_name: string | null;
  status: string;
  created_at: string;
}

export function CopyTraderPanel() {
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [pending, setPending] = useState<PendingTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [newAddress, setNewAddress] = useState('');
  const [newLabel, setNewLabel] = useState('');

  function loadWallets() {
    apiFetch<Wallet[]>('/api/copytrader/wallets')
      .then(setWallets)
      .catch((e) => setError(e.message))
      .finally(() => setIsLoading(false));
  }

  function loadPending() {
    apiFetch<PendingTrade[]>('/api/copytrader/pending')
      .then(setPending)
      .catch(() => {});
  }

  useEffect(() => { loadWallets(); loadPending(); }, []);

  async function addWallet(e: React.FormEvent) {
    e.preventDefault();
    if (!newAddress.trim()) return;
    try {
      await apiFetch('/api/copytrader/wallets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: newAddress.trim(), label: newLabel.trim() || newAddress.trim().slice(0, 10) }),
      });
      setNewAddress('');
      setNewLabel('');
      loadWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add wallet');
    }
  }

  async function removeWallet(id: string) {
    try {
      await apiFetch('/api/copytrader/wallets/' + id, { method: 'DELETE' });
      loadWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove wallet');
    }
  }

  async function triggerScan() {
    setIsScanning(true);
    try {
      const res = await apiFetch<{ trades_placed: number }>('/api/copytrader/scan', { method: 'POST' });
      loadPending();
      alert('Scan complete. Pending trades: ' + res.trades_placed);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setIsScanning(false);
    }
  }

  async function confirmTrade(id: string) {
    try {
      await apiFetch('/api/copytrader/confirm/' + id, { method: 'POST' });
      loadPending();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm trade');
    }
  }

  async function rejectTrade(id: string) {
    try {
      await apiFetch('/api/copytrader/reject/' + id, { method: 'POST' });
      loadPending();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject trade');
    }
  }

  async function confirmAll() {
    try {
      const res = await apiFetch<{ confirmed: number; errors: string[] }>('/api/copytrader/confirm-all', { method: 'POST' });
      loadPending();
      if (res.errors.length > 0) {
        alert(`Confirmed ${res.confirmed}, errors: ${res.errors.join(', ')}`);
      } else {
        alert(`Confirmed ${res.confirmed} trades`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm all');
    }
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-accent-cyan" />
          <h2 className="font-display text-xl tracking-[3px] uppercase">COPY TRADING</h2>
        </div>
        <button
          onClick={triggerScan}
          disabled={isScanning}
          className="flex items-center gap-1.5 rounded-lg bg-accent-cyan/10 px-3 py-1.5 text-xs font-medium text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-50"
        >
          <RefreshCw className={'h-3 w-3' + (isScanning ? ' animate-spin' : '')} />
          {isScanning ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {/* Add wallet form */}
      <form onSubmit={addWallet} className="mb-4 flex gap-2">
        <input
          value={newAddress}
          onChange={(e) => setNewAddress(e.target.value)}
          placeholder="0x... wallet address"
          className="flex-1 rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-xs font-mono text-text-primary placeholder-text-muted focus:border-accent-cyan focus:outline-none"
        />
        <input
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          placeholder="Label (optional)"
          className="w-32 rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-xs text-text-primary placeholder-text-muted focus:border-accent-cyan focus:outline-none"
        />
        <button
          type="submit"
          className="flex items-center gap-1 rounded-lg bg-accent-cyan px-3 py-2 text-xs font-medium text-black hover:bg-accent-cyan/90"
        >
          <Plus className="h-3 w-3" /> Add
        </button>
      </form>

      {error && <p className="mb-3 font-mono text-[11px] text-red">{error}</p>}

      {/* Wallets list */}
      {isLoading ? (
        <div className="space-y-2">{[1,2].map(i => <div key={i} className="h-10 animate-pulse rounded bg-bg-elevated" />)}</div>
      ) : wallets.length === 0 ? (
        <p className="font-mono text-[11px] text-text-muted mb-4">No wallets tracked yet. Add a wallet above to start copy trading.</p>
      ) : (
        <div className="space-y-2 mb-6">
          {wallets.map((w) => (
            <div key={w.id} className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-deep px-4 py-3">
              <div>
                <p className="font-mono text-xs text-text-primary">{w.label}</p>
                <p className="font-mono text-[10px] text-text-muted">{w.wallet_address.slice(0, 8)}...{w.wallet_address.slice(-6)}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className={'font-mono text-[10px] px-2 py-0.5 rounded ' + (w.active ? 'bg-green/10 text-green' : 'bg-red/10 text-red')}>
                  {w.active ? 'ACTIVE' : 'INACTIVE'}
                </span>
                <button onClick={() => removeWallet(w.id)} className="text-text-muted hover:text-red">
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pending copy trades */}
      <div className="border-t border-border-subtle pt-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-accent-amber" />
            <h3 className="font-display text-sm tracking-[2px] uppercase text-accent-amber">
              Pending Review ({pending.length})
            </h3>
          </div>
          {pending.length > 0 && (
            <button
              onClick={confirmAll}
              className="flex items-center gap-1 rounded-lg bg-green/10 px-2 py-1 text-xs font-medium text-green hover:bg-green/20"
            >
              <Check className="h-3 w-3" /> Confirm All
            </button>
          )}
        </div>

        {pending.length === 0 ? (
          <p className="font-mono text-[11px] text-text-muted">No pending trades. Run "Scan Now" to find copy opportunities.</p>
        ) : (
          <div className="space-y-3">
            {pending.map((trade) => (
              <div key={trade.id} className="rounded-lg border border-accent-amber/30 bg-accent-amber/5 px-4 py-3">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-xs text-text-primary truncate">{trade.title}</p>
                    <p className="font-mono text-[10px] text-text-muted mt-0.5">
                      {trade.wallet_address.slice(0, 8)}... &middot; {trade.is_open ? 'OPEN' : 'CLOSED'} &middot;{' '}
                      ${trade.initial_value.toFixed(2)} &middot;{' '}
                      {(trade.avg_price * 100).toFixed(1)}% &middot;{' '}
                      odds {trade.odds.toFixed(2)}x
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => confirmTrade(trade.id)}
                      className="flex items-center gap-1 rounded-lg bg-green/10 px-2 py-1 text-xs font-medium text-green hover:bg-green/20"
                      title="Confirm"
                    >
                      <Check className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => rejectTrade(trade.id)}
                      className="flex items-center gap-1 rounded-lg bg-red/10 px-2 py-1 text-xs font-medium text-red hover:bg-red/20"
                      title="Reject"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                </div>

                {/* AI Analysis */}
                {trade.ai_probability != null && (
                  <div className="mt-2 rounded bg-bg-deep px-3 py-2 border border-border-subtle">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[10px] text-accent-cyan">
                        {trade.agent_name || 'AI Agent'}
                      </span>
                      <div className="flex gap-3">
                        <span className="font-mono text-[10px] text-text-muted">
                          AI: <span className="text-accent-cyan">{(trade.ai_probability * 100).toFixed(0)}%</span>
                        </span>
                        <span className="font-mono text-[10px] text-text-muted">
                          Edge: <span className={trade.edge > 0 ? 'text-green' : 'text-red'}>{trade.edge > 0 ? '+' : ''}{(trade.edge * 100).toFixed(1)}%</span>
                        </span>
                        {trade.ai_confidence != null && (
                          <span className="font-mono text-[10px] text-text-muted">
                            Conf: <span className="text-text-primary">{(trade.ai_confidence * 100).toFixed(0)}%</span>
                          </span>
                        )}
                      </div>
                    </div>
                    {trade.ai_reasoning && (
                      <p className="font-mono text-[10px] text-text-muted leading-relaxed">
                        {trade.ai_reasoning.slice(0, 200)}{trade.ai_reasoning.length > 200 ? '...' : ''}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
