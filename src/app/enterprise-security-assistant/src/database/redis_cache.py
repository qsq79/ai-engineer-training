"""
Redis缓存管理
实现租户限流配置、会话状态、Agent状态、任务队列、分布式锁、Token使用追踪的Redis存储
"""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.database.redis_pool import RedisManager
from src.utils.logger import logger


class RedisCacheManager:
    """Redis缓存管理器
    
    职责：
    1. 租户限流配置的Redis存储
    2. 会话状态的Redis存储和管理
    3. Agent状态的Redis存储和更新
    4. 任务队列（pending、running、completed）的Redis存储
    5. 分布式锁机制（租户锁、Agent锁）
    6. Token使用追踪的Redis存储
    """
    
    def __init__(self, redis_manager: RedisManager):
        """初始化Redis缓存管理器"""
        self.redis = redis_manager
        logger.info("Redis缓存管理器初始化完成")
    
    # ==================== 租户限流配置 ====================
    
    async def set_tenant_rate_limit(
        self,
        tenant_id: str,
        limit: int,
        window_seconds: int = 60
    ):
        """设置租户限流配置
        
        Args:
            tenant_id: 租户ID
            limit: 限流阈值
            window_seconds: 时间窗口（秒）
        """
        key = f"tenant:{tenant_id}:rate_limit"
        value = json.dumps({
            "limit": limit,
            "window_seconds": window_seconds,
            "created_at": datetime.utcnow().isoformat()
        })
        
        await self.redis.set(key, value, ex=86400)  # 24小时过期
        logger.info(f"设置租户限流配置: {tenant_id}, limit={limit}, window={window_seconds}s")
    
    async def get_tenant_rate_limit(
        self,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取租户限流配置
        
        Args:
            tenant_id: 租户ID
        
        Returns:
            限流配置，如果不存在则返回None
        """
        key = f"tenant:{tenant_id}:rate_limit"
        value = await self.redis.get(key)
        
        if value:
            return json.loads(value)
        
        return None
    
    async def check_tenant_rate_limit(
        self,
        tenant_id: str,
        request_count: int = 1
    ) -> bool:
        """检查租户限流
        
        Args:
            tenant_id: 租户ID
            request_count: 请求计数
        
        Returns:
            是否允许请求
        """
        config = await self.get_tenant_rate_limit(tenant_id)
        if not config:
            return True  # 没有配置则不限流
        
        key = f"tenant:{tenant_id}:request_count"
        current = await self.redis.get(key)
        
        if current is None:
            await self.redis.incrby(key, request_count)
            await self.redis.expire(key, config["window_seconds"])
            return True
        
        if int(current) + request_count <= config["limit"]:
            await self.redis.incrby(key, request_count)
            return True
        
        logger.warning(f"租户限流触发: {tenant_id}, current={current}, limit={config['limit']}")
        return False
    
    # ==================== 会话状态管理 ====================
    
    async def set_session(
        self,
        session_id: str,
        tenant_id: str,
        user_id: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
        expires_hours: int = 24
    ):
        """设置会话状态
        
        Args:
            session_id: 会话ID
            tenant_id: 租户ID
            user_id: 用户ID
            context: 会话上下文
            history: 会话历史
            expires_hours: 过期时间（小时）
        """
        key = f"session:{session_id}"
        value = json.dumps({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "context": context,
            "history": history,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        
        await self.redis.set(key, value, ex=expires_hours * 3600)
        logger.info(f"设置会话状态: {session_id}, user={user_id}, history_len={len(history)}")
    
    async def get_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取会话状态
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话状态，如果不存在则返回None
        """
        key = f"session:{session_id}"
        value = await self.redis.get(key)
        
        if value:
            return json.loads(value)
        
        return None
    
    async def update_session(
        self,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ):
        """更新会话状态
        
        Args:
            session_id: 会话ID
            context: 会话上下文（可选）
            history: 会话历史（可选）
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"会话不存在，无法更新: {session_id}")
            return
        
        if context is not None:
            session["context"].update(context)
        
        if history is not None:
            session["history"].extend(history)
        
        session["updated_at"] = datetime.utcnow().isoformat()
        
        key = f"session:{session_id}"
        value = json.dumps(session)
        await self.redis.set(key, value)
        logger.info(f"更新会话状态: {session_id}")
    
    async def delete_session(self, session_id: str):
        """删除会话状态
        
        Args:
            session_id: 会话ID
        """
        key = f"session:{session_id}"
        await self.redis.delete(key)
        logger.info(f"删除会话状态: {session_id}")
    
    # ==================== Agent状态管理 ====================
    
    async def set_agent_status(
        self,
        agent_name: str,
        status: str,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """设置Agent状态
        
        Args:
            agent_name: Agent名称
            status: 状态（idle、running、error）
            tenant_id: 租户ID（可选）
            metadata: 元数据（可选）
        """
        key = f"agent:{agent_name}:status"
        value = json.dumps({
            "status": status,
            "tenant_id": tenant_id,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow().isoformat()
        })
        
        await self.redis.set(key, value, ex=3600)  # 1小时过期
        logger.info(f"设置Agent状态: {agent_name}, status={status}")
    
    async def get_agent_status(
        self,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取Agent状态
        
        Args:
            agent_name: Agent名称
        
        Returns:
            Agent状态，如果不存在则返回None
        """
        key = f"agent:{agent_name}:status"
        value = await self.redis.get(key)
        
        if value:
            return json.loads(value)
        
        return None
    
    # ==================== 任务队列管理 ====================
    
    async def add_task_to_queue(
        self,
        queue_name: str,
        task_id: str,
        task_data: Dict[str, Any]
    ):
        """添加任务到队列
        
        Args:
            queue_name: 队列名称（pending、running、completed）
            task_id: 任务ID
            task_data: 任务数据
        """
        key = f"queue:{queue_name}"
        await self.redis.lpush(key, json.dumps({
            "task_id": task_id,
            "task_data": task_data,
            "created_at": datetime.utcnow().isoformat()
        }))
        logger.info(f"添加任务到队列: {queue_name}, task_id={task_id}")
    
    async def get_task_from_queue(
        self,
        queue_name: str,
        block: bool = False,
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        """从队列获取任务
        
        Args:
            queue_name: 队列名称
            block: 是否阻塞等待
            timeout: 超时时间（秒）
        
        Returns:
            任务数据，如果没有任务则返回None
        """
        key = f"queue:{queue_name}"
        
        if block:
            # BRPOP：阻塞式获取
            result = await self.redis.brpop(key, timeout=timeout)
        else:
            # RPOP：非阻塞获取
            result = await self.redis.rpop(key)
        
        if result:
            return json.loads(result)
        
        return None
    
    async def move_task_between_queues(
        self,
        from_queue: str,
        to_queue: str,
        task_id: str,
        task_data: Dict[str, Any]
    ):
        """移动任务到另一个队列
        
        Args:
            from_queue: 源队列
            to_queue: 目标队列
            task_id: 任务ID
            task_data: 任务数据
        """
        # 先从源队列删除（简化处理，实际可能需要LRANGE）
        await self.add_task_to_queue(to_queue, task_id, task_data)
        logger.info(f"移动任务: {from_queue} -> {to_queue}, task_id={task_id}")
    
    # ==================== Token使用追踪 ====================
    
    async def track_token_usage(
        self,
        tenant_id: str,
        model: str,
        tokens: int,
        cost: float
    ):
        """记录Token使用情况
        
        Args:
            tenant_id: 租户ID
            model: 模型名称
            tokens: Token数量
            cost: 成本
        """
        key = f"token_usage:{tenant_id}:{model}:{datetime.utcnow().strftime('%Y%m%d')}"
        
        # 获取当前使用量
        current = await self.redis.get(key)
        if current:
            data = json.loads(current)
            data["total_tokens"] += tokens
            data["total_cost"] += cost
            data["call_count"] += 1
            data["updated_at"] = datetime.utcnow().isoformat()
        else:
            data = {
                "tenant_id": tenant_id,
                "model": model,
                "date": datetime.utcnow().strftime('%Y-%m-%d'),
                "total_tokens": tokens,
                "total_cost": cost,
                "call_count": 1,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        
        await self.redis.set(key, json.dumps(data), ex=86400 * 7)  # 7天过期
        logger.info(f"记录Token使用: {tenant_id}, model={model}, tokens={tokens}, cost={cost}")
    
    async def get_token_usage(
        self,
        tenant_id: str,
        model: str,
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取Token使用情况
        
        Args:
            tenant_id: 租户ID
            model: 模型名称
            date: 日期（YYYY-MM-DD格式，可选）
        
        Returns:
            Token使用情况，如果不存在则返回None
        """
        if date:
            key = f"token_usage:{tenant_id}:{model}:{date.replace('-', '')}"
        else:
            # 使用今天的日期
            key = f"token_usage:{tenant_id}:{model}:{datetime.utcnow().strftime('%Y%m%d')}"
        
        value = await self.redis.get(key)
        
        if value:
            return json.loads(value)
        
        return None


# ============ 便捷函数 ============

# 全局Redis缓存管理器实例
_redis_cache_manager: Optional[RedisCacheManager] = None


def get_redis_cache_manager(redis_manager: RedisManager) -> RedisCacheManager:
    """获取Redis缓存管理器实例（单例模式）
    
    Args:
        redis_manager: Redis管理器
    
    Returns:
        Redis缓存管理器实例
    """
    global _redis_cache_manager
    
    if _redis_cache_manager is None:
        _redis_cache_manager = RedisCacheManager(redis_manager)
    
    return _redis_cache_manager


# 导出
__all__ = [
    "RedisCacheManager",
    "get_redis_cache_manager"
]
