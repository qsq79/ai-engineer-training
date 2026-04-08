# 企业级安全智能助手

面向企业级SaaS安全平台，提供多Agent协同的智能安全分析助手，通过专业化分工和协作，为安全运营团队提供全方位的智能支持。

## 📋 项目概述

本项目是一个企业级多Agent安全智能助手，核心特点：

- **专业化分工**：8个专业Agent各司其职，协作完成复杂任务
- **企业级特性**：多租户隔离、权限控制、监控告警、审计合规
- **可扩展架构**：模块化设计，易于扩展新Agent和新功能
- **业务价值明确**：解决真实痛点，提升安全运营效率

## 🚀 快速开始

### 前置要求

- Python 3.13+
- PostgreSQL 14+
- Redis 6+
- OpenAI API密钥

### 安装步骤

1. **克隆项目**
```bash
cd src/app/enterprise-security-assistant
```

2. **创建虚拟环境并安装依赖**
```bash
# 使用启动脚本（推荐）
./start.sh

# 或手动执行
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 复制配置模板
cp .env.example .env

# 编辑.env文件，填入实际的配置
nano .env  # 或使用其他编辑器
```

**关键配置项**：
- `ESA_OPENAI_API_KEY`: OpenAI API密钥（必填）
- `ESA_DATABASE_URL`: PostgreSQL数据库连接URL
- `ESA_REDIS_URL`: Redis连接URL
- `ESA_JWT_SECRET_KEY`: JWT密钥（生产环境必须修改）

4. **启动应用**
```bash
# 使用启动脚本
./start.sh

# 或直接运行
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

5. **访问应用**
- API文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- API健康检查：http://localhost:8000/api/v1/health

## 📁 项目结构

```
enterprise-security-assistant/
├── src/                        # 源代码目录
│   ├── main.py                # 主应用程序入口
│   ├── config/                 # 配置管理
│   │   └── settings.py
│   ├── database/               # 数据库和缓存
│   │   ├── db_pool.py
│   │   └── redis_pool.py
│   ├── api/                    # API层
│   │   └── middleware/         # 中间件
│   │       ├── auth.py          # 认证中间件
│   │       ├── rate_limit.py    # 限流中间件
│   │       └── logging.py       # 日志中间件
│   ├── utils/                  # 工具函数
│   │   └── logger.py
│   └── agents/                 # Agent实现（待后续任务创建）
├── .env.example                # 环境变量配置示例
├── .env                       # 实际的环境变量配置（需要自行创建）
├── requirements.txt            # Python依赖
├── start.sh                   # 启动脚本
└── README.md                  # 本文件
```

## 🔧 配置说明

所有配置项都在`.env`文件中配置，主要配置类别：

### 应用基础配置
- `ESA_APP_NAME`: 应用名称
- `ESA_APP_VERSION`: 应用版本
- `ESA_DEBUG`: 调试模式（true/false）
- `ESA_HOST`: 服务器主机地址
- `ESA_PORT`: 服务器端口

### 日志配置
- `ESA_LOG_LEVEL`: 日志级别（DEBUG/INFO/WARNING/ERROR）
- `ESA_LOG_FILE`: 日志文件路径
- `ESA_LOG_ROTATION`: 日志轮转大小
- `ESA_LOG_RETENTION`: 日志保留时间

### OpenAI配置
- `ESA_OPENAI_API_KEY`: OpenAI API密钥
- `ESA_OPENAI_MODEL`: 默认模型
- `ESA_OPENAI_TEMPERATURE`: LLM温度参数
- `ESA_OPENAI_MAX_TOKENS`: 最大Token数

### 数据库配置
- `ESA_DATABASE_URL`: PostgreSQL连接URL
- `ESA_DATABASE_POOL_SIZE`: 连接池大小
- `ESA_DATABASE_MAX_OVERFLOW`: 最大溢出

### Redis配置
- `ESA_REDIS_URL`: Redis连接URL
- `ESA_REDIS_POOL_SIZE`: 连接池大小

### 安全配置
- `ESA_JWT_SECRET_KEY`: JWT密钥
- `ESA_JWT_ALGORITHM`: JWT算法
- `ESA_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: 访问Token过期时间

### 限流配置
- `ESA_RATE_LIMIT_ENABLED`: 是否启用限流
- `ESA_RATE_LIMIT_DEFAULT_QPS`: 默认QPS限制
- `ESA_RATE_LIMIT_TENANT_QPS`: 租户QPS限制
- `ESA_RATE_LIMIT_USER_QPS`: 用户QPS限制

## 🏗️ 架构说明

### 技术栈
- **Agent框架**: LangChain + LangGraph
- **Web框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy
- **缓存**: Redis
- **向量数据库**: Chroma / FAISS
- **LLM**: OpenAI GPT-4
- **监控**: Prometheus + Grafana
- **日志**: Loguru

### 核心模块

#### 1. 配置管理（config/settings.py）
- 使用Pydantic Settings实现配置管理
- 支持环境变量和.env文件
- 提供配置验证和默认值

#### 2. 日志模块（utils/logger.py）
- 使用Loguru实现日志管理
- 支持控制台和文件输出
- 支持日志轮转和压缩
- 提供上下文绑定和过滤

#### 3. 数据库连接池（database/db_pool.py）
- 实现PostgreSQL异步连接池
- 提供会话管理（上下文管理器）
- 支持连接池配置和自动回收

#### 4. Redis连接池（database/redis_pool.py）
- 实现Redis连接池管理
- 提供便捷的Redis操作方法
- 支持分布式锁和限流

#### 5. 认证中间件（api/middleware/auth.py）
- 实现JWT认证和验证
- 提供用户信息提取
- 支持权限检查和Token黑名单

#### 6. 限流中间件（api/middleware/rate_limit.py）
- 实现多级限流（系统级、租户级、用户级）
- 实现熔断器机制（CLOSED、OPEN、HALF_OPEN）
- 提供限流统计信息

#### 7. 日志中间件（api/middleware/logging.py）
- 记录所有API请求和响应
- 支持性能监控（处理时间）
- 支持审计日志（脱敏处理）

## 📝 开发指南

### 代码规范
- **类名**：大驼峰（PascalCase）
- **函数名**：小写+下划线（snake_case）
- **常量**：大写+下划线（UPPER_SNAKE_CASE）
- **私有变量**：前缀下划线（_private_variable）

### 提交代码
1. 确保代码通过格式检查
2. 添加适当的文档字符串
3. 编写单元测试（覆盖率≥80%）
4. 更新相关文档

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_specific.py

# 查看测试覆盖率
pytest --cov=src --cov-report=html
```

## 🧪 待完成功能

根据任务规划，以下功能将在后续任务中实现：

### Phase 1: 核心Agent开发
- [ ] 任务2: 实现数据库模型
- [ ] 任务6: 实现意图识别Agent
- [ ] 任务7: 实现工作流协调Agent
- [ ] 任务8: 实现日志查询Agent
- [ ] 任务9: 实现评分解读Agent
- [ ] 任务10: 实现威胁分析Agent
- [ ] 任务11: 实现合规检查Agent

### Phase 2: 企业级特性
- [ ] 任务12: 实现多租户隔离
- [ ] 任务13: 实现权限控制（RBAC）
- [ ] 任务14: 实现监控告警
- [ ] 任务15: 实现审计日志

### Phase 3: 扩展功能
- [ ] 任务16: 实现知识库Agent
- [ ] 任务17: 实现异常检测Agent

### Phase 4: API接口
- [ ] 完善API路由和端点
- [ ] 实现RESTful API完整接口

## 📚 相关文档

- [需求文档](.cospec/enterprise-security-assistant/requirements.md)
- [设计文档](.cospec/enterprise-security-assistant/design.md)
- [任务清单](.cospec/enterprise-security-assistant/tasks.md)
- [实施指南](IMPLEMENTATION_GUIDE.md)
- [技术架构](TECHNICAL_ARCHITECTURE.md)
- [产品设计](PRODUCT_DESIGN.md)

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见LICENSE文件

## 👥 作者

- 产品经理：安全服务平台产品经理（10年经验）
- 技术负责人：架构师
- 项目经理：技术负责人

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与社区讨论

---

**注意**：本项目正在开发中，部分功能尚未完成。请关注任务清单了解当前进度。
