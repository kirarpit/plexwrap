import yaml
import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta, date
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    tautulli_url: str
    tautulli_api_key: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    openai_api_key: Optional[str] = None
    use_llm: bool = True  # Enable/disable LLM features
    openai_base_url: Optional[str] = None  # Base URL for OpenAI-compatible APIs
    openai_model: Optional[str] = None  # Model name (defaults to "gpt-5-mini")
    google_image_api_key: Optional[str] = None
    use_image_generation: bool = False  # Enable/disable image generation
    name_mappings: Dict[str, str] = {}  # Username to display name mappings
    custom_prompt_context: Optional[str] = None  # Custom context for AI prompts
    excluded_users: list = []  # Users to exclude from wrap generation
    timezone: Optional[str] = (
        None  # Timezone for watch time analysis (e.g., "Australia/Sydney", "America/New_York")
    )
    southern_hemisphere: bool = (
        False  # Set to True for Southern Hemisphere season mapping
    )
    cross_user_comparison: bool = True  # Enable/disable cross-user comparison stats

    class Config:
        env_file = ".env"
        case_sensitive = False


def load_config():
    """Load configuration from config.yaml or environment variables"""
    config_path = Path("config.yaml")

    # Helper to convert date objects to strings
    def date_to_string(d):
        if d is None:
            return None
        if isinstance(d, date):
            return d.strftime("%Y-%m-%d")
        if isinstance(d, datetime):
            return d.strftime("%Y-%m-%d")
        return str(d) if d else None

    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        time_range = config.get("time_range", {})
        start_date = date_to_string(time_range.get("start_date"))
        end_date = date_to_string(time_range.get("end_date"))

        settings = Settings(
            tautulli_url=config.get("tautulli", {}).get(
                "url", os.getenv("TAUTULLI_URL", "")
            ),
            tautulli_api_key=config.get("tautulli", {}).get(
                "api_key", os.getenv("TAUTULLI_API_KEY", "")
            ),
            openai_api_key=config.get("openai", {}).get(
                "api_key", os.getenv("OPENAI_API_KEY", "")
            ),
            use_llm=config.get("openai", {}).get("enabled", True),
            openai_base_url=config.get("openai", {}).get(
                "base_url", os.getenv("OPENAI_BASE_URL")
            ),
            openai_model=config.get("openai", {}).get(
                "model", os.getenv("OPENAI_MODEL")
            ),
            google_image_api_key=config.get("image_generation", {}).get(
                "api_key", os.getenv("GOOGLE_IMAGE_API_KEY", "")
            ),
            use_image_generation=config.get("image_generation", {}).get(
                "enabled", False
            ),
            start_date=start_date,
            end_date=end_date,
            name_mappings=config.get("name_mappings", {}),
            custom_prompt_context=config.get("custom_prompt_context"),
            excluded_users=config.get("excluded_users", []),
            timezone=config.get("timezone", os.getenv("TIMEZONE")),
            southern_hemisphere=config.get("southern_hemisphere", False),
            cross_user_comparison=config.get("cross_user_comparison", True),
        )
    else:
        settings = Settings()

    # Default to last year if not specified
    if not settings.start_date:
        settings.start_date = (datetime.now() - timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )
    if not settings.end_date:
        settings.end_date = datetime.now().strftime("%Y-%m-%d")

    return settings
