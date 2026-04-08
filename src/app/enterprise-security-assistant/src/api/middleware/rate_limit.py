"""
企业级安全智能助手 - 限流和熔断中间件

实现多级限流（租户级、用户级、Agent级、系统级）和熔断器机制
"""
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict, deque
import time

from ...config.settings import settings
from ...database.redis_pool import redis_manager
from ...utils.logger import logger


class CircuitBreakerState:
    """熔断器状态枚举"""
    CLOSED = "closed"      # 关闭：正常工作
    OPEN = "open"          # 开启：熔断中
    HALF_OPEN = "half_open"  # 半开：尝试恢复


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.open_time = None
    
    def record_success(self):
        """记录成功调用"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            
            # 如果连续成功次数达到阈值，关闭熔断器
            if self.success_count >= 2:
                self._close()
        else:
            self.failure_count = 0
    
    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            # 半开状态失败，重新开启熔断器
            self._open()
        elif self.failure_count >= self.failure_threshold:
            # 达到失败阈值，开启熔断器
            self._open()
    
    def can_execute(self) -> bool:
        """
        检查是否可以执行请求
        
        Returns:
            是否可以执行
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            # 检查是否到达恢复时间
            if self.open_time and datetime.utcnow() >= self.open_time + timedelta(seconds=self.recovery_timeout):
                # 到达恢复时间，进入半开状态
                self._half_open()
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def _close(self):
        """关闭熔断器"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.open_time = None
        logger.info("熔断器已关闭，恢复正常工作")
    
    def _open(self):
        """开启熔断器"""
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        self.open_time = datetime.utcnow()
        logger.warning(f"熔断器已开启，failure_count={self.failure_count}")
    
    def _half_open(self):
        """半开熔断器"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        logger.info("熔断器已半开，尝试恢复")


class RateLimiter:
    """限流器"""
    
    def __init__(
        self,
        qps: int,
        window_size: int = 60,
    ):
        """
        初始化限流器
        
        Args:
            qps: 每秒请求数限制
            window_size: 时间窗口大小（秒）
        """
        self.qps = qps
        self.window_size = window_size
        self.requests: deque = deque()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> tuple[bool, int]:
        """
        检查是否允许请求
        
        Returns:
            (是否允许, 剩余请求数）
        """
        async with self.lock:
            now = time.time()
            
            # 移除过期的请求记录
            while self.requests and self.requests[0] < now - self.window_size:
                self.requests.popleft()
            
            # 检查当前窗口内的请求数
            current_count = len(self.requests)
            remaining = self.qps - current_count
            
            if remaining > 0:
                # 允许请求
                self.requests.append(now)
                return True, remaining - 1
            else:
                # 超过限制
                return False, 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取限流器统计信息
        
        Returns:
            统计信息字典
        """
        now = time.time()
        recent_requests = [r for r in self.requests if r >= now - self.window_size]
        
        return {
            "qps": self.qps,
            "window_size": self.window_size,
            "current_requests": len(recent_requests),
            "remaining_requests": max(0, self.qps - len(recent_requests)),
        }


class RateLimitMiddleware:
    """限流和熔断中间件"""
    
    def __init__(self, app=None):
        """
        初始化限流中间件
        
        Args:
            app: FastAPI应用实例（可选）
        """
        self.app = app
        
        # 多级限流器
        self.system_limiter = RateLimiter(
            qps=settings.rate_limit_default_qps,
        )
        
        self.tenant_limiters: Dict[str, RateLimiter] = {}
        self.user_limiters: Dict[str, RateLimiter] = {}
        self.agent_limiters: Dict[str, RateLimiter] = {}
        
        # 熔断器字典（key: 资源名，value: CircuitBreaker）
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Redis用于分布式限流
        self.redis_enabled = True
    
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
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)
        
        try:
            # 多级限流检查
            await self._check_rate_limits(request)
            
            # 熔断器检查
            await self._check_circuit_breakers(request)
            
            response = await call_next(request)
            
            # 记录成功（更新熔断器状态）
            await self._record_success(request)
            
            return response
        
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            logger.error(f"限流中间件错误: {e}")
            
            # 记录失败（更新熔断器状态）
            await self._record_failure(request)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="限流检查过程中发生错误",
            )
    
    async def _check_rate_limits(self, request: Request):
        """
        检查多级限流
        
        Args:
            request: FastAPI请求对象
            
        Raises:
            HTTPException: 如果超过限流限制
        """
        # 系统级限流
        allowed, remaining = await self.system_limiter.is_allowed()
        if not allowed:
            logger.warning(f"系统级限流触发: qps={self.system_limiter.qps}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"系统繁忙，请稍后重试",
                headers={
                    "X-RateLimit-Limit": str(self.system_limiter.qps),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                },
            )
        
        # 租户级限流
        if hasattr(request.state, "tenant_id"):
            tenant_id = request.state.tenant_id
            tenant_limiter = self._get_tenant_limiter(tenant_id)
            allowed, remaining = await tenant_limiter.is_allowed()
            
            if not allowed:
                logger.warning(f"租户级限流触发: tenant_id={tenant_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"租户请求频率过高，请稍后重试",
                    headers={
                        "X-RateLimit-Limit": str(tenant_limiter.qps),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + 60),
                    },
                )
        
        # 用户级限流
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
            user_limiter = self._get_user_limiter(user_id)
            allowed, remaining = await user_limiter.is_allowed()
            
            if not allowed:
                logger.warning(f"用户级限流触发: user_id={user_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"个人请求频率过高，请稍后重试",
                    headers={
                        "X-RateLimit-Limit": str(user_limiter.qps),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + 60),
                    },
                )
    
    async def _check_circuit_breakers(self, request: Request):
        """
        检查熔断器状态
        
        Args:
            request: FastAPI请求对象
            
        Raises:
            HTTPException: 如果熔断器开启
        """
        # 根据请求路径确定资源名
        resource_name = self._get_resource_name(request)
        
        if resource_name:
            circuit_breaker = self._get_circuit_breaker(resource_name)
            
            if not circuit_breaker.can_execute():
                logger.warning(f"熔断器开启: resource={resource_name}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"服务暂时不可用，熔断器已开启",
                    headers={
                        "X-CircuitBreaker-State": circuit_breaker.state,
                        "Retry-After": str(settings.circuit_breaker_recovery_timeout),
                    },
                )
    
    async def _record_success(self, request: Request):
        """
        记录成功请求
        
        Args:
            request: FastAPI请求对象
        """
        resource_name = self._get_resource_name(request)
        
        if resource_name:
            circuit_breaker = self._get_circuit_breaker(resource_name)
            circuit_breaker.record_success()
    
    async def _record_failure(self, request: Request):
        """
        记录失败请求
        
        Args:
            request: FastAPI请求对象
        """
        resource_name = self._get_resource_name(request)
        
        if resource_name:
            circuit_breaker = self._get_circuit_breaker(resource_name)
            circuit_breaker.record_failure()
    
    def _get_resource_name(self, request: Request) -> Optional[str]:
        """
        获取资源名（用于熔断器）
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            资源名
        """
        # 根据请求路径确定资源名
        path_parts = request.url.path.split("/")
        
        if len(path_parts) >= 4:
            # /api/v1/agents/{agent_name}/execute -> agents
            return path_parts[3]
        
        return None
    
    def _get_tenant_limiter(self, tenant_id: str) -> RateLimiter:
        """
        获取或创建租户限流器
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            租户限流器
        """
        if tenant_id not in self.tenant_limiters:
            self.tenant_limiters[tenant_id] = RateLimiter(
                qps=settings.rate_limit_tenant_qps,
            )
        
        return self.tenant_limiters[tenant_id]
    
    def _get_user_limiter(self, user_id: str) -> RateLimiter:
        """
        获取或创建用户限流器
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户限流器
        """
        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = RateLimiter(
                qps=settings.rate_limit_user_qps,
            )
        
        return self.user_limiters[user_id]
    
    def _get_circuit_breaker(self, resource_name: str) -> CircuitBreaker:
        """
        获取或创建熔断器
        
        Args:
            resource_name: 资源名
            
        Returns:
            熔断器实例
        """
        if resource_name not in self.circuit_breakers:
            self.circuit_breakers[resource_name] = CircuitBreaker(
                failure_threshold=settings.circuit_breaker_failure_threshold,
                recovery_timeout=settings.circuit_breaker_recovery_timeout,
            )
        
        return self.circuit_breakers[resource_name]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取限流和熔断器统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "system_limiter": self.system_limiter.get_stats(),
            "tenant_limiters": {k: v.get_stats() for k, v in self.tenant_limiters.items()},
            "user_limiters": {k: v.get_stats() for k, v in self.user_limiters.items()},
            "circuit_breakers": {
                k: {
                    "state": v.state,
                    "failure_count": v.failure_count,
                    "success_count": v.success_count,
                }
                for k, v in self.circuit_breakers.items()
            },
        }
        
        return stats


# 全局限流中间件实例
rate_limit_middleware = RateLimitMiddleware()
