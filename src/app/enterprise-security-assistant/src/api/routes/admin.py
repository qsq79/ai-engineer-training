"""
企业级安全智能助手 - 管理员接口

提供租户和用户管理的接口
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import time
import uuid

from ...utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["管理员"])


# 请求模型
class CreateTenantRequest(BaseModel):
    """创建租户请求模型"""
    name: str = Field(..., description="租户名称")
    description: Optional[str] = Field(None, description="描述")
    contact_email: Optional[str] = Field(None, description="联系邮箱")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置")


class CreateUserRequest(BaseModel):
    """创建用户请求模型"""
    tenant_id: str = Field(..., description="租户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    role: str = Field(default="user", description="角色（admin, user）")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置")


# 租户存储（临时使用内存存储，生产环境应使用数据库）
tenants: Dict[str, Dict[str, Any]] = {}

# 用户存储（临时使用内存存储，生产环境应使用数据库）
users: Dict[str, Dict[str, Any]] = {}


# 初始化默认租户和用户
if not tenants:
    default_tenant_id = str(uuid.uuid4())
    tenants[default_tenant_id] = {
        "tenant_id": default_tenant_id,
        "name": "默认租户",
        "description": "系统默认租户",
        "contact_email": "admin@example.com",
        "settings": {},
        "status": "active",
        "created_at": time.time(),
        "updated_at": time.time()
    }
    
    default_user_id = str(uuid.uuid4())
    users[default_user_id] = {
        "user_id": default_user_id,
        "tenant_id": default_tenant_id,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "settings": {},
        "status": "active",
        "created_at": time.time(),
        "updated_at": time.time()
    }


@router.post("/tenants/create", summary="创建租户")
async def create_tenant(request: CreateTenantRequest):
    """
    创建新租户
    
    - **name**: 租户名称
    - **description**: 描述（可选）
    - **contact_email**: 联系邮箱（可选）
    - **settings**: 配置（可选）
    """
    tenant_id = str(uuid.uuid4())
    
    try:
        logger.info(f"创建租户: tenant_id={tenant_id}, name={request.name}")
        
        tenant = {
            "tenant_id": tenant_id,
            "name": request.name,
            "description": request.description,
            "contact_email": request.contact_email,
            "settings": request.settings,
            "status": "active",
            "created_at": time.time(),
            "updated_at": time.time()
        }
        
        tenants[tenant_id] = tenant
        
        logger.info(f"租户创建成功: tenant_id={tenant_id}")
        
        return tenant
        
    except Exception as e:
        logger.error(f"创建租户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建租户失败: {str(e)}"
        )


@router.get("/tenants/{tenant_id}", summary="查询租户")
async def get_tenant(tenant_id: str):
    """
    查询租户详情
    
    - **tenant_id**: 租户ID
    """
    if tenant_id not in tenants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"租户不存在: {tenant_id}"
        )
    
    return tenants[tenant_id]


@router.get("/tenants", summary="租户列表")
async def list_tenants(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取租户列表
    
    - **status**: 状态（可选，用于过滤）
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    # 过滤租户
    filtered_tenants = []
    
    for tenant_id, tenant in tenants.items():
        # 应用过滤条件
        if status and tenant.get("status") != status:
            continue
        
        filtered_tenants.append(tenant)
    
    # 排序（按创建时间倒序）
    filtered_tenants.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    total = len(filtered_tenants)
    tenant_list = filtered_tenants[offset:offset + limit]
    
    return {
        "tenants": tenant_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/users/create", summary="创建用户")
async def create_user(request: CreateUserRequest):
    """
    创建新用户
    
    - **tenant_id**: 租户ID
    - **username**: 用户名
    - **email**: 邮箱
    - **role**: 角色（admin, user）
    - **settings**: 配置（可选）
    """
    user_id = str(uuid.uuid4())
    
    try:
        logger.info(f"创建用户: user_id={user_id}, username={request.username}, tenant_id={request.tenant_id}")
        
        # 验证租户是否存在
        if request.tenant_id not in tenants:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"租户不存在: {request.tenant_id}"
            )
        
        user = {
            "user_id": user_id,
            "tenant_id": request.tenant_id,
            "username": request.username,
            "email": request.email,
            "role": request.role,
            "settings": request.settings,
            "status": "active",
            "created_at": time.time(),
            "updated_at": time.time()
        }
        
        users[user_id] = user
        
        logger.info(f"用户创建成功: user_id={user_id}")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


@router.get("/users/{user_id}", summary="查询用户")
async def get_user(user_id: str):
    """
    查询用户详情
    
    - **user_id**: 用户ID
    """
    if user_id not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户不存在: {user_id}"
        )
    
    return users[user_id]


@router.get("/users", summary="用户列表")
async def list_users(
    tenant_id: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取用户列表
    
    - **tenant_id**: 租户ID（可选，用于过滤）
    - **role**: 角色（可选，用于过滤）
    - **status**: 状态（可选，用于过滤）
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    # 过滤用户
    filtered_users = []
    
    for user_id, user in users.items():
        # 应用过滤条件
        if tenant_id and user.get("tenant_id") != tenant_id:
            continue
        if role and user.get("role") != role:
            continue
        if status and user.get("status") != status:
            continue
        
        filtered_users.append(user)
    
    # 排序（按创建时间倒序）
    filtered_users.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 分页
    total = len(filtered_users)
    user_list = filtered_users[offset:offset + limit]
    
    return {
        "users": user_list,
        "total": total,
        "limit": limit,
        "offset": offset
    }
