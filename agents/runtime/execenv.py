"""Execution environment — prepares isolated workdirs for agent tasks."""
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_WORKSPACE_ROOT = Path.home() / "polybot_workspaces"


class ExecutionEnvironment:
    """Prepares isolated workdirs with context files and skills."""

    def __init__(self, workspace_root: str | Path | None = None):
        self._root = Path(workspace_root or DEFAULT_WORKSPACE_ROOT)

    def prepare(
        self,
        workspace_id: str,
        task_id: str,
        agent_config: dict[str, Any],
        skills: list[dict[str, Any]] | None = None,
    ) -> str:
        """Create an isolated workdir and return the workdir path.

        Structure:
            {workspace_root}/{workspace_id}/{task_id}/
                workdir/           # cwd for the agent
                    AGENTS.md      # instructions
                    SOUL.md        # persona/voice
                    COMMANDS.md    # custom commands
                    .skills/       # injected skills
                output/            # artifacts
                logs/              # execution logs
        """
        base_dir = self._root / workspace_id / task_id
        workdir = base_dir / "workdir"
        output_dir = base_dir / "output"
        logs_dir = base_dir / "logs"
        skills_dir = workdir / ".skills"

        # Create directories
        for d in (workdir, output_dir, logs_dir, skills_dir):
            d.mkdir(parents=True, exist_ok=True)

        # Write context files
        self._write_agents_md(workdir, agent_config)
        self._write_soul_md(workdir, agent_config)
        self._write_commands_md(workdir, agent_config)

        # Write skills
        if skills:
            for skill in skills:
                self._write_skill(skills_dir, skill)

        logger.info(f"Workdir prepared: {workdir}")
        return str(workdir)

    def _write_agents_md(self, workdir: Path, agent_config: dict[str, Any]) -> None:
        """Generate AGENTS.md from agent config."""
        content = agent_config.get("system_prompt", "")
        if not content:
            content = f"""# Agent: {agent_config.get('name', 'Unknown')}

## Role
{agent_config.get('description', 'AI analysis agent for Polymarket betting bot.')}

## Runtime
{agent_config.get('runtime', 'unknown')} ({agent_config.get('model', 'default')})

## Instructions
1. Research the market using available tools before calculating probability.
2. Cite your sources.
3. Respond in the required JSON format.
"""
        (workdir / "AGENTS.md").write_text(content, encoding="utf-8")

    def _write_soul_md(self, workdir: Path, agent_config: dict[str, Any]) -> None:
        """Generate SOUL.md with persona/voice."""
        content = f"""# Persona: {agent_config.get('name', 'Agent')}

You are a precise, data-driven analyst. You value evidence over intuition.
You communicate clearly and concisely.
"""
        (workdir / "SOUL.md").write_text(content, encoding="utf-8")

    def _write_commands_md(self, workdir: Path, agent_config: dict[str, Any]) -> None:
        """Generate COMMANDS.md with custom commands."""
        custom_args = agent_config.get("custom_args", [])
        if not custom_args:
            content = "# Custom Commands\n\nNo custom commands defined.\n"
        else:
            content = "# Custom Commands\n\n" + "\n".join(f"- `{arg}`" for arg in custom_args) + "\n"
        (workdir / "COMMANDS.md").write_text(content, encoding="utf-8")

    def _write_skill(self, skills_dir: Path, skill: dict[str, Any]) -> None:
        """Write a skill as a markdown file in .skills/."""
        name = skill.get("name", "unnamed")
        content = skill.get("content", "")
        filename = f"{name}.md"
        (skills_dir / filename).write_text(content, encoding="utf-8")
        logger.debug(f"Skill written: {filename}")

    def cleanup_old_workspaces(self, max_age_days: int = 7) -> int:
        """Remove workspaces older than max_age_days. Returns count removed."""
        if not self._root.exists():
            return 0

        import time

        removed = 0
        cutoff = time.time() - (max_age_days * 86400)

        for ws_dir in self._root.iterdir():
            if not ws_dir.is_dir():
                continue
            try:
                mtime = ws_dir.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(ws_dir)
                    removed += 1
                    logger.info(f"Cleaned old workspace: {ws_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace {ws_dir}: {e}")

        return removed
