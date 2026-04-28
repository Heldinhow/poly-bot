import { useState } from 'react';

const decisions = ['ALL', 'ACCEPT', 'REJECT', 'SKIP'] as const;
const betResults = ['ALL', 'WIN', 'LOSS', 'PENDING'] as const;

export default function AuditFilterBar() {
  const [dateInput, setDateInput] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('since') || '';
  });

  const getParam = (key: string) => new URLSearchParams(window.location.search).get(key) || 'ALL';
  const [currentDecision, setCurrentDecision] = useState(getParam('decision'));
  const [currentBetResult, setCurrentBetResult] = useState(getParam('bet_result'));

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(window.location.search);
    if (value === 'ALL') {
      params.delete(key);
    } else {
      params.set(key, value);
    }
    params.delete('cursor');
    const search = params.toString();
    window.history.pushState({}, '', search ? `?${search}` : window.location.pathname);
    if (key === 'decision') setCurrentDecision(value);
    if (key === 'bet_result') setCurrentBetResult(value);
    if (key === 'since') setDateInput(value);
    window.dispatchEvent(new Event('popstate'));
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border-subtle bg-surface-elevated p-3">
      <div className="flex gap-1">
        {decisions.map(d => (
          <button
            key={d}
            onClick={() => updateFilter('decision', d)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              currentDecision === d
                ? d === 'ACCEPT'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : d === 'REJECT'
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                  : d === 'SKIP'
                  ? 'bg-text-muted/20 text-text-muted border border-text-muted/30'
                  : 'bg-accent-cyan text-black border border-accent-cyan/30'
                : 'text-text-muted hover:bg-surface-hover hover:text-text-primary'
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">Since:</span>
        <input
          type="date"
          value={dateInput}
          onChange={e => setDateInput(e.target.value)}
          className="rounded-lg border border-border-subtle bg-bg-deep px-3 py-1.5 text-xs text-text-primary"
        />
        {dateInput && (
          <button
            onClick={() => updateFilter('since', dateInput)}
            className="rounded-lg bg-accent-cyan/20 px-2 py-1 text-xs text-accent-cyan hover:bg-accent-cyan/30"
          >
            Apply
          </button>
        )}
      </div>

      <div className="flex gap-1">
        {betResults.map(r => (
          <button
            key={r}
            onClick={() => updateFilter('bet_result', r)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              currentBetResult === r
                ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30'
                : 'text-text-muted hover:bg-surface-hover hover:text-text-primary'
            }`}
          >
            {r}
          </button>
        ))}
      </div>
    </div>
  );
}