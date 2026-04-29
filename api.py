import asyncio
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from aiohttp import web

from db.agent_repository import AgentRepository
from db.truth_claim_repository import TruthClaimRepository
from db.decision_factor_repository import DecisionFactorRepository
from db.execution_summary_repository import ExecutionSummaryRepository
from db.agent_metrics_repository import AgentMetricsRepository
from db.wallet_watch_list_repository import WalletWatchListRepository
from db.pending_copy_trades_repository import PendingCopyTradesRepository


# Remove control chars invalid in JSON (allow \n, \r, \t)
_JSON_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _serialize_json(data):
    """Recursively serialize datetime, date, UUID, Decimal, and sanitize strings for JSON."""
    if isinstance(data, dict):
        return {k: _serialize_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_serialize_json(v) for v in data]
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, dt.date) and not isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, UUID):
        return str(data)
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, str):
        return _JSON_CTRL_RE.sub("", data)
    return data
from db.agent_skill_repository import AgentSkillRepository
from db.execution_repository import ExecutionRepository
from db.skill_repository import SkillRepository
from realtime.events import EXECUTION_STEP

logger = logging.getLogger(__name__)

# Global references for graceful shutdown
_api_runner = None
_api_site = None


@web.middleware
async def cors_middleware(request, handler):
    """Add CORS headers to all responses."""
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            logger.exception("Unhandled error in API handler")
            response = web.json_response(
                {"error": "Internal server error", "detail": str(e)},
                status=500,
            )
    if response is None:
        return None
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


class APIHandler:
    """HTTP request handlers for the dashboard API."""

    def __init__(self, portfolio, scan_controller=None, event_bus=None):
        self.portfolio = portfolio
        self._scan_controller = scan_controller
        self._event_bus = event_bus
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._agent_repo = AgentRepository()
        self._skill_repo = SkillRepository()
        self._execution_repo = ExecutionRepository()
        self._agent_skill_repo = AgentSkillRepository()
        self._truth_repo = TruthClaimRepository()
        self._factor_repo = DecisionFactorRepository()
        self._summary_repo = ExecutionSummaryRepository()
        self._agent_metrics_repo = AgentMetricsRepository()
        self._wallet_repo = WalletWatchListRepository()
        self._pending_copy_repo = PendingCopyTradesRepository()

    def _safe_stats(self):
        with self._lock:
            return self.portfolio.stats()

    def _safe_open_bets(self):
        with self._lock:
            return self.portfolio.get_open_bets()

    def _safe_resolved_bets(self):
        with self._lock:
            return self.portfolio.get_resolved_bets()

    async def stats(self, request):
        """GET /api/stats — portfolio statistics."""
        try:
            data = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_stats
            )
            return web.json_response(data)
        except Exception as e:
            logger.exception("Error in /api/stats")
            return web.json_response(
                {"error": "Failed to fetch stats", "detail": str(e)}, status=500
            )

    async def open_bets(self, request):
        """GET /api/bets/open — unresolved bets."""
        try:
            bets = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_open_bets
            )
            return web.json_response([b.to_dict() for b in bets])
        except Exception as e:
            logger.exception("Error in /api/bets/open")
            return web.json_response(
                {"error": "Failed to fetch open bets", "detail": str(e)}, status=500
            )

    async def resolved_bets(self, request):
        """GET /api/bets/resolved?limit=50 — resolved bets ordered by resolved_at DESC."""
        try:
            limit = int(request.query.get("limit", "50"))
        except ValueError:
            limit = 50

        try:
            bets = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_resolved_bets
            )
            bets.sort(key=lambda b: (b.resolved_at or b.timestamp, b.timestamp), reverse=True)
            return web.json_response([b.to_dict() for b in bets[:limit]])
        except Exception as e:
            logger.exception("Error in /api/bets/resolved")
            return web.json_response(
                {"error": "Failed to fetch resolved bets", "detail": str(e)}, status=500
            )

    async def timeseries(self, request):
        """GET /api/bets/timeseries?days=30 — cumulative realized P&L over time.

        Each resolved bet contributes its realized P&L:
          - WIN  → payout - stake
          - LOSS → -stake

        The curve starts at 0 and accumulates over resolved_at ascending.
        Final value equals total_realized_pnl (chart_last_value == total_pnl).
        Open bets have ZERO impact on this chart.
        """
        try:
            days = int(request.query.get("days", "30"))
        except ValueError:
            days = 30

        try:
            resolved_bets = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_resolved_bets
            )
        except Exception as e:
            logger.exception("Error fetching bets for timeseries")
            return web.json_response(
                {"error": "Failed to fetch bets", "detail": str(e)}, status=500
            )

        # Filter resolved bets only
        resolved = [b for b in resolved_bets if b.resolved and b.resolved_at]
        if not resolved:
            return web.json_response([])

        # Sort by resolved_at ASC (oldest first)
        resolved.sort(key=lambda b: b.resolved_at)

        # Build cumulative realized P&L series
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Include historical dates before window so curve is continuous
        all_event_dates = [datetime.strptime(b.resolved_at[:10], "%Y-%m-%d").date() for b in resolved]
        first_event_date = min(all_event_dates)

        cutoff = min(first_event_date, start_date)
        cumulative = 0.0
        result = []
        current_date = cutoff

        while current_date <= end_date:
            date_str = current_date.isoformat()

            # Add all bet P&L events for this date
            for bet in resolved:
                if bet.resolved_at and bet.resolved_at[:10] == date_str:
                    if bet.result == "win":
                        cumulative += bet.payout - bet.stake
                    else:
                        cumulative -= bet.stake

            if current_date >= start_date:
                result.append({
                    "date": date_str,
                    "realized_pnl": round(cumulative, 2),
                })

            current_date += timedelta(days=1)

        return web.json_response(result)

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    async def list_agents(self, request):
        """GET /api/agents — list all active agents."""
        try:
            agents = self._agent_repo.list_agents(active_only=True)
            # Load skills for each agent
            for agent in agents:
                agent["skills"] = self._agent_skill_repo.get_skills_for_agent(agent["id"])
            return web.json_response(_serialize_json(agents))
        except Exception as e:
            logger.exception("Error in /api/agents")
            return web.json_response({"error": str(e)}, status=500)

    async def get_agent(self, request):
        """GET /api/agents/:id — get agent by id."""
        try:
            agent_id = UUID(request.match_info["id"])
            agent = self._agent_repo.get_agent_by_id(agent_id)
            if not agent:
                return web.json_response({"error": "Agent not found"}, status=404)
            agent["skills"] = self._agent_skill_repo.get_skills_for_agent(agent_id)
            return web.json_response(_serialize_json(agent))
        except Exception as e:
            logger.exception("Error in GET /api/agents/:id")
            return web.json_response({"error": str(e)}, status=500)

    async def create_agent(self, request):
        """POST /api/agents — create a new agent."""
        try:
            data = await request.json()
            agent_id = self._agent_repo.create_agent(
                name=data["name"],
                runtime=data["runtime"],
                description=data.get("description"),
                model=data.get("model"),
                system_prompt=data.get("system_prompt"),
                max_concurrent_tasks=data.get("max_concurrent_tasks", 1),
                max_retries=data.get("max_retries", 1),
                custom_args=data.get("custom_args", []),
                custom_env=data.get("custom_env", {}),
            )
            # Link skills if provided
            skill_ids = data.get("skill_ids", [])
            for skill_id_str in skill_ids:
                self._agent_skill_repo.link_skill(agent_id, UUID(skill_id_str))
            return web.json_response({"id": str(agent_id)}, status=201)
        except Exception as e:
            logger.exception("Error in POST /api/agents")
            return web.json_response({"error": str(e)}, status=500)

    async def update_agent(self, request):
        """PUT /api/agents/:id — update an agent."""
        try:
            agent_id = UUID(request.match_info["id"])
            data = await request.json()
            self._agent_repo.update_agent(
                agent_id,
                name=data.get("name"),
                description=data.get("description"),
                runtime=data.get("runtime"),
                model=data.get("model"),
                system_prompt=data.get("system_prompt"),
                max_concurrent_tasks=data.get("max_concurrent_tasks"),
                max_retries=data.get("max_retries"),
                custom_args=data.get("custom_args"),
                custom_env=data.get("custom_env"),
                is_active=data.get("is_active"),
            )
            # Update skills if provided
            if "skill_ids" in data:
                skill_ids = [UUID(s) for s in data["skill_ids"]]
                self._agent_skill_repo.set_skills_for_agent(agent_id, skill_ids)
            return web.json_response({"success": True})
        except Exception as e:
            logger.exception("Error in PUT /api/agents/:id")
            return web.json_response({"error": str(e)}, status=500)

    async def delete_agent(self, request):
        """DELETE /api/agents/:id — delete an agent."""
        try:
            agent_id = UUID(request.match_info["id"])
            self._agent_repo.delete_agent(agent_id)
            return web.json_response({"success": True})
        except Exception as e:
            logger.exception("Error in DELETE /api/agents/:id")
            return web.json_response({"error": str(e)}, status=500)

    # ------------------------------------------------------------------
    # Agent Metrics
    # ------------------------------------------------------------------

    async def list_agent_metrics(self, request):
        """GET /api/agents/metrics — list all agent metrics."""
        try:
            metrics = self._agent_metrics_repo.get_all()
            return web.json_response(_serialize_json(list(metrics)))
        except Exception as e:
            logger.exception('Error in /api/agents/metrics')
            return web.json_response({'error': str(e)}, status=500)

    async def get_agent_metrics(self, request):
        """GET /api/agents/metrics/:agent_name — get single agent metrics."""
        try:
            name = request.match_info['agent_name']
            metrics = self._agent_metrics_repo.get_by_name(name)
            if not metrics:
                return web.json_response({'error': 'Agent not found'}, status=404)
            return web.json_response(_serialize_json(metrics))
        except Exception as e:
            logger.exception('Error in GET /api/agents/metrics/:name')
            return web.json_response({'error': str(e)}, status=500)

    # ------------------------------------------------------------------
    # Copy Trading
    # ------------------------------------------------------------------

    async def list_wallets(self, request):
        """GET /api/copytrader/wallets — list watched wallets."""
        try:
            wallets = self._wallet_repo.get_all()
            return web.json_response(_serialize_json(list(wallets)))
        except Exception as e:
            logger.exception('Error in /api/copytrader/wallets')
            return web.json_response({'error': str(e)}, status=500)

    async def add_wallet(self, request):
        """POST /api/copytrader/wallets — add wallet to watch list."""
        try:
            data = await request.json()
            wallet_address = data.get('wallet_address', '').strip()
            label = data.get('label', wallet_address[:10])
            weight = float(data.get('weight', 1.0))
            if not wallet_address:
                return web.json_response({'error': 'wallet_address required'}, status=400)
            wallet_id = self._wallet_repo.add(wallet_address, label, weight)
            return web.json_response({'id': str(wallet_id)}, status=201)
        except Exception as e:
            logger.exception('Error in POST /api/copytrader/wallets')
            return web.json_response({'error': str(e)}, status=500)

    async def remove_wallet(self, request):
        """DELETE /api/copytrader/wallets/:id — remove wallet from watch list."""
        try:
            wallet_id = request.match_info['id']
            self._wallet_repo.remove(wallet_id)
            return web.json_response({'success': True})
        except Exception as e:
            logger.exception('Error in DELETE /api/copytrader/wallets/:id')
            return web.json_response({'error': str(e)}, status=500)

    async def trigger_copy_scan(self, request):
        """POST /api/copytrader/scan — manually trigger copy trade scan."""
        try:
            from agents.copy_trader import CopyTraderAgent
            from data_client import PolymarketDataClient
            agent = CopyTraderAgent(
                wallet_repo=self._wallet_repo,
                data_client=PolymarketDataClient(),
                portfolio=self.portfolio,
                agent_runner=self._agent_runner,
            )
            loop = asyncio.get_event_loop()
            count = await agent.scan_wallets()
            return web.json_response({'trades_placed': count})
        except Exception as e:
            logger.exception('Error in POST /api/copytrader/scan')
            return web.json_response({'error': str(e)}, status=500)

    async def list_pending_copy_trades(self, request):
        """GET /api/copytrader/pending — list pending copy trades awaiting review."""
        try:
            pending = self._pending_copy_repo.get_pending()
            return web.json_response(_serialize_json(list(pending)))
        except Exception as e:
            logger.exception('Error in /api/copytrader/pending')
            return web.json_response({'error': str(e)}, status=500)

    async def confirm_copy_trade(self, request):
        """POST /api/copytrader/confirm/:id — confirm a pending copy trade."""
        try:
            pending_id = request.match_info['id']
            pending = self._pending_copy_repo.get_pending()
            trade = next((p for p in pending if str(p['id']) == pending_id), None)
            if not trade:
                return web.json_response({'error': 'Pending trade not found'}, status=404)

            bet = self.portfolio.record_bet(
                market_id=trade['condition_id'],
                question=trade['title'],
                outcome=trade['outcome'],
                price=float(trade['avg_price']),
                probability_ai=float(trade['ai_probability']) if trade.get('ai_probability') is not None else 0.5,
                analysis_summary=f"Copy trade from watched wallet (confirmed) | AI reasoning: {trade.get('ai_reasoning', '')[:200]}",
                agent_name=trade.get('agent_name') or "CopyTrader",
            )
            if not bet:
                return web.json_response({'error': 'Failed to place bet — market may already have an open bet'}, status=400)

            self._pending_copy_repo.confirm(pending_id)
            return web.json_response({'success': True, 'bet_id': bet.id})
        except Exception as e:
            logger.exception('Error in POST /api/copytrader/confirm/:id')
            return web.json_response({'error': str(e)}, status=500)

    async def reject_copy_trade(self, request):
        """POST /api/copytrader/reject/:id — reject a pending copy trade."""
        try:
            pending_id = request.match_info['id']
            self._pending_copy_repo.reject(pending_id)
            return web.json_response({'success': True})
        except Exception as e:
            logger.exception('Error in POST /api/copytrader/reject/:id')
            return web.json_response({'error': str(e)}, status=500)

    async def confirm_all_copy_trades(self, request):
        """POST /api/copytrader/confirm-all — confirm all pending copy trades."""
        try:
            pending = self._pending_copy_repo.get_pending()
            confirmed = 0
            errors = []
            for trade in pending:
                bet = self.portfolio.record_bet(
                    market_id=trade['condition_id'],
                    question=trade['title'],
                    outcome=trade['outcome'],
                    price=float(trade['avg_price']),
                    probability_ai=float(trade['ai_probability']) if trade.get('ai_probability') is not None else 0.5,
                    analysis_summary=f"Copy trade from watched wallet (bulk confirm) | AI reasoning: {trade.get('ai_reasoning', '')[:200]}",
                    agent_name=trade.get('agent_name') or "CopyTrader",
                )
                if bet:
                    self._pending_copy_repo.confirm(str(trade['id']))
                    confirmed += 1
                else:
                    errors.append(f"Market {trade['condition_id']} — already has open bet or stake too small")
            return web.json_response({'confirmed': confirmed, 'errors': errors})
        except Exception as e:
            logger.exception('Error in POST /api/copytrader/confirm-all')
            return web.json_response({'error': str(e)}, status=500)

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    async def list_skills(self, request):
        """GET /api/skills — list all active skills."""
        try:
            skills = self._skill_repo.list_skills(active_only=True)
            return web.json_response(_serialize_json(skills))
        except Exception as e:
            logger.exception("Error in /api/skills")
            return web.json_response({"error": str(e)}, status=500)

    async def get_skill(self, request):
        """GET /api/skills/:id — get skill by id."""
        try:
            skill_id = UUID(request.match_info["id"])
            skill = self._skill_repo.get_skill_by_id(skill_id)
            if not skill:
                return web.json_response({"error": "Skill not found"}, status=404)
            return web.json_response(_serialize_json(skill))
        except Exception as e:
            logger.exception("Error in GET /api/skills/:id")
            return web.json_response({"error": str(e)}, status=500)

    async def create_skill(self, request):
        """POST /api/skills — create a new skill."""
        try:
            data = await request.json()
            skill_id = self._skill_repo.create_skill(
                name=data["name"],
                content=data["content"],
                description=data.get("description"),
            )
            return web.json_response({"id": str(skill_id)}, status=201)
        except Exception as e:
            logger.exception("Error in POST /api/skills")
            return web.json_response({"error": str(e)}, status=500)

    async def update_skill(self, request):
        """PUT /api/skills/:id — update a skill."""
        try:
            skill_id = UUID(request.match_info["id"])
            data = await request.json()
            self._skill_repo.update_skill(
                skill_id,
                name=data.get("name"),
                description=data.get("description"),
                content=data.get("content"),
                is_active=data.get("is_active"),
            )
            return web.json_response({"success": True})
        except Exception as e:
            logger.exception("Error in PUT /api/skills/:id")
            return web.json_response({"error": str(e)}, status=500)

    async def delete_skill(self, request):
        """DELETE /api/skills/:id — delete a skill."""
        try:
            skill_id = UUID(request.match_info["id"])
            self._skill_repo.delete_skill(skill_id)
            return web.json_response({"success": True})
        except Exception as e:
            logger.exception("Error in DELETE /api/skills/:id")
            return web.json_response({"error": str(e)}, status=500)

    # ------------------------------------------------------------------
    # Executions
    # ------------------------------------------------------------------

    async def list_executions(self, request):
        """GET /api/executions — list executions with optional filters."""
        try:
            market_id = request.query.get("market_id")
            status = request.query.get("status")
            limit = int(request.query.get("limit", "100"))
            offset = int(request.query.get("offset", "0"))
            executions = self._execution_repo.list_logs(
                market_id=market_id,
                status=status,
                limit=limit,
                offset=offset,
            )
            # Strip large fields from list view (available in detail endpoint)
            for exec_ in executions:
                exec_.pop("raw_output", None)
            return web.json_response(_serialize_json(executions))
        except Exception as e:
            logger.exception("Error in /api/executions")
            return web.json_response({"error": str(e)}, status=500)

    async def get_execution(self, request):
        """GET /api/executions/:id — get execution detail."""
        try:
            log_id = UUID(request.match_info["id"])
            execution = self._execution_repo.get_log(log_id)
            if not execution:
                return web.json_response({"error": "Execution not found"}, status=404)
            return web.json_response(_serialize_json(execution))
        except Exception as e:
            logger.exception("Error in GET /api/executions/:id")
            return web.json_response({"error": str(e)}, status=500)

    async def get_execution_steps(self, request):
        """GET /api/executions/:id/steps — get execution steps."""
        try:
            log_id = UUID(request.match_info["id"])
            steps = self._execution_repo.list_steps(log_id)
            return web.json_response(_serialize_json(steps))
        except Exception as e:
            logger.exception("Error in GET /api/executions/:id/steps")
            return web.json_response({"error": str(e)}, status=500)

    async def executions_live_ws(self, request):
        """GET /api/executions/live — WebSocket endpoint for live execution updates."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

        subscription = None

        def send_event(data):
            asyncio.create_task(ws.send_json(_serialize_json(data)))

        if self._event_bus:
            subscription = self._event_bus.subscribe(send_event)

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.CLOSE:
                    break
        finally:
            if subscription is not None:
                self._event_bus.unsubscribe(subscription)
            await ws.close()

    async def executions_stream_ws(self, request):
        """GET /api/executions/{id}/stream — WebSocket endpoint streaming steps for one execution."""
        log_id_str = request.match_info["id"]
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        await ws.send_json({"type": "connected", "execution_log_id": log_id_str})

        sent_seqs = set()
        subscription = None

        def on_event(data):
            if data.type == EXECUTION_STEP:
                exec_data = data.data if isinstance(data.data, dict) else {}
                if exec_data.get("execution_log_id") != log_id_str:
                    return
                seq = exec_data.get("seq")
                if seq in sent_seqs:
                    return
                sent_seqs.add(seq)
                asyncio.create_task(ws.send_json({
                    "type": "step",
                    "seq": exec_data.get("seq"),
                    "step_type": exec_data.get("step_type"),
                    "content": exec_data.get("content"),
                    "tool_name": exec_data.get("tool_name"),
                    "tool_input": exec_data.get("tool_input"),
                    "tool_output": exec_data.get("tool_output"),
                }))

        if self._event_bus:
            subscription = self._event_bus.subscribe(on_event)

        async def heartbeat():
            while not ws.closed:
                try:
                    await asyncio.sleep(15)
                    await ws.send_json({"type": "ping"})
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.CLOSE:
                    break
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            heartbeat_task.cancel()
            if subscription is not None:
                # subscription is a lambda that calls _unsubscribe
                subscription()
            await ws.close()

    # ------------------------------------------------------------------
    # Audit Trail
    # ------------------------------------------------------------------

    async def get_market_audit(self, request):
        """GET /api/audit/market/:market_id — full audit trail for a market."""
        try:
            market_id = request.match_info["market_id"]
            summary = self._summary_repo.get_market_summary(market_id)
            if not summary:
                return web.json_response({"error": "Not found"}, status=404)
            factors = self._factor_repo.list_by_market(market_id)
            # Fetch truth claims for each execution_log_id
            all_claims = []
            for factor in factors:
                exec_id = factor.get("execution_log_id")
                if exec_id:
                    try:
                        claims = self._truth_repo.list_by_execution(exec_id)
                        all_claims.extend(claims)
                    except Exception:
                        pass
            return web.json_response(_serialize_json({
                "summary": summary,
                "decision_factors": factors,
                "truth_claims": all_claims,
            }))
        except Exception as e:
            logger.exception("Error in GET /api/audit/market/:market_id")
            return web.json_response({"error": str(e)}, status=500)

    async def list_decisions(self, request):
        """GET /api/audit/decisions?decision=REJECT&since=... — filterable decision log."""
        try:
            decision = request.query.get("decision")
            since_str = request.query.get("since")
            since = datetime.fromisoformat(since_str) if since_str else None
            limit = int(request.query.get("limit", "100"))
            offset = int(request.query.get("offset", "0"))
            factors = self._factor_repo.list_by_decision(
                decision, since=since, limit=limit, offset=offset
            )
            return web.json_response(_serialize_json(factors))
        except Exception as e:
            logger.exception("Error in GET /api/audit/decisions")
            return web.json_response({"error": str(e)}, status=500)

    async def list_execution_summaries(self, request):
        """GET /api/audit/summary?decision=HIGH&limit=50 — paginated dashboard view."""
        try:
            decision = request.query.get("decision")
            since_str = request.query.get("since")
            since = datetime.fromisoformat(since_str) if since_str else None
            bet_result = request.query.get("bet_result")
            limit = int(request.query.get("limit", "100"))
            offset = int(request.query.get("offset", "0"))
            summaries = self._summary_repo.list_summaries(
                decision=decision, since=since, bet_result=bet_result,
                limit=limit, offset=offset
            )
            return web.json_response(_serialize_json({
                "items": summaries,
                "next_cursor": None,
            }))
        except Exception as e:
            logger.exception("Error in GET /api/audit/summary")
            return web.json_response({"error": str(e)}, status=500)

    # ------------------------------------------------------------------
    # Scan Control
    # ------------------------------------------------------------------

    async def get_scan_status(self, request):
        """GET /api/scan/status — current scan enabled/disabled state."""
        try:
            if self._scan_controller:
                return web.json_response(self._scan_controller.status())
            return web.json_response({"enabled": False, "error": "No scan controller"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def toggle_scan(self, request):
        """POST /api/scan/toggle — toggle scan on/off."""
        try:
            if self._scan_controller:
                enabled = self._scan_controller.toggle()
                return web.json_response({"enabled": enabled})
            return web.json_response({"error": "No scan controller"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def enable_scan(self, request):
        """POST /api/scan/enable — enable scanning."""
        try:
            if self._scan_controller:
                self._scan_controller.enable()
                return web.json_response({"enabled": True})
            return web.json_response({"error": "No scan controller"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def disable_scan(self, request):
        """POST /api/scan/disable — disable scanning."""
        try:
            if self._scan_controller:
                self._scan_controller.disable()
                return web.json_response({"enabled": False})
            return web.json_response({"error": "No scan controller"}, status=500)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # ------------------------------------------------------------------
    # Static files
    # ------------------------------------------------------------------

    async def static_files(self, request):
        """Serve static files from frontend/dist/ with SPA fallback to index.html."""
        path = request.match_info.get("path", "")
        dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
        index_path = os.path.join(dist_dir, "index.html")

        loop = asyncio.get_event_loop()

        def _check_index():
            return os.path.exists(index_path)

        def _resolve_path():
            file_path = os.path.join(dist_dir, path)
            file_path_real = os.path.realpath(file_path)
            dist_dir_real = os.path.realpath(dist_dir)

            if not file_path_real.startswith(dist_dir_real):
                return index_path

            if os.path.exists(file_path_real) and os.path.isfile(file_path_real):
                return file_path_real

            return index_path

        try:
            has_index = await loop.run_in_executor(None, _check_index)
            if not has_index:
                return web.Response(
                    text="Frontend not built. Run npm run build in frontend/",
                    status=404,
                )

            target = await loop.run_in_executor(None, _resolve_path)
            return web.FileResponse(target)
        except Exception as e:
            logger.exception("Error serving static files")
            return web.Response(
                text=f"Error serving file: {e}", status=500
            )


def create_app(portfolio, scan_controller=None, event_bus=None):
    """Create and configure the aiohttp application."""
    handler = APIHandler(portfolio, scan_controller=scan_controller, event_bus=event_bus)
    app = web.Application(middlewares=[cors_middleware])

    # Existing routes
    app.router.add_get("/api/stats", handler.stats)
    app.router.add_get("/api/bets/open", handler.open_bets)
    app.router.add_get("/api/bets/resolved", handler.resolved_bets)
    app.router.add_get("/api/bets/timeseries", handler.timeseries)

    # Agent runtime routes
    app.router.add_get("/api/agents", handler.list_agents)
    app.router.add_post("/api/agents", handler.create_agent)
    app.router.add_get("/api/agents/{id}", handler.get_agent)
    app.router.add_put("/api/agents/{id}", handler.update_agent)
    app.router.add_delete("/api/agents/{id}", handler.delete_agent)

    app.router.add_get("/api/skills", handler.list_skills)
    app.router.add_post("/api/skills", handler.create_skill)
    app.router.add_get("/api/skills/{id}", handler.get_skill)
    app.router.add_put("/api/skills/{id}", handler.update_skill)
    app.router.add_delete("/api/skills/{id}", handler.delete_skill)

    app.router.add_get("/api/executions", handler.list_executions)
    app.router.add_get("/api/executions/live", handler.executions_live_ws)
    app.router.add_get("/api/executions/{id}/stream", handler.executions_stream_ws)
    app.router.add_get("/api/executions/{id}/steps", handler.get_execution_steps)
    app.router.add_get("/api/executions/{id}", handler.get_execution)

    # Audit trail routes
    app.router.add_get("/api/audit/market/{market_id}", handler.get_market_audit)
    app.router.add_get("/api/audit/decisions", handler.list_decisions)
    app.router.add_get("/api/audit/summary", handler.list_execution_summaries)

    # Scan control routes
    app.router.add_get("/api/scan/status", handler.get_scan_status)
    app.router.add_post("/api/scan/toggle", handler.toggle_scan)
    app.router.add_post("/api/scan/enable", handler.enable_scan)
    app.router.add_post("/api/scan/disable", handler.disable_scan)

    # Copy trading routes
    app.router.add_get("/api/copytrader/wallets", handler.list_wallets)
    app.router.add_post("/api/copytrader/wallets", handler.add_wallet)
    app.router.add_delete("/api/copytrader/wallets/{id}", handler.remove_wallet)
    app.router.add_post("/api/copytrader/scan", handler.trigger_copy_scan)
    app.router.add_get("/api/copytrader/pending", handler.list_pending_copy_trades)
    app.router.add_post("/api/copytrader/confirm/{id}", handler.confirm_copy_trade)
    app.router.add_post("/api/copytrader/reject/{id}", handler.reject_copy_trade)
    app.router.add_post("/api/copytrader/confirm-all", handler.confirm_all_copy_trades)

    # Agent metrics routes
    app.router.add_get("/api/agents/metrics", handler.list_agent_metrics)
    app.router.add_get("/api/agents/metrics/{agent_name}", handler.get_agent_metrics)

    # Static files (SPA fallback — must be last)
    app.router.add_get("/{path:.*}", handler.static_files)
    return app


def start_api_server(portfolio, port=8080, scan_controller=None, event_bus=None):
    """Start the aiohttp server in a background daemon thread."""
    global _api_runner, _api_site
    app = create_app(portfolio, scan_controller=scan_controller, event_bus=event_bus)
    started_event = threading.Event()
    startup_error = []

    async def start_runner():
        global _api_runner, _api_site
        runner = web.AppRunner(app)
        await runner.setup()
        _api_runner = runner
        site = web.TCPSite(runner, "0.0.0.0", port)
        _api_site = site
        try:
            await site.start()
            logger.info(f"API server started on http://localhost:{port}")
            started_event.set()
        except OSError as e:
            startup_error.append(e)
            logger.error(f"Failed to start API server on port {port}: {e}")
            started_event.set()

    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_runner())
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    logger.info(f"API server starting on port {port}...")

    # Wait briefly for startup result
    started_event.wait(timeout=5.0)
    if startup_error:
        raise startup_error[0]


def stop_api_server():
    """Gracefully stop the aiohttp server."""
    global _api_runner
    if _api_runner is not None:
        logger.info("Shutting down API server...")
        asyncio.run(_api_runner.cleanup())
        _api_runner = None
        logger.info("API server stopped.")
