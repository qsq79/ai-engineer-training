# 运维助手使用指南

## 快速开始

### 1. 安装依赖

```bash
cd src/app/ops-assistant
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key。

### 3. 运行程序

#### 方式一：交互式聊天（推荐）

```bash
cd src/app/ops-assistant
python main.py
```

然后可以输入问题，例如：
```
您的问题: 用户 bob 登录失败的原因是什么？
您的问题: 查询 alice 的用户信息
您的问题: user002 为什么无法登录？
```

#### 方式二：单次查询

```bash
cd src/app/ops-assistant

# 查询问题
python main.py --query "用户 bob 登录失败的原因是什么？"

# 查询用户信息
python main.py --user alice

# 查询用户登录日志
python main.py --user bob --log
```

## 测试场景

### 场景 1: 查询正常用户

**输入**: "用户 alice 的信息"

**预期输出**:
- 显示 alice 的基本信息（ID、邮箱、状态等）
- 状态为 active，账号正常

### 场景 2: 分析登录失败

**输入**: "用户 bob 登录失败的原因是什么？"

**预期输出**:
- Agent 自动调用 check_login_log 工具
- 显示 bob 最近3次登录失败，原因都是密码错误
- 提示账号可能被锁定

### 场景 3: 账号过期问题

**输入**: "用户 david 为什么登录不了？"

**预期输出**:
- Agent 调用工具查询
- 显示 david 的状态是 inactive
- 登录日志显示 "账号已过期"

### 场景 4: IP 白名单问题

**输入**: "查看 eve 的登录日志"

**预期输出**:
- 显示 eve 的登录记录
- 其中一次失败原因是 "IP地址不在白名单中"

## 测试说明

本项目的工具使用 Mock 数据（在 `tools/mock_data.py` 中定义），因此可以直接测试而无需连接真实的数据源。Mock 数据包含了几种典型场景的用户和登录日志数据，用于验证 Agent 的工具调用和问题分析能力。

测试场景包括：
- 正常用户查询（alice）
- 账号锁定分析（bob）
- 账号过期检查（david）
- IP 白名单问题（eve）

这些测试用例可以帮助验证 Agent 能够正确识别问题并调用相应的工具进行分析。

## 可用的测试用户

| 用户名 | 用户ID | 状态 | 描述 |
|--------|--------|------|------|
| alice | user001 | active | 正常用户，登录成功 |
| bob | user002 | locked | 多次密码错误被锁定 |
| charlie | user003 | active | 正常用户 |
| david | user004 | inactive | 账号过期 |
| eve | user005 | active | 有IP白名单问题 |

## 架构说明

```
用户输入
    ↓
LangChain Agent (判断需要调用哪个工具)
    ↓
┌───────────────┬──────────────────┐
│  get_user_info│ check_login_log  │
│  获取用户信息  │   检查登录日志    │
└───────┬───────┴────────┬─────────┘
        ↓                ↓
    Mock Data (模拟数据)
        ↓
    Agent 整合结果
        ↓
    输出回答
```

## 扩展建议

1. **添加更多工具**: 可以添加更多运维相关的工具，如：
   - 检查服务器状态
   - 查询系统日志
   - 重启服务
   - 检查资源使用情况

2. **连接真实数据**: 将 mock_data 替换为真实的数据库查询

3. **添加记忆功能**: 让 Agent 记住对话历史，支持多轮对话

4. **添加日志记录**: 记录所有查询和操作，便于审计
