"""Agent runner — orchestrates the full task execution pipeline."""
import asyncio
import logging
import time
import uuid
from typing import Any

from agents.circuit_breaker import CircuitBreakerRegistry
from agents.registry import AgentRegistry
from agents.runtime.execenv import ExecutionEnvironment
from agents.runtime.manager import RuntimeManager
from agents.runtime.models import ExecOptions, Result, Task
from agents.runtime.prompt_builder import build_task_prompt
from agents.runtime.registry import BackendRegistry
from agents.runtime.claude_backend import ClaudeBackend
from agents.runtime.opencode_backend import OpencodeBackend
from agents.tracker import ExecutionTracker
from db.agent_repository import AgentRepository
from db.agent_skill_repository import AgentSkillRepository
from db.execution_repository import ExecutionRepository

logger = logging.getLogger(__name__)


class AgentRunner:
    """Orchestrates task execution: select agent → prepare → execute → track → result."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        runtime_manager: RuntimeManager | None = None,
        tracker: ExecutionTracker | None = None,
        exec_env: ExecutionEnvironment | None = None,
        circuit_breakers: CircuitBreakerRegistry | None = None,
    ):
        self._registry = registry or AgentRegistry()
        self._runtime = runtime_manager or RuntimeManager()
        self._tracker = tracker or ExecutionTracker()
        self._exec_env = exec_env or ExecutionEnvironment()
        self._circuit_breakers = circuit_breakers or CircuitBreakerRegistry()

        # Register default backends
        self._runtime.registry.register("claude", ClaudeBackend)
        self._runtime.registry.register("opencode", OpencodeBackend)

    async def analyze_market(
        self,
        market_id: str,
        question: str,
        yes_price: float,
        no_price: float,
        volume_24h: float,
        resolution_date: str | None = None,
    ) -> Result | None:
        """Analyze a single market using the agent runtime.

        Returns the agent's Result, or None if no agent/runtime available.
        """
        start_time = time.time()

        # 1. Select agent(s)
        agents = self._registry.select_agents_for_market(question)
        if not agents:
            logger.warning(f"No agent available for market: {question[:60]}")
            return None

        # For MVP, use the first matched agent (no ensemble yet)
        agent = agents[0]
        agent_id = agent["id"]
        agent_name = agent.get("name", "unknown")
        agent_runtime = agent["runtime"]
        agent_config = self._registry.get_agent_with_skills(agent_id)
        if not agent_config:
            logger.warning(f"Could not load agent config for {agent_id}")
            return None

        # Log agent selection
        logger.info(
            f"[AgentRunner] Selected agent: {agent_name} (runtime={agent_runtime}, "
            f"model={agent_config.get('model', 'default')})"
        )

        # 2. Check circuit breaker
        if not self._circuit_breakers.can_execute(agent_runtime):
            logger.warning(f"Circuit breaker open for runtime: {agent_runtime}")
            return None

        # 3. Create execution log
        task_id = str(uuid.uuid4())
        log_id = self._tracker._repo.create_log(
            task_id=task_id,
            market_id=market_id,
            agent_id=agent_id,
            runtime=agent_runtime,
            model=agent_config.get("model"),
        )

        # 4. Claim the log
        if not self._tracker.claim(log_id, agent_runtime):
            logger.warning(f"Could not claim execution log {log_id}")
            return None

        # 5. Start the log
        self._tracker.start(log_id)

        # 6. Prepare execution environment
        try:
            skills = agent_config.get("skills", [])
            workdir = self._exec_env.prepare(
                workspace_id=task_id[:8],
                task_id=task_id,
                agent_config=agent_config,
                skills=skills,
            )
        except Exception as e:
            logger.error(f"Failed to prepare workdir: {e}")
            self._tracker.finalize(
                log_id,
                Result(error_message=f"Workdir preparation failed: {e}"),
            )
            self._circuit_breakers.record_failure(agent_runtime)
            return None

        # 7. Build prompt
        task = Task(
            task_id=task_id,
            market_id=market_id,
            question=question,
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=volume_24h,
            resolution_date=resolution_date,
            agent_id=str(agent_id),
            agent_config=agent_config,
        )
        prompt = build_task_prompt(task, agent_config)

        # Log prompt preview
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        logger.info(f"[AgentRunner] Prompt ({len(prompt)} chars): {prompt_preview}")

        # 8. Execute via runtime manager
        opts = ExecOptions(
            cwd=workdir,
            model=agent_config.get("model", ""),
            system_prompt=agent_config.get("system_prompt", ""),
            timeout=__import__("datetime").timedelta(minutes=5),  # Reduced from 20
            max_retries=agent_config.get("max_retries", 1),
            custom_args=agent_config.get("custom_args", []),
            custom_env=agent_config.get("custom_env", {}),
        )

        try:
            result = await self._runtime.execute_task(
                task=task,
                prompt=prompt,
                opts=opts,
                agent_runtime=agent_runtime,
            )

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Enrich result with metadata
            result.agent_name = agent_name
            result.runtime = agent_runtime
            result.duration_ms = duration_ms
            result.prompt_used = prompt

            # Log result
            if result.probability is not None:
                logger.info(
                    f"[AgentRunner] Result: agent={agent_name} "
                    f"prob={result.probability:.2%} conf={result.confidence:.2%} "
                    f"tokens={result.input_tokens}+{result.output_tokens} "
                    f"duration={duration_ms}ms"
                )
            else:
                logger.warning(
                    f"[AgentRunner] No result: agent={agent_name} "
                    f"error={result.error_message} duration={duration_ms}ms"
                )

            # 9. Finalize
            self._tracker.finalize(log_id, result)

            # 10. Record circuit breaker
            if result.error_message:
                self._circuit_breakers.record_failure(agent_runtime)
            else:
                self._circuit_breakers.record_success(agent_runtime)

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[AgentRunner] Exception: agent={agent_name} error={e} duration={duration_ms}ms")
            error_result = Result(
                error_message=str(e),
                agent_name=agent_name,
                runtime=agent_runtime,
                duration_ms=duration_ms,
                prompt_used=prompt,
            )
            self._tracker.finalize(log_id, error_result)
            self._circuit_breakers.record_failure(agent_runtime)
            return error_result
