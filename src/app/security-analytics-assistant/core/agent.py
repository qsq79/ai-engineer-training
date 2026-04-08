#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景一：复杂日志查询解释（Agent模式）
"""

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from config import get_config, AppConfig
from tools import (
    get_report_query_conditions,
    get_user_query_conditions,
    generate_sql_with_conditions,
    compare_conditions,
)


@tool
def get_query_intent(user_question: str) -> str:
    """
    分析用户问题，判断意图
    
    Args:
        user_question: 用户问题
    
    Returns:
        意图类型：query_diff（查询差异）或 explain_result（解释结果）
    """
    question = user_question.lower()
    
    # 关键词判断
    if any(kw in question for kw in ['为什么', '为什么', '对不上', '不一致', '差', '少', '多']):
        return 'query_diff'
    
    return 'explain_result'


class QueryExplanationAgent:
    """日志查询解释 Agent"""
    
    def __init__(self, config: AppConfig = None, model: str = None):
        """
        初始化 Agent
        
        Args:
            config: 配置对象
            model: 模型名称（可选）
        """
        self.config = config or get_config()
        
        # 获取模型配置
        model_name = model or self.config.default_model
        llm_params = {
            "model": model_name,
            "api_key": self.config.api_key,
            "api_base": self.config.api_base,
            "temperature": 0.0,  # 使用较低的温度以获得更准确的分析
            "max_tokens": self.config.max_tokens
        }
        
        self.llm = ChatOpenAI(**llm_params)
        self.agent = create_agent(
            model=self.llm,
            tools=[
                get_report_query_conditions,
                get_user_query_conditions,
                generate_sql_with_conditions,
                compare_conditions
            ],
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """你是一个专业的安全数据分析助手，专门帮助客户理解日志查询数据的差异。

你的任务是：
1. 理解用户关于月报数据和日志中心查询数据不匹配的问题
2. 调用相应的工具获取月报查询条件和用户查询条件
3. 对比两个条件，找出差异
4. 生成可在日志中心执行的 SQL
5. 用清晰、友好的语言解释差异原因

可用工具：
- get_report_query_conditions: 获取月报生成时使用的查询条件（资产组、资源组、攻击类型、IP排除等）
- get_user_query_conditions: 获取用户在日志中心使用的查询条件
- compare_conditions: 对比两个条件，找出差异
- generate_sql_with_conditions: 根据条件生成 SQL 查询语句

注意事项：
- 月报通常会有隐藏的过滤条件（如特定资产组、资源组、IP排除等）
- 用户可能不知道这些隐藏条件，导致查询结果不一致
- 需要详细解释每个差异点，帮助用户理解问题所在

请用专业、友好的语气回答用户的问题。"""
    
    def query(self, user_question: str, report_id: str = None, metric_name: str = None, user_id: str = None, query_time_range: str = None) -> str:
        """
        处理用户查询
        
        Args:
            user_question: 用户问题
            report_id: 月报ID（可选）
            metric_name: 指标名称（可选）
            user_id: 用户ID（可选）
            query_time_range: 查询时间范围（可选）
        
        Returns:
            Agent 的回答
        """
        try:
            # 构建 Agent 输入
            inputs = {"messages": [{"role": "user", "content": user_question}]}
            
            # 如果提供了具体的参数，可以在问题中包含
            if report_id:
                inputs["report_id"] = report_id
            if metric_name:
                inputs["metric_name"] = metric_name
            if user_id:
                inputs["user_id"] = user_id
            if query_time_range:
                inputs["query_time_range"] = query_time_range
            
            # 调用 Agent
            result = self.agent.invoke(inputs)
            
            # 提取回答
            if result and "messages" in result:
                last_message = result["messages"][-1]
                return last_message.content
            
            return "抱歉，处理您的请求时出现了问题。"
        
        except Exception as e:
            return f"处理请求时出错：{str(e)}"
    
    def query_stream(self, user_question: str, report_id: str = None, metric_name: str = None, user_id: str = None):
        """
        流式处理用户查询
        
        Args:
            user_question: 用户问题
            report_id: 月报ID（可选）
            metric_name: 指标名称（可选）
            user_id: 用户ID（可选）
        
        Yields:
            Agent 的流式回答
        """
        try:
            # 构建 Agent 输入
            inputs = {"messages": [{"role": "user", "content": user_question}]}
            
            if report_id:
                inputs["report_id"] = report_id
            if metric_name:
                inputs["metric_name"] = metric_name
            if user_id:
                inputs["user_id"] = user_id
            
            # 调用 Agent（流式）
            for event in self.agent.stream(inputs):
                if "messages" in event:
                    for message in event["messages"]:
                        yield message.content
        
        except Exception as e:
            yield f"处理请求时出错：{str(e)}"
