#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

from .settings import (
    AppConfig,
    ModelConfig,
    get_config,
    reload_config,
)
from .model_router import (
    IntelligentModelRouter,
    create_model_router_middleware,
    get_model_router,
)
from .tool_middleware import (
    ToolErrorHandler,
    create_tool_error_middleware,
    get_tool_error_handler,
)
from .retry_middleware import (
    RetryConfig,
    RetryMiddleware,
    create_tool_retry_middleware,
    create_model_retry_middleware,
    get_tool_retry_middleware,
    get_model_retry_middleware,
)
from .monitoring_middleware import (
    MetricsCollector,
    MonitoringMiddleware,
    create_tool_monitoring_middleware,
    create_model_monitoring_middleware,
    get_monitoring_middleware,
    get_metrics_collector,
)
from .rate_limit_middleware import (
    RateLimiter,
    RateLimitMiddleware,
    create_tool_rate_limit_middleware,
    create_model_rate_limit_middleware,
    get_rate_limit_middleware,
)
from .middleware_chain import (
    MiddlewareChain,
    get_model_middleware_chain,
    get_tool_middleware_chain,
    reset_middleware_chains,
)

__all__ = [
    'AppConfig',
    'ModelConfig',
    'get_config',
    'reload_config',
    'IntelligentModelRouter',
    'create_model_router_middleware',
    'get_model_router',
    'ToolErrorHandler',
    'create_tool_error_middleware',
    'get_tool_error_handler',
    # 中间件链
    'MiddlewareChain',
    'get_model_middleware_chain',
    'get_tool_middleware_chain',
    'reset_middleware_chains',
    # 重试中间件
    'RetryConfig',
    'RetryMiddleware',
    'create_tool_retry_middleware',
    'create_model_retry_middleware',
    'get_tool_retry_middleware',
    'get_model_retry_middleware',
    # 监控中间件
    'MetricsCollector',
    'MonitoringMiddleware',
    'create_tool_monitoring_middleware',
    'create_model_monitoring_middleware',
    'get_monitoring_middleware',
    'get_metrics_collector',
    # 限流中间件
    'RateLimiter',
    'RateLimitMiddleware',
    'create_tool_rate_limit_middleware',
    'create_model_rate_limit_middleware',
    'get_rate_limit_middleware',
]
