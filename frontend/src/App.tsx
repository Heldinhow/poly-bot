import { useState } from 'react';
import DashboardHeader from '@/components/DashboardHeader';
import { KpiRow } from '@/components/KpiRow';
import { PrismRegime } from '@/components/PrismRegime';
import JanusWeights from '@/components/JanusWeights';
import { AgentHierarchy } from '@/components/AgentHierarchy';
import PerformanceChart from '@/components/PerformanceChart';
import OpenBetsTable from '@/components/OpenBetsTable';
import ResolvedBetsTable from '@/components/ResolvedBetsTable';
import ExportActions from '@/components/ExportActions';
import AgentsPage from '@/pages/AgentsPage';
import SkillsPage from '@/pages/SkillsPage';
import ExecutionsPage from '@/pages/ExecutionsPage';
import { LayoutDashboard, Bot, FileText, Activity } from 'lucide-react';

type Tab = 'dashboard' | 'agents' | 'skills' | 'executions';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="h-4 w-4" /> },
    { key: 'agents', label: 'Agents', icon: <Bot className="h-4 w-4" /> },
    { key: 'skills', label: 'Skills', icon: <FileText className="h-4 w-4" /> },
    { key: 'executions', label: 'Executions', icon: <Activity className="h-4 w-4" /> },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-bg-deep text-text-primary font-body antialiased">
      <DashboardHeader />

      {/* Tab Navigation */}
      <nav className="mx-auto w-full max-w-[1600px] px-4 pt-4 sm:px-6 lg:px-8">
        <div className="flex gap-1 rounded-xl border border-border-subtle bg-surface-elevated p-1">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-accent-cyan text-black'
                  : 'text-text-muted hover:bg-surface-hover hover:text-text-primary'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-5 sm:px-6 lg:px-8">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'agents' && <AgentsPage />}
        {activeTab === 'skills' && <SkillsPage />}
        {activeTab === 'executions' && <ExecutionsPage />}
      </main>
    </div>
  );
}

function Dashboard() {
  return (
    <>
      {/* Section: KPIs */}
      <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.05s' }}>
        <KpiRow />
      </section>

      {/* Section: Performance Chart */}
      <section className="mb-4 animate-fade-up" style={{ animationDelay: '0.1s' }}>
        <PerformanceChart />
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
    </>
  );
}

export default App;
