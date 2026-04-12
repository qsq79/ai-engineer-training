"""
企业级安全智能助手 - 主应用程序

整合所有中间件和基础架构，提供FastAPI应用入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from .config.settings import settings
from .database.db_pool import init_database, close_database, db_manager
from .database.redis_pool import init_redis, close_redis, redis_manager
from .utils.logger import logger

# 导入中间件（将在后续任务中创建完整路由）
from .api.middleware.auth import auth_middleware
from .api.middleware.rate_limit import rate_limit_middleware
from .api.middleware.logging import logging_middleware, audit_log_middleware


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="企业级多Agent智能安全分析助手",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.debug,
)

# 获取静态文件目录的绝对路径 (src/static)
current_dir = os.path.dirname(__file__)
static_dir = os.path.join(current_dir, "static")

# 注册静态文件服务
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 根路径返回前端页面
@app.get("/")
async def root():
    """返回前端页面"""
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

# 配置CORS
def parse_corsOrigins(value):
    """解析CORSOrigins配置"""
    if isinstance(value, str):
        if value == "*":
            return ["*"]
        # 尝试解析为JSON数组
        import json
        try:
            return json.loads(value)
        except:
            # 如果失败，尝试按逗号分隔
            return [v.strip() for v in value.split(",") if v.strip()]
    return value if value else ["*"]

def parse_cors_list(value):
    """解析CORS列表配置（方法、头部等）"""
    if isinstance(value, str):
        if value == "*":
            return ["*"]
        import json
        try:
            return json.loads(value)
        except:
            return [v.strip() for v in value.split(",") if v.strip()]
    return value if value else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_corsOrigins(settings.cors_origins),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=parse_cors_list(settings.cors_allow_methods),
    allow_headers=parse_cors_list(settings.cors_allow_headers),
)

# 导入并注册路由
from .api.routes import (
    query_router,
    agents_router,
    workflows_router,
    sessions_router,
    compliance_router,
    stats_router,
    admin_router,
    auth_router,
)

# 注册所有路由
app.include_router(query_router, prefix="/api/v1", tags=["查询"])
app.include_router(agents_router, prefix="/api/v1", tags=["Agent"])
app.include_router(workflows_router, prefix="/api/v1", tags=["工作流"])
app.include_router(sessions_router, prefix="/api/v1", tags=["会话"])
app.include_router(compliance_router, prefix="/api/v1", tags=["合规"])
app.include_router(stats_router, prefix="/api/v1", tags=["统计"])
app.include_router(admin_router, prefix="/api/v1", tags=["管理"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])

# 添加中间件
app.middleware("http")(audit_log_middleware)
app.middleware("http")(logging_middleware)
app.middleware("http")(auth_middleware)
app.middleware("http")(rate_limit_middleware)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info(f"{settings.app_name} v{settings.app_version} 正在启动...")
    
    # 初始化数据库连接池
    try:
        await init_database()
        logger.info("数据库连接池初始化成功")
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        raise
    
    # 初始化Redis连接池
    try:
        await init_redis()
        logger.info("Redis连接池初始化成功")
    except Exception as e:
        logger.error(f"Redis连接池初始化失败: {e}")
        raise
    
    logger.info(f"{settings.app_name} 已成功启动")
    
    yield
    
    # 关闭事件
    logger.info(f"{settings.app_name} 正在关闭...")
    
    # 关闭Redis连接池
    try:
        await close_redis()
        logger.info("Redis连接池已关闭")
    except Exception as e:
        logger.error(f"关闭Redis连接池失败: {e}")
    
    # 关闭数据库连接池
    try:
        await close_database()
        logger.info("数据库连接池已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接池失败: {e}")
    
    logger.info(f"{settings.app_name} 已关闭")


# 配置应用生命周期
app.router.lifespan_context = lifespan


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
    }


# API健康检查端点
@app.get("/api/v1/health")
async def api_health_check():
    """API健康检查端点"""
    # 检查数据库连接
    db_status = "ok"
    try:
        if db_manager._initialized:
            # 尝试获取一个会话来验证连接
            async with db_manager.get_session():
                pass
        else:
            db_status = "not_initialized"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # 检查Redis连接
    redis_status = "ok"
    try:
        if redis_manager._initialized:
            # 尝试执行一个Redis命令来验证连接
            client = await redis_manager.get_async_client()
            await client.ping()
        else:
            redis_status = "not_initialized"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "components": {
            "database": db_status,
            "redis": redis_status,
        },
    }


# 根路径 - 已在上面定义，返回前端页面


# 404处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """404错误处理"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": "请求的资源不存在",
            "path": request.url.path,
        },
    )


# 500错误处理
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """500错误处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "服务器内部错误",
            "error": str(exc) if settings.debug else "Internal Server Error",
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
