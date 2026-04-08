#!/bin/bash
# 企业级安全智能助手 - 启动脚本

echo "=========================================="
echo "企业级安全智能助手"
echo "=========================================="
echo ""

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✓ 虚拟环境已存在"
else
    echo "✗ 虚拟环境不存在，正在创建..."
    python3 -m venv .venv
fi

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source .venv/bin/activate

# 检查.env文件
if [ -f ".env" ]; then
    echo "✓ 配置文件(.env)已存在"
else
    echo "✗ 配置文件(.env)不存在，正在创建..."
    cp .env.example .env
    echo ""
    echo "⚠️  请编辑.env文件，填入实际的配置值"
    echo "⚠️  特别注意："
    echo "   - OPENAI_API_KEY: 必须设置为有效的OpenAI API密钥"
    echo "   - DATABASE_URL: 必须设置为实际的数据库连接URL"
    echo "   - REDIS_URL: 必须设置为实际的Redis连接URL"
    echo "   - JWT_SECRET_KEY: 生产环境必须设置为强密钥"
    echo ""
    read -p "按Enter键继续（请先配置.env文件）..."
fi

# 安装依赖
echo ""
echo "安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 确保日志目录存在
mkdir -p logs

echo ""
echo "=========================================="
echo "准备启动应用..."
echo "=========================================="
echo ""
echo "应用配置："
echo "  - 主机: ${ESA_HOST:-0.0.0.0}"
echo "  - 端口: ${ESA_PORT:-8001}"
echo "  - 调试模式: ${ESA_DEBUG:-false}"
echo ""
echo "启动命令："
echo "  uvicorn src.main:app --host ${ESA_HOST:-0.0.0.0} --port ${ESA_PORT:-8001} --reload"
echo ""
echo "=========================================="
echo ""

# 启动应用
uvicorn src.main:app --host ${ESA_HOST:-0.0.0.0} --port ${ESA_PORT:-8001} --reload
