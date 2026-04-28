"""Runtime Manager — auto-detects installed agent CLIs and orchestrates execution."""
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from agents.runtime.models import AgentBackend, ExecutionContext, ExecOptions, Result, Session, Task
from agents.runtime.registry import BackendRegistry

logger = logging.getLogger(__name__)

_CACHE_PATH = Path.home() / ".polybot" / "runtimes.json"


class RuntimeManager:
    """Singleton that manages agent runtimes: detect, select, execute."""

    # Map: runtime name -> CLI command name
    RUNTIME_COMMANDS = {
        "claude": "claude",
        "codex": "codex",
        "openclaw": "openclaw",
        "opencode": "opencode",
        "hermes": "hermes",
        "gemini": "gemini",
        "pi": "pi",
        "cursor-agent": "cursor-agent",
        "kimi": "kimi",
        "kiro-cli": "kiro-cli",
    }

    # Env var pattern: MULTICA_{RUNTIME}_PATH
    def __init__(self):
        self._registry = BackendRegistry()
        self._installed: list[str] | None = None

    @property
    def registry(self) -> BackendRegistry:
        return self._registry

    def _get_cli_path(self, runtime: str) -> str | None:
        """Return CLI path for a runtime, checking env overrides first."""
        env_var = f"MULTICA_{runtime.upper().replace('-', '_')}_PATH"
        custom_path = os.environ.get(env_var)
        if custom_path and shutil.which(custom_path):
            return custom_path
        cmd = self.RUNTIME_COMMANDS.get(runtime, runtime)
        return shutil.which(cmd)

    def detect_installed_runtimes(self, use_cache: bool = True) -> list[str]:
        """Detect which agent CLIs are available on PATH. Cached in ~/.polybot/runtimes.json"""
        if self._installed is not None:
            return self._installed

        if use_cache and _CACHE_PATH.exists():
            try:
                with open(_CACHE_PATH, "r") as f:
                    cached = json.load(f)
                if isinstance(cached, list):
                    self._installed = cached
                    logger.info(f"Runtimes loaded from cache: {cached}")
                    return cached
            except Exception:
                pass

        installed = []
        for runtime in self.RUNTIME_COMMANDS:
            if self._get_cli_path(runtime):
                installed.append(runtime)

        self._installed = installed
        self._save_cache(installed)
        logger.info(f"Runtimes auto-detected: {installed}")
        return installed

    def _save_cache(self, runtimes: list[str]) -> None:
        try:
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_CACHE_PATH, "w") as f:
                json.dump(runtimes, f)
        except Exception as e:
            logger.warning(f"Failed to save runtime cache: {e}")

    def invalidate_cache(self) -> None:
        """Force re-detection on next call."""
        self._installed = None
        if _CACHE_PATH.exists():
            _CACHE_PATH.unlink()
        logger.info("Runtime cache invalidated")

    def get_backend_for_runtime(self, runtime: str) -> AgentBackend | None:
        """Get a backend instance for a runtime, if available."""
        installed = self.detect_installed_runtimes()
        if runtime not in installed:
            logger.warning(f"Runtime '{runtime}' not installed")
            return None
        return self._registry.get(runtime)

    def select_runtime_for_agent(self, agent_runtime: str, fallback_order: list[str] | None = None) -> str | None:
        """Select the best available runtime for an agent."""
        installed = self.detect_installed_runtimes()

        candidates = [agent_runtime]
        if fallback_order:
            candidates.extend(fallback_order)
        else:
            # Default fallback: all installed runtimes except the preferred
            candidates.extend(r for r in installed if r != agent_runtime)

        for runtime in candidates:
            if runtime in installed:
                return runtime

        logger.error(f"No runtime available for agent (preferred: {agent_runtime})")
        return None

    async def execute_task(
        self,
        task: Task,
        prompt: str,
        opts: ExecOptions,
        agent_runtime: str,
        fallback_order: list[str] | None = None,
    ) -> Result:
        """Execute a task through the runtime manager with fallback."""
        runtime = self.select_runtime_for_agent(agent_runtime, fallback_order)
        if not runtime:
            return Result(
                error_message=f"No runtime available for agent (preferred: {agent_runtime})",
            )

        backend = self.get_backend_for_runtime(runtime)
        if not backend:
            return Result(
                error_message=f"Backend not registered for runtime: {runtime}",
            )

        ctx = ExecutionContext(
            task_id=task.task_id,
            market_id=task.market_id,
            agent_id=task.agent_id,
            workspace_id=task.task_id,
        )

        session = await backend.execute(ctx, prompt, opts)
        # Wait for the result future
        try:
            result = await session.result
            return result
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return Result(error_message=str(e))
