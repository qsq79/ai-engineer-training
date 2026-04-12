"""
企业级安全智能助手 - 配置管理模块

使用Pydantic Settings实现配置管理，支持环境变量和.env文件
"""
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ESA_",
        case_sensitive=False,
    )
    
    # 应用基础配置
    app_name: str = Field(default="Enterprise Security Assistant", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机地址")
    port: int = Field(default=8000, description="服务器端口")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: Optional[str] = Field(default="logs/app.log", description="日志文件路径")
    log_rotation: str = Field(default="10 MB", description="日志轮转大小")
    log_retention: str = Field(default="30 days", description="日志保留时间")
    
    # OpenAI配置
    openai_api_key: str = Field(default="", description="OpenAI API密钥")
    openai_api_base: Optional[str] = Field(default="https://api.openai.com/v1", description="OpenAI API基础URL")
    openai_model: str = Field(default="gpt-4o", description="默认OpenAI模型")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM温度参数")
    openai_max_tokens: int = Field(default=2000, ge=1, description="LLM最大Token数")
    
    # 合规检查专用模型配置
    compliance_model: str = Field(default="gpt-4o", description="合规检查专用模型")
    
    # 数据库配置
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/esa_db",
        description="数据库连接URL"
    )
    database_pool_size: int = Field(default=10, ge=1, description="数据库连接池大小")
    database_max_overflow: int = Field(default=20, ge=0, description="数据库连接池最大溢出")
    
    # Redis配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    redis_pool_size: int = Field(default=10, ge=1, description="Redis连接池大小")
    
    # 向量数据库配置
    vector_db_type: str = Field(default="chroma", description="向量数据库类型（chroma/faiss）")
    vector_db_path: str = Field(default="data/vector_db", description="向量数据库路径")
    chroma_persist_directory: str = Field(default="./data/chroma", description="Chroma持久化目录")
    
    # JWT配置
    jwt_secret_key: str = Field(default="your-secret-key-here", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, description="访问Token过期时间（分钟）")
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, description="刷新Token过期时间（天）")
    
    # 限流配置
    rate_limit_enabled: bool = Field(default=True, description="是否启用限流")
    rate_limit_default_qps: int = Field(default=100, ge=1, description="默认QPS限制")
    rate_limit_tenant_qps: int = Field(default=1000, ge=1, description="租户QPS限制")
    rate_limit_user_qps: int = Field(default=100, ge=1, description="用户QPS限制")
    rate_limit_token_per_day: int = Field(default=1000000, ge=1, description="每租户每日Token限制")
    rate_limit_concurrent_requests: int = Field(default=10, ge=1, description="并发请求数限制")
    
    # 熔断配置
    circuit_breaker_enabled: bool = Field(default=True, description="是否启用熔断器")
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, description="熔断失败阈值")
    circuit_breaker_recovery_timeout: int = Field(default=60, ge=1, description="熔断恢复超时（秒）")
    
    # 监控配置
    prometheus_enabled: bool = Field(default=True, description="是否启用Prometheus监控")
    tracing_enabled: bool = Field(default=True, description="是否启用链路追踪")
    
    # CORS配置
    cors_origins: str = Field(default="*", description="CORS允许的源（逗号分隔或*）")
    cors_allow_credentials: bool = Field(default=True, description="CORS允许凭证")
    cors_allow_methods: str = Field(default="*", description="CORS允许的方法（逗号分隔或*）")
    cors_allow_headers: str = Field(default="*", description="CORS允许的头部（逗号分隔或*）")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日志级别必须是以下之一: {valid_levels}")
        return v.upper()
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """验证数据库URL"""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("数据库URL必须以postgresql://或postgresql+asyncpg://开头")
        return v
    
    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """验证Redis URL"""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL必须以redis://开头")
        return v
    
    @field_validator("vector_db_type")
    @classmethod
    def validate_vector_db_type(cls, v: str) -> str:
        """验证向量数据库类型"""
        valid_types = ["chroma", "faiss"]
        if v.lower() not in valid_types:
            raise ValueError(f"向量数据库类型必须是以下之一: {valid_types}")
        return v.lower()


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（用于依赖注入）"""
    return settings
