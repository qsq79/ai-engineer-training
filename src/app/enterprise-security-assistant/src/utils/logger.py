"""
企业级安全智能助手 - 日志模块

使用loguru实现日志管理，支持控制台和文件输出，支持日志轮转和压缩
"""
from loguru import logger as loguru_logger
from typing import Optional
import sys
import os
from pathlib import Path

from ..config.settings import settings


class Logger:
    """日志管理器"""
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        log_rotation: str = "10 MB",
        log_retention: str = "30 days",
    ):
        """
        初始化日志管理器
        
        Args:
            log_level: 日志级别
            log_file: 日志文件路径
            log_rotation: 日志轮转大小
            log_retention: 日志保留时间
        """
        self.log_level = log_level
        self.log_file = log_file
        self.log_rotation = log_rotation
        self.log_retention = log_retention
        
        # 移除默认的处理器
        loguru_logger.remove()
        
        # 添加控制台处理器
        self._add_console_handler()
        
        # 添加文件处理器
        if log_file:
            self._add_file_handler()
    
    def _add_console_handler(self):
        """添加控制台处理器"""
        loguru_logger.add(
            sys.stderr,
            level=self.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    
    def _add_file_handler(self):
        """添加文件处理器"""
        # 确保日志目录存在
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            self.log_file,
            level=self.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=self.log_rotation,
            retention=self.log_retention,
            compression="zip",
            backtrace=True,
            diagnose=True,
            encoding="utf-8",
        )
    
    def get_logger(self, name: Optional[str] = None):
        """
        获取日志记录器
        
        Args:
            name: 日志记录器名称（通常是模块名）
            
        Returns:
            日志记录器实例
        """
        if name:
            return loguru_logger.bind(name=name)
        return loguru_logger


# 全局日志实例
_logger = Logger(
    log_level=settings.log_level,
    log_file=settings.log_file,
    log_rotation=settings.log_rotation,
    log_retention=settings.log_retention,
).get_logger(__name__)

# 导出日志记录器
logger = _logger

def get_logger(name: Optional[str] = None):
    """
    获取日志记录器（用于依赖注入）
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    if name:
        return _logger.bind(name=name)
    return _logger
