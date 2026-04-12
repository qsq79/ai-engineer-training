"""
企业级安全智能助手 - 认证服务

提供用户注册、登录、Token管理等认证相关业务逻辑
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt, ExpiredSignatureError

from ..config.settings import settings
from ..database.models import User, Tenant
from ..database.db_pool import get_db_session
from ..utils.logger import logger

# bcrypt工作因子
BCRYPT_ROUNDS = 12

# JWT配置
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.jwt_refresh_token_expire_days


class AuthService:
    """认证服务类"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        使用bcrypt加密密码
        
        Args:
            password: 明文密码
            
        Returns:
            加密后的密码哈希
        """
        # bcrypt限制密码最长72字节
        password_bytes = password.encode('utf-8')[:72]
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        验证密码
        
        Args:
            plain_password: 明文密码
            hashed_password: 加密后的密码哈希
            
        Returns:
            验证结果
        """
        if not hashed_password:
            return False
        try:
            password_bytes = plain_password.encode('utf-8')
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.warning(f"密码验证失败: {e}")
            return False
    
    @staticmethod
    async def create_user(
        username: str,
        password: str,
        tenant_id: str,
        email: Optional[str] = None,
        role: str = "security_analyst",
    ) -> Dict[str, Any]:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            tenant_id: 租户ID
            email: 邮箱（可选）
            role: 角色
            
        Returns:
            用户信息字典
        """
        async with get_db_session() as session:
            # 检查用户名是否已存在
            existing_user = await session.execute(
                User.__table__.select().where(User.username == username)
            )
            if existing_user.fetchone():
                raise ValueError("用户名已存在")
            
            # 检查租户是否存在
            tenant = await session.get(Tenant, tenant_id)
            if not tenant:
                raise ValueError("租户不存在")
            
            # 生成用户ID
            user_id = f"user-{uuid.uuid4().hex[:12]}"
            
            # 加密密码
            password_hash = AuthService.hash_password(password)
            
            # 创建用户
            new_user = User(
                user_id=user_id,
                tenant_id=tenant_id,
                username=username,
                email=email,
                role=role,
                permissions=["query", "analysis"],
                is_active=True,
                password_hash=password_hash,
            )
            
            session.add(new_user)
            await session.commit()
            
            logger.info(f"用户创建成功: user_id={user_id}, username={username}")
            
            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "tenant_id": tenant_id,
            }
    
    @staticmethod
    async def authenticate_user(
        username: str,
        password: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        验证用户登录
        
        Args:
            username: 用户名
            password: 密码
            tenant_id: 租户ID（可选）
            
        Returns:
            用户信息字典，如果验证失败返回None
        """
        async with get_db_session() as session:
            # 构建查询条件
            query = User.__table__.select().where(User.username == username)
            if tenant_id:
                query = query.where(User.tenant_id == tenant_id)
            
            result = await session.execute(query)
            user_row = result.fetchone()
            
            if not user_row:
                logger.warning(f"用户不存在: username={username}")
                return None
            
            # 转换为字典
            user_dict = dict(user_row._mapping)
            
            # 检查用户是否激活
            if not user_dict.get("is_active", True):
                logger.warning(f"用户未激活: username={username}")
                return None
            
            # 验证密码
            password_hash = user_dict.get("password_hash")
            if not AuthService.verify_password(password, password_hash):
                logger.warning(f"密码错误: username={username}")
                return None
            
            logger.info(f"用户登录成功: username={username}, user_id={user_dict['user_id']}")
            
            return {
                "user_id": user_dict["user_id"],
                "username": user_dict["username"],
                "email": user_dict.get("email"),
                "role": user_dict["role"],
                "tenant_id": user_dict["tenant_id"],
                "permissions": user_dict.get("permissions", []),
                "is_active": user_dict.get("is_active", True),
            }
    
    @staticmethod
    def create_access_token(user_info: Dict[str, Any]) -> str:
        """
        创建访问令牌
        
        Args:
            user_info: 用户信息字典
            
        Returns:
            JWT访问令牌
        """
        from datetime import timedelta
        
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "user_id": user_info["user_id"],
            "tenant_id": user_info["tenant_id"],
            "role": user_info["role"],
            "permissions": user_info.get("permissions", []),
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"创建访问令牌: user_id={user_info['user_id']}")
        return token
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """
        创建刷新令牌
        
        Args:
            user_id: 用户ID
            
        Returns:
            JWT刷新令牌
        """
        from datetime import timedelta
        
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"创建刷新令牌: user_id={user_id}")
        return token
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        验证令牌
        
        Args:
            token: JWT令牌
            token_type: 令牌类型（access/refresh）
            
        Returns:
            令牌载荷，如果验证失败返回None
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                logger.warning(f"令牌类型不匹配: expected={token_type}, got={payload.get('type')}")
                return None
            
            # 检查是否过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("令牌已过期")
                return None
            
            return payload
            
        except ExpiredSignatureError:
            logger.warning("令牌已过期")
            return None
        except JWTError as e:
            logger.warning(f"JWT验证失败: {e}")
            return None
    
    @staticmethod
    async def refresh_access_token(refresh_token: str) -> Optional[str]:
        """
        使用刷新令牌获取新的访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的访问令牌，如果失败返回None
        """
        # 验证刷新令牌
        payload = AuthService.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        
        # 获取用户信息
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user or not user.is_active:
                return None
            
            user_info = {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "permissions": user.permissions or [],
            }
        
        # 创建新的访问令牌
        return AuthService.create_access_token(user_info)
    
    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """
        根据用户ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户信息字典，如果不存在返回None
        """
        async with get_db_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return None
            
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "tenant_id": user.tenant_id,
                "permissions": user.permissions or [],
                "is_active": user.is_active,
            }
    
    @staticmethod
    async def create_mock_user(username: str, password: str, tenant_id: str) -> Dict[str, Any]:
        """
        创建模拟用户（用于测试，不需要数据库）
        
        Args:
            username: 用户名
            password: 密码
            tenant_id: 租户ID
            
        Returns:
            用户信息字典
        """
        import hashlib
        
        # 使用固定的用户ID
        user_id = f"user-{hashlib.md5(username.encode()).hexdigest()[:12]}"
        
        # 加密密码
        password_hash = AuthService.hash_password(password)
        
        logger.info(f"创建模拟用户: username={username}, user_id={user_id}")
        
        return {
            "user_id": user_id,
            "username": username,
            "email": f"{username}@example.com",
            "role": "security_analyst",
            "tenant_id": tenant_id,
            "permissions": ["query", "analysis"],
            "is_active": True,
            "password_hash": password_hash,
        }
    
    @staticmethod
    async def authenticate_mock_user(
        username: str,
        password: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        验证模拟用户（用于测试）
        
        Args:
            username: 用户名
            password: 密码
            tenant_id: 租户ID
            
        Returns:
            用户信息，如果验证失败返回None
        """
        # 模拟用户数据
        mock_users = {
            "admin": {
                "user_id": "user-admin001",
                "username": "admin",
                "email": "admin@example.com",
                "role": "super_admin",
                "tenant_id": "tenant-001",
                "permissions": ["admin", "query", "analysis", "compliance"],
                "is_active": True,
                "password": "admin123",
            },
            "security": {
                "user_id": "user-sec001",
                "username": "security",
                "email": "security@example.com",
                "role": "security_manager",
                "tenant_id": "tenant-001",
                "permissions": ["query", "analysis", "compliance"],
                "is_active": True,
                "password": "security123",
            },
            "analyst": {
                "user_id": "user-ana001",
                "username": "analyst",
                "email": "analyst@example.com",
                "role": "security_analyst",
                "tenant_id": "tenant-001",
                "permissions": ["query", "analysis"],
                "is_active": True,
                "password": "analyst123",
            },
        }
        
        # 检查用户
        user = mock_users.get(username)
        if not user:
            logger.warning(f"模拟用户不存在: username={username}")
            return None
        
        # 检查租户
        if tenant_id and user["tenant_id"] != tenant_id:
            logger.warning(f"租户不匹配: expected={tenant_id}, got={user['tenant_id']}")
            return None
        
        # 验证密码（简化版本）
        if password != user["password"]:
            logger.warning(f"模拟用户密码错误: username={username}")
            # 测试阶段允许密码为username+123格式
            expected_password = f"{username}123"
            if password != expected_password:
                return None
        
        logger.info(f"模拟用户登录成功: username={username}")
        
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "permissions": user["permissions"],
            "is_active": user["is_active"],
        }


# 全局认证服务实例
auth_service = AuthService()