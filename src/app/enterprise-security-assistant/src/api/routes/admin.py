"""
企业级安全智能助手 - 管理员接口

提供租户和用户管理的接口
"""
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from ...utils.logger import get_logger
from ...database.db_pool import get_db_session
from ...database.models import Tenant, User

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["管理员"])


# 请求模型
class CreateTenantRequest(BaseModel):
    """创建租户请求模型"""
    tenant_id: str = Field(..., description="租户ID")
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


class TenantResponse(BaseModel):
    """租户响应模型"""
    tenant_id: str
    tenant_name: str
    status: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    settings: Dict[str, Any] = {}
    created_at: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型"""
    user_id: str
    tenant_id: str
    username: str
    email: Optional[str] = None
    role: str
    permissions: List[str] = []
    is_active: bool = True
    created_at: Optional[str] = None


def tenant_to_dict(tenant: Tenant) -> Dict[str, Any]:
    """将租户对象转换为字典"""
    return {
        "tenant_id": tenant.tenant_id,
        "tenant_name": tenant.tenant_name,
        "status": tenant.status,
        "description": None,
        "contact_email": None,
        "settings": {},
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


def user_to_dict(user: User) -> Dict[str, Any]:
    """将用户对象转换为字典"""
    return {
        "user_id": user.user_id,
        "tenant_id": user.tenant_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions or [],
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/tenants/create", summary="创建租户")
async def create_tenant(request: CreateTenantRequest):
    """
    创建新租户
    """
    async with get_db_session() as session:
        try:
            # 检查租户ID是否已存在
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == request.tenant_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"租户ID已存在: {request.tenant_id}"
                )

            # 创建新租户
            tenant = Tenant(
                tenant_id=request.tenant_id,
                tenant_name=request.name,
                description=request.description,
                contact_email=request.contact_email,
                settings=request.settings,
                status="active",
            )
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)

            logger.info(f"租户创建成功: tenant_id={request.tenant_id}")
            return tenant_to_dict(tenant)

        except HTTPException:
            raise
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
    """
    async with get_db_session() as session:
        try:
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"租户不存在: {tenant_id}"
                )
            
            return tenant_to_dict(tenant)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"查询租户失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询租户失败: {str(e)}"
            )


@router.get("/tenants", summary="租户列表")
async def list_tenants(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取租户列表
    """
    async with get_db_session() as session:
        try:
            # 构建查询
            query = select(Tenant)
            count_query = select(func.count(Tenant.tenant_id))
            
            # 应用过滤条件
            if status:
                query = query.where(Tenant.status == status)
                count_query = count_query.where(Tenant.status == status)
            
            # 排序（按创建时间倒序）
            query = query.order_by(Tenant.created_at.desc())
            
            # 分页
            query = query.offset(offset).limit(limit)
            
            # 执行查询
            result = await session.execute(query)
            tenants = result.scalars().all()
            
            # 获取总数
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            return {
                "tenants": [tenant_to_dict(t) for t in tenants],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询租户列表失败: {str(e)}"
            )


@router.post("/users/create", summary="创建用户")
async def create_user(request: CreateUserRequest):
    """
    创建新用户
    """
    async with get_db_session() as session:
        try:
            # 检查租户是否存在
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == request.tenant_id)
            )
            tenant = result.scalar_one_or_none()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"租户不存在: {request.tenant_id}"
                )

            # 生成用户ID
            user_id = f"U{uuid.uuid4().hex[:6].upper()}"

            # 根据角色设置权限
            role_permissions = {
                "super_admin": ["query", "analyze", "config", "manage", "audit"],
                "security_manager": ["query", "analyze", "manage", "audit"],
                "security_analyst": ["query", "analyze"],
                "read_only": ["query"],
                "user": ["query"],
            }
            permissions = role_permissions.get(request.role, ["query"])

            # 创建用户
            user = User(
                user_id=user_id,
                tenant_id=request.tenant_id,
                username=request.username,
                email=request.email,
                role=request.role,
                permissions=permissions,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            logger.info(f"用户创建成功: user_id={user_id}, username={request.username}")
            return user_to_dict(user)

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
    """
    async with get_db_session() as session:
        try:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"用户不存在: {user_id}"
                )
            
            return user_to_dict(user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"查询用户失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询用户失败: {str(e)}"
            )


@router.get("/users", summary="用户列表")
async def list_users(
    tenant_id: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    获取用户列表
    """
    async with get_db_session() as session:
        try:
            # 构建查询
            query = select(User)
            count_query = select(func.count(User.user_id))
            
            # 应用过滤条件
            if tenant_id:
                query = query.where(User.tenant_id == tenant_id)
                count_query = count_query.where(User.tenant_id == tenant_id)
            if role:
                query = query.where(User.role == role)
                count_query = count_query.where(User.role == role)
            if is_active is not None:
                query = query.where(User.is_active == is_active)
                count_query = count_query.where(User.is_active == is_active)
            
            # 排序（按创建时间倒序）
            query = query.order_by(User.created_at.desc())
            
            # 分页
            query = query.offset(offset).limit(limit)
            
            # 执行查询
            result = await session.execute(query)
            users = result.scalars().all()
            
            # 获取总数
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            return {
                "users": [user_to_dict(u) for u in users],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"查询用户列表失败: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"查询用户列表失败: {str(e)}"
            )
