"""
企业级安全智能助手 - Agent相关接口

提供Agent执行和管理的接口
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ...agents.intent_agent import IntentAgent
from ...agents.log_query_agent import LogQueryAgent
from ...agents.scoring_agent import ScoringAgent
from ...agents.threat_analysis_agent import ThreatAnalysisAgent
from ...agents.workflow_agent import WorkflowExecutor
from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agents"])


# 请求模型
class AgentExecuteRequest(BaseModel):
    """Agent执行请求模型"""
    query: str = Field(..., description="查询文本", min_length=1)
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="参数")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


class AgentExecuteResponse(BaseModel):
    """Agent执行响应模型"""
    agent_name: str = Field(..., description="Agent名称")
    result: Dict[str, Any] = Field(..., description="执行结果")
    execution_time: float = Field(..., description="执行时间（秒）")
    token_usage: Optional[Dict[str, int]] = Field(default_factory=dict, description="Token使用统计")


# Agent列表
AGENTS = {
    "intent_agent": {
        "name": "IntentAgent",
        "description": "意图识别Agent，识别用户查询意图",
        "capabilities": ["意图识别", "参数提取", "置信度计算"]
    },
    "log_query_agent": {
        "name": "LogQueryAgent",
        "description": "日志查询Agent，查询和分析日志数据",
        "capabilities": ["日志查询", "差异分析", "SQL生成"]
    },
    "scoring_agent": {
        "name": "ScoringAgent",
        "description": "评分解读Agent，解释安全评分",
        "capabilities": ["评分解读", "明细展示", "改进建议"]
    },
    "threat_agent": {
        "name": "ThreatAgent",
        "description": "威胁分析Agent，分析威胁情报",
        "capabilities": ["威胁分析", "攻击图", "MITRE ATT&CK"]
    },
    "workflow_agent": {
        "name": "WorkflowAgent",
        "description": "工作流协调Agent，协调多Agent协作",
        "capabilities": ["工作流执行", "任务调度", "结果聚合"]
    }
}


# Agent工厂函数（懒加载）
def get_agent(agent_name: str):
    """获取Agent实例"""
    from ...database.db_pool import db_manager
    
    if agent_name == "intent_agent":
        return IntentAgent()
    elif agent_name == "log_query_agent":
        from ...agents.log_query_agent import get_log_query_agent
        return get_log_query_agent(db_manager)
    elif agent_name == "scoring_agent":
        from ...agents.scoring_agent import get_scoring_agent
        return get_scoring_agent(db_manager)
    elif agent_name == "threat_agent":
        from ...agents.threat_analysis_agent import get_threat_analysis_agent
        return get_threat_analysis_agent(db_manager)
    elif agent_name == "workflow_agent":
        from ...agents.workflow_agent import get_workflow_executor
        return get_workflow_executor(db_manager)
    return None


@router.get("/list", summary="Agent列表")
async def list_agents():
    """
    获取所有可用的Agent列表
    
    返回所有可用的Agent及其描述和能力
    """
    return {
        "agents": AGENTS,
        "total": len(AGENTS)
    }


@router.post("/{agent_name}/execute", response_model=AgentExecuteResponse, summary="执行Agent")
async def execute_agent(
    agent_name: str,
    request: AgentExecuteRequest,
):
    """
    执行指定的Agent
    
    - **agent_name**: Agent名称（intent_agent, log_query_agent, scoring_agent, threat_agent, workflow_agent）
    - **query**: 查询文本
    - **tenant_id**: 租户ID
    - **user_id**: 用户ID
    - **session_id**: 会话ID（可选）
    - **parameters**: 参数（可选）
    - **context**: 上下文信息（可选）
    """
    import time
    import uuid
    
    # 验证Agent是否存在
    if agent_name not in AGENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent不存在: {agent_name}"
        )
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        logger.info(f"执行Agent: {agent_name}, query={request.query}")
        
        # 获取Agent实例
        agent = agents[agent_name]
        
        # 执行Agent
        if agent_name == "intent_agent":
            result = await agent.recognize_intent(
                query=request.query,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                context=request.context
            )
        elif agent_name == "log_query_agent":
            result = await agent.query_diff(
                query=request.query,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                parameters=request.parameters
            )
        elif agent_name == "scoring_agent":
            result = await agent.explain_score(
                query=request.query,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                parameters=request.parameters
            )
        elif agent_name == "threat_agent":
            result = await agent.analyze_threat(
                query=request.query,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                parameters=request.parameters
            )
        elif agent_name == "workflow_agent":
            result = await agent.execute_workflow(
                workflow_config=request.parameters.get("workflow_config", {}),
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id
            )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 模拟Token使用统计
        token_usage = {
            "prompt_tokens": len(request.query.split()) * 10,
            "completion_tokens": len(str(result).split()) * 5,
            "total_tokens": len(request.query.split()) * 10 + len(str(result).split()) * 5
        }
        
        logger.info(f"Agent执行完成: {agent_name}, execution_time={execution_time:.2f}s")
        
        return AgentExecuteResponse(
            agent_name=AGENTS[agent_name]["name"],
            result=result,
            execution_time=execution_time,
            token_usage=token_usage
        )
        
    except Exception as e:
        logger.error(f"Agent执行失败: {agent_name}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent执行失败: {str(e)}"
        )


@router.get("/{agent_name}", summary="获取Agent信息")
async def get_agent_info(agent_name: str):
    """
    获取指定Agent的详细信息
    
    - **agent_name**: Agent名称
    """
    if agent_name not in AGENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent不存在: {agent_name}"
        )
    
    return {
        "agent_name": agent_name,
        "info": AGENTS[agent_name]
    }
