"""
企业级安全智能助手 - 会话管理接口

提供会话创建、查询和删除的接口
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import time
import uuid

from ...database.db_pool import get_db_session
from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["会话管理"])


# 请求模型
class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")


class UpdateSessionRequest(BaseModel):
    """更新会话请求模型"""
    title: Optional[str] = Field(None, description="会话标题")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


# 会话存储（临时使用内存存储，生产环境应使用数据库）
sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/create", summary="创建会话")
async def create_session(request: CreateSessionRequest):
    """
    创建新会话
    
    - **tenant_id**: 租户ID
    - **user_id**: 用户ID
    - **title**: 会话标题（可选）
    - **context**: 上下文信息（可选）
    """
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"创建会话: session_id={session_id}, tenant_id={request.tenant_id}, user_id={request.user_id}")
        
        session = {
            "session_id": session_id,
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "title": request.title or f"会话 {len(sessions) + 1}",
            "context": request.context,
            "created_at": time.time(),
            "updated_at": time.time(),
            "message_count": 0
        }
        
        sessions[session_id] = session
        
        logger.info(f"会话创建成功: session_id={session_id}")
        
        return session
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )


@router.get("/{session_id}", summary="查询会话")
async def get_session(session_id: str):
    """
    查询会话详情
    
    - **session_id**: 会话ID
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在: {session_id}"
        )
    
    return sessions[session_id]


@router.put("/{session_id}", summary="更新会话")
async def update_session(session_id: str, request: UpdateSessionRequest):
    """
    更新会话信息
    
    - **session_id**: 会话ID
    - **title**: 会话标题（可选）
    - **context**: 上下文信息（可选）
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在: {session_id}"
        )
    
    try:
        logger.info(f"更新会话: session_id={session_id}")
        
        session = sessions[session_id]
        
        # 更新字段
        if request.title is not None:
            session["title"] = request.title
        if request.context is not None:
            session["context"].update(request.context)
        
        session["updated_at"] = time.time()
        
        logger.info(f"会话更新成功: session_id={session_id}")
        
        return session
        
    except Exception as e:
        logger.error(f"更新会话失败: session_id={session_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新会话失败: {str(e)}"
        )


@router.delete("/{session_id}", summary="删除会话")
async def delete_session(session_id: str):
    """
    删除会话
    
    - **session_id**: 会话ID
    """
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在: {session_id}"
        )
    
    try:
        logger.info(f"删除会话: session_id={session_id}")
        
        del sessions[session_id]
        
        logger.info(f"会话删除成功: session_id={session_id}")
        
        return {
            "message": "会话删除成功",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"删除会话失败: session_id={session_id}, error={e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除会话失败: {str(e)}"
        )


@router.get("/list", summary="会话列表")
async def list_sessions(
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取会话列表
    
    - **tenant_id**: 租户ID（可选，用于过滤）
    - **user_id**: 用户ID（可选，用于过滤）
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    # 过滤会话
    filtered_sessions = []
    
    for session_id, session in sessions.items():
        # 应用过滤条件
        if tenant_id and session.get("tenant_id") != tenant_id:
            continue
        if user_id and session.get("user_id") != user_id:
            continue
        
        filtered_sessions.append(session)
    
    # 排序（按更新时间倒序）
    filtered_sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    
    # 分页
    total = len(filtered_sessions)
    session_list = filtered_sessions[offset:offset + limit]
    
    return {
        "sessions": session_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }
