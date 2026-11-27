from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASTRA_", env_file=".env", extra="ignore")

    env: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = f"sqlite:///{BASE_DIR / 'astra.db'}"
    ephemeris_dir: str = str(BASE_DIR / "data" / "ephemeris")
    ephemeris_file: str = "de440s.bsp"
    geocoder_provider: str = "nominatim"
    geocoder_api_key: str = ""
    geocoder_user_agent: str = "astra-os-dev/1.0"
    frontend_origin: str = "http://localhost:8000"
    access_token_minutes: int = 10080
    free_chart_limit: int = 3

    stripe_secret_key: str = Field(default="", validation_alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", validation_alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id_pro_monthly: str = Field(default="", validation_alias="STRIPE_PRICE_ID_PRO_MONTHLY")
    stripe_success_url: str = Field(default="http://localhost:8000/?billing=success", validation_alias="STRIPE_SUCCESS_URL")
    stripe_cancel_url: str = Field(default="http://localhost:8000/?billing=cancelled", validation_alias="STRIPE_CANCEL_URL")

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


settings = Settings()
