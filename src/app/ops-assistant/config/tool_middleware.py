#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具调用错误处理中间件
用于捕获和记录工具执行过程中的错误，便于线上问题排查
"""

import os
import logging
import traceback
from datetime import datetime
from typing import Callable

from langchain.agents.middleware import wrap_tool_call
from langchain.agents.middleware.types import ToolRequest, ToolResponse
from langchain.messages import ToolMessage

from .settings import get_config


# 配置日志
logger = logging.getLogger(__name__)


class ToolErrorHandler:
    """工具调用错误处理器"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self._setup_logging()

    def _setup_logging(self):
        """配置日志系统"""
        log_level = os.getenv("TOOL_LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )

        # 控制台处理器
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件处理器（可选）
        log_file = os.getenv("TOOL_LOG_FILE")
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    def _format_error_message(self, tool_name: str, error: Exception) -> str:
        """
        格式化错误消息

        对于模型：简洁的描述性错误
        对于日志：详细的技术信息
        """
        # 根据错误类型返回不同的用户友好消息
        error_type = type(error).__name__
        error_msg = str(error)

        if "connect" in error_msg.lower() or "connection" in error_msg.lower():
            return f"Unable to connect to the service. Please check if the API server is running at {self.config.api_base or os.getenv('OPS_API_BASE_URL', 'http://localhost:8000')}"

        if "timeout" in error_msg.lower():
            return f"Service request timed out. Please try again."

        if "404" in error_msg or "not found" in error_msg.lower():
            return f"Resource not found. Please verify the input parameters."

        if "401" in error_msg or "403" in error_msg or "auth" in error_msg.lower():
            return f"Authentication error. Please check your API credentials."

        # 默认错误消息
        return f"Tool execution failed: {error_type}. Please check the logs for details."

    def _log_tool_call(self, tool_name: str, tool_input: dict):
        """记录工具调用开始"""
        logger.info(f"[TOOL_CALL] Tool: {tool_name}")
        logger.debug(f"[TOOL_INPUT] Input: {tool_input}")

    def _log_tool_success(self, tool_name: str, duration_ms: float):
        """记录工具调用成功"""
        logger.info(f"[TOOL_SUCCESS] Tool: {tool_name} | Duration: {duration_ms:.2f}ms")

    def _log_tool_error(self, tool_name: str, error: Exception, duration_ms: float):
        """记录工具调用错误"""
        logger.error(f"[TOOL_ERROR] Tool: {tool_name} | Error: {type(error).__name__}: {str(error)} | Duration: {duration_ms:.2f}ms")
        logger.debug(f"[TOOL_ERROR] Traceback:\n{traceback.format_exc()}")

    def create_middleware(self):
        """创建工具错误处理中间件"""

        @wrap_tool_call
        def tool_error_handler(
            request: ToolRequest,
            handler: Callable[[ToolRequest], ToolResponse]
        ) -> ToolResponse:
            """
            工具调用错误处理中间件

            功能：
            1. 记录工具调用开始和结束
            2. 捕获工具执行过程中的异常
            3. 返回用户友好的错误消息给 LLM
            4. 记录详细的错误日志用于排查
            """
            tool_name = request.tool_name
            tool_input = request.tool_input
            start_time = datetime.now()

            # 记录工具调用开始
            self._log_tool_call(tool_name, tool_input)

            try:
                # 执行工具调用
                response = handler(request)

                # 计算执行时间
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录成功
                self._log_tool_success(tool_name, duration_ms)

                return response

            except Exception as e:
                # 计算执行时间
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录详细错误
                self._log_tool_error(tool_name, e, duration_ms)

                # 返回用户友好的错误消息给模型
                error_message = self._format_error_message(tool_name, e)

                return ToolMessage(
                    content=error_message,
                    tool_call_id=request.tool_call["id"]
                )

        return tool_error_handler


# 全局错误处理器实例
_global_error_handler = None


def get_tool_error_handler(config=None):
    """获取全局工具错误处理器实例"""
    global _global_error_handler
    if _global_error_handler is None or config is not None:
        _global_error_handler = ToolErrorHandler(config)
    return _global_error_handler


def create_tool_error_middleware():
    """便捷函数：创建工具错误处理中间件"""
    return get_tool_error_handler().create_middleware()
