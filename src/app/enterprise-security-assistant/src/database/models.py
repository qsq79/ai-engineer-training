"""
企业级安全智能助手 - 数据库模型

使用SQLAlchemy AsyncORM定义所有数据表模型
"""
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, 
    JSON, ForeignKey, Index, Enum as SQLEnum, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB

from .db_pool import Base


class Tenant(Base):
    """租户信息表"""
    __tablename__ = "tenants"
    
    tenant_id = Column(String(50), primary_key=True, index=True, comment="租户ID")
    tenant_name = Column(String(100), nullable=False, comment="租户名称")
    status = Column(String(20), nullable=False, default="active", comment="状态")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="tenant")
    agent_calls = relationship("AgentCall", back_populates="tenant")
    workflow_executions = relationship("WorkflowExecution", back_populates="tenant")
    compliance_checks = relationship("ComplianceCheck", back_populates="tenant")
    token_usage_stats = relationship("TokenUsageStats", back_populates="tenant")


class User(Base):
    """用户信息表"""
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True, index=True, comment="用户ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, comment="租户ID")
    username = Column(String(100), nullable=False, index=True, comment="用户名")
    email = Column(String(255), nullable=True, comment="邮箱")
    role = Column(String(50), nullable=False, comment="角色（super_admin/security_manager/security_analyst/read_only）")
    permissions = Column(JSONB, nullable=False, comment="权限列表")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    tenant = relationship("Tenant", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Session(Base):
    """会话管理表"""
    __tablename__ = "sessions"
    
    session_id = Column(String(100), primary_key=True, index=True, comment="会话ID")
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, comment="租户ID")
    context = Column(JSONB, nullable=True, comment="会话上下文")
    history = Column(JSONB, nullable=True, comment="历史记录")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    
    # 关系
    tenant = relationship("Tenant", back_populates="sessions")
    user = relationship("User", back_populates="sessions")


class AgentCall(Base):
    """Agent调用记录表"""
    __tablename__ = "agent_calls"
    
    call_id = Column(String(100), primary_key=True, index=True, comment="调用ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    agent_name = Column(String(100), nullable=False, index=True, comment="Agent名称")
    intent = Column(String(50), nullable=True, comment="意图类型")
    status = Column(String(20), nullable=False, comment="状态（success/failed/pending/timeout）")
    error_message = Column(Text, nullable=True, comment="错误消息")
    input_params = Column(JSONB, nullable=True, comment="输入参数")
    output_result = Column(JSONB, nullable=True, comment="输出结果")
    duration_ms = Column(Integer, comment="处理时长（毫秒）")
    tokens_used = Column(Integer, default=0, comment="使用的Token数")
    cost = Column(Float, default=0.0, comment="成本")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")
    
    # 关系
    tenant = relationship("Tenant", back_populates="agent_calls")


class WorkflowExecution(Base):
    """工作流执行记录表"""
    __tablename__ = "workflow_executions"
    
    execution_id = Column(String(100), primary_key=True, index=True, comment="执行ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    workflow_name = Column(String(100), nullable=False, comment="工作流名称")
    workflow_config = Column(JSONB, nullable=True, comment="工作流配置")
    status = Column(String(20), nullable=False, comment="状态（pending/running/completed/failed/timeout）")
    result = Column(JSONB, nullable=True, comment="执行结果")
    summary = Column(JSONB, nullable=True, comment="执行摘要")
    total_duration = Column(Float, comment="总时长（秒）")
    success_rate = Column(Float, comment="成功率")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 关系
    tenant = relationship("Tenant", back_populates="workflow_executions")
    tasks = relationship("WorkflowTask", back_populates="execution", cascade="all, delete-orphan")


class WorkflowTask(Base):
    """工作流任务记录表"""
    __tablename__ = "workflow_tasks"
    
    task_id = Column(String(100), primary_key=True, index=True, comment="任务ID")
    execution_id = Column(String(100), ForeignKey("workflow_executions.execution_id", ondelete="CASCADE"), nullable=False, index=True, comment="执行ID")
    task_order = Column(Integer, nullable=False, comment="任务顺序")
    agent_name = Column(String(100), nullable=False, comment="Agent名称")
    intent = Column(String(50), nullable=True, comment="意图类型")
    input_params = Column(JSONB, nullable=True, comment="输入参数")
    dependencies = Column(JSONB, nullable=True, comment="依赖关系（任务ID列表）")
    status = Column(String(20), nullable=False, comment="状态（pending/running/completed/failed/timeout）")
    result = Column(JSONB, nullable=True, comment="执行结果")
    error_message = Column(Text, nullable=True, comment="错误消息")
    timeout_seconds = Column(Integer, nullable=True, comment="超时时间（秒）")
    duration = Column(Float, comment="执行时长（秒）")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    
    # 关系
    execution = relationship("WorkflowExecution", back_populates="tasks")


class ComplianceCheck(Base):
    """合规检查记录表"""
    __tablename__ = "compliance_checks"
    
    check_id = Column(String(100), primary_key=True, index=True, comment="检查ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    compliance_type = Column(String(50), nullable=False, comment="合规类型（dbp2.0/gdpr/iso27001等）")
    scope = Column(String(255), nullable=True, comment="检查范围")
    score = Column(Float, nullable=False, comment="合规评分")
    pass_threshold = Column(Float, nullable=False, comment="通过阈值")
    is_passed = Column(Boolean, nullable=False, comment="是否通过")
    total_checks = Column(Integer, default=0, comment="总检查数")
    passed_checks = Column(Integer, default=0, comment="通过检查数")
    failed_checks = Column(Integer, default=0, comment="失败检查数")
    results = Column(JSONB, nullable=True, comment="检查结果详情")
    report_path = Column(String(255), nullable=True, comment="报告文件路径")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")
    
    # 关系
    tenant = relationship("Tenant", back_populates="compliance_checks")


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"
    
    audit_id = Column(String(100), primary_key=True, index=True, comment="审计ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    user_id = Column(String(50), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True, comment="用户ID")
    action = Column(String(50), nullable=False, comment="操作类型（create/update/delete/query等）")
    resource = Column(String(255), nullable=True, comment="操作资源（表名、ID等）")
    query_params = Column(Text, nullable=True, comment="查询参数（脱敏）")
    request_body = Column(Text, nullable=True, comment="请求体（脱敏）")
    response_status = Column(Integer, comment="响应状态码")
    ip_address = Column(String(45), nullable=False, comment="IP地址")
    user_agent = Column(String(255), nullable=True, comment="用户代理")
    success = Column(Boolean, nullable=False, comment="是否成功")
    error_message = Column(Text, nullable=True, comment="错误消息")
    duration = Column(Float, comment="处理时长（秒）")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")
    
    # 关系
    tenant = relationship("Tenant")
    user = relationship("User", back_populates="audit_logs")


class TokenUsageStats(Base):
    """Token使用统计表"""
    __tablename__ = "token_usage_stats"
    
    id = Column(BigInteger, primary_key=True, comment="主键ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    date = Column(String(20), nullable=False, comment="日期（YYYY-MM-DD）")
    model = Column(String(50), nullable=False, index=True, comment="模型名称")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    input_tokens = Column(Integer, default=0, comment="输入Token数")
    output_tokens = Column(Integer, default=0, comment="输出Token数")
    total_calls = Column(Integer, default=0, comment="总调用次数")
    total_cost = Column(Float, default=0.0, comment="总成本")
    cost_per_token = Column(Float, default=0.0, comment="每Token成本")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 索引
    __table_args__ = (
        Index("idx_tenant_date_model", "tenant_id", "date", "model"),
    )
    
    # 关系
    tenant = relationship("Tenant", back_populates="token_usage_stats")


class ThreatIntelligence(Base):
    """威胁情报表"""
    __tablename__ = "threat_intelligence"
    
    intel_id = Column(String(100), primary_key=True, index=True, comment="情报ID")
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True, comment="租户ID")
    indicator_type = Column(String(50), nullable=False, comment="指标类型（ip/domain/hash/ioc等）")
    indicator_value = Column(String(255), nullable=False, comment="指标值")
    threat_level = Column(String(20), nullable=False, index=True, comment="威胁等级（critical/high/medium/low/info）")
    confidence = Column(Float, nullable=True, comment="置信度")
    source = Column(String(100), nullable=True, comment="情报来源")
    description = Column(Text, nullable=True, comment="描述")
    attributes = Column(JSONB, nullable=True, comment="附加属性")
    first_seen = Column(DateTime, default=datetime.utcnow, comment="首次发现时间")
    last_seen = Column(DateTime, default=datetime.utcnow, comment="最后发现时间")
    is_active = Column(Boolean, default=True, comment="是否活跃")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 索引
    __table_args__ = (
        Index("idx_tenant_indicator", "tenant_id", "indicator_type", "indicator_value"),
        Index("idx_threat_level", "threat_level"),
    )
    
    # 关系
    tenant = relationship("Tenant")
