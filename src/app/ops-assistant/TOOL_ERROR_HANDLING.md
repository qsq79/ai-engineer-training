# 工具调用错误处理说明

## 概述

工具调用错误处理中间件使用 `@wrap_tool_call` 装饰器实现，用于捕获和记录工具执行过程中的错误，便于线上问题排查。

## 功能特性

1. **自动错误捕获**: 捕获所有工具执行过程中的异常
2. **用户友好消息**: 向 LLM 返回简洁的描述性错误消息
3. **详细日志记录**: 记录完整的技术信息用于问题排查
4. **执行时间统计**: 记录每个工具调用的执行时间
5. **可配置日志级别**: 支持不同级别的日志输出

## 中间件实现

### 核心代码

```python
from langchain.agents.middleware import wrap_tool_call
from langchain.agents.middleware.types import ToolRequest, ToolResponse
from langchain.messages import ToolMessage

@wrap_tool_call
def tool_error_handler(
    request: ToolRequest,
    handler: Callable[[ToolRequest], ToolResponse]
) -> ToolResponse:
    """工具调用错误处理中间件"""
    start_time = datetime.now()

    try:
        # 执行工具调用
        response = handler(request)

        # 记录成功
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"[TOOL_SUCCESS] Tool: {tool_name} | Duration: {duration_ms:.2f}ms")

        return response

    except Exception as e:
        # 记录详细错误
        logger.error(f"[TOOL_ERROR] Tool: {tool_name} | Error: {type(e).__name__}: {str(e)}")
        logger.debug(f"[TOOL_ERROR] Traceback:\n{traceback.format_exc()}")

        # 返回用户友好的错误消息
        error_message = format_error_message(tool_name, e)

        return ToolMessage(
            content=error_message,
            tool_call_id=request.tool_call["id"]
        )
```

## 错误消息策略

### 对 LLM 的消息（简洁）

根据错误类型返回不同的描述性消息：

| 错误类型 | LLM 收到的消息 |
|---------|--------------|
| 连接失败 | Unable to connect to the service. Please check if the API server is running... |
| 超时 | Service request timed out. Please try again. |
| 404 | Resource not found. Please verify the input parameters. |
| 401/403 | Authentication error. Please check your API credentials. |
| 其他 | Tool execution failed: {ErrorType}. Please check the logs for details. |

### 日志记录（详细）

日志包含完整的技术信息：

```
2026-02-25 10:30:15 - __main__ - INFO - [tool_error_handler:_log_tool_call:45] - [TOOL_CALL] Tool: get_user_info
2026-02-25 10:30:15 - __main__ - DEBUG - [tool_error_handler:_log_tool_call:46] - [TOOL_INPUT] Input: {'user_identifier': 'alice'}
2026-02-25 10:30:16 - __main__ - ERROR - [tool_error_handler:_log_tool_error:60] - [TOOL_ERROR] Tool: get_user_info | Error: ConnectError: Connection refused | Duration: 1234.56ms
2026-02-25 10:30:16 - __main__ - DEBUG - [tool_error_handler:_log_tool_error:61] - [TOOL_ERROR] Traceback:
Traceback (most recent call last):
  File "...", line 53, in tool_error_handler
    response = handler(request)
  ...
```

## 配置选项

### 环境变量

```env
# 工具错误处理日志配置
TOOL_LOG_LEVEL=DEBUG   # 可选: DEBUG, INFO, WARNING, ERROR (默认: INFO)
TOOL_LOG_FILE=logs/tool_errors.log  # 可选: 日志文件路径 (默认仅控制台)
```

### 编程配置

```python
from core import OpsAssistantAgent

# 创建 Agent（默认启用工具错误处理）
agent = OpsAssistantAgent()

# 禁用工具错误处理
agent = OpsAssistantAgent(enable_tool_error_handler=False)
```

## 日志级别说明

| 级别 | 用途 | 输出内容 |
|------|------|---------|
| DEBUG | 开发调试 | 完整的工具输入、错误堆栈 |
| INFO | 生产环境 | 工具调用开始、成功/失败状态、执行时间 |
| WARNING | 警告信息 | 可能的问题 |
| ERROR | 错误信息 | 错误类型和消息 |

## 使用示例

### 正常流程

```bash
# 用户提问
Your question: Get user info for alice

# 日志输出
[TOOL_CALL] Tool: get_user_info
[TOOL_INPUT] Input: {'user_identifier': 'alice'}
[TOOL_SUCCESS] Tool: get_user_info | Duration: 45.23ms

# Agent 回复
Here is the user information for Alice:
- User ID: U001
- Username: alice
...
```

### 错误流程

```bash
# 用户提问
Your question: Get user info for alice

# 日志输出（API 服务未启动）
[TOOL_CALL] Tool: get_user_info
[TOOL_INPUT] Input: {'user_identifier': 'alice'}
[TOOL_ERROR] Tool: get_user_info | Error: ConnectError: Connection refused | Duration: 1234.56ms
[TOOL_ERROR] Traceback:
Traceback (most recent call last):
  ...

# Agent 回复（基于友好的错误消息）
I apologize, but I'm unable to retrieve the user information right now. The service appears to be unavailable. Please check if the API server is running at http://localhost:8000.
```

## 问题排查指南

### 1. API 服务未启动

**症状**: 日志显示 `Connection refused` 或 `Unable to connect`

**解决**:
```bash
# 启动 API 服务
cd src/app/ops-assistant-api
python -m app.main
```

### 2. API 超时

**症状**: 日志显示 `timeout` 或超时错误

**解决**: 增加 `OPS_API_TIMEOUT` 配置值

### 3. 认证错误

**症状**: 日志显示 `401` 或 `403`

**解决**: 检查 API 认证配置

### 4. 查看详细日志

```bash
# 启用 DEBUG 级别
export TOOL_LOG_LEVEL=DEBUG
python main.py

# 或指定日志文件
export TOOL_LOG_FILE=logs/tool_errors.log
python main.py
```

## 性能监控

中间件会记录每个工具调用的执行时间，可用于性能分析：

```bash
# 查看工具执行时间统计
grep "TOOL_SUCCESS" logs/tool_errors.log | awk '{print $NF}'
```

## 扩展性

### 自定义错误消息

编辑 `config/tool_middleware.py` 中的 `_format_error_message` 方法：

```python
def _format_error_message(self, tool_name: str, error: Exception) -> str:
    # 添加自定义错误类型处理
    if "custom_error" in str(error).lower():
        return "Your custom error message here"

    # ... 现有逻辑
```

### 添加新的日志处理器

```python
def _setup_logging(self):
    # 添加其他日志处理器（如发送到远程日志服务）
    from logging.handlers import RotatingFileHandler

    rotating_handler = RotatingFileHandler(
        'logs/tool_errors.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    rotating_handler.setFormatter(formatter)
    logger.addHandler(rotating_handler)
```

## 最佳实践

1. **生产环境**: 使用 `INFO` 级别，记录必要的调用信息
2. **开发环境**: 使用 `DEBUG` 级别，查看完整的输入输出
3. **日志文件**: 定期清理或使用日志轮转
4. **监控告警**: 基于 `TOOL_ERROR` 日志设置告警规则
5. **性能优化**: 定期检查工具执行时间，优化慢查询

## 参考资料

- [LangChain Middleware 文档](https://docs.langchain.com/oss/python/langchain/middleware)
- [@wrap_tool_call API 参考](https://docs.langchain.com/oss/python/langchain/middleware/custom)
