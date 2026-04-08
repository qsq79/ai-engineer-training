"""
企业级安全智能助手 - 日志记录中间件

记录所有API请求和响应，支持审计日志和性能监控
"""
from typing import Callable
from fastapi import Request, Response
import time
import json
from datetime import datetime

from ...utils.logger import logger


class LoggingMiddleware:
    """日志记录中间件"""
    
    def __init__(self, app=None):
        """
        初始化日志记录中间件
        
        Args:
            app: FastAPI应用实例（可选）
        """
        self.app = app
    
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
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        method = request.method
        url = str(request.url)
        path = request.url.path
        
        # 获取客户端信息
        client_host = request.client.host if request.client else None
        client_port = request.client.port if request.client else None
        
        # 获取用户信息（如果有）
        user_id = None
        tenant_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        if hasattr(request.state, "tenant_id"):
            tenant_id = request.state.tenant_id
        
        # 记录请求
        logger.info(
            f"请求开始: {method} {path} "
            f"client={client_host}:{client_port} "
            f"user_id={user_id} tenant_id={tenant_id}"
        )
        
        try:
            # 调用下一个中间件或路由
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应
            logger.info(
                f"请求完成: {method} {path} "
                f"status={response.status_code} "
                f"duration={process_time:.3f}s "
                f"user_id={user_id} tenant_id={tenant_id}"
            )
            
            # 添加性能头部
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = self._generate_request_id()
            
            return response
        
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误
            logger.error(
                f"请求失败: {method} {path} "
                f"duration={process_time:.3f}s "
                f"user_id={user_id} tenant_id={tenant_id} "
                f"error={str(e)}"
            )
            
            raise
    
    def _generate_request_id(self) -> str:
        """
        生成唯一请求ID
        
        Returns:
            请求ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"req-{timestamp}"


class AuditLogMiddleware:
    """审计日志中间件"""
    
    def __init__(self, app=None):
        """
        初始化审计日志中间件
        
        Args:
            app: FastAPI应用实例（可选）
        """
        self.app = app
    
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
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        method = request.method
        path = request.url.path
        query_params = str(request.url.query) if request.url.query else None
        
        # 获取用户信息
        user_id = None
        tenant_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        if hasattr(request.state, "tenant_id"):
            tenant_id = request.state.tenant_id
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        try:
            # 调用下一个中间件或路由
            response = await call_next(request)
            
            # 记录审计日志
            audit_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": method,
                "resource": path,
                "query_params": query_params,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "client_ip": client_ip,
                "status_code": response.status_code,
                "duration": time.time() - start_time,
                "success": response.status_code < 400,
            }
            
            # 记录审计日志（脱敏处理）
            self._log_audit_event(audit_log)
            
            return response
        
        except Exception as e:
            # 记录审计日志（失败）
            audit_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": method,
                "resource": path,
                "query_params": query_params,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "client_ip": client_ip,
                "status_code": 500,
                "duration": time.time() - start_time,
                "success": False,
                "error": str(e),
            }
            
            # 记录审计日志（脱敏处理）
            self._log_audit_event(audit_log)
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端IP地址
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            客户端IP地址
        """
        # 尝试从X-Forwarded-For头部获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # 尝试从X-Real-IP头部获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 从连接信息获取
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _log_audit_event(self, audit_log: dict):
        """
        记录审计事件（脱敏处理）
        
        Args:
            audit_log: 审计日志数据
        """
        # 脱敏处理
        audit_log = self._sanitize_audit_log(audit_log)
        
        # 记录审计日志
        logger.info(f"审计日志: {json.dumps(audit_log, ensure_ascii=False)}")
    
    def _sanitize_audit_log(self, audit_log: dict) -> dict:
        """
        审计日志脱敏处理
        
        Args:
            audit_log: 原始审计日志数据
            
        Returns:
            脱敏后的审计日志数据
        """
        sanitized_log = audit_log.copy()
        
        # 脱敏查询参数（可能包含密码、Token等敏感信息）
        if sanitized_log.get("query_params"):
            sanitized_log["query_params"] = self._sanitize_query_params(
                sanitized_log["query_params"]
            )
        
        # 脱敏错误信息
        if sanitized_log.get("error"):
            sanitized_log["error"] = self._sanitize_error(
                sanitized_log["error"]
            )
        
        return sanitized_log
    
    def _sanitize_query_params(self, query_params: str) -> str:
        """
        脱敏查询参数
        
        Args:
            query_params: 查询参数字符串
            
        Returns:
            脱敏后的查询参数
        """
        # 这里可以根据实际需要添加更多脱敏规则
        sanitized = query_params
        
        # 脱敏password参数
        if "password=" in sanitized:
            sanitized = sanitized.replace(
                "password=" + sanitized.split("password=")[1].split("&")[0],
                "password=***",
            )
        
        # 脱敏token参数
        if "token=" in sanitized:
            sanitized = sanitized.replace(
                "token=" + sanitized.split("token=")[1].split("&")[0],
                "token=***",
            )
        
        return sanitized
    
    def _sanitize_error(self, error: str) -> str:
        """
        脱敏错误信息
        
        Args:
            error: 错误信息
            
        Returns:
            脱敏后的错误信息
        """
        # 这里可以根据实际需要添加更多脱敏规则
        sanitized = error
        
        # 脱敏Token信息
        if "token" in sanitized.lower():
            # 简单的Token脱敏
            sanitized = "***"
        
        return sanitized


# 全局日志中间件实例
logging_middleware = LoggingMiddleware()
audit_log_middleware = AuditLogMiddleware()
