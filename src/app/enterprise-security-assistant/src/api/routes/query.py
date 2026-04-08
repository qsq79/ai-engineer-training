"""
企业级安全智能助手 - 统一查询接口

提供统一的查询接口，支持多种查询类型
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field

from ...agents.intent_agent import IntentAgent, IntentType
from ...agents.log_query_agent import LogQueryAgent
from ...agents.scoring_agent import ScoringAgent
from ...agents.threat_analysis_agent import ThreatAnalysisAgent
from ...database import db_manager, redis_manager
from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="", tags=["查询"])


# 请求模型
class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="用户查询文本", min_length=1)
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


# 响应模型
class QueryResponse(BaseModel):
    """查询响应模型"""
    intent: str = Field(..., description="识别的意图类型")
    result: Dict[str, Any] = Field(..., description="查询结果")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    suggested_followup: List[str] = Field(default_factory=list, description="建议的后续查询")


# Agent实例（延迟初始化，在实际使用时创建）
def get_agents():
    """获取Agent实例"""
    from ...database.db_pool import db_manager
    intent_agent = IntentAgent()
    from ...agents.log_query_agent import get_log_query_agent
    from ...agents.scoring_agent import get_scoring_agent
    from ...agents.threat_analysis_agent import get_threat_analysis_agent
    log_query_agent = get_log_query_agent(db_manager)
    scoring_agent = get_scoring_agent(db_manager)
    threat_agent = get_threat_analysis_agent(db_manager)
    return {
        "intent_agent": intent_agent,
        "log_query_agent": log_query_agent,
        "scoring_agent": scoring_agent,
        "threat_agent": threat_agent
    }

# 全局Agent实例（懒加载）
_agents = None
def _get_intent_agent():
    global _agents
    if _agents is None:
        _agents = get_agents()
    return _agents["intent_agent"]


@router.post("/query", response_model=QueryResponse, summary="统一查询接口")
async def unified_query(
    request: Request,
    query_req: QueryRequest,
):
    """
    统一查询接口
    
    自动识别用户意图，调用相应的Agent进行处理，并返回结果。
    
    - **query**: 用户查询文本
    - **tenant_id**: 租户ID
    - **user_id**: 用户ID
    - **session_id**: 会话ID（可选）
    - **context**: 上下文信息（可选）
    """
    try:
        logger.info(f"收到查询请求: query={query_req.query}, tenant_id={query_req.tenant_id}, user_id={query_req.user_id}")
        
        # 步骤1：意图识别
        intent_result = await _get_intent_agent().recognize_intent(
            query=query_req.query,
            tenant_id=query_req.tenant_id,
            user_id=query_req.user_id,
            session_id=query_req.session_id
        )
        
        logger.info(f"意图识别结果: {intent_result}")
        
        # 步骤2：根据意图调用相应的Agent
        result = {}
        confidence = intent_result.get("confidence", 0.0)
        
        if intent_result["intent"] == IntentType.QUERY_DIFF:
            # 日志查询差异
            result = await log_query_agent.query_diff(
                query=query_req.query,
                tenant_id=query_req.tenant_id,
                user_id=query_req.user_id,
                session_id=query_req.session_id,
                parameters=intent_result.get("parameters", {})
            )
            
        elif intent_result["intent"] == IntentType.SCORING_EXPLANATION:
            # 评分解读
            result = await scoring_agent.explain_score(
                query=query_req.query,
                tenant_id=query_req.tenant_id,
                user_id=query_req.user_id,
                session_id=query_req.session_id,
                parameters=intent_result.get("parameters", {})
            )
            
        elif intent_result["intent"] == IntentType.THREAT_ANALYSIS:
            # 威胁分析
            result = await threat_agent.analyze_threat(
                query=query_req.query,
                tenant_id=query_req.tenant_id,
                user_id=query_req.user_id,
                session_id=query_req.session_id,
                parameters=intent_result.get("parameters", {})
            )
            
        elif intent_result["intent"] == IntentType.COMPLIANCE_CHECK:
            # 合规检查
            result = {
                "message": "合规检查功能正在开发中",
                "status": "in_development"
            }
            
        elif intent_result["intent"] == IntentType.KNOWLEDGE_SEARCH:
            # 知识检索
            result = {
                "message": "知识检索功能正在开发中",
                "status": "in_development"
            }
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"未知意图类型: {intent_result['intent']}"
            )
        
        # 步骤3：生成响应
        response = QueryResponse(
            intent=intent_result["intent"],
            result=result,
            confidence=confidence,
            suggested_followup=intent_result.get("suggested_followup", [])
        )
        
        logger.info(f"查询处理完成: intent={intent_result['intent']}, confidence={confidence}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"统一查询处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询处理失败: {str(e)}"
        )
