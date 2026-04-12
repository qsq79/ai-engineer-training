"""
企业级安全智能助手 - 认证路由

提供用户登录、注册、Token刷新、登出等认证相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional

from ...services.auth_service import AuthService
from ...api.middleware.auth import get_current_user
from ...config.settings import settings

# 创建路由
router = APIRouter()


# ========== 请求/响应模型 ==========

class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    email: Optional[str] = Field(None, description="邮箱")
    tenant_id: str = Field(..., description="租户ID")
    role: str = Field(default="security_analyst", description="用户角色")


class LoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    tenant_id: Optional[str] = Field(None, description="租户ID")


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field(..., description="角色")
    tenant_id: str = Field(..., description="租户ID")
    permissions: list = Field(default_factory=list, description="权限列表")
    is_active: bool = Field(..., description="是否激活")


class MessageResponse(BaseModel):
    """消息响应"""
    message: str = Field(..., description="消息")


class RegisterResponse(BaseModel):
    """注册响应"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")


# ========== API端点 ==========

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    用户注册接口
    
    新用户可以通过提供用户名、密码、邮箱等信息进行注册
    """
    # 验证密码最小长度
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码长度至少为6位",
        )
    
    try:
        # 创建用户
        user_info = await AuthService.create_user(
            username=request.username,
            password=request.password,
            tenant_id=request.tenant_id,
            email=request.email,
            role=request.role,
        )
        
        return RegisterResponse(
            user_id=user_info["user_id"],
            username=user_info["username"],
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}",
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    用户登录接口
    
    用户可通过用户名和密码进行身份认证，获取访问令牌
    """
    # 使用数据库进行用户认证（生产环境）
    user_info = await AuthService.authenticate_user(
        username=request.username,
        password=request.password,
        tenant_id=request.tenant_id,
    )
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建Token
    access_token = AuthService.create_access_token(user_info)
    refresh_token = AuthService.create_refresh_token(user_info["user_id"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新Token接口
    
    用户可使用refresh_token获取新的访问令牌
    """
    # 验证刷新令牌
    new_access_token = await AuthService.refresh_access_token(request.refresh_token)
    
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request):
    """
    用户登出接口
    
    用户可使当前访问令牌失效
    """
    # 从请求中获取Token并加入黑名单
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # 这里可以调用auth_middleware.add_to_blacklist(token)来加入黑名单
        # 目前使用内存黑名单
        from ..middleware.auth import auth_middleware
        auth_middleware.add_to_blacklist(token)
    
    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息接口
    
    返回当前登录用户的信息
    """
    return UserInfoResponse(
        user_id=current_user["user_id"],
        username="",  # 从Token中提取
        email="",  # 从Token中提取
        role=current_user["role"],
        tenant_id=current_user["tenant_id"],
        permissions=current_user.get("permissions", []),
        is_active=True,
    )