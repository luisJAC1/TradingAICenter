"""TradingAICenter — Brain configuration (loaded from environment variables)."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8791, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")

    # Claw-Empire UI (for bridge notifications)
    ui_url: str = Field(default="http://claw-empire:8790", alias="UI_URL")
    ui_api_token: str = Field(default="", alias="API_AUTH_TOKEN")

    # Redis (Knowledge Bus)
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # ChromaDB (semantic memory)
    chroma_host: str = Field(default="chromadb", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")

    # LLM
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    # analysis_model: fast + cheap — structured JSON, news tagging, pattern desc ($0.80/$4 per 1M)
    analysis_model: str = Field(
        default="claude-haiku-4-5-20251001", alias="ANALYSIS_MODEL"
    )
    # reasoning_model: deep synthesis — Bull/Bear debates, Architect, Boss ($3/$15 per 1M)
    reasoning_model: str = Field(
        default="claude-sonnet-4-6", alias="REASONING_MODEL"
    )
    # default_model: fallback (maps to reasoning)
    default_model: str = Field(
        default="claude-sonnet-4-6", alias="DEFAULT_MODEL"
    )

    # Trading / Paper mode
    live_trading: bool = Field(default=False, alias="LIVE_TRADING")
    alpaca_api_key: str = Field(default="", alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")

    # Risk profile — drives all risk math across Architect, Shield, Boss
    # CONSERVATIVE: 0.5%/trade, 3% heat, max 3 plans
    # BALANCED:     1.0%/trade, 5% heat, max 5 plans  (default)
    # AGGRESSIVE:   2.0%/trade, 6% heat, max 5 plans
    # CUSTOM:       use the three fields below directly
    risk_profile: str = Field(default="BALANCED", alias="RISK_PROFILE")
    risk_pct_per_trade: float = Field(default=1.0, alias="RISK_PCT_PER_TRADE")
    max_portfolio_heat: float = Field(default=5.0, alias="MAX_PORTFOLIO_HEAT")
    max_simultaneous_plans: int = Field(default=5, alias="MAX_SIMULTANEOUS_PLANS")

    # Notifications — UI is always on; WhatsApp is opt-in
    # Options: "ui" | "whatsapp" | "both"
    notification_channel: str = Field(default="ui", alias="NOTIFICATION_CHANNEL")
    openclaw_url: str = Field(default="http://openclaw:18789", alias="OPENCLAW_URL")
    whatsapp_phone: str = Field(default="", alias="WHATSAPP_PHONE")  # e.g. "+15551234567"

    # Ollama (local LLM for high-frequency/cheap tasks — optional)
    ollama_url: str = Field(default="", alias="OLLAMA_URL")   # e.g. "http://localhost:11434"
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")

    # Budget (Tokin watchdog)
    monthly_llm_budget_usd: float = Field(
        default=30.0, alias="MONTHLY_LLM_BUDGET_USD"
    )
    alert_threshold_pct: float = Field(
        default=80.0, alias="ALERT_THRESHOLD_PCT"
    )

    model_config = {"env_file": ".env", "populate_by_name": True}

    def apply_risk_profile(self) -> None:
        """Override risk fields based on RISK_PROFILE (called at startup)."""
        profiles = {
            "CONSERVATIVE": (0.5, 3.0, 3),
            "BALANCED":     (1.0, 5.0, 5),
            "AGGRESSIVE":   (2.0, 6.0, 5),
        }
        if self.risk_profile.upper() in profiles:
            rpt, heat, plans = profiles[self.risk_profile.upper()]
            # Only override if user hasn't set custom values via env
            object.__setattr__(self, "risk_pct_per_trade", rpt)
            object.__setattr__(self, "max_portfolio_heat", heat)
            object.__setattr__(self, "max_simultaneous_plans", plans)


settings = Settings()
