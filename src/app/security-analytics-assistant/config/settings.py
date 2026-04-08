#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AppConfig:
    """应用配置类"""
    
    # OpenAI API 配置
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    
    # 默认模型配置
    default_model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 4096
    
    # 向量数据库配置（RAG）
    vector_db_path: str = "./data/vector_store"
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # 场景配置
    enable_rag_cache: bool = True
    rag_top_k: int = 3
    
    @classmethod
    def from_env(cls, env_file: str = ".env") -> 'AppConfig':
        """从环境变量加载配置"""
        # 加载 .env 文件
        env_vars = {}
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        return cls(
            api_key=env_vars.get('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY', '')),
            api_base=env_vars.get('OPENAI_API_BASE', os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')),
            default_model=env_vars.get('DEFAULT_MODEL', os.getenv('DEFAULT_MODEL', 'gpt-4o-mini')),
            temperature=float(env_vars.get('TEMPERATURE', os.getenv('TEMPERATURE', '0.0'))),
            max_tokens=int(env_vars.get('MAX_TOKENS', os.getenv('MAX_TOKENS', '4096'))),
            vector_db_path=env_vars.get('VECTOR_DB_PATH', os.getenv('VECTOR_DB_PATH', './data/vector_store')),
            chunk_size=int(env_vars.get('CHUNK_SIZE', os.getenv('CHUNK_SIZE', '500'))),
            chunk_overlap=int(env_vars.get('CHUNK_OVERLAP', os.getenv('CHUNK_OVERLAP', '50'))),
            enable_rag_cache=env_vars.get('ENABLE_RAG_CACHE', os.getenv('ENABLE_RAG_CACHE', 'true')).lower() == 'true',
            rag_top_k=int(env_vars.get('RAG_TOP_K', os.getenv('RAG_TOP_K', '3'))
        )


# 全局配置实例
_global_config: Optional[AppConfig] = None


def get_config(env_file: str = ".env") -> AppConfig:
    """获取全局配置实例（单例）"""
    global _global_config
    if _global_config is None:
        _global_config = AppConfig.from_env(env_file)
    return _global_config


def reload_config(env_file: str = ".env") -> AppConfig:
    """重新加载配置"""
    global _global_config
    _global_config = AppConfig.from_env(env_file)
    return _global_config
