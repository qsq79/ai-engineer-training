"""
企业级安全智能助手 - 认证中间件

实现JWT认证和用户身份验证，支持Token验证和用户信息提取
"""
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import json

from ...config.settings import settings
from ...utils.logger import logger


# JWT密钥和算法
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days


class AuthMiddleware:
    """认证中间件"""
    
    def __init__(self, app=None):
        """
        初始化认证中间件
        
        Args:
            app: FastAPI应用实例（可选，用于直接作为中间件使用）
        """
        self.app = app
        self.security = HTTPBearer(auto_error=False)
        self.token_blacklist = set()  # Token黑名单
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable,
    ):
        """
        中间件调用处理
        
        Args:
            request: FastAPI请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        # 跳过健康检查等公共端点
        public_paths = [
            "/health",
            "/api/v1/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            # API端点（开发模式无需认证）
            "/api/v1/query",
            "/api/v1/agents/list",
            "/api/v1/agents/execute",
            "/api/v1/workflows/list",
            "/api/v1/workflows/execute",
            "/api/v1/sessions",
            "/api/v1/compliance",
            "/api/v1/stats",
            "/api/v1/admin",
        ]
        
        # 检查是否是以API开头的路径（所有API都跳过认证）
        if request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # 跳过静态文件
        if request.url.path.startswith("/static"):
            return await call_next(request)
        
        # 跳过公共端点
        if request.url.path in public_paths:
            return await call_next(request)
        
        # 跳过OPTIONS请求（CORS预检）
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # 获取Authorization头部
            credentials: Optional[HTTPAuthorizationCredentials] = await self.security(request)
            
            if not credentials or not credentials.credentials:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未提供认证令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 验证Token
            token = credentials.credentials
            payload = self.verify_token(token)
            
            if payload:
                # 将用户信息添加到请求状态
                request.state.user_id = payload.get("user_id")
                request.state.tenant_id = payload.get("tenant_id")
                request.state.role = payload.get("role")
                request.state.permissions = payload.get("permissions", [])
                
                logger.debug(f"用户认证成功: user_id={payload.get('user_id')}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的认证令牌",
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"认证中间件错误: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="认证过程中发生错误",
            )
        
        return await call_next(request)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """
        验证JWT Token
        
        Args:
            token: JWT Token
            
        Returns:
            Token载荷（如果有效），否则返回None
        """
        # 检查Token黑名单
        if token in self.token_blacklist:
            logger.warning("尝试使用黑名单中的Token")
            return None
        
        try:
            # 解码Token
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
            
            # 检查Token过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token已过期")
                return None
            
            return payload
        
        except JWTError as e:
            logger.warning(f"JWT验证失败: {e}")
            return None
    
    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        permissions: list = None,
    ) -> str:
        """
        创建访问Token
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            role: 用户角色
            permissions: 用户权限列表
            
        Returns:
            JWT Token
        """
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "permissions": permissions or [],
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"创建访问Token: user_id={user_id}")
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
    ) -> str:
        """
        创建刷新Token
        
        Args:
            user_id: 用户ID
            
        Returns:
            JWT Token
        """
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"创建刷新Token: user_id={user_id}")
        return token
    
    def add_to_blacklist(self, token: str):
        """
        将Token添加到黑名单
        
        Args:
            token: 要黑名单的Token
        """
        self.token_blacklist.add(token)
        logger.debug(f"Token已添加到黑名单: {token[:10]}...")


# 全局认证中间件实例
auth_middleware = AuthMiddleware()


def get_current_user(request: Request):
    """
    获取当前用户信息（用于FastAPI依赖注入）
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        用户信息字典
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": request.state.user_id,
        "tenant_id": request.state.tenant_id,
        "role": request.state.role,
        "permissions": request.state.permissions,
    }


def check_permission(required_permission: str):
    """
    检查用户权限的装饰器工厂
    
    Args:
        required_permission: 需要的权限
        
    Returns:
        依赖函数
    """
    def permission_checker(request: Request):
        """权限检查器"""
        user = get_current_user(request)
        
        if "super_admin" in user["role"]:
            # 超级管理员拥有所有权限
            return user
        
        if required_permission not in user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要权限: {required_permission}",
            )
        
        return user
    
    return permission_checker
