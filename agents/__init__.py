"""Agent initialization module."""
from .base import BaseAgent
from .sports_analyst import SportsAnalyst
from .esports_analyst import EsportsAnalyst
from .odds_analyst import OddsAnalyst

__all__ = ["BaseAgent", "SportsAnalyst", "EsportsAnalyst", "OddsAnalyst"]


def create_default_agents() -> list[BaseAgent]:
    """Create the default set of analysis agents."""
    return [
        SportsAnalyst(),
        EsportsAnalyst(),
        OddsAnalyst(),
    ]
