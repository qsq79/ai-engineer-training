#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain Agent 核心模块
使用 LangChain 1.x+ 最新的 create_agent API 创建运维助手
支持统一配置管理、动态模型选择和智能模型路由
"""

import os
from typing import Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from tools import TOOLS
from config import (
    get_config, AppConfig,
    create_model_router_middleware, create_tool_error_middleware,
    create_tool_retry_middleware, create_model_retry_middleware,
    create_tool_monitoring_middleware, create_model_monitoring_middleware,
    create_tool_rate_limit_middleware, create_model_rate_limit_middleware,
    RetryConfig,
    get_metrics_collector,
)


class OpsAssistantAgent:
    """运维助手 Agent 类"""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        config: Optional[AppConfig] = None,
        enable_smart_routing: bool = True,
        enable_tool_error_handler: bool = True,
        enable_retry: bool = False,
        retry_config: Optional[RetryConfig] = None,
        enable_monitoring: bool = True,
        enable_rate_limit: bool = False,
        **kwargs
    ):
        """
        初始化运维助手 Agent

        Args:
            model: 模型名称，如果为 None 则使用配置文件中的默认模型
            temperature: 温度参数，覆盖配置文件中的值
            max_tokens: 最大 token 数，覆盖配置文件中的值
            config: 配置对象，如果为 None 则自动加载
            enable_smart_routing: 是否启用智能模型路由（默认 True）
            enable_tool_error_handler: 是否启用工具错误处理中间件（默认 True）
            enable_retry: 是否启用重试中间件（默认 False）
            retry_config: 重试配置（可选）
            enable_monitoring: 是否启用监控中间件（默认 True）
            enable_rate_limit: 是否启用限流中间件（默认 False）
            **kwargs: 其他传递给 ChatOpenAI 的参数
        """
        # 加载配置
        self.config = config or get_config()

        # 验证 API Key
        if not self.config.api_key:
            raise ValueError("未找到 OPENAI_API_KEY，请设置环境变量或在 .env 文件中配置")

        # 获取模型配置
        model_config = self.config.get_model_config(model)

        # 应用参数覆盖
        if temperature is not None:
            model_config.temperature = temperature
        if max_tokens is not None:
            model_config.max_tokens = max_tokens

        # 保存当前使用的模型配置
        self.model_config = model_config

        # 保存各种中间件开关
        self.enable_smart_routing = enable_smart_routing and self.config.enable_model_routing
        self.enable_tool_error_handler = enable_tool_error_handler
        self.enable_retry = enable_retry
        self.enable_monitoring = enable_monitoring
        self.enable_rate_limit = enable_rate_limit

        # 初始化 LLM
        llm_params = model_config.to_dict()
        llm_params["api_key"] = self.config.api_key
        llm_params.update(kwargs)

        self.llm = ChatOpenAI(**llm_params)

        # 准备中间件列表
        model_middleware = []
        tool_middleware = []

        # 添加智能模型路由中间件
        if self.enable_smart_routing:
            model_middleware.append(create_model_router_middleware())

        # 添加重试中间件
        if self.enable_retry:
            model_middleware.append(create_model_retry_middleware(retry_config))
            tool_middleware.append(create_tool_retry_middleware(retry_config))

        # 添加监控中间件
        if self.enable_monitoring:
            model_middleware.append(create_model_monitoring_middleware())
            tool_middleware.append(create_tool_monitoring_middleware())

        # 添加限流中间件
        if self.enable_rate_limit:
            model_middleware.append(create_model_rate_limit_middleware())
            tool_middleware.append(create_tool_rate_limit_middleware())

        # 添加工具错误处理中间件（最后执行，确保捕获所有错误）
        if self.enable_tool_error_handler:
            tool_middleware.append(create_tool_error_middleware())

        # 合并中间件
        middleware = model_middleware + tool_middleware

        # 创建 Agent
        self.agent = create_agent(
            model=self.llm,
            tools=TOOLS,
            system_prompt=self._get_system_prompt(),
            middleware=middleware,
        )

        # 用于保存对话历史
        self.thread = None

    def _get_system_prompt(self) -> str:
        """Get system prompt"""
        return """You are a professional operations assistant, specializing in helping users analyze and resolve user login issues.

You have access to the following tools:
1. get_user_info: Get basic user information including user ID, username, email, account status, role, department, etc.
2. check_login_log: Check user login logs including login time, IP address, login status, failure reason, etc.

Usage Guide:
- When asking about user information, use the get_user_info tool
- When asking about login issues or login failures, first use the check_login_log tool to check login logs
- If more information is needed, combine both tools
- Based on query results, provide clear analysis and recommendations

Common Issue Analysis:
- If user status is "locked", the account is locked, usually due to multiple login failures
- If login log shows "password error", recommend user to reset password
- If login log shows "IP not in whitelist", need to check IP whitelist configuration
- If login log shows "account expired", need to contact administrator to handle the account

Please respond to user questions in a friendly, professional tone.
"""

    def query(self, user_input: str) -> str:
        """
        处理用户查询

        Args:
            user_input: 用户的输入问题

        Returns:
            Agent 的回复
        """
        try:
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": user_input}]
            })

            # 提取最后一条消息的内容
            if result and "messages" in result:
                last_message = result["messages"][-1]
                # LangChain 消息对象总有 content 属性
                return last_message.content

            return "Sorry, there was an issue processing your request."

        except Exception as e:
            # 简化错误处理，区分认证错误和其他错误
            if "401" in str(e) or "auth" in str(e).lower():
                return "Authentication error: Please check your API key."

            # 开发环境显示详细错误，生产环境简化
            if os.getenv("DEBUG", "false").lower() == "true":
                import traceback
                return f"Error: {type(e).__name__}\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"

            return f"An error occurred while processing your request. Please try again."

    def query_stream(self, user_input: str):
        """
        流式处理用户查询

        Args:
            user_input: 用户的输入问题

        Yields:
            Agent 的流式回复
        """
        try:
            for event in self.agent.stream({
                "messages": [{"role": "user", "content": user_input}]
            }):
                if "messages" in event:
                    for message in event["messages"]:
                        yield message.content
        except Exception as e:
            yield f"Error: {str(e)}"

    def switch_model(self, model: str, **kwargs):
        """
        动态切换模型

        注意：这会重新创建 Agent，智能路由会被禁用

        Args:
            model: 新的模型名称
            **kwargs: 其他要覆盖的参数
        """
        # 获取新的模型配置
        model_config = self.config.get_model_config(model)

        # 应用参数覆盖
        if 'temperature' in kwargs:
            model_config.temperature = kwargs.pop('temperature')
        if 'max_tokens' in kwargs:
            model_config.max_tokens = kwargs.pop('max_tokens')

        # 更新模型配置
        self.model_config = model_config

        # 重新创建 LLM
        llm_params = model_config.to_dict()
        llm_params["api_key"] = self.config.api_key
        llm_params.update(kwargs)

        self.llm = ChatOpenAI(**llm_params)

        # 重新创建 Agent（不包含智能路由中间件）
        self.agent = create_agent(
            model=self.llm,
            tools=TOOLS,
            system_prompt=self._get_system_prompt(),
        )

        # 切换模型后禁用智能路由
        self.enable_smart_routing = False

    def get_current_model_info(self) -> dict:
        """获取当前使用的模型信息"""
        return self.config.get_model_info(self.model_config.name)

    def list_available_models(self) -> list:
        """列出所有可用的模型"""
        return self.config.list_models()

    def enable_model_routing(self):
        """启用智能模型路由"""
        if not self.enable_smart_routing:
            self.agent = create_agent(
                model=self.llm,
                tools=TOOLS,
                system_prompt=self._get_system_prompt(),
                middleware=[create_model_router_middleware()],
            )
            self.enable_smart_routing = True

    def disable_model_routing(self):
        """禁用智能模型路由"""
        if self.enable_smart_routing:
            self.agent = create_agent(
                model=self.llm,
                tools=TOOLS,
                system_prompt=self._get_system_prompt(),
            )
            self.enable_smart_routing = False

    def get_metrics(self) -> dict:
        """
        获取监控指标

        Returns:
            包含工具和模型调用统计的字典
        """
        if not self.enable_monitoring:
            return {"monitoring": "disabled"}

        collector = get_metrics_collector()
        
        return {
            "tool_stats": collector.get_all_tool_stats(),
            "model_stats": collector.get_all_model_stats(),
            "recent_calls": len(collector.get_recent_history(minutes=5))
        }

    def print_metrics(self):
        """打印监控指标"""
        metrics = self.get_metrics()
        
        if "monitoring" in metrics and metrics["monitoring"] == "disabled":
            print("Monitoring is disabled")
            return

        print("\n" + "=" * 60)
        print("Monitoring Metrics")
        print("=" * 60)
        
        # 工具统计
        print("\nTool Statistics:")
        for tool_name, stats in metrics["tool_stats"].items():
            if stats:
                print(f"\n  {tool_name}:")
                print(f"    Calls: {stats.get('call_count', 0)}")
                print(f"    Success Rate: {stats.get('success_rate', 0) * 100:.2f}%")
                print(f"    Avg Duration: {stats.get('avg_duration_ms', 0):.2f}ms")
                print(f"    P95 Duration: {stats.get('p95_duration_ms', 0):.2f}ms")
                print(f"    P99 Duration: {stats.get('p99_duration_ms', 0):.2f}ms")
        
        # 模型统计
        print("\nModel Statistics:")
        for model_name, stats in metrics["model_stats"].items():
            if stats:
                print(f"\n  {model_name}:")
                print(f"    Calls: {stats.get('call_count', 0)}")
                print(f"    Success Rate: {stats.get('success_rate', 0) * 100:.2f}%")
                print(f"    Avg Duration: {stats.get('avg_duration_ms', 0):.2f}ms")
                print(f"    P95 Duration: {stats.get('p95_duration_ms', 0):.2f}ms")
                print(f"    P99 Duration: {stats.get('p99_duration_ms', 0):.2f}ms")
        
        print(f"\nRecent Calls (last 5 minutes): {metrics['recent_calls']}")
        print("=" * 60 + "\n")

    def chat(self):
        """启动交互式聊天模式"""
        routing_status = "enabled" if self.enable_smart_routing else "disabled"
        print("=" * 60)
        print(f"Ops Assistant (Model: {self.model_config.name})")
        print(f"Smart Model Routing: {routing_status}")
        print("Commands: /models, /model <name>, /routing on/off")
        print("Type 'quit' or 'exit' to exit")
        print("=" * 60)

        while True:
            try:
                user_input = input("\nYour question: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nThank you for using Ops Assistant. Goodbye!")
                    break

                # 动态切换模型
                if user_input.startswith('/model '):
                    new_model = user_input[7:].strip()
                    try:
                        self.switch_model(new_model)
                        print(f"Switched to {self.model_config.name} (routing disabled)")
                        continue
                    except Exception as e:
                        print(f"Failed to switch model: {e}")
                        continue

                # 列出可用模型
                if user_input in ['/models', '/list']:
                    models = self.list_available_models()
                    print("\nAvailable models:")
                    for m in models:
                        info = self.config.get_model_info(m)
                        current = " *" if m == self.model_config.name else ""
                        print(f"  {m}: {info['name']}{current}")
                    continue

                # 切换智能路由
                if user_input == '/routing on':
                    self.enable_model_routing()
                    print("Smart model routing enabled")
                    continue

                if user_input == '/routing off':
                    self.disable_model_routing()
                    print("Smart model routing disabled")
                    continue

                print("\nProcessing...")
                response = self.query(user_input)
                print(f"\nResponse:\n{response}")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
