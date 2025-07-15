"""
Configuration settings for Tiny Backspace API
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    
    # Authentication
    require_auth: bool = Field(default=False, env="REQUIRE_AUTH")
    api_key: str = Field(default="", env="API_KEY")
    
    # Sandbox Configuration
    sandbox_provider: str = Field(default="daytona", env="SANDBOX_PROVIDER")
    daytona_api_key: str = Field(default="", env="DAYTONA_API_KEY")
    daytona_api_url: str = Field(
        default="https://app.daytona.io/api",
        env="DAYTONA_API_URL"
    )
    
    # Agent Configuration
    agent_type: str = Field(default="claude", env="AGENT_TYPE")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    claude_code_oauth_token: str = Field(default="", env="CLAUDE_CODE_OAUTH_TOKEN")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    
    # GitHub Configuration
    github_token: str = Field(default="", env="GITHUB_TOKEN")
    github_username: str = Field(default="", env="GITHUB_USERNAME")
    github_email: str = Field(default="", env="GITHUB_EMAIL")
    
    # Resource Limits
    max_sandbox_duration: int = Field(default=600, env="MAX_SANDBOX_DURATION")  # seconds
    max_file_size: int = Field(default=1048576, env="MAX_FILE_SIZE")  # 1MB
    max_files_per_pr: int = Field(default=50, env="MAX_FILES_PER_PR")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=10, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Observability
    enable_telemetry: bool = Field(default=False, env="ENABLE_TELEMETRY")
    otel_endpoint: str = Field(default="", env="OTEL_ENDPOINT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file