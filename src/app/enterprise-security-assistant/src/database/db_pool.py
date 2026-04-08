"""
企业级安全智能助手 - 数据库连接池模块

实现PostgreSQL数据库的连接池管理，使用asyncpg和SQLAlchemy
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from contextlib import asynccontextmanager

from ..config.settings import settings
from ..utils.logger import logger


class DatabaseManager:
    """数据库连接池管理器"""
    
    def __init__(self):
        """初始化数据库管理器"""
        self.engine = None
        self.async_session_maker = None
        self._initialized = False
    
    async def initialize(self):
        """初始化数据库连接池"""
        if self._initialized:
            logger.warning("数据库连接池已初始化，跳过重复初始化")
            return
        
        try:
            # 创建异步引擎
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,  # 连接前检查
                pool_recycle=3600,  # 1小时后回收连接
            )
            
            # 创建会话工厂
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            self._initialized = True
            logger.info(
                f"数据库连接池初始化成功，"
                f"pool_size={settings.database_pool_size}, "
                f"max_overflow={settings.database_max_overflow}"
            )
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭数据库连接池"""
        if not self._initialized:
            logger.warning("数据库连接池未初始化，无需关闭")
            return
        
        try:
            if self.engine:
                await self.engine.dispose()
                self._initialized = False
                logger.info("数据库连接池已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接池失败: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取数据库会话（上下文管理器）
        
        Yields:
            数据库会话实例
        """
        if not self._initialized:
            raise RuntimeError("数据库连接池未初始化，请先调用initialize()方法")
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_session_sync(self):
        """
        获取数据库会话（同步方式，用于非async上下文）
        
        Returns:
            数据库会话实例
            
        Warning:
            此方法仅用于兼容性，建议使用get_session()异步方法
        """
        if not self._initialized:
            raise RuntimeError("数据库连接池未初始化，请先调用initialize()方法")
        return self.async_session_maker()


# 数据库基类
class Base(DeclarativeBase):
    """所有ORM模型的基类"""
    pass


# 全局数据库管理器实例
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（用于FastAPI依赖注入）
    
    Yields:
        数据库会话实例
    """
    async with db_manager.get_session() as session:
        yield session


async def init_database():
    """初始化数据库连接池"""
    await db_manager.initialize()


async def close_database():
    """关闭数据库连接池"""
    await db_manager.close()
