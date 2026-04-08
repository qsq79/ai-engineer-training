"""
企业级安全智能助手 - Redis连接池模块

实现Redis连接池管理，支持连接池、分布式锁等高级功能
"""
from typing import Optional, Any
import json
from redis import Redis, ConnectionPool
from redis.asyncio import Redis as AsyncRedis, from_url as async_from_url, ConnectionPool as AsyncConnectionPool

from ..config.settings import settings
from ..utils.logger import logger


class RedisManager:
    """Redis连接池管理器"""
    
    def __init__(self):
        """初始化Redis管理器"""
        self.sync_pool: Optional[ConnectionPool] = None
        self.async_pool: Optional[AsyncConnectionPool] = None
        self._initialized = False
    
    async def initialize(self):
        """初始化Redis连接池"""
        if self._initialized:
            logger.warning("Redis连接池已初始化，跳过重复初始化")
            return
        
        try:
            # 创建同步连接池
            self.sync_pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            # 创建异步连接池
            self.async_pool = AsyncConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_pool_size,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            self._initialized = True
            logger.info(f"Redis连接池初始化成功，pool_size={settings.redis_pool_size}")
        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭Redis连接池"""
        if not self._initialized:
            logger.warning("Redis连接池未初始化，无需关闭")
            return
        
        try:
            if self.sync_pool:
                self.sync_pool.disconnect()
            
            if self.async_pool:
                await self.async_pool.disconnect()
            
            self._initialized = False
            logger.info("Redis连接池已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接池失败: {e}")
            raise
    
    def get_sync_client(self) -> Redis:
        """
        获取同步Redis客户端
        
        Returns:
            同步Redis客户端实例
            
        Warning:
            此方法仅用于兼容性，建议使用异步方法
        """
        if not self._initialized:
            raise RuntimeError("Redis连接池未初始化，请先调用initialize()方法")
        return Redis(connection_pool=self.sync_pool)
    
    async def get_async_client(self) -> AsyncRedis:
        """
        获取异步Redis客户端
        
        Returns:
            异步Redis客户端实例
        """
        if not self._initialized:
            raise RuntimeError("Redis连接池未初始化，请先调用initialize()方法")
        return AsyncRedis(connection_pool=self.async_pool)
    
    # 便捷方法
    async def get(self, key: str) -> Optional[Any]:
        """
        获取Redis键值
        
        Args:
            key: Redis键
            
        Returns:
            键值（如果存在）
        """
        client = await self.get_async_client()
        return await client.get(key)
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置Redis键值
        
        Args:
            key: Redis键
            value: 值（会自动序列化为JSON）
            ex: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        client = await self.get_async_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.set(key, value, ex=ex)
    
    async def delete(self, key: str) -> int:
        """
        删除Redis键
        
        Args:
            key: Redis键
            
        Returns:
            删除的键数量
        """
        client = await self.get_async_client()
        return await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """
        检查Redis键是否存在
        
        Args:
            key: Redis键
            
        Returns:
            键是否存在
        """
        client = await self.get_async_client()
        return await client.exists(key) > 0
    
    async def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置Redis哈希字段
        
        Args:
            name: 哈希名
            key: 哈希键
            value: 值
            
        Returns:
            添加的字段数量
        """
        client = await self.get_async_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """
        获取Redis哈希字段
        
        Args:
            name: 哈希名
            key: 哈希键
            
        Returns:
            哈希值
        """
        client = await self.get_async_client()
        value = await client.hget(name, key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def hgetall(self, name: str) -> dict:
        """
        获取Redis哈希所有字段
        
        Args:
            name: 哈希名
            
        Returns:
            所有哈希字段
        """
        client = await self.get_async_client()
        data = await client.hgetall(name)
        # 尝试解析JSON值
        result = {}
        for key, value in data.items():
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        return result
    
    async def lpush(self, name: str, value: Any) -> int:
        """
        向Redis列表左侧添加元素
        
        Args:
            name: 列表名
            value: 值
            
        Returns:
            列表长度
        """
        client = await self.get_async_client()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await client.lpush(name, value)
    
    async def lpop(self, name: str) -> Optional[Any]:
        """
        从Redis列表左侧弹出元素
        
        Args:
            name: 列表名
            
        Returns:
            弹出的元素
        """
        client = await self.get_async_client()
        value = await client.lpop(name)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def llen(self, name: str) -> int:
        """
        获取Redis列表长度
        
        Args:
            name: 列表名
            
        Returns:
            列表长度
        """
        client = await self.get_async_client()
        return await client.llen(name)
    
    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking_timeout: Optional[int] = None,
    ) -> bool:
        """
        获取分布式锁
        
        Args:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            blocking_timeout: 阻塞超时时间（秒），None表示不阻塞
            
        Returns:
            是否获取到锁
        """
        client = await self.get_async_client()
        return await client.set(
            f"lock:{lock_name}",
            "locked",
            ex=timeout,
            nx=True,
        ) or (blocking_timeout is None)
    
    async def release_lock(self, lock_name: str) -> int:
        """
        释放分布式锁
        
        Args:
            lock_name: 锁名称
            
        Returns:
            删除的键数量
        """
        client = await self.get_async_client()
        return await client.delete(f"lock:{lock_name}")


# 全局Redis管理器实例
redis_manager = RedisManager()


async def init_redis():
    """初始化Redis连接池"""
    await redis_manager.initialize()


async def close_redis():
    """关闭Redis连接池"""
    await redis_manager.close()


async def get_redis_client() -> AsyncRedis:
    """
    获取Redis客户端（用于FastAPI依赖注入）
    
    Returns:
        异步Redis客户端实例
    """
    return await redis_manager.get_async_client()
