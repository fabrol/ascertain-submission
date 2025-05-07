from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
if os.path.exists(".env"):
    load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str

    # Application
    ENVIRONMENT: str
    DEBUG: bool

    # API
    API_V1_STR: str
    PROJECT_NAME: str

    # OpenAI
    OPENAI_API_KEY: str

    def is_test_environment(self) -> bool:
        """Check if we're in the test environment."""
        return self.ENVIRONMENT.lower() == "test"

    def is_openai_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.OPENAI_API_KEY)


# Create a single instance of settings
settings = Settings()
