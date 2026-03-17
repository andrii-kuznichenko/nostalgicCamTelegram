from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    ai_api_key: str = Field(alias="AI_API_KEY")
    ai_api_url: str = Field(default="https://queue.fal.run", alias="AI_API_URL")
    ai_model_name: str = Field(default="fal-ai/flux-2/klein/9b/edit", alias="AI_MODEL_NAME")
    payment_provider: str = Field(default="telegram_stars", alias="PAYMENT_PROVIDER")
    payment_provider_token: str = Field(default="", alias="PAYMENT_PROVIDER_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", alias="DATABASE_URL")
    temp_dir: Path = Field(default=Path("./temp"), alias="TEMP_DIR")
    free_credits_on_start: int = Field(default=5, alias="FREE_CREDITS_ON_START")
    package_price_usd: int = Field(default=7, alias="PACKAGE_PRICE_USD")
    package_price_stars: int = Field(default=350, alias="PACKAGE_PRICE_STARS")
    package_credits: int = Field(default=50, alias="PACKAGE_CREDITS")
    max_photo_size_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_PHOTO_SIZE_BYTES")
    max_concurrent_generations_per_user: int = Field(default=1, alias="MAX_CONCURRENT_GENERATIONS_PER_USER")
    max_concurrent_generations_global: int = Field(default=2, alias="MAX_CONCURRENT_GENERATIONS_GLOBAL")
    flood_window_seconds: int = Field(default=2, alias="FLOOD_WINDOW_SECONDS")
    temp_file_ttl_hours: int = Field(default=24, alias="TEMP_FILE_TTL_HOURS")
    use_mock_ai_provider: bool = Field(default=True, alias="USE_MOCK_AI_PROVIDER")
    prompt_preview_mode: bool = Field(default=True, alias="PROMPT_PREVIEW_MODE")
    fal_poll_interval_seconds: float = Field(default=1.5, alias="FAL_POLL_INTERVAL_SECONDS")
    fal_timeout_seconds: int = Field(default=180, alias="FAL_TIMEOUT_SECONDS")


VINTAGE_FLASH_PROMPT = (
    "Transform the uploaded photo into a photorealistic vintage flash image while keeping the exact same "
    "person, identity, pose, clothing, hairstyle, framing, and scene composition. Apply a harsh direct-flash "
    "look as if the photo was taken on a compact digital camera or disposable camera in low light or at night. "
    "Create bright frontal flash lighting, slightly overexposed highlights on the skin, natural flash shadows, "
    "a darker ambient background, subtle film grain, a touch of digital sensor noise, soft glow, and an authentic "
    "early-2000s nostalgic camera aesthetic. Preserve realistic skin, hands, fabric texture, and proportions. "
    "Do not change the person, face, clothes, body shape, facial expression, or composition. The final result "
    "must look like a real live flash photograph with a vintage aesthetic, not like an obviously AI-generated image."
)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    Path("./data").mkdir(parents=True, exist_ok=True)
    return settings
