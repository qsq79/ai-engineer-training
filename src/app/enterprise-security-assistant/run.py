#!/usr/bin/env python3
"""
企业级安全智能助手启动脚本
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 现在导入应用
from app.enterprise_security_assistant.main import app

if __name__ == '__main__':
    import uvicorn
    print("启动企业级安全智能助手...")
    print("应用名称: app.enterprise_security_assistant.main:app")
    uvicorn.run(app, host="0.0.0.0", port=8000)
