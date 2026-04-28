"""Agent registry — DB-backed agent selection and lifecycle management."""
import logging
from typing import Any
from uuid import UUID

from agents.classifier import MarketClassifier
from db.agent_repository import AgentRepository
from db.agent_skill_repository import AgentSkillRepository

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for agents backed by the database."""

    def __init__(
        self,
        agent_repository: AgentRepository | None = None,
        skill_repository: AgentSkillRepository | None = None,
    ):
        self._repo = agent_repository or AgentRepository()
        self._skill_repo = skill_repository or AgentSkillRepository()
        self._classifier = MarketClassifier()

    def select_agents_for_market(self, question: str) -> list[dict[str, Any]]:
        """Select agent(s) for a market based on classification rules.

        Selection logic:
        1. Classify the market question into categories
        2. Find active agents whose name/description matches those categories
        3. If no match, return the default agent (if any)
        4. If multiple agents match, return all (ensemble mode)
        """
        categories = self._classifier.classify(question)
        all_agents = self._repo.list_agents(active_only=True)

        if not all_agents:
            logger.warning("No active agents in registry")
            return []

        matched = []
        question_lower = question.lower()

        for agent in all_agents:
            name = (agent.get("name") or "").lower()
            description = (agent.get("description") or "").lower()

            # Check if agent matches any category
            for category in categories:
                if category in name or category in description:
                    matched.append(agent)
                    break
            else:
                # Also check if any keyword from the question appears in agent metadata
                agent_text = f"{name} {description}"
                for word in question_lower.split():
                    if len(word) > 3 and word in agent_text:
                        matched.append(agent)
                        break

        if matched:
            logger.info(f"Selected {len(matched)} agent(s) for market: {[a['name'] for a in matched]}")
            return matched

        # Fallback: return a "default" agent if one exists
        default_agents = [a for a in all_agents if "default" in (a.get("name") or "").lower()]
        if default_agents:
            logger.info(f"Using default agent: {default_agents[0]['name']}")
            return [default_agents[0]]

        # Ultimate fallback: return the first active agent
        logger.info(f"Using first available agent: {all_agents[0]['name']}")
        return [all_agents[0]]

    def get_agent_with_skills(self, agent_id: UUID) -> dict[str, Any] | None:
        """Get an agent with its linked skills loaded."""
        agent = self._repo.get_agent_by_id(agent_id)
        if not agent:
            return None
        skills = self._skill_repo.get_skills_for_agent(agent_id)
        agent["skills"] = skills
        return agent

    def list_active_agents(self) -> list[dict[str, Any]]:
        """Return all active, non-archived agents."""
        return self._repo.list_agents(active_only=True)
