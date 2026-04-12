"""
企业级安全智能助手 - 意图识别Agent

理解用户自然语言查询，识别意图类型，提取关键参数，路由到合适的业务Agent
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import BaseOutputParser

from ..config.settings import settings
from ..database.models import Session, AgentCall
from ..database.db_pool import get_db_session
from ..utils.logger import get_logger

logger = get_logger(__name__)


# 意图类型定义
class IntentType:
    """意图类型枚举"""
    QUERY_DIFF = "query_diff"                # 日志查询差异
    SCORING_EXPLANATION = "scoring_explanation"  # 评分解读
    THREAT_ANALYSIS = "threat_analysis"      # 威胁分析
    COMPLIANCE_CHECK = "compliance_check"      # 合规检查
    KNOWLEDGE_SEARCH = "knowledge_search"      # 知识检索


# 意图分类体系
INTENT_CLASSIFICATION = {
    IntentType.QUERY_DIFF: {
        "keywords": ["为什么", "对不上", "不一致", "差异", "不一样"],
        "description": "查询结果和月报数据的差异",
        "target_agent": "QueryAgent",
        "params": ["report_id", "metric_name"],
    },
    IntentType.SCORING_EXPLANATION: {
        "keywords": ["评分", "分", "怎么算", "为什么"],
        "description": "解读安全评分，解释评分逻辑",
        "target_agent": "ScoringAgent",
        "params": ["score"],
    },
    IntentType.THREAT_ANALYSIS: {
        "keywords": ["威胁", "攻击", "恶意", "漏洞"],
        "description": "分析威胁情报，识别潜在威胁",
        "target_agent": "ThreatAgent",
        "params": ["time_range", "threat_type"],
    },
    IntentType.COMPLIANCE_CHECK: {
        "keywords": ["合规", "检查", "审计", "GDPR", "等保"],
        "description": "执行合规检查，生成合规报告",
        "target_agent": "ComplianceAgent",
        "params": ["compliance_type", "scope"],
    },
    IntentType.KNOWLEDGE_SEARCH: {
        "keywords": ["如何", "怎么", "什么是", "最佳实践"],
        "description": "检索知识库，提供知识推荐",
        "target_agent": "KnowledgeAgent",
        "params": ["query"],
    },
}


@dataclass
class IntentRecognitionResult:
    """意图识别结果"""
    intent_type: str                       # 意图类型
    target_agent: str                       # 目标Agent名称
    confidence: float                         # 置信度（0-1）
    params: Dict[str, Any]                   # 提取的参数
    reasoning: str                           # 识别推理过程
    timestamp: datetime                        # 识别时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "intent_type": self.intent_type,
            "target_agent": self.target_agent,
            "confidence": self.confidence,
            "params": self.params,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


class IntentAgent:
    """意图识别Agent"""
    
    def __init__(self):
        """初始化意图识别Agent"""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=settings.openai_temperature,
            max_tokens=settings.openai_max_tokens,
            api_key=settings.openai_api_key,
        )
        
        # 创建意图分类Prompt模板
        self.intent_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个企业级安全智能助手的意图识别助手。你的任务是理解用户的自然语言查询，识别意图类型并提取关键参数。\n\n"
                "支持的意图类型：\n"
                "1. query_diff（查询差异）：用户发现查询结果和月报数据不一致\n"
                "   关键词：为什么、对不上、不一致、差异、不一样\n"
                "   参数：report_id（月报ID）、metric_name（指标名称）\n\n"
                "2. scoring_explanation（评分解读）：用户希望了解安全评分的计算逻辑和明细\n"
                "   关键词：评分、分、怎么算、为什么\n"
                "   参数：score（评分值）\n\n"
                "3. threat_analysis（威胁分析）：用户希望分析某个威胁或攻击\n"
                "   关键词：威胁、攻击、恶意、漏洞\n"
                "   参数：time_range（时间范围）、threat_type（威胁类型）\n\n"
                "4. compliance_check（合规检查）：用户希望执行合规检查\n"
                "   关键词：合规、检查、审计、GDPR、等保\n"
                "   参数：compliance_type（合规类型）、scope（检查范围）\n\n"
                "5. knowledge_search（知识检索）：用户希望查询某个安全概念或最佳实践\n"
                "   关键词：如何、怎么、什么是、最佳实践\n"
                "   参数：query（查询问题）\n\n"
                "识别规则：\n"
                "1. 首先通过关键词匹配进行初步判断\n"
                "2. 然后使用LLM进行语义理解和验证\n"
                "3. 提供置信度（0-1），高置信度表示更确定的判断\n"
                "4. 提取请求中的关键参数\n"
                "5. 给出详细的识别推理过程\n\n"
                "输出格式（JSON）：\n"
                "```json\n"
                "{{\n"
                "  \"intent_type\": \"意图类型\",\n"
                "  \"target_agent\": \"目标Agent名称\",\n"
                "  \"confidence\": 0.0-1.0,\n"
                "  \"params\": {{参数字典}},\n"
                "  \"reasoning\": \"识别推理过程\"\n"
                "}}\n"
                "```\n"
            ),
            ("human", "{query}"),
        ])
    
    async def preprocess(self, query: str, session_id: Optional[str] = None) -> str:
        """
        预处理查询
        
        Args:
            query: 用户查询
            session_id: 会话ID（用于获取上下文）
            
        Returns:
            预处理后的查询
        """
        # 文本清洗
        cleaned_query = query.strip()
        
        # 补充上下文（如果有）
        if session_id:
            context = await self._get_session_context(session_id)
            if context:
                cleaned_query = f"上下文: {json.dumps(context, ensure_ascii=False)}\n\n用户查询: {cleaned_query}"
                logger.debug(f"已补充会话上下文，session_id={session_id}")
        
        return cleaned_query
    
    async def _get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话上下文
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话上下文（如果存在）
        """
        # 简化处理：直接返回None，不尝试数据库查询
        # 在没有实际数据库的情况下，避免SQL错误
        logger.warning(f"获取会话上下文被跳过（session_id={session_id}）- 数据库未配置")
        return None
    
    async def _classify_by_keywords(self, query: str) -> Optional[Dict[str, Any]]:
        """
        通过关键词匹配进行初步意图分类
        
        Args:
            query: 用户查询
            
        Returns:
            匹配的意图类型（如果找到）
        """
        query_lower = query.lower()
        
        for intent_type, intent_config in INTENT_CLASSIFICATION.items():
            keywords = intent_config["keywords"]
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    logger.debug(f"关键词匹配: '{keyword}' -> {intent_type}")
                    # 返回完整信息，包含 intent_type
                    return {**intent_config, "intent_type": intent_type}
        
        return None
    
    async def _classify_by_llm(self, query: str, context: Optional[Dict[str, Any]] = None) -> IntentRecognitionResult:
        """
        使用LLM进行语义理解
        
        Args:
            query: 用户查询
            context: 会话上下文
            
        Returns:
            意图识别结果
        """
        try:
            # 构建Prompt
            messages = self.intent_prompt.format_messages(query=query)
            
            # 调用LLM
            response = await self.llm.ainvoke(messages)
            response_text = response.content.strip()
            
            # 解析JSON响应
            try:
                result_dict = json.loads(response_text)
                
                # 验证结果格式
                if not all(k in result_dict for k in ["intent_type", "target_agent", "confidence", "params", "reasoning"]):
                    logger.warning(f"LLM返回格式不正确: {result_dict}")
                    return self._fallback_classification(query)
                
                # 验证意图类型
                # 获取IntentType的所有字符串常量值
                intent_type_values = [v for k, v in IntentType.__dict__.items() if not k.startswith("_") and isinstance(v, str)]
                if result_dict["intent_type"] not in intent_type_values:
                    logger.warning(f"LLM返回了未知的意图类型: {result_dict['intent_type']}")
                    return self._fallback_classification(query)
                
                # 构建结果
                result = IntentRecognitionResult(
                    intent_type=result_dict["intent_type"],
                    target_agent=result_dict["target_agent"],
                    confidence=min(1.0, max(0.0, float(result_dict.get("confidence", 0.9)))),
                    params=result_dict.get("params", {}),
                    reasoning=result_dict.get("reasoning", ""),
                    timestamp=datetime.utcnow(),
                )
                
                logger.debug(f"LLM分类成功: {result.to_dict()}")
                return result
            
            except json.JSONDecodeError as e:
                logger.error(f"LLM响应JSON解析失败: {e}")
                return self._fallback_classification(query)
        
        except Exception as e:
            logger.error(f"LLM分类失败: {e}")
            return self._fallback_classification(query)
    
    def _fallback_classification(self, query: str) -> IntentRecognitionResult:
        """
        降级分类（基于规则）
        
        Args:
            query: 用户查询
            
        Returns:
            意图识别结果
        """
        # 简单的关键词匹配
        query_lower = query.lower()
        
        for intent_type, intent_config in INTENT_CLASSIFICATION.items():
            keywords = intent_config["keywords"]
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    return IntentRecognitionResult(
                        intent_type=intent_type,
                        target_agent=intent_config["target_agent"],
                        confidence=0.8,  # 降级分类的置信度较低
                        params={},
                        reasoning=f"通过关键词'{keyword}'匹配到{intent_config['description']}",
                        timestamp=datetime.utcnow(),
                    )
        
        # 默认归类为知识检索
        logger.warning(f"未匹配到任何意图，默认归类为知识检索")
        return IntentRecognitionResult(
            intent_type=IntentType.KNOWLEDGE_SEARCH,
            target_agent="KnowledgeAgent",
            confidence=0.5,
            params={"query": query},
            reasoning="未匹配到特定意图，归类为知识检索",
            timestamp=datetime.utcnow(),
        )
    
    async def recognize_intent(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> IntentRecognitionResult:
        """
        识别意图
        
        Args:
            query: 用户查询
            user_id: 用户ID
            session_id: 会话ID
            tenant_id: 租户ID
            
        Returns:
            意图识别结果
        """
        logger.info(f"开始意图识别: query='{query}', user_id={user_id}, session_id={session_id}")
        
        try:
            # 1. 预处理查询
            processed_query = await self.preprocess(query, session_id)
            
            # 2. 获取上下文
            context = await self._get_session_context(session_id)
            
            # 3. 关键词匹配（快速路径）
            keyword_match = await self._classify_by_keywords(processed_query)
            if keyword_match:
                result = IntentRecognitionResult(
                    intent_type=keyword_match["intent_type"],
                    target_agent=keyword_match["target_agent"],
                    confidence=0.9,
                    params={},
                    reasoning=f"通过关键词匹配到{keyword_match['description']}",
                    timestamp=datetime.utcnow(),
                )
                logger.info(f"关键词匹配成功: {result.to_dict()}")
                return result
            
            # 4. LLM语义理解（精准路径）
            result = await self._classify_by_llm(processed_query, context)
            
            # 5. 记录调用日志（暂时跳过，因为数据库未配置）
            # await self._log_agent_call(
            #     user_id=user_id,
            #     tenant_id=tenant_id,
            #     agent_name="IntentAgent",
            #     intent=result.intent_type,
            #     status="success",
            #     input_params={"query": query, "context": context},
            #     output_result=result.to_dict(),
            #     duration_ms=0,
            # )
            
            logger.info(f"意图识别成功: {result.to_dict()}")
            return result
        
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            
            # 记录失败调用
            await self._log_agent_call(
                user_id=user_id,
                tenant_id=tenant_id,
                agent_name="IntentAgent",
                intent="unknown",
                status="failed",
                input_params={"query": query},
                output_result={"error": str(e)},
                duration_ms=0,
            )
            
            # 返回降级结果
            return self._fallback_classification(query)
    
    async def _log_agent_call(
        self,
        user_id: Optional[str],
        tenant_id: Optional[str],
        agent_name: str,
        intent: str,
        status: str,
        input_params: Optional[Dict[str, Any]] = None,
        output_result: Optional[Dict[str, Any]] = None,
        duration_ms: int = 0,
    ):
        """
        记录Agent调用日志
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            agent_name: Agent名称
            intent: 意图类型
            status: 状态
            input_params: 输入参数
            output_result: 输出结果
            duration_ms: 处理时长（毫秒）
        """
        from ..database.db_pool import db_manager
        import uuid
        async with db_manager.get_session() as session:
            call = AgentCall(
                call_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                agent_name=agent_name,
                intent=intent,
                status=status,
                input_params=input_params or {},
                output_result=output_result or {},
                duration_ms=duration_ms,
            )
            
            session.add(call)
            await session.commit()
            
            logger.debug(f"Agent调用日志已记录: {agent_name} - {status}")


# 全局意图识别Agent实例
intent_agent = IntentAgent()


async def recognize_intent_with_context(
    query: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> IntentRecognitionResult:
    """
    识别意图（带上下文）
    
    Args:
        query: 用户查询
        user_id: 用户ID
        session_id: 会话ID
        tenant_id: 租户ID
        
    Returns:
        意图识别结果
    """
    return await intent_agent.recognize_intent(
        query=query,
        user_id=user_id,
        session_id=session_id,
        tenant_id=tenant_id,
    )
