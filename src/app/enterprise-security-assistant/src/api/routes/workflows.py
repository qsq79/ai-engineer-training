"""
企业级安全智能助手 - 工作流相关接口

提供工作流执行和管理的接口
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.workflow_agent import WorkflowExecutor
from ...database.db_pool import get_db_session
from ...utils.logger import get_logger
import time
import uuid

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["工作流"])


# 请求模型
class WorkflowExecuteRequest(BaseModel):
    """工作流执行请求模型"""
    workflow_config: Dict[str, Any] = Field(..., description="工作流配置")
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="参数")


class WorkflowExecuteResponse(BaseModel):
    """工作流执行响应模型"""
    workflow_id: str = Field(..., description="工作流ID")
    status: str = Field(..., description="状态")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    execution_time: float = Field(..., description="执行时间（秒）")
    message: str = Field(..., description="消息")


# 工作流实例（懒加载）
def get_workflow():
    """获取工作流实例"""
    from ...agents.workflow_agent import get_workflow_executor
    from ...database.db_pool import db_manager
    return get_workflow_executor(db_manager)


# 存储工作流执行记录（临时使用内存存储，生产环境应使用数据库）
workflow_executions: Dict[str, Dict[str, Any]] = {}


@router.post("/execute", response_model=WorkflowExecuteResponse, summary="执行工作流")
async def execute_workflow(request: WorkflowExecuteRequest):
    """
    执行工作流
    
    - **workflow_config**: 工作流配置（包含任务列表、依赖关系等）
    - **tenant_id**: 租户ID
    - **user_id**: 用户ID
    - **session_id**: 会话ID（可选）
    - **parameters**: 参数（可选）
    """
    start_time = time.time()
    workflow_id = str(uuid.uuid4())
    
    try:
        logger.info(f"执行工作流: workflow_id={workflow_id}, tenant_id={request.tenant_id}, user_id={request.user_id}")
        
        # 执行工作流
        result = await workflow_agent.execute_workflow(
            workflow_config=request.workflow_config,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            session_id=request.session_id,
            parameters=request.parameters
        )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 存储执行记录
        workflow_executions[workflow_id] = {
            "workflow_id": workflow_id,
            "status": result.get("status", "completed"),
            "result": result,
            "execution_time": execution_time,
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "created_at": time.time()
        }
        
        logger.info(f"工作流执行完成: workflow_id={workflow_id}, status={result.get('status')}, execution_time={execution_time:.2f}s")
        
        return WorkflowExecuteResponse(
            workflow_id=workflow_id,
            status=result.get("status", "completed"),
            result=result,
            execution_time=execution_time,
            message="工作流执行成功"
        )
        
    except Exception as e:
        logger.error(f"工作流执行失败: workflow_id={workflow_id}, error={e}", exc_info=True)
        
        # 存储失败记录
        workflow_executions[workflow_id] = {
            "workflow_id": workflow_id,
            "status": "failed",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "created_at": time.time()
        }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"工作流执行失败: {str(e)}"
        )


@router.get("/{workflow_id}", summary="查询工作流状态")
async def get_workflow_status(workflow_id: str):
    """
    查询工作流执行状态
    
    - **workflow_id**: 工作流ID
    """
    if workflow_id not in workflow_executions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作流不存在: {workflow_id}"
        )
    
    execution = workflow_executions[workflow_id]
    
    return {
        "workflow_id": workflow_id,
        "status": execution["status"],
        "result": execution.get("result"),
        "execution_time": execution["execution_time"],
        "created_at": execution["created_at"]
    }


@router.get("/list", summary="工作流列表")
async def list_workflows(
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取工作流列表
    
    - **tenant_id**: 租户ID（可选，用于过滤）
    - **user_id**: 用户ID（可选，用于过滤）
    - **status**: 状态（可选，用于过滤）
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    # 过滤工作流
    filtered_workflows = []
    
    for workflow_id, execution in workflow_executions.items():
        # 应用过滤条件
        if tenant_id and execution.get("tenant_id") != tenant_id:
            continue
        if user_id and execution.get("user_id") != user_id:
            continue
        if status and execution.get("status") != status:
            continue
        
        filtered_workflows.append({
            "workflow_id": workflow_id,
            "status": execution["status"],
            "execution_time": execution["execution_time"],
            "created_at": execution["created_at"]
        })
    
    # 排序（按创建时间倒序）
    filtered_workflows.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    total = len(filtered_workflows)
    workflows = filtered_workflows[offset:offset + limit]
    
    return {
        "workflows": workflows,
        "total": total,
        "limit": limit,
        "offset": offset
    }
