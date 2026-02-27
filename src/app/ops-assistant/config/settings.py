#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理模块
支持模型配置、API 配置和动态模型选择
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv


@dataclass
class ModelConfig:
    """模型配置类"""
    name: str
    model_id: str
    provider: str = "openai"
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    timeout: int = 30
    max_retries: int = 2
    base_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于传递给 ChatOpenAI"""
        result = {
            "model": self.model_id,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }
        if self.max_tokens:
            result["max_tokens"] = self.max_tokens
        if self.base_url:
            result["base_url"] = self.base_url
        return result


@dataclass
class AppConfig:
    """应用配置类"""

    # API 配置
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"

    # 默认模型
    default_model: str = "gpt-4o-mini"

    # Agent 配置
    agent_max_iterations: int = 10
    agent_verbose: bool = False

    # 智能模型路由配置
    enable_model_routing: bool = True  # 是否启用智能模型路由
    model_routing_debug: bool = False  # 是否输出路由调试信息

    # 模型层级配置
    model_tiers: Dict[str, str] = field(default_factory=lambda: {
        'fast': 'gpt-4o-mini',      # 快速、低成本
        'balanced': 'gpt-4o',        # 平衡性能和成本
        'powerful': 'gpt-4-turbo',   # 高性能
        'premium': 'gpt-4',          # 最强能力
    })

    # 可用模型列表
    available_models: Dict[str, ModelConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "AppConfig":
        """从环境变量加载配置"""
        # 加载 .env 文件
        if env_file:
            load_dotenv(env_file)
        else:
            # 尝试自动查找 .env 文件
            load_dotenv()

        # 获取 API 配置
        api_key = os.getenv("OPENAI_API_KEY", "")
        api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

        # 清理 API Key 中的中文引号
        api_key = cls._clean_api_key(api_key)

        # 创建配置实例
        config = cls(
            api_key=api_key,
            api_base=api_base,
            default_model=os.getenv("DEFAULT_MODEL", "gpt-4o-mini"),
            agent_max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
            agent_verbose=os.getenv("AGENT_VERBOSE", "false").lower() == "true",
        )

        # 初始化可用模型列表
        config._init_models()

        return config

    @staticmethod
    def _clean_api_key(api_key: str) -> str:
        """清理 API Key 中的中文引号"""
        if not api_key:
            return api_key
        api_key = api_key.strip()
        # 移除中文引号
        if api_key.startswith('\u201c') and api_key.endswith('\u201d'):
            api_key = api_key[1:-1]
        elif api_key.startswith('\u2018') and api_key.endswith('\u2019'):
            api_key = api_key[1:-1]
        return api_key

    def _init_models(self):
        """初始化预定义的模型配置"""
        # OpenAI 模型
        self.available_models = {
            "gpt-4o-mini": ModelConfig(
                name="GPT-4o Mini",
                model_id="gpt-4o-mini",
                provider="openai",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
                base_url=self.api_base,
            ),
            "gpt-4o": ModelConfig(
                name="GPT-4o",
                model_id="gpt-4o",
                provider="openai",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
                base_url=self.api_base,
            ),
            "gpt-4-turbo": ModelConfig(
                name="GPT-4 Turbo",
                model_id="gpt-4-turbo",
                provider="openai",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
                base_url=self.api_base,
            ),
            "gpt-4": ModelConfig(
                name="GPT-4",
                model_id="gpt-4",
                provider="openai",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
                base_url=self.api_base,
            ),
            "gpt-3.5-turbo": ModelConfig(
                name="GPT-3.5 Turbo",
                model_id="gpt-3.5-turbo",
                provider="openai",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
                base_url=self.api_base,
            ),
        }

        # 从环境变量加载自定义模型
        self._load_custom_models()

    def _load_custom_models(self):
        """从环境变量加载自定义模型配置"""
        # 格式: CUSTOM_MODELS=model1:model_id:temp:tokens;model2:model_id:temp:tokens
        custom_models_str = os.getenv("CUSTOM_MODELS", "")
        if not custom_models_str:
            return

        for model_def in custom_models_str.split(";"):
            parts = model_def.split(":")
            if len(parts) >= 2:
                name = parts[0]
                model_id = parts[1]
                temperature = float(parts[2]) if len(parts) > 2 else 0.0
                max_tokens = int(parts[3]) if len(parts) > 3 else None

                self.available_models[name] = ModelConfig(
                    name=name,
                    model_id=model_id,
                    provider="custom",
                    temperature=temperature,
                    max_tokens=max_tokens,
                    base_url=self.api_base,
                )

    def get_model_config(self, model_name: Optional[str] = None) -> ModelConfig:
        """
        获取指定模型的配置

        Args:
            model_name: 模型名称，如果为 None 则使用默认模型

        Returns:
            ModelConfig: 模型配置对象

        Raises:
            ValueError: 如果指定的模型不存在
        """
        if model_name is None:
            model_name = self.default_model

        # 检查是否是预定义模型
        if model_name in self.available_models:
            return self.available_models[model_name]

        # 如果不是预定义模型，创建一个临时配置
        return ModelConfig(
            name=model_name,
            model_id=model_name,
            provider="custom",
            base_url=self.api_base,
        )

    def list_models(self) -> List[str]:
        """返回所有可用模型的名称列表"""
        return list(self.available_models.keys())

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型的详细信息"""
        config = self.get_model_config(model_name)
        return {
            "name": config.name,
            "model_id": config.model_id,
            "provider": config.provider,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }


# 全局配置实例
_global_config: Optional[AppConfig] = None


def get_config(env_file: Optional[str] = None, reload: bool = False) -> AppConfig:
    """
    获取全局配置实例（单例模式）

    Args:
        env_file: .env 文件路径
        reload: 是否重新加载配置

    Returns:
        AppConfig: 配置实例
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = AppConfig.from_env(env_file)

    return _global_config


def reload_config(env_file: Optional[str] = None) -> AppConfig:
    """重新加载配置"""
    return get_config(env_file, reload=True)
