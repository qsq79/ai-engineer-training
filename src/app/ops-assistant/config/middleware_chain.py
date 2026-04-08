#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中间件链管理器
实现可插拔的中间件系统，支持按需加载和管理多个中间件
"""

from typing import List, Any, Callable, Optional
from functools import wraps


class MiddlewareChain:
    """中间件链管理器"""

    def __init__(self):
        self.middlewares: List[Callable] = []
        self.enabled_middlewares: set = set()

    def add(self, middleware: Callable, name: Optional[str] = None, enabled: bool = True) -> 'MiddlewareChain':
        """
        添加中间件到链中

        Args:
            middleware: 中间件函数
            name: 中间件名称（可选）
            enabled: 是否启用（默认 True）

        Returns:
            self，支持链式调用
        """
        self.middlewares.append(middleware)
        if name and enabled:
            self.enabled_middlewares.add(name)
        return self

    def remove(self, name: str) -> 'MiddlewareChain':
        """
        从链中移除中间件

        Args:
            name: 要移除的中间件名称

        Returns:
            self，支持链式调用
        """
        self.enabled_middlewares.discard(name)
        return self

    def enable(self, name: str) -> 'MiddlewareChain':
        """
        启用指定的中间件

        Args:
            name: 中间件名称

        Returns:
            self，支持链式调用
        """
        self.enabled_middlewares.add(name)
        return self

    def disable(self, name: str) -> 'MiddlewareChain':
        """
        禁用指定的中间件

        Args:
            name: 中间件名称

        Returns:
            self，支持链式调用
        """
        self.enabled_middlewares.discard(name)
        return self

    def is_enabled(self, name: str) -> bool:
        """
        检查中间件是否启用

        Args:
            name: 中间件名称

        Returns:
            是否启用
        """
        return name in self.enabled_middlewares

    def get_enabled_middlewares(self) -> List[Callable]:
        """
        获取所有启用的中间件

        Returns:
            启用的中间件列表
        """
        return self.middlewares

    def clear(self) -> 'MiddlewareChain':
        """
        清空中间件链

        Returns:
            self，支持链式调用
        """
        self.middlewares.clear()
        self.enabled_middlewares.clear()
        return self

    def apply_to_handler(self, handler: Callable, middleware_filter: Optional[Callable[[str], bool]] = None) -> Callable:
        """
        将中间件链应用到处理函数

        Args:
            handler: 原始处理函数
            middleware_filter: 可选的中间件过滤函数，接收中间件名称返回是否应用

        Returns:
            包装后的处理函数
        """
        wrapped_handler = handler

        # 反向应用中间件（洋葱模型）
        for middleware in reversed(self.middlewares):
            wrapped_handler = middleware(wrapped_handler)

        return wrapped_handler


# 全局中间件链实例
_model_middleware_chain: Optional[MiddlewareChain] = None
_tool_middleware_chain: Optional[MiddlewareChain] = None


def get_model_middleware_chain() -> MiddlewareChain:
    """获取模型中间件链（单例）"""
    global _model_middleware_chain
    if _model_middleware_chain is None:
        _model_middleware_chain = MiddlewareChain()
    return _model_middleware_chain


def get_tool_middleware_chain() -> MiddlewareChain:
    """获取工具中间件链（单例）"""
    global _tool_middleware_chain
    if _tool_middleware_chain is None:
        _tool_middleware_chain = MiddlewareChain()
    return _tool_middleware_chain


def reset_middleware_chains():
    """重置所有中间件链（用于测试）"""
    global _model_middleware_chain, _tool_middleware_chain
    _model_middleware_chain = None
    _tool_middleware_chain = None
