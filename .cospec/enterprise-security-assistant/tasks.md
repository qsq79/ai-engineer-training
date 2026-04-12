# 任务清单 - 企业安全助手登录与认证授权功能

## 概述

本文档将登录与认证授权功能需求拆解为可执行的任务清单，涵盖从数据模型扩展到功能验证的完整开发流程。

---

## 任务列表

### 任务1：扩展User数据模型 - 添加密码哈希字段

- [x] 1.1 修改User表添加password_hash字段
  - 在`src/database/models.py`中的User类添加`password_hash = Column(String(255), nullable=True, comment="bcrypt加密后的密码")`字段
  - 确保字段类型为String(255)以容纳bcrypt哈希值
  - _需求：[AUTH-007]_

- [x] 1.2 验证数据模型更新
  - 检查SQLAlchemy模型语法正确性
  - _需求：[AUTH-007]_

---

### 任务2：创建认证服务层 - 实现认证业务逻辑

- [x] 2.1 创建认证服务文件
  - 创建`src/services/auth_service.py`文件
  - 定义AuthService类处理认证业务逻辑
  - _需求：[AUTH-001, AUTH-002, AUTH-003, AUTH-007]_

- [x] 2.2 实现密码加密验证功能
  - 使用bcrypt库实现`hash_password(password: str) -> str`方法
  - 实现`verify_password(plain_password: str, hashed_password: str) -> bool`方法
  - 工作因子使用12（与需求文档一致）
  - _需求：[AUTH-001, AUTH-007]_

- [x] 2.3 实现用户认证方法
  - 实现`authenticate_user(username: str, password: str, tenant_id: str)`方法
  - 查询数据库验证用户名和密码
  - _需求：[AUTH-001]_

- [x] 2.4 实现Token管理方法
  - 继承auth.py中的Token创建方法
  - 实现Token验证和刷新逻辑
  - _需求：[AUTH-002]_

---

### 任务3：创建认证路由模块 - 实现登录注册接口

- [x] 3.1 创建认证路由文件
  - 创建`src/api/routes/auth.py`文件
  - 导入FastAPI、APIRouter等必要模块
  - _需求：[AUTH-001, AUTH-002, AUTH-003, AUTH-006, AUTH-007]_

- [x] 3.2 实现注册接口
  - 定义`POST /api/v1/auth/register`路由
  - 接受username、password、email、tenant_id参数
  - 验证用户名是否已存在
  - 验证密码最小长度（6位）
  - 使用bcrypt加密密码后存储
  - 返回用户ID和用户名
  - _需求：[AUTH-007]_

- [x] 3.3 实现登录接口
  - 定义`POST /api/v1/auth/login`路由
  - 接受username、password参数
  - 调用认证服务验证用户
  - 返回access_token和refresh_token
  - _需求：[AUTH-001]_

- [x] 3.4 实现Token刷新接口
  - 定义`POST /api/v1/auth/refresh`路由
  - 接受refresh_token参数
  - 验证refresh_token有效性
  - 返回新的access_token
  - _需求：[AUTH-002]_

- [x] 3.5 实现登出接口
  - 定义`POST /api/v1/auth/logout`路由
  - 获取当前Token并加入黑名单
  - 返回登出成功消息
  - _需求：[AUTH-003]_

- [x] 3.6 实现用户信息获取接口
  - 定义`GET /api/v1/auth/me`路由
  - 从request.state获取当前用户信息
  - 返回user_id、username、email、role、tenant_id、permissions
  - _需求：[AUTH-006]_

---

### 任务4：修改认证中间件 - 修复静态资源401问题

- [x] 4.1 扩展公共路径白名单
  - 修改`src/api/middleware/auth.py`中的`public_paths`列表
  - 添加`/api/v1/auth/register`（注册接口公开）
  - 添加`/api/v1/auth/login`（登录接口公开）
  - 添加`/api/v1/auth/refresh`（刷新Token公开）
  - _需求：[AUTH-005]_

- [x] 4.2 添加静态资源绕过逻辑
  - 在auth.py的`__call__`方法中添加favicon.ico跳过逻辑
  - 确保`/static`路径下的资源无需认证
  - 修复非API路径的静态请求401问题
  - _需求：[AUTH-004]_

- [x] 4.3 调整开发模式认证逻辑
  - 修改API请求的认证跳过逻辑
  - 确保开发模式下除公开接口外都需要认证
  - _需求：[AUTH-005]_

---

### 任务5：注册认证路由到应用

- [x] 5.1 挂载认证路由
  - 修改`src/main.py`
  - 导入auth路由模块
  - 使用`app.include_router(auth_router, prefix="/api/v1/auth", tags=["认证"])`注册路由
  - _需求：[AUTH-005]_

- [x] 5.2 确保中间件注册顺序正确
  - 检查认证中间件在应用中的注册位置
  - 确保静态资源在认证之前被处理
  - _需求：[AUTH-004, AUTH-005]_

---

### 任务6：功能验证测试

- [x] 6.1 测试用户注册功能
  - 发送POST请求到`/api/v1/auth/register`
  - 验证返回201状态码和用户信息
  - 测试用户名重复返回400错误
  - _需求：[AUTH-007]_

- [x] 6.2 测试用户登录功能
  - 发送POST请求到`/api/v1/auth/login`
  - 验证返回access_token和refresh_token
  - 测试错误密码返回401错误
  - _需求：[AUTH-001]_

- [x] 6.3 测试Token刷新功能
  - 使用refresh_token请求`/api/v1/auth/refresh`
  - 验证返回新的access_token
  - _需求：[AUTH-002]_

- [x] 6.4 测试登出功能
  - 使用access_token请求`/api/v1/auth/logout`
  - 验证Token被加入黑名单
  - _需求：[AUTH-003]_

- [x] 6.5 测试用户信息获取
  - 使用access_token请求`/api/v1/auth/me`
  - 验证返回当前用户信息
  - _需求：[AUTH-006]_

- [x] 6.6 测试静态资源访问
  - 访问`/favicon.ico`验证返回200
  - 访问`/static/css/style.css`验证返回200
  - _需求：[AUTH-004]_

---

## 任务依赖关系图

```
┌─────────────┐     ┌─────────────┐
│  任务1      │     │  任务4      │
│ 扩展数据模型 │     │ 修改中间件  │
└──────┬──────┘     └──────┬──────┘
       │                    │
       ▼                    │
┌─────────────┐            │
│  任务2      │            │
│ 认证服务层  │            │
└──────┬──────┘            │
       │                    │
       ▼                    │
┌─────────────┐            │
│  任务3      │            │
│ 认证路由    │◄───────────┘
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  任务5      │
│ 注册路由    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  任务6      │
│ 功能验证    │
└─────────────┘
```

---

## 验收标准

### 功能验收

- [x] 用户可以成功注册新账户
- [ ] 用户可以成功登录并获取access_token和refresh_token
- [x] 使用refresh_token可以刷新access_token
- [x] 登出后access_token无法再使用
- [x] 获取当前用户信息接口正常工作
- [x] 访问favicon.ico不再返回401
- [x] 访问/static路径下的资源无需认证
- [x] 未认证访问受保护API返回401

### 安全验收

- [x] 密码以bcrypt加密存储
- [x] Token包含过期时间
- [x] 登出后Token加入黑名单
