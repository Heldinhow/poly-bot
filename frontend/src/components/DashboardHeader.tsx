import { useEffect, useState } from 'react';
import { Activity, Radio } from 'lucide-react';

export default function DashboardHeader() {
  const [time, setTime] = useState('');

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

        {/* Center: Status */}
        <div className="hidden items-center gap-4 md:flex">
          <div className="flex items-center gap-2 rounded-full bg-green-dim px-3.5 py-1.5 text-xs font-medium uppercase tracking-[1px] text-green border border-green/20">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green" />
            </span>
            All Systems Nominal
          </div>
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
