"""
Configuration management for Qwen Vision-Language Service
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    https_enabled: bool = Field(default=False, env="HTTPS_ENABLED")
    ssl_cert_path: Optional[str] = Field(default=None, env="SSL_CERT_PATH")
    ssl_key_path: Optional[str] = Field(default=None, env="SSL_KEY_PATH")
    
    # Model
    model_path: str = Field(default="/root/models/qwen2.5-vl-32b", env="MODEL_PATH")
    model_dtype: str = Field(default="float16", env="MODEL_DTYPE")
    model_max_tokens: int = Field(default=2048, env="MODEL_MAX_TOKENS")
    response_max_tokens: int = Field(default=128, env="RESPONSE_MAX_TOKENS")
    
    # vLLM
    vllm_host: str = Field(default="localhost", env="VLLM_HOST")
    vllm_port: int = Field(default=12345, env="VLLM_PORT")
    vllm_api_base: str = Field(default="http://localhost:12345/v1", env="VLLM_API_BASE")
    
    # Frame processing
    frame_sample_rate: float = Field(default=2.0, env="FRAME_SAMPLE_RATE")
    frame_queue_size: int = Field(default=8, env="FRAME_QUEUE_SIZE")
    frame_width: int = Field(default=1024, env="FRAME_WIDTH")
    frame_height: int = Field(default=1024, env="FRAME_HEIGHT")
    
    # Security
    jwt_secret_key: str = Field(default="CHANGE_THIS", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, env="JWT_EXPIRE_MINUTES")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # Safety
    enable_nsfw_filter: bool = Field(default=True, env="ENABLE_NSFW_FILTER")
    enable_face_blur: bool = Field(default=False, env="ENABLE_FACE_BLUR")
    
    # Performance
    max_concurrent_sessions: int = Field(default=10, env="MAX_CONCURRENT_SESSIONS")
    gpu_memory_utilization: float = Field(default=0.90, env="GPU_MEMORY_UTILIZATION")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Analytics
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

