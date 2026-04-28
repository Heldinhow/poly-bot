import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polymarket Merge — Underdog + AI</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;padding:20px}
h1{color:#58a6ff;margin-bottom:20px;font-size:1.4rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}
.stat-label{font-size:.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
.stat-value{font-size:1.5rem;font-weight:700}
.pos{color:#3fb950}.neg{color:#f85149}.neu{color:#58a6ff}
.section{margin-bottom:28px}
.section-title{font-size:1rem;color:#8b949e;margin-bottom:10px;border-bottom:1px solid #30363d;padding-bottom:6px}
table{width:100%;border-collapse:collapse;font-size:.875rem}
th{text-align:left;color:#8b949e;font-weight:500;padding:8px 10px;border-bottom:1px solid #30363d}
td{padding:10px 10px;border-bottom:1px solid #21262d;vertical-align:top}
tr:hover td{background:#1c2128}
.win{color:#3fb950}.lose{color:#f85149}.pend{color:#d29922}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600}
.bw{background:#0f2d1a;color:#3fb950}.bl{background:#2d1215;color:#f85149}.bp{background:#2d200a;color:#d29922}
.roi-big{font-size:2rem}
.updated{font-size:.75rem;color:#484f58;margin-top:20px;text-align:center}
.no-bets{color:#484f58;font-style:italic;padding:20px;text-align:center}
.mono{font-family:monospace;font-size:.85rem}
.ai-tag{background:#1a2d4a;color:#58a6ff;padding:2px 6px;border-radius:4px;font-size:.75rem}
</style>
</head>
<body>
<h1>Polymarket Merge — Underdog + AI</h1>
<div class="stats" id="stats">Loading...</div>
<div class="section">
  <div class="section-title">Open Bets (<span id="open-count">0</span>)</div>
  <div id="open-bets"><div class="no-bets">Loading...</div></div>
</div>
<div class="section">
  <div class="section-title">Resolved Bets (recent)</div>
  <div id="resolved-bets"><div class="no-bets">Loading...</div></div>
</div>
<div class="updated" id="updated">--</div>
<script>
let lastData = null;
function render(d) {
  lastData = d;
  const s = d;
  const roiCls = s.roi_pct >= 0 ? 'pos' : 'neg';
  const bankrollCls = s.bankroll >= s.initial_bankroll ? 'pos' : 'neg';
  document.getElementById('stats').innerHTML = `
    <div class="stat"><div class="stat-label">Bankroll</div><div class="stat-value ${bankrollCls}">$${s.bankroll.toFixed(2)}</div></div>
    <div class="stat"><div class="stat-label">ROI</div><div class="stat-value roi-big ${roiCls}">${s.roi_pct>=0?'+':''}${s.roi_pct.toFixed(1)}%</div></div>
    <div class="stat"><div class="stat-label">Total Bets</div><div class="stat-value neu">${s.total_bets}</div></div>
    <div class="stat"><div class="stat-label">Win Rate</div><div class="stat-value">${s.win_rate.toFixed(0)}%</div></div>
    <div class="stat"><div class="stat-label">Wins</div><div class="stat-value win">${s.wins}</div></div>
    <div class="stat"><div class="stat-label">Losses</div><div class="stat-value lose">${s.losses}</div></div>
    <div class="stat"><div class="stat-label">Sharpe</div><div class="stat-value neu">${s.sharpe_ratio?s.sharpe_ratio.toFixed(2):'N/A'}</div></div>
    <div class="stat"><div class="stat-label">Max DD</div><div class="stat-value ${s.max_drawdown<10?'pos':'neg'}">${s.max_drawdown?s.max_drawdown.toFixed(1):'N/A'}%</div></div>
    <div class="stat"><div class="stat-label">Underdog HR</div><div class="stat-value">${s.underdog_hit_rate?s.underdog_hit_rate.toFixed(0):'N/A'}%</div></div>
  `;
  document.getElementById('open-count').textContent = s.open_bets;
  if (!d.open_bets.length) {
    document.getElementById('open-bets').innerHTML='<div class="no-bets">No open bets</div>';
  } else {
    let t='<table><tr><th>Market</th><th>Bet</th><th>Price</th><th>Stake</th><th>Payout</th><th>Edge</th><th>AI Prob</th></tr>';
    for(const b of d.open_bets){
      const aiProb = b.probability_ai ? (b.probability_ai*100).toFixed(1)+'%' : 'N/A';
      t+=`<tr><td>${esc(b.question.substring(0,55))}</td>
        <td><span class="badge bp">${esc(b.outcome)}</span></td>
        <td>${(b.price*100).toFixed(1)}%</td>
        <td class="mono">$${parseFloat(b.stake).toFixed(2)}</td>
        <td class="mono">$${parseFloat(b.payout).toFixed(2)}</td>
        <td class="pend">+${(b.edge*100).toFixed(0)}%</td>
        <td>${aiProb}</td></tr>`;
    }
    t+='</table>';
    document.getElementById('open-bets').innerHTML=t;
  }
  if(!d.recent_bets.length){
    document.getElementById('resolved-bets').innerHTML='<div class="no-bets">No resolved bets yet</div>';
  } else {
    let t='<table><tr><th>Market</th><th>Bet</th><th>Price</th><th>Stake</th><th>Payout</th><th>P&L</th><th>AI Prob</th></tr>';
    for(const b of d.recent_bets){
      const pnl=b.result==='win'?parseFloat(b.payout)-parseFloat(b.stake):-parseFloat(b.stake);
      const pnlStr=(pnl>=0?'+':'')+'$'+pnl.toFixed(2);
      const cls=b.result==='win'?'win':'lose';
      const badge=b.result==='win'?'bw':'bl';
      const aiProb = b.probability_ai ? (b.probability_ai*100).toFixed(1)+'%' : 'N/A';
      t+=`<tr><td>${esc(b.question.substring(0,45))}</td>
        <td><span class="badge ${badge}">${esc(b.outcome)}</span></td>
        <td>${(b.price*100).toFixed(1)}%</td>
        <td class="mono">$${parseFloat(b.stake).toFixed(2)}</td>
        <td class="mono">$${parseFloat(b.payout).toFixed(2)}</td>
        <td class="${cls}">${pnlStr}</td>
        <td>${aiProb}</td></tr>`;
    }
    t+='</table>';
    document.getElementById('resolved-bets').innerHTML=t;
  }
  document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();
}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
async function load(){try{const r=await fetch('state.json?t='+Date.now());if(r.ok)render(await r.json());}catch(e){console.warn(e);}}
load();setInterval(load,15000);
</script>
</body>
</html>
"""


def write_dashboard(state: dict, output_dir: str = "dashboard") -> None:
    out = Path(output_dir)
    out.mkdir(exist_ok=True)
    state_path = out / "state.json"
    html_path = out / "index.html"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    if not html_path.exists():
        with open(html_path, "w") as f:
            f.write(DASHBOARD_HTML)
        logger.info(f"Dashboard created at {out}")
