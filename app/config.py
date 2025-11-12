"""
Configuration and settings for the Web Crawling Agent
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    # LiteLLM Proxy Settings
    LITELLM_PROXY_BASE_URL: str = os.getenv("LITELLM_PROXY_BASE_URL", "")
    LITELLM_PROXY_API_KEY: str = os.getenv("LITELLM_PROXY_API_KEY", "")

    # LiteLLM API (Managed Service)
    LITELLM_API_KEY: str = os.getenv("LITELLM_API_KEY", "")

    # Provider API Keys (Fallback - for direct access)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")

    # Azure OpenAI
    AZURE_API_KEY: str = os.getenv("AZURE_API_KEY", "")
    AZURE_API_BASE: str = os.getenv("AZURE_API_BASE", "")
    AZURE_API_VERSION: str = os.getenv("AZURE_API_VERSION", "")

    # HTTP Proxy Settings
    HTTP_PROXY: str = os.getenv("HTTP_PROXY", "")
    HTTPS_PROXY: str = os.getenv("HTTPS_PROXY", "")
    NO_PROXY: str = os.getenv("NO_PROXY", "")

    # Default LLM Model
    DEFAULT_LLM_MODEL: str = "claude-3-5-haiku-20241022"

    # Default Output Directory
    DEFAULT_OUTPUT_DIR: str = "output_markdown"
    DEFAULT_DEBUG_OUTPUT_DIR: str = "debug_output"


# Global settings instance
settings = Settings()
