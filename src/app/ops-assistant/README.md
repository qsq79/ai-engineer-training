# 运维助手 (Ops Assistant)

基于 LangChain 1.x+ 构建的智能运维助手，专门用于分析用户登录问题。

## 功能特性

- 🤖 **智能 Agent**: 使用 LangChain 1.x+ 最新的 `create_agent` API 构建
- 🔌 **微服务架构**: 通过 HTTP 调用独立的用户管理 API 服务
  - `get_user_info`: 获取用户基本信息
  - `check_login_log`: 查询用户登录日志
- 🎯 **自动路由**: Agent 根据用户问题自动决定调用哪个工具
- 💬 **交互式 CLI**: 支持命令行交互和单次查询两种模式
- 🌊 **流式输出**: 支持流式响应（可选）
- 🔧 **统一配置管理**: 支持配置文件管理和环境变量配置
- 🔄 **动态模型选择**: 支持多种模型切换和参数配置
- 🧠 **智能模型路由**: 使用 `@wrap_model_call` 中间件实现智能模型选择
- 🛡️ **工具错误处理**: 使用 `@wrap_tool_call` 中间件实现工具调用错误捕获和日志记录
- 📊 **执行监控**: 记录工具调用时间和状态，便于问题排查

## 项目结构

```
ops-assistant/
├── config/
│   ├── __init__.py
│   └── settings.py       # 统一配置管理模块
├── core/
│   ├── __init__.py
│   └── agent.py          # LangChain Agent 核心实现
├── tools/
│   ├── __init__.py
│   ├── mock_data.py      # 模拟数据（用户信息、登录日志）
│   └── ops_tools.py      # LangChain 工具定义
├── main.py               # 命令行入口
├── test_basic.py         # 基础工具测试（无需 API）
├── test_config.py        # 配置系统测试
├── debug_test.py         # 调试测试
├── requirements.txt      # 项目依赖
├── .env.example          # 环境变量示例
├── README.md            # 项目说明
├── API_REFERENCE.md     # LangChain 1.x+ API 参考说明
├── TOOL_ERROR_HANDLING.md  # 工具错误处理说明
└── USAGE.md             # 详细使用指南
```

## 技术栈

| 包名 | 版本 | 说明 |
|------|------|------|
| langchain | >=1.2.10 | LangChain 核心库 |
| langchain-core | >=1.2.14 | LangChain 核心组件 |
| langchain-openai | >=1.1.10 | OpenAI 集成 |
| langchain-community | >=0.4.1 | 社区集成 |
| langgraph | >=1.0.9 | Agent 运行时 |

## 安装与配置

### 前置要求

本项目需要同时运行两个服务：

1. **ops-assistant-api**: 用户管理 REST API 服务
2. **ops-assistant**: LangChain Agent 服务

### 1. 安装 API 服务依赖

```bash
cd /Users/quan/langchain-leanring/src/app/ops-assistant-api
pip install -r requirements.txt
```

### 2. 启动 API 服务

```bash
# 在 ops-assistant-api 目录下
python -m app.main
```

API 将在 `http://localhost:8000` 启动。

### 3. 安装 Agent 服务依赖

```bash
cd /Users/quan/langchain-leanring/src/app/ops-assistant
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key:

```env
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# 默认模型选择
DEFAULT_MODEL=gpt-4o-mini

# Ops Assistant API 配置
# 用户管理微服务的地址
OPS_API_BASE_URL=http://localhost:8000
OPS_API_TIMEOUT=30

# 工具错误处理日志配置（可选）
# TOOL_LOG_LEVEL=DEBUG   # 可选: DEBUG, INFO, WARNING, ERROR
# TOOL_LOG_FILE=logs/tool_errors.log  # 可选: 日志文件路径
```

### 3. 配置模型参数

项目支持以下预定义模型：

| 模型名称 | 说明 | 默认温度 | 最大 Token |
|---------|------|---------|-----------|
| gpt-4o-mini | GPT-4o Mini | 0.0 | 4096 |
| gpt-4o | GPT-4o | 0.0 | 4096 |
| gpt-4-turbo | GPT-4 Turbo | 0.0 | 4096 |
| gpt-4 | GPT-4 | 0.0 | 4096 |
| gpt-3.5-turbo | GPT-3.5 Turbo | 0.0 | 4096 |

你也可以通过环境变量 `CUSTOM_MODELS` 添加自定义模型。

## 使用方式

### 列出可用模型

```bash
python main.py --list-models
```

### 交互式聊天模式

```bash
# 使用默认模型
python main.py

# 使用指定模型
python main.py --model gpt-4o

# 指定模型参数
python main.py --model gpt-4o --temperature 0.7 --max-tokens 2000
```

交互模式支持的命令：
- `/models` 或 `/list` - 列出所有可用模型
- `/model <name>` - 动态切换模型
- `quit` 或 `exit` - 退出程序

### 单次查询模式

```bash
# 基本查询
python main.py --query "Get user info for alice"

# 使用指定模型查询
python main.py --model gpt-4o --query "Check login logs for bob"

# 用户查询模式
python main.py --user alice
python main.py --user bob --log

# 带参数覆盖
python main.py --model gpt-4o --temperature 0.8 --query "Tell me a joke"
```

### 编程方式使用

```python
from core import OpsAssistantAgent
from config import get_config, ModelConfig

# 使用默认配置
agent = OpsAssistantAgent()
response = agent.query("Get user info for alice")

# 指定模型
agent = OpsAssistantAgent(model="gpt-4o")
response = agent.query("Check login logs for bob")

# 参数覆盖
agent = OpsAssistantAgent(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=2000
)

# 动态切换模型
agent.switch_model("gpt-3.5-turbo")

# 获取当前模型信息
info = agent.get_current_model_info()
print(f"Current model: {info}")

# 列出可用模型
models = agent.list_available_models()
print(f"Available models: {models}")
```

### 自定义模型配置

```python
from config import AppConfig, ModelConfig

# 创建自定义配置
config = AppConfig()
config.available_models["my-model"] = ModelConfig(
    name="My Custom Model",
    model_id="my-custom-model-id",
    provider="custom",
    temperature=0.5,
    max_tokens=2048,
    base_url="https://my-api.com/v1",
)

# 使用自定义配置
agent = OpsAssistantAgent(
    model="my-model",
    config=config
)
```

## 配置系统详解

### ModelConfig 类

```python
@dataclass
class ModelConfig:
    name: str              # 模型显示名称
    model_id: str          # 模型 ID（用于 API 调用）
    provider: str          # 提供商
    temperature: float     # 温度参数
    max_tokens: int        # 最大 token 数
    timeout: int           # 超时时间
    base_url: str          # API Base URL
```

### AppConfig 类

```python
# 从环境变量加载配置
config = AppConfig.from_env(".env")

# 获取模型配置
model_config = config.get_model_config("gpt-4o-mini")

# 列出所有模型
models = config.list_models()

# 获取模型信息
info = config.get_model_info("gpt-4o")
```

### 全局配置访问

```python
from config import get_config, reload_config

# 获取全局配置（单例模式）
config = get_config()

# 重新加载配置
config = reload_config()
```

## 测试

### 工具测试（无需 API）

```bash
python test_basic.py
```

### 配置系统测试

```bash
python test_config.py
```

### 调试测试

```bash
python debug_test.py
```

## 测试数据说明

项目包含以下模拟用户：

| 用户ID | 用户名 | 状态 | 角色 | 说明 |
|--------|--------|------|------|------|
| user001 | alice | active | developer | 正常用户 |
| user002 | bob | locked | admin | 多次密码错误被锁定 |
| user003 | charlie | active | viewer | 正常用户 |
| user004 | david | inactive | developer | 账号过期 |
| user005 | eve | active | analyst | 有IP白名单问题 |

## 架构说明

### LangChain 1.x+ Agent 架构

```
用户输入 (messages)
    ↓
create_agent (基于 LangGraph)
    ↓
┌──────────────────────────────────┐
│  Model Node (LLM 决策)           │
│  - 决定是否调用工具              │
│  - 选择哪个工具                  │
│  - 生成工具参数                  │
└──────────┬───────────────────────┘
           │ (需要调用工具)
           ↓
┌──────────────────────────────────┐
│  Tools Node (执行工具)           │
│  - get_user_info                 │
│  - check_login_log               │
└──────────┬───────────────────────┘
           │ (返回结果)
           ↓
     回到 Model Node
           │
           ↓ (无需调用工具)
     输出最终结果
```

### 配置系统架构

```
.env 文件 / 环境变量
    ↓
AppConfig (统一配置管理)
    ↓
┌─────────────────────────────┐
│  ModelConfig (模型配置)      │
│  - 预定义模型列表            │
│  - 自定义模型支持            │
│  - 参数配置                  │
└──────────┬──────────────────┘
           │
           ↓
    ChatOpenAI (LLM 初始化)
           │
           ↓
    create_agent (Agent 创建)
```

## LangChain 1.x+ 主要变化

1. **更简洁的 API**: 使用 `create_agent` 替代 `create_tool_calling_agent` + `AgentExecutor`
2. **标准消息格式**: 使用 `{"role": "user", "content": "..."}` 格式
3. **基于 LangGraph**: 内部使用 LangGraph 构建，提供更强的编排能力
4. **配置灵活性**: 支持动态模型切换和参数配置

更多详细信息请参考 [API_REFERENCE.md](API_REFERENCE.md)

## 示例对话

```
============================================================
Ops Assistant (Model: GPT-4o Mini)
Type 'quit' or 'exit' to exit
============================================================

Your question: Get user info for alice

Processing...

Response:
Here is the user information for Alice:

- **User ID:** user001
- **Username:** alice
- **Email:** alice@example.com
- **Status:** Active
- **Role:** Developer
- **Department:** Engineering

Your question: /models

Available models:
  - gpt-4o-mini: GPT-4o Mini (current)
  - gpt-4o: GPT-4o
  - gpt-4-turbo: GPT-4 Turbo
  ...

Your question: /model gpt-4o

Switched to model: GPT-4o

Your question: quit

Thank you for using Ops Assistant. Goodbye!
```

## 扩展建议

1. **添加更多工具**:
   - 检查服务器状态
   - 查询系统日志
   - 重启服务
   - 检查资源使用情况

2. **扩展 API 服务**:
   - 在 `ops-assistant-api` 中添加更多端点
   - 替换 mock 数据为真实数据库连接
   - 添加用户认证和授权

3. **添加对话历史**: 使用 thread_id 保持多轮对话上下文

4. **添加中间件**:
   - 工具调用限制
   - 自动重试
   - 日志记录

5. **流式输出**: 使用 `agent.stream()` 实现流式响应

6. **多模型支持**:
   - 添加更多模型配置
   - 支持不同提供商
   - 模型性能比较

## 相关文档

- [API_REFERENCE.md](API_REFERENCE.md) - LangChain 1.x+ API 详细说明
- [TOOL_ERROR_HANDLING.md](TOOL_ERROR_HANDLING.md) - 工具错误处理说明
- [MODEL_ROUTING.md](MODEL_ROUTING.md) - 智能模型路由说明
- [USAGE.md](USAGE.md) - 详细使用指南

## 参考资料

- [LangChain 官方文档](https://docs.langchain.com)
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph 概述](https://docs.langchain.com/oss/python/langgraph/overview)
