import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from aiohttp import web

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
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


class APIHandler:
    """HTTP request handlers for the dashboard API."""

    def __init__(self, portfolio):
        self.portfolio = portfolio
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

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
        """GET /api/bets/timeseries?days=30 — daily bankroll over time."""
        try:
            days = int(request.query.get("days", "30"))
        except ValueError:
            days = 30

        try:
            open_bets = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_open_bets
            )
            resolved_bets = await asyncio.get_event_loop().run_in_executor(
                None, self._safe_resolved_bets
            )
        except Exception as e:
            logger.exception("Error fetching bets for timeseries")
            return web.json_response(
                {"error": "Failed to fetch bets", "detail": str(e)}, status=500
            )

        all_bets = open_bets + resolved_bets

        if not all_bets:
            return web.json_response([])

        # Build a chronological event log: (date_str, delta)
        events = {}  # date_str -> delta

        for bet in all_bets:
            place_date = bet.timestamp[:10] if bet.timestamp else None
            if place_date:
                events.setdefault(place_date, 0.0)
                events[place_date] -= bet.stake

            if bet.resolved and bet.resolved_at:
                resolve_date = bet.resolved_at[:10]
                if bet.result == "win":
                    events.setdefault(resolve_date, 0.0)
                    events[resolve_date] += bet.payout
                # losses: stake already subtracted on place_date, no further change

        # Sort unique dates
        sorted_dates = sorted(events.keys())
        if not sorted_dates:
            return web.json_response([])

        # Generate result for requested window
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Also include historical dates before window so we can carry forward bankroll
        all_event_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in sorted_dates]
        first_event_date = min(all_event_dates)

        current_date = min(first_event_date, start_date)
        bankroll = self.portfolio.initial_bankroll
        result = []

        while current_date <= end_date:
            date_str = current_date.isoformat()
            if date_str in events:
                bankroll += events[date_str]

            if current_date >= start_date:
                result.append({"date": date_str, "bankroll": round(bankroll, 2)})

            current_date += timedelta(days=1)

        return web.json_response(result)

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


def create_app(portfolio):
    """Create and configure the aiohttp application."""
    handler = APIHandler(portfolio)
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/stats", handler.stats)
    app.router.add_get("/api/bets/open", handler.open_bets)
    app.router.add_get("/api/bets/resolved", handler.resolved_bets)
    app.router.add_get("/api/bets/timeseries", handler.timeseries)
    app.router.add_get("/{path:.*}", handler.static_files)
    return app


def start_api_server(portfolio, port=8080):
    """Start the aiohttp server in a background daemon thread."""
    global _api_runner, _api_site
    app = create_app(portfolio)
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
