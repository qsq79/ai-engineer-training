"""
企业级安全智能助手 - 数据库模块
"""
from .db_pool import (
    db_manager,
    Base,
    get_db_session,
    init_database,
    close_database,
)

from .redis_pool import (
    redis_manager,
    init_redis,
    close_redis,
    get_redis_client,
)

from .redis_cache import (
    RedisCacheManager,
    get_redis_cache_manager,
)

from .models import (
    Tenant,
    User,
    Session,
    AgentCall,
    WorkflowExecution,
    WorkflowTask,
    ComplianceCheck,
    AuditLog,
    TokenUsageStats,
    ThreatIntelligence,
)

from .init_db import (
    create_tables,
    drop_tables,
    verify_tables,
    create_tenant_sample,
)

__all__ = [
    # 数据库
    "db_manager",
    "Base",
    "get_db_session",
    "init_database",
    "close_database",
    # Redis
    "redis_manager",
    "init_redis",
    "close_redis",
    "get_redis_client",
    # Redis缓存
    "RedisCacheManager",
    "get_redis_cache_manager",
    # 模型
    "Tenant",
    "User",
    "Session",
    "AgentCall",
    "WorkflowExecution",
    "WorkflowTask",
    "ComplianceCheck",
    "AuditLog",
    "TokenUsageStats",
    "ThreatIntelligence",
    # 初始化
    "create_tables",
    "drop_tables",
    "verify_tables",
    "create_tenant_sample",
]
