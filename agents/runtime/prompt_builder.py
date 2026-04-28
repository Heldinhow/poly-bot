"""Prompt builder for agent tasks."""
from typing import Any

from agents.runtime.models import Task


def build_task_prompt(task: Task, agent_config: dict[str, Any]) -> str:
    """Build the initial prompt for an agent task.

    Args:
        task: The task containing market data.
        agent_config: Agent configuration from the database.

    Returns:
        A formatted prompt string for the agent.
    """
    skills = agent_config.get("skills", [])
    skill_names = [s.get("name", "") for s in skills if isinstance(s, dict)]

    skills_section = ""
    if skill_names:
        skills_section = """
## Available Skills
You have access to the following skills in the `.skills/` directory:
"""
        for name in skill_names:
            skills_section += f"- {name}\n"
        skills_section += """
Read the relevant skills in `.skills/` before proceeding.
"""

    prompt = f"""You are running as an analysis agent for a Polymarket betting bot.

Your task is to evaluate this prediction market and estimate the true probability of the outcome.

## Market
Question: {task.question}
Yes price: {task.yes_price:.2%}
No price: {task.no_price:.2%}
Volume 24h: ${task.volume_24h:,.0f}
Resolution date: {task.resolution_date or "Not specified"}

## Instructions
1. First, RESEARCH the topic using available tools (web search, APIs, bash)
2. Gather real-time data relevant to this market
3. Calculate the TRUE probability of the outcome
4. Respond with a single JSON object as your final answer:

```json
{{
  "probability": 0.XX,
  "confidence": 0.XX,
  "reasoning": "...",
  "sources": ["..."]
}}
```

- `probability`: your estimated true probability (0.0 to 1.0)
- `confidence`: how confident you are in this estimate (0.0 to 1.0)
- `reasoning`: concise explanation of your analysis
- `sources`: list of sources you used
{skills_section}
## Important Rules
- Always research with tools before calculating probability
- Cite your sources
- Respond ONLY with the JSON object — no extra text before or after
- If you cannot determine the probability, set probability to null and explain why
"""
    return prompt
