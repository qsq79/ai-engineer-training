#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
限流中间件
用于控制工具和模型调用的频率，防止过度调用
"""

import time
import logging
from typing import Callable, Any, Dict, Optional
from collections import deque
from datetime import datetime, timedelta

from langchain.agents.middleware import wrap_tool_call, wrap_model_call


logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""

    def __init__(
        self,
        max_calls: int = 60,
        time_window_seconds: int = 60
    ):
        """
        初始化速率限制器

        Args:
            max_calls: 时间窗口内允许的最大调用次数
            time_window_seconds: 时间窗口大小（秒）
        """
        self.max_calls = max_calls
        self.time_window = timedelta(seconds=time_window_seconds)
        self.call_timestamps = deque()

    def acquire(self) -> bool:
        """
        尝试获取调用许可

        Returns:
            是否允许调用
        """
        now = datetime.now()
        
        # 清理过期的调用记录
        cutoff = now - self.time_window
        while self.call_timestamps and self.call_timestamps[0] < cutoff:
            self.call_timestamps.popleft()
        
        # 检查是否超过限制
        if len(self.call_timestamps) >= self.max_calls:
            return False
        
        # 记录当前调用
        self.call_timestamps.append(now)
        return True

    def get_wait_time(self) -> float:
        """
        获取需要等待的时间（秒）

        Returns:
            需要等待的秒数，如果可以立即调用则返回 0
        """
        if len(self.call_timestamps) < self.max_calls:
            return 0.0
        
        # 计算最早的一次调用何时过期
        oldest_call = self.call_timestamps[0]
        expiry_time = oldest_call + self.time_window
        wait_seconds = (expiry_time - datetime.now()).total_seconds()
        
        return max(0.0, wait_seconds)

    def reset(self):
        """重置速率限制器"""
        self.call_timestamps.clear()


class RateLimitMiddleware:
    """限流中间件"""

    def __init__(
        self,
        tool_rate_limit: Dict[str, RateLimiter] = None,
        default_tool_rate_limit: RateLimiter = None,
        model_rate_limit: Dict[str, RateLimiter] = None,
        default_model_rate_limit: RateLimiter = None
    ):
        """
        初始化限流中间件

        Args:
            tool_rate_limit: 特定工具的速率限制器字典
            default_tool_rate_limit: 工具的默认速率限制器
            model_rate_limit: 特定模型的速率限制器字典
            default_model_rate_limit: 模型的默认速率限制器
        """
        self.tool_rate_limit = tool_rate_limit or {}
        self.default_tool_rate_limit = default_tool_rate_limit or RateLimiter(
            max_calls=100,
            time_window_seconds=60
        )
        self.model_rate_limit = model_rate_limit or {}
        self.default_model_rate_limit = default_model_rate_limit or RateLimiter(
            max_calls=60,
            time_window_seconds=60
        )

    def _get_tool_rate_limiter(self, tool_name: str) -> RateLimiter:
        """获取工具的速率限制器"""
        return self.tool_rate_limit.get(tool_name, self.default_tool_rate_limit)

    def _get_model_rate_limiter(self, model_name: str) -> RateLimiter:
        """获取模型的速率限制器"""
        return self.model_rate_limit.get(model_name, self.default_model_rate_limit)

    def create_tool_rate_limit_middleware(self):
        """创建工具限流中间件"""

        @wrap_tool_call
        def tool_rate_limit_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            工具调用限流中间件

            功能：
            1. 检查工具调用频率
            2. 如果超过限制，等待或拒绝
            3. 记录限流日志
            """
            tool_name = getattr(request, 'tool_name', 'unknown')
            rate_limiter = self._get_tool_rate_limiter(tool_name)

            # 检查速率限制
            if not rate_limiter.acquire():
                wait_time = rate_limiter.get_wait_time()
                
                logger.warning(
                    f"[Tool Rate Limit] Tool {tool_name} rate limit exceeded. "
                    f"Wait time: {wait_time:.2f}s"
                )
                
                # 可以选择等待或直接拒绝
                # 这里选择等待
                if wait_time > 0:
                    time.sleep(wait_time)
                    logger.info(f"[Tool Rate Limit] Tool {tool_name} resumed after waiting")

            # 执行工具调用
            return handler(request)

        return tool_rate_limit_middleware

    def create_model_rate_limit_middleware(self):
        """创建模型限流中间件"""

        @wrap_model_call
        def model_rate_limit_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            模型调用限流中间件

            功能：
            1. 检查模型调用频率
            2. 如果超过限制，等待或拒绝
            3. 记录限流日志
            """
            # 尝试获取模型名称
            model = getattr(request, 'model', None)
            model_name = getattr(model, 'model_name', 'unknown') if model else 'unknown'
            
            rate_limiter = self._get_model_rate_limiter(model_name)

            # 检查速率限制
            if not rate_limiter.acquire():
                wait_time = rate_limiter.get_wait_time()
                
                logger.warning(
                    f"[Model Rate Limit] Model {model_name} rate limit exceeded. "
                    f"Wait time: {wait_time:.2f}s"
                )
                
                # 可以选择等待或直接拒绝
                # 这里选择等待
                if wait_time > 0:
                    time.sleep(wait_time)
                    logger.info(f"[Model Rate Limit] Model {model_name} resumed after waiting")

            # 执行模型调用
            return handler(request)

        return model_rate_limit_middleware

    def set_tool_rate_limit(self, tool_name: str, max_calls: int, time_window_seconds: int):
        """
        设置特定工具的速率限制

        Args:
            tool_name: 工具名称
            max_calls: 时间窗口内允许的最大调用次数
            time_window_seconds: 时间窗口大小（秒）
        """
        self.tool_rate_limit[tool_name] = RateLimiter(
            max_calls=max_calls,
            time_window_seconds=time_window_seconds
        )

    def set_model_rate_limit(self, model_name: str, max_calls: int, time_window_seconds: int):
        """
        设置特定模型的速率限制

        Args:
            model_name: 模型名称
            max_calls: 时间窗口内允许的最大调用次数
            time_window_seconds: 时间窗口大小（秒）
        """
        self.model_rate_limit[model_name] = RateLimiter(
            max_calls=max_calls,
            time_window_seconds=time_window_seconds
        )


# 全局限流中间件实例
_global_rate_limit_middleware: Optional[RateLimitMiddleware] = None


def get_rate_limit_middleware(
    tool_rate_limit: Dict[str, RateLimiter] = None,
    default_tool_rate_limit: RateLimiter = None,
    model_rate_limit: Dict[str, RateLimiter] = None,
    default_model_rate_limit: RateLimiter = None
) -> RateLimitMiddleware:
    """获取限流中间件实例（单例）"""
    global _global_rate_limit_middleware
    if _global_rate_limit_middleware is None or any([tool_rate_limit, model_rate_limit]):
        _global_rate_limit_middleware = RateLimitMiddleware(
            tool_rate_limit=tool_rate_limit,
            default_tool_rate_limit=default_tool_rate_limit,
            model_rate_limit=model_rate_limit,
            default_model_rate_limit=default_model_rate_limit
        )
    return _global_rate_limit_middleware


def create_tool_rate_limit_middleware(
    tool_rate_limit: Dict[str, RateLimiter] = None,
    default_tool_rate_limit: RateLimiter = None,
    model_rate_limit: Dict[str, RateLimiter] = None,
    default_model_rate_limit: RateLimiter = None
) -> Callable:
    """便捷函数：创建工具限流中间件"""
    return get_rate_limit_middleware(
        tool_rate_limit=tool_rate_limit,
        default_tool_rate_limit=default_tool_rate_limit,
        model_rate_limit=model_rate_limit,
        default_model_rate_limit=default_model_rate_limit
    ).create_tool_rate_limit_middleware()


def create_model_rate_limit_middleware(
    tool_rate_limit: Dict[str, RateLimiter] = None,
    default_tool_rate_limit: RateLimiter = None,
    model_rate_limit: Dict[str, RateLimiter] = None,
    default_model_rate_limit: RateLimiter = None
) -> Callable:
    """便捷函数：创建模型限流中间件"""
    return get_rate_limit_middleware(
        tool_rate_limit=tool_rate_limit,
        default_tool_rate_limit=default_tool_rate_limit,
        model_rate_limit=model_rate_limit,
        default_model_rate_limit=default_model_rate_limit
    ).create_model_rate_limit_middleware()
