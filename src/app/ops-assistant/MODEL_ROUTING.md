# 智能模型路由说明

## 概述

智能模型路由是运维助手的核心特性之一，使用 LangChain 的 `@wrap_model_call` 装饰器实现。系统会根据任务类型、复杂度、对话长度等因素自动选择最合适的模型，实现成本与性能的最优平衡。

## 设计理念

在生产环境中，**系统自动控制**比用户手动选择更合适，原因如下：

1. **成本优化**: 简单查询使用低成本模型，复杂任务使用高性能模型
2. **性能优化**: 根据任务需求动态调整，避免过度使用昂贵模型
3. **用户体验**: 用户无需了解模型差异，系统透明地处理
4. **运维简化**: 统一管理模型策略，便于监控和调优

## 路由策略

### 模型层级

| 层级 | 模型 | 用途 | 成本 |
|------|------|------|------|
| fast | gpt-4o-mini | 快速、简单查询 | 低 |
| balanced | gpt-4o | 平衡性能和成本 | 中 |
| powerful | gpt-4-turbo | 高性能、复杂分析 | 高 |
| premium | gpt-4 | 最强能力、长对话 | 最高 |

### 路由规则

#### 1. 任务复杂度分析

```python
# 简单任务关键词
SIMPLE_TASKS = [
    'get', 'fetch', 'list', 'show', 'check',
    '获取', '显示', '检查', ...
]
→ 使用 fast 模型

# 复杂任务关键词
COMPLEX_TASKS = [
    'analyze', 'investigate', 'debug', 'troubleshoot',
    '分析', '调查', '调试', '排错', ...
]
→ 使用 powerful 模型

# 高精度任务
HIGH_PRECISION = [
    'security', 'auth', 'permission', 'compliance',
    '安全', '认证', '权限', '合规', ...
]
→ 使用 powerful 模型
```

#### 2. 对话长度

```python
# 短对话 (< 5 轮)
→ 使用 fast/balanced 模型

# 中等对话 (5-10 轮)
→ 使用 balanced 模型

# 长对话 (10-15 轮)
→ 使用 powerful 模型

# 超长对话 (> 15 轮)
→ 使用 premium 模型
```

#### 3. 工具调用次数

```python
# 无工具调用
→ 使用 fast 模型

# 少量工具调用 (1-2 次)
→ 使用 balanced 模型

# 中等工具调用 (3-5 次)
→ 使用 powerful 模型

# 大量工具调用 (> 5 次)
→ 使用 premium 模型
```

#### 4. 上下文大小

```python
# 短上下文 (< 1000 tokens)
→ 使用 fast 模型

# 长上下文 (> 8000 tokens)
→ 使用 premium 模型
```

## 中间件实现

### 核心代码

```python
from langchain.agents.middleware import wrap_model_call
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def intelligent_model_router(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """智能模型路由中间件"""

    # 1. 分析任务
    messages = request.state.get('messages', [])
    complexity = analyze_task_complexity(messages)
    context_size = calculate_context_size(messages)
    tool_calls = count_tool_calls(messages)

    # 2. 选择模型
    selected_model = select_model(complexity, context_size, tool_calls)

    # 3. 应用选择
    return handler(request.override(model=selected_model))
```

### 工作流程

```
用户输入
    ↓
Agent 调用模型
    ↓
@wrap_model_call 中间件拦截
    ↓
分析任务:
  - 任务类型
  - 对话长度
  - 工具调用次数
  - 上下文大小
    ↓
选择最合适的模型
    ↓
使用选定模型调用 API
    ↓
返回结果
```

## 配置选项

### 环境变量

```env
# 启用智能路由
ENABLE_MODEL_ROUTING=true

# 调试模式（输出路由决策）
MODEL_ROUTING_DEBUG=true
```

### 编程配置

```python
from core import OpsAssistantAgent

# 创建 Agent（默认启用智能路由）
agent = OpsAssistantAgent()

# 禁用智能路由
agent = OpsAssistantAgent(enable_smart_routing=False)

# 运行时切换
agent.enable_model_routing()   # 启用
agent.disable_model_routing()  # 禁用
```

## 调试输出

启用 `MODEL_ROUTING_DEBUG=true` 后，每次模型调用都会输出路由决策：

```
[Model Routing]
  Messages: 1
  Context size: ~23 tokens
  Tool calls: 0
  Selected model: gpt-4o-mini
```

## 示例场景

### 场景 1: 简单查询

```
输入: "Get user info for alice"

路由决策:
  - 任务类型: 简单 (包含 "get")
  - 对话长度: 1 轮
  - 工具调用: 0 次

选择: gpt-4o-mini (fast)
原因: 简单查询，快速响应
```

### 场景 2: 复杂分析

```
输入: "Analyze login failure patterns for bob"

路由决策:
  - 任务类型: 复杂 (包含 "analyze")
  - 对话长度: 1 轮
  - 工具调用: 0 次

选择: gpt-4-turbo (powerful)
原因: 需要深度分析
```

### 场景 3: 多轮对话

```
第 1-3 轮: gpt-4o-mini
第 4-6 轮: gpt-4o (自动升级)
第 7-10 轮: gpt-4-turbo (继续升级)
第 10+ 轮: gpt-4 (最高级)
```

## 性能优化

### 成本优化

- 简单查询占比约 60-70%，使用低成本模型
- 复杂查询占比约 20-30%，使用中高性能模型
- 长对话占比约 10%，使用高性能模型

### 性能监控

```python
# 统计模型使用情况
agent._model_usage_stats = {
    'gpt-4o-mini': 150,
    'gpt-4o': 45,
    'gpt-4-turbo': 12,
    'gpt-4': 3,
}
```

## 扩展性

### 添加自定义路由规则

编辑 `config/model_router.py` 中的 `ModelRoutingConfig` 类：

```python
class ModelRoutingConfig:
    # 添加新的任务类型
    URGENT_TASKS = [
        'urgent', 'emergency', 'critical',
        '紧急', '紧急情况', ...
    ]

    # 添加新的模型层级
    MODEL_TIERS = {
        'fast': 'gpt-4o-mini',
        'balanced': 'gpt-4o',
        'powerful': 'gpt-4-turbo',
        'premium': 'gpt-4',
        'urgent': 'gpt-4',  # 紧急任务专用
    }
```

### 自定义选择逻辑

修改 `select_model` 方法实现更复杂的路由逻辑：

```python
def select_model(self, request: ModelRequest) -> str:
    # 基于用户类型的路由
    user_tier = request.runtime.context.get('user_tier', 'free')

    if user_tier == 'enterprise':
        return 'gpt-4'
    elif user_tier == 'pro':
        return 'gpt-4-turbo'
    else:
        return self._base_select_model(request)
```

## 最佳实践

1. **默认启用智能路由**: 让系统自动处理模型选择
2. **监控路由决策**: 定期查看调试输出，优化路由策略
3. **设置预算限制**: 使用 `ModelCallLimitMiddleware` 防止过度调用
4. **AB 测试**: 对比固定模型和智能路由的成本与性能
5. **定期调优**: 根据实际使用数据调整路由规则

## 参考资料

- [LangChain Middleware 文档](https://docs.langchain.com/oss/python/langchain/middleware)
- [Dynamic Model 文档](https://docs.langchain.com/oss/python/langchain/agents)
- [@wrap_model_call API 参考](https://docs.langchain.com/oss/python/langchain/middleware/custom)
