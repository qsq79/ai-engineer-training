#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运维助手 - 命令行入口

使用 LangChain 构建的运维助手，可以帮助分析用户登录问题。

运行前请确保：
1. 已安装依赖: pip install -r requirements.txt
2. 已配置环境变量: 复制 .env.example 为 .env 并填入 API Key

使用方式:
    python main.py                    # 启动交互式聊天
    python main.py --query "问题"      # 直接查询一个问题
    python main.py --user alice       # 查询指定用户
    python main.py --list-models      # 列出可用模型
"""

import argparse
import io
import os
import sys

# ============================================================
# 第一时间设置编码 - 必须在任何导入之前
# ============================================================
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["LANG"] = "C.UTF-8"
os.environ["LANGCHAIN_VERBOSE"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_API_KEY"] = ""  # 禁用 LangSmith

# 立即修复 stdout 和 stderr
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')

from core import OpsAssistantAgent
from config import get_config


def list_models():
    """列出所有可用的模型"""
    config = get_config()
    models = config.list_models()

    print("\nAvailable Models:")
    print("=" * 60)
    for model_name in models:
        info = config.get_model_info(model_name)
        is_default = " (default)" if model_name == config.default_model else ""
        print(f"  {model_name:20} - {info['name']}{is_default}")
        print(f"                       Provider: {info['provider']}")
        print(f"                       Temperature: {info['temperature']}")
        if info['max_tokens']:
            print(f"                       Max Tokens: {info['max_tokens']}")
        print()


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="Ops Assistant - Analyze user login issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                        Interactive mode
  python main.py --query "bob login"     Direct query
  python main.py --user alice            Get user info
  python main.py --user bob --log        Check login logs
  python main.py --list-models           List available models
  python main.py --model gpt-4o           Use specific model

Interactive Commands:
  /models                               List available models
  /model <name>                         Switch to another model
  /list                                 Alias for /models
  quit or exit                          Exit the program
        """
    )

    parser.add_argument(
        '--query', '-q',
        help='Query string',
        type=str
    )

    parser.add_argument(
        '--user', '-u',
        help='Username to query',
        type=str
    )

    parser.add_argument(
        '--log', '-l',
        help='Show login logs for user',
        action='store_true'
    )

    parser.add_argument(
        '--model', '-m',
        help='Model to use (default: from .env or gpt-4o-mini)',
        type=str,
        default=None
    )

    parser.add_argument(
        '--temperature', '-t',
        help='Temperature override',
        type=float,
        default=None
    )

    parser.add_argument(
        '--max-tokens',
        help='Max tokens override',
        type=int,
        default=None
    )

    parser.add_argument(
        '--list-models',
        help='List all available models and exit',
        action='store_true'
    )

    args = parser.parse_args()

    # 列出模型
    if args.list_models:
        list_models()
        return

    # 初始化 Agent
    print("Initializing Ops Assistant...")
    try:
        agent = OpsAssistantAgent(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        print(f"Ready! Using model: {agent.model_config.name}")
        print()
    except Exception as e:
        print(f"Init failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 处理不同的命令模式
    if args.query:
        # 直接查询模式
        print(f"Query: {args.query}")
        print("\nProcessing...\n")
        response = agent.query(args.query)
        print(f"Response:\n{response}")

    elif args.user:
        # 用户查询模式
        if args.log:
            query = f"Check login logs for {args.user} and analyze failures"
        else:
            query = f"Get user info for {args.user}"

        print(f"Query: {query}")
        print("\nProcessing...\n")
        response = agent.query(query)
        print(f"Response:\n{response}")

    else:
        # 交互式聊天模式
        agent.chat()


if __name__ == '__main__':
    main()
