"""
企业级安全智能助手 - 数据库初始化脚本

创建所有表，提供数据库初始化功能，提供种子数据
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import (
    Base, Tenant, User, Session, AgentCall,
    WorkflowExecution, WorkflowTask, ComplianceCheck,
    AuditLog, TokenUsageStats, ThreatIntelligence,
)
from ..config.settings import settings
from ..utils.logger import logger


async def create_tables():
    """创建所有表"""
    try:
        # 创建异步引擎
        engine = create_async_engine(settings.database_url)
        
        # 创建所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("所有数据库表已创建")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise


async def drop_tables():
    """删除所有表（慎用）"""
    try:
        engine = create_async_engine(settings.database_url)
        
        # 删除所有表
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("所有数据库表已删除")
    except Exception as e:
        logger.error(f"删除数据库表失败: {e}")
        raise


async def create_tenant_sample():
    """创建示例租户"""
    from .db_pool import db_manager
    
    try:
        # 初始化数据库管理器
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # 创建示例租户
            tenant = Tenant(
                tenant_id="T001",
                tenant_name="示例租户",
                status="active",
            )
            session.add(tenant)
            await session.flush()  # 确保租户先创建
            
            # 导入密码哈希工具
            from ..services.auth_service import AuthService
            
            # 创建管理员用户（密码：admin123）
            admin_user = User(
                user_id="U001",
                tenant_id="T001",
                username="admin",
                email="admin@esa.com",
                role="super_admin",
                permissions=["query", "analyze", "config", "manage", "audit"],
                is_active=True,
                password_hash=AuthService.hash_password("admin123"),
            )
            session.add(admin_user)
            
            # 创建安全分析师用户（密码：analyst123）
            analyst_user = User(
                user_id="U002",
                tenant_id="T001",
                username="analyst",
                email="analyst@esa.com",
                role="security_analyst",
                permissions=["query", "analyze"],
                is_active=True,
                password_hash=AuthService.hash_password("analyst123"),
            )
            session.add(analyst_user)
            
            # 创建只读用户（密码：readonly123）
            readonly_user = User(
                user_id="U003",
                tenant_id="T001",
                username="readonly",
                email="readonly@esa.com",
                role="read_only",
                permissions=["query"],
                is_active=True,
                password_hash=AuthService.hash_password("readonly123"),
            )
            session.add(readonly_user)
            
            await session.commit()
        
        logger.info("示例租户和用户已创建")
        logger.info("  - 租户: T001 (示例租户）")
        logger.info("  - 用户: U001 (admin) - 角色: super_admin")
        logger.info("  - 用户: U002 (analyst) - 角色: security_analyst")
        logger.info("  - 用户: U003 (readonly) - 角色: read_only")
        
        await db_manager.close()
    
    except Exception as e:
        logger.error(f"创建示例数据失败: {e}")
        raise


async def verify_tables():
    """验证所有表是否创建成功"""
    from .db_pool import db_manager
    
    try:
        # 初始化数据库管理器
        await db_manager.initialize()
        
        async with db_manager.get_session() as session:
            # 检查租户表
            tenant_count = await session.execute(
                "SELECT COUNT(*) FROM tenants"
            )
            logger.info(f"租户表记录数: {tenant_count.scalar()}")
            
            # 检查用户表
            user_count = await session.execute(
                "SELECT COUNT(*) FROM users"
            )
            logger.info(f"用户表记录数: {user_count.scalar()}")
            
            # 检查会话表
            session_count = await session.execute(
                "SELECT COUNT(*) FROM sessions"
            )
            logger.info(f"会话表记录数: {session_count.scalar()}")
            
            # 检查Agent调用表
            agent_call_count = await session.execute(
                "SELECT COUNT(*) FROM agent_calls"
            )
            logger.info(f"Agent调用表记录数: {agent_call_count.scalar()}")
        
        await db_manager.close()
        
        logger.info("数据库表验证完成")
    
    except Exception as e:
        logger.error(f"验证数据库表失败: {e}")
        raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="企业级安全智能助手 - 数据库初始化")
    parser.add_argument(
        "--action",
        choices=["create", "drop", "verify", "seed"],
        default="create",
        help="执行的操作（创建/删除/验证/种子数据）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制执行（无需确认）",
    )
    
    args = parser.parse_args()
    
    # 确认危险操作
    if args.action in ["drop"] and not args.force:
        confirm = input("⚠️  警告：此操作将删除所有数据库表和 数据！确认继续？(yes/no): ")
        if confirm.lower() != "yes":
            print("操作已取消")
            sys.exit(0)
    
    try:
        if args.action == "create":
            logger.info("开始创建数据库表...")
            await create_tables()
            logger.info("✓ 数据库表创建成功")
        
        elif args.action == "drop":
            logger.info("开始删除数据库表...")
            await drop_tables()
            logger.info("✓ 数据库表删除成功")
        
        elif args.action == "verify":
            logger.info("开始验证数据库表...")
            await verify_tables()
            logger.info("✓ 数据库表验证成功")
        
        elif args.action == "seed":
            logger.info("开始创建示例数据...")
            await create_tenant_sample()
            logger.info("✓ 示例数据创建成功")
    
    except KeyboardInterrupt:
        logger.warning("操作已取消")
        sys.exit(1)
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
