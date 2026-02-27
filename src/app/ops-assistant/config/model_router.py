#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能模型路由中间件

根据任务类型、复杂度、对话轮次等因素动态选择模型
使用 @wrap_model_call 装饰器实现
"""

import os
from typing import Callable, Dict

from langchain.agents.middleware import wrap_model_call
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_openai import ChatOpenAI

from .settings import get_config


class IntelligentModelRouter:
    """智能模型路由器"""

    # 任务复杂度关键词
    COMPLEX_TASKS = [
        'analyze', 'analysis', 'investigate', 'debug', 'troubleshoot',
        'explain', 'compare', 'evaluate', 'recommend', 'design',
        '分析', '调查', '调试', '排错', '解释', '比较', '评估', '建议', '设计'
    ]

    # 简单任务关键词
    SIMPLE_TASKS = [
        'get', 'fetch', 'list', 'show', 'check', 'what', 'who', 'when', 'where',
        '获取', '显示', '检查', '什么', '谁', '什么时候', '哪里'
    ]

    # 高精度任务关键词
    HIGH_PRECISION = [
        'security', 'auth', 'permission', 'compliance', 'audit',
        '安全', '认证', '权限', '合规', '审计'
    ]

    # 模型层级
    MODEL_TIERS = {
        'fast': 'gpt-4o-mini',      # 快速、低成本
        'balanced': 'gpt-4o',        # 平衡
        'powerful': 'gpt-4-turbo',   # 高性能
        'premium': 'gpt-4',          # 最强
    }

    def __init__(self, config=None):
        self.config = config or get_config()
        self._model_cache: Dict[str, ChatOpenAI] = {}

    def _get_model(self, model_name: str) -> ChatOpenAI:
        """获取或创建模型实例（带缓存）"""
        if model_name not in self._model_cache:
            model_config = self.config.get_model_config(model_name)
            llm_params = model_config.to_dict()
            llm_params["api_key"] = self.config.api_key
            self._model_cache[model_name] = ChatOpenAI(**llm_params)
        return self._model_cache[model_name]

    def _analyze_task_complexity(self, messages: list) -> str:
        """分析任务复杂度，返回 'simple', 'balanced', 或 'complex'"""
        # 获取最近的用户消息
        user_message = ""
        for msg in reversed(messages):
            content = getattr(msg, 'content', '')
            if isinstance(content, str):
                user_message = content.lower()
                break

        # 检查简单任务
        if any(kw in user_message for kw in self.SIMPLE_TASKS):
            return 'simple'

        # 检查高精度任务
        if any(kw in user_message for kw in self.HIGH_PRECISION):
            return 'complex'

        # 检查复杂任务
        if any(kw in user_message for kw in self.COMPLEX_TASKS):
            return 'complex'

        return 'balanced'

    def _calculate_context_size(self, messages: list) -> int:
        """估算上下文 token 数"""
        total_chars = 0
        for msg in messages:
            content = getattr(msg, 'content', '')
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        total_chars += len(item['text'])
        # 1 token ≈ 4 字符
        return total_chars // 4

    def _count_tool_calls(self, messages: list) -> int:
        """计算对话中的工具调用次数"""
        count = 0
        for msg in messages:
            tool_calls = getattr(msg, 'tool_calls', None)
            if tool_calls:
                count += len(tool_calls)
        return count

    def select_model(self, request: ModelRequest) -> str:
        """根据请求状态智能选择模型"""
        messages = request.state.get('messages', [])

        # 分析任务复杂度
        complexity = self._analyze_task_complexity(messages)

        # 计算上下文大小
        context_size = self._calculate_context_size(messages)

        # 计算对话轮次
        message_count = len(messages)

        # 计算工具调用次数
        tool_call_count = self._count_tool_calls(messages)

        # 根据综合因素选择模型
        if context_size > 8000 or tool_call_count > 5:
            return self.MODEL_TIERS['premium']

        if complexity == 'complex':
            return self.MODEL_TIERS['powerful']

        if message_count > 10:
            return self.MODEL_TIERS['powerful']
        elif message_count > 5:
            return self.MODEL_TIERS['balanced']

        if complexity == 'simple':
            return self.MODEL_TIERS['fast']

        return self.MODEL_TIERS['balanced']

    def create_middleware(self):
        """创建模型路由中间件"""

        @wrap_model_call
        def intelligent_model_router(
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse]
        ) -> ModelResponse:
            """智能模型路由中间件"""
            selected_model = self.select_model(request)

            # 调试输出
            if os.getenv('MODEL_ROUTING_DEBUG'):
                messages = request.state.get('messages', [])
                print(f"\n[Model Routing] Selected: {selected_model} | Messages: {len(messages)} | Tools: {self._count_tool_calls(messages)}")

            return handler(request.override(model=self._get_model(selected_model)))

        return intelligent_model_router


# 全局路由器实例
_global_router = None


def get_model_router(config=None):
    """获取全局模型路由器实例"""
    global _global_router
    if _global_router is None or config is not None:
        _global_router = IntelligentModelRouter(config)
    return _global_router


def create_model_router_middleware():
    """便捷函数：创建模型路由中间件"""
    return get_model_router().create_middleware()
