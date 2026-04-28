import { useEffect, useState } from 'react';
import { Activity, Radio, Scan, Pause, Play } from 'lucide-react';

export default function DashboardHeader() {
  const [time, setTime] = useState('');
  const [scanEnabled, setScanEnabled] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, '0');
      const m = String(now.getUTCMinutes()).padStart(2, '0');
      const s = String(now.getUTCSeconds()).padStart(2, '0');
      setTime(`${h}:${m}:${s} UTC`);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch('/api/scan/status')
      .then(r => r.json())
      .then(d => setScanEnabled(d.enabled))
      .catch(() => {});
  }, []);

  const toggleScan = () => {
    setLoading(true);
    fetch('/api/scan/toggle', { method: 'POST' })
      .then(r => r.json())
      .then(d => {
        setScanEnabled(d.enabled);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border-subtle bg-bg-primary/85 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <h1 className="font-display text-2xl tracking-[4px] text-cyan">
            ATLAS
          </h1>
          <span className="hidden font-mono text-xs font-light tracking-[2px] text-text-muted sm:inline">
            Polymarket
          </span>
        </div>

        {/* Center: Status + Scan Toggle */}
        <div className="hidden items-center gap-4 md:flex">
          <div className={`flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium uppercase tracking-[1px] border ${scanEnabled ? 'bg-green-dim text-green border-green/20' : 'bg-red-500/10 text-red-400 border-red-400/20'}`}>
            <span className={`relative flex h-2 w-2 ${scanEnabled ? '' : ''}`}>
              {scanEnabled && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green opacity-75" />}
              <span className={`relative inline-flex h-2 w-2 rounded-full ${scanEnabled ? 'bg-green' : 'bg-red-400'}`} />
            </span>
            {scanEnabled ? 'All Systems Nominal' : 'Scan Paused'}
          </div>
          <button
            onClick={toggleScan}
            disabled={loading}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-all ${
              scanEnabled
                ? 'border-cyan/30 bg-cyan/10 text-cyan hover:bg-cyan/20'
                : 'border-text-muted/20 bg-bg-elevated text-text-muted hover:bg-bg-hover'
            } disabled:opacity-50`}
          >
            {scanEnabled ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            {scanEnabled ? 'Pause Scan' : 'Resume Scan'}
          </button>
        </div>

        {/* Right: Mode + Time */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-md border border-amber/30 bg-amber-dim px-2.5 py-1 text-[11px] font-mono font-medium uppercase tracking-[1px] text-amber">
            <Radio className="h-3 w-3" />
            Paper Trade
          </div>
          <div className="hidden items-center gap-1.5 font-mono text-[11px] tracking-[0.5px] text-text-muted sm:flex">
            <Activity className="h-3.5 w-3.5 text-cyan" />
            <span>{time}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
