import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Scan settings
    scan_interval_secs: int = 300
    min_volume: float = 10000.0
    max_price: float = 0.35
    max_odds: float = 20.0

    # Trading
    paper_mode: bool = True  # Deprecated: use trading_mode
    trading_mode: str = "paper"
    initial_bankroll: float = 50.0
    kelly_frac: float = 0.25
    min_edge: float = 0.05

    # Database
    database_url: str

    # API Server
    api_port: int = 8080

    # MiniMax API
    minimax_api_key: str
    minimax_base_url: str = "https://api.minimax.chat/v1"

    # Polymarket
    polymarket_api_url: str = "https://gamma-api.polymarket.com"

    # Thresholds
    high_confidence_threshold: float = 0.60
    low_confidence_threshold: float = 0.40

    # Agent Runtime
    workspace_root: str = "~/polybot_workspaces"
    agent_timeout_secs: int = 1200  # 20 minutes
    agent_max_retries: int = 1

    # Scan
    scan_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate(self) -> None:
        """Validate required settings."""
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if not self.minimax_api_key:
            missing.append("MINIMAX_API_KEY")
        if not self.database_url:
            missing.append("DATABASE_URL")

        # Normalize trading_mode
        mode = self.trading_mode.lower().strip()
        if mode not in ("paper", "live"):
            import logging
            logging.getLogger(__name__).warning(
                f"Invalid TRADING_MODE '{self.trading_mode}', defaulting to 'paper'"
            )
            self.trading_mode = "paper"
        else:
            self.trading_mode = mode

        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings
