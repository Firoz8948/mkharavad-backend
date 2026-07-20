from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "M Kharavad Company"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"

    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/mkharavad"
    )

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 4
    OTP_DEBUG: bool = True

    RENFLAIR_API_KEY: str = ""

    EMAILJS_SERVICE_ID: str = ""
    EMAILJS_TEMPLATE_ID: str = ""
    EMAILJS_PUBLIC_KEY: str = ""

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    ADMIN_EMAIL: str = "admin@mkharavad.com"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    SHIPROCKET_EMAIL: str = ""
    SHIPROCKET_PASSWORD: str = ""
    SHIPROCKET_BASE_URL: str = "https://apiv2.shiprocket.in/v1/external"
    # Pickup nickname exactly as shown in Shiprocket → Settings → Pickup Addresses
    SHIPROCKET_PICKUP_LOCATION: str = "Primary"
    SHIPROCKET_CHANNEL_ID: str = ""
    SHIPROCKET_COURIER_ID: str = ""
    # Auto-create Shiprocket order when a store order is placed
    SHIPROCKET_AUTO_PUSH: bool = True
    # After create, try to assign AWB automatically (requires active courier wallet)
    SHIPROCKET_AUTO_AWB: bool = False
    SHIPROCKET_DEFAULT_LENGTH: float = 10
    SHIPROCKET_DEFAULT_BREADTH: float = 10
    SHIPROCKET_DEFAULT_HEIGHT: float = 10

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        origins = {
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        }
        return [origin for origin in origins if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
