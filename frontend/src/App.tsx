import DashboardHeader from '@/components/DashboardHeader';
import { KpiRow } from '@/components/KpiRow';
import { PrismRegime } from '@/components/PrismRegime';
import JanusWeights from '@/components/JanusWeights';
import { AgentHierarchy } from '@/components/AgentHierarchy';
import PerformanceChart from '@/components/PerformanceChart';
import OpenBetsTable from '@/components/OpenBetsTable';
import ResolvedBetsTable from '@/components/ResolvedBetsTable';
import ExportActions from '@/components/ExportActions';

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-bg-deep text-text-primary font-body antialiased">
      <DashboardHeader />

      <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-5 sm:px-6 lg:px-8">
        {/* Section: KPIs */}
        <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.05s' }}>
          <KpiRow />
        </section>

        {/* Section: PRISM + JANUS Row */}
        <section className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="animate-fade-up" style={{ animationDelay: '0.15s' }}>
            <PrismRegime />
          </div>
          <div className="animate-fade-up" style={{ animationDelay: '0.2s' }}>
            <JanusWeights />
          </div>
        </section>

        {/* Section: Agent Hierarchy */}
        <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.25s' }}>
          <AgentHierarchy />
        </section>

        {/* Section: Performance Chart */}
        <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.3s' }}>
          <PerformanceChart />
        </section>

        {/* Section: Open Bets */}
        <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.35s' }}>
          <OpenBetsTable />
        </section>

        {/* Section: Resolved Bets */}
        <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.4s' }}>
          <ResolvedBetsTable />
        </section>

        {/* Section: Export + Footer */}
        <footer className="animate-fade-up border-t border-border-subtle py-6" style={{ animationDelay: '0.45s' }}>
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <ExportActions />
            <div className="text-center sm:text-right">
              <p className="font-mono text-[10px] tracking-[1px] text-text-muted uppercase">
                ATLAS Dashboard v2 — Real-time data from PostgreSQL
              </p>
              <p className="mt-1 font-mono text-[10px] text-text-muted/60">
                Auto-refresh every 5s · Zero mock data
              </p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
