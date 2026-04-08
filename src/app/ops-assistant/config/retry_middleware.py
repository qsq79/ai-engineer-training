#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重试中间件
用于在工具或模型调用失败时自动重试，支持指数退避策略
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

from langchain.agents.middleware import wrap_tool_call, wrap_model_call


logger = logging.getLogger(__name__)


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_exceptions: tuple = (Exception,)
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_exceptions = retry_on_exceptions


class RetryMiddleware:
    """重试中间件"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避）"""
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        return delay

    def _should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试"""
        return isinstance(exception, self.config.retry_on_exceptions)

    def create_tool_retry_middleware(self):
        """创建工具重试中间件"""

        @wrap_tool_call
        def tool_retry_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            工具调用重试中间件

            功能：
            1. 捕获工具调用异常
            2. 根据配置进行自动重试
            3. 使用指数退避策略避免过载
            4. 记录重试日志
            """
            tool_name = getattr(request, 'tool_name', 'unknown')

            last_exception = None

            for attempt in range(self.config.max_retries):
                try:
                    # 尝试执行工具调用
                    return handler(request)

                except Exception as e:
                    last_exception = e

                    # 判断是否应该重试
                    if not self._should_retry(e):
                        logger.warning(
                            f"[Tool Retry] Tool {tool_name} failed with non-retryable error: {type(e).__name__}: {e}"
                        )
                        raise

                    # 如果是最后一次尝试，不再重试
                    if attempt == self.config.max_retries - 1:
                        logger.error(
                            f"[Tool Retry] Tool {tool_name} failed after {self.config.max_retries} attempts. "
                            f"Final error: {type(e).__name__}: {e}"
                        )
                        raise

                    # 计算延迟时间
                    delay = self._calculate_delay(attempt)

                    logger.info(
                        f"[Tool Retry] Tool {tool_name} failed (attempt {attempt + 1}/{self.config.max_retries}). "
                        f"Error: {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # 等待后重试
                    time.sleep(delay)

            # 理论上不会到达这里
            raise last_exception

        return tool_retry_middleware

    def create_model_retry_middleware(self):
        """创建模型重试中间件"""

        @wrap_model_call
        def model_retry_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            模型调用重试中间件

            功能：
            1. 捕获模型调用异常
            2. 根据配置进行自动重试
            3. 使用指数退避策略避免过载
            4. 记录重试日志
            """
            last_exception = None

            for attempt in range(self.config.max_retries):
                try:
                    # 尝试执行模型调用
                    return handler(request)

                except Exception as e:
                    last_exception = e

                    # 判断是否应该重试
                    if not self._should_retry(e):
                        logger.warning(
                            f"[Model Retry] Model call failed with non-retryable error: {type(e).__name__}: {e}"
                        )
                        raise

                    # 如果是最后一次尝试，不再重试
                    if attempt == self.config.max_retries - 1:
                        logger.error(
                            f"[Model Retry] Model call failed after {self.config.max_retries} attempts. "
                            f"Final error: {type(e).__name__}: {e}"
                        )
                        raise

                    # 计算延迟时间
                    delay = self._calculate_delay(attempt)

                    logger.info(
                        f"[Model Retry] Model call failed (attempt {attempt + 1}/{self.config.max_retries}). "
                        f"Error: {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # 等待后重试
                    time.sleep(delay)

            # 理论上不会到达这里
            raise last_exception

        return model_retry_middleware


# 全局重试中间件实例
_global_tool_retry_middleware: Optional[RetryMiddleware] = None
_global_model_retry_middleware: Optional[RetryMiddleware] = None


def get_tool_retry_middleware(config: Optional[RetryConfig] = None) -> RetryMiddleware:
    """获取工具重试中间件实例（单例）"""
    global _global_tool_retry_middleware
    if _global_tool_retry_middleware is None or config is not None:
        _global_tool_retry_middleware = RetryMiddleware(config)
    return _global_tool_retry_middleware


def get_model_retry_middleware(config: Optional[RetryConfig] = None) -> RetryMiddleware:
    """获取模型重试中间件实例（单例）"""
    global _global_model_retry_middleware
    if _global_model_retry_middleware is None or config is not None:
        _global_model_retry_middleware = RetryMiddleware(config)
    return _global_model_retry_middleware


def create_tool_retry_middleware(config: Optional[RetryConfig] = None) -> Callable:
    """便捷函数：创建工具重试中间件"""
    return get_tool_retry_middleware(config).create_tool_retry_middleware()


def create_model_retry_middleware(config: Optional[RetryConfig] = None) -> Callable:
    """便捷函数：创建模型重试中间件"""
    return get_model_retry_middleware(config).create_model_retry_middleware()
