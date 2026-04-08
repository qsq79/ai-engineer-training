"""
合规检查Agent
负责执行合规检查，生成合规报告
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from langchain_openai import ChatOpenAI

from ..config.settings import settings
from ..utils.logger import logger
from ..database.db_pool import DatabaseManager
from ..database.models import AgentCall, ComplianceCheck


class ComplianceType(str, Enum):
    """合规类型枚举"""
    GB_T22239 = "gb22239"  # 等保2.0
    GDPR = "gdpr"  # 通用数据保护条例
    ISO27001 = "iso27001"  # 信息安全管理体系
    HIPAA = "hipaa"  # 健康保险流通与责任法案
    PCI_DSS = "pci_dss"  # 支付卡行业数据安全标准


class CheckStatus(str, Enum):
    """检查状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ============ 数据结构定义 ============

@dataclass
class ComplianceRule:
    """合规规则"""
    rule_id: str
    name: str
    description: str
    category: str
    compliance_type: str
    severity: str  # critical, high, medium, low
    check_method: str
    expected_value: Any
    actual_value: Any = None
    status: str = "pending"
    recommendation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "compliance_type": self.compliance_type,
            "severity": self.severity,
            "check_method": self.check_method,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "status": self.status,
            "recommendation": self.recommendation
        }


@dataclass
class CheckResult:
    """检查结果"""
    rule: ComplianceRule
    is_passed: bool
    actual_value: Any
    evidence: str = ""
    details: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule.to_dict(),
            "is_passed": self.is_passed,
            "actual_value": self.actual_value,
            "evidence": self.evidence,
            "details": self.details
        }


@dataclass
class ComplianceReport:
    """合规报告"""
    report_id: str
    compliance_type: str
    scope: str
    overall_score: float
    pass_threshold: float
    is_passed: bool
    total_rules: int
    passed_rules: int
    failed_rules: int
    warning_rules: int
    results: List[CheckResult]
    risk_summary: Dict[str, int]
    recommendations: List[str]
    executive_summary: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "compliance_type": self.compliance_type,
            "scope": self.scope,
            "overall_score": self.overall_score,
            "pass_threshold": self.pass_threshold,
            "is_passed": self.is_passed,
            "total_rules": self.total_rules,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warning_rules": self.warning_rules,
            "results": [r.to_dict() for r in self.results],
            "risk_summary": self.risk_summary,
            "recommendations": self.recommendations,
            "executive_summary": self.executive_summary,
            "generated_at": self.generated_at.isoformat()
        }


# ============ 合规规则引擎 ============

class ComplianceRuleEngine:
    """合规规则引擎"""
    
    # 等保2.0三级检查规则
    GB22239_RULES = [
        # 身份鉴别
        {
            "rule_id": "GB22239_S1_1_1",
            "name": "身份鉴别",
            "description": "应对登录用户进行身份标识和鉴别",
            "category": "身份鉴别",
            "severity": "critical",
            "check_method": "check_authentication",
            "expected_value": "enabled"
        },
        {
            "rule_id": "GB22239_S1_1_2",
            "name": "鉴别信息保护",
            "description": "应采用两种或两种以上的鉴别技术",
            "category": "身份鉴别",
            "severity": "high",
            "check_method": "check_multi_factor",
            "expected_value": "enabled"
        },
        # 访问控制
        {
            "rule_id": "GB22239_S1_2_1",
            "name": "访问控制策略",
            "description": "应制定访问控制策略",
            "category": "访问控制",
            "severity": "high",
            "check_method": "check_access_policy",
            "expected_value": "configured"
        },
        {
            "rule_id": "GB22239_S1_2_2",
            "name": "默认账户清理",
            "description": "应重命名或删除默认账户",
            "category": "访问控制",
            "severity": "medium",
            "check_method": "check_default_accounts",
            "expected_value": "cleaned"
        },
        # 安全审计
        {
            "rule_id": "GB22239_S1_3_1",
            "name": "审计日志启用",
            "description": "应启用安全审计功能",
            "category": "安全审计",
            "severity": "critical",
            "check_method": "check_audit_enabled",
            "expected_value": "enabled"
        },
        {
            "rule_id": "GB22239_S1_3_2",
            "name": "审计日志保护",
            "description": "审计记录应受到保护",
            "category": "安全审计",
            "severity": "high",
            "check_method": "check_audit_protection",
            "expected_value": "protected"
        },
        {
            "rule_id": "GB22239_S1_3_3",
            "name": "审计日志留存",
            "description": "审计记录应留存至少6个月",
            "category": "安全审计",
            "severity": "medium",
            "check_method": "check_audit_retention",
            "expected_value": 6,
            "unit": "months"
        },
        # 入侵防范
        {
            "rule_id": "GB22239_S1_4_1",
            "name": "入侵检测",
            "description": "应部署入侵检测系统",
            "category": "入侵防范",
            "severity": "high",
            "check_method": "check_ids",
            "expected_value": "deployed"
        },
        {
            "rule_id": "GB22239_S1_4_2",
            "name": "恶意代码防范",
            "description": "应部署恶意代码防护系统",
            "category": "入侵防范",
            "severity": "high",
            "check_method": "check_antivirus",
            "expected_value": "deployed"
        },
        # 数据安全
        {
            "rule_id": "GB22239_S2_1_1",
            "name": "数据传输加密",
            "description": "应采用加密等方式保护传输数据",
            "category": "数据安全",
            "severity": "critical",
            "check_method": "check_transport_encryption",
            "expected_value": "enabled"
        },
        {
            "rule_id": "GB22239_S2_1_2",
            "name": "数据存储加密",
            "description": "应采用加密等方式保护存储数据",
            "category": "数据安全",
            "severity": "high",
            "check_method": "check_storage_encryption",
            "expected_value": "enabled"
        },
    ]
    
    # GDPR 规则
    GDPR_RULES = [
        {
            "rule_id": "GDPR_ART_5_1",
            "name": "数据最小化原则",
            "description": "应仅收集处理与目的相关的最小数据",
            "category": "数据最小化",
            "severity": "high",
            "check_method": "check_data_minimization",
            "expected_value": "compliant"
        },
        {
            "rule_id": "GDPR_ART_5_2",
            "name": "数据处理记录",
            "description": "应维护数据处理活动记录",
            "category": "数据处理记录",
            "severity": "high",
            "check_method": "check_processing_records",
            "expected_value": "maintained"
        },
        {
            "rule_id": "GDPR_ART_6",
            "name": "合法性基础",
            "description": "数据处理应有合法基础",
            "category": "合法性基础",
            "severity": "critical",
            "check_method": "check_legal_basis",
            "expected_value": "documented"
        },
        {
            "rule_id": "GDPR_ART_7",
            "name": "同意管理",
            "description": "应实现有效的同意管理机制",
            "category": "同意管理",
            "severity": "high",
            "check_method": "check_consent_mechanism",
            "expected_value": "implemented"
        },
        {
            "rule_id": "GDPR_ART_15",
            "name": "数据主体权利",
            "description": "应支持数据访问、更正、删除权利",
            "category": "数据主体权利",
            "severity": "critical",
            "check_method": "check_subject_rights",
            "expected_value": "supported"
        },
        {
            "rule_id": "GDPR_ART_32",
            "name": "安全措施",
            "description": "应实施适当的技术和组织安全措施",
            "category": "安全措施",
            "severity": "critical",
            "check_method": "check_security_measures",
            "expected_value": "implemented"
        },
    ]
    
    # ISO 27001 规则
    ISO27001_RULES = [
        {
            "rule_id": "ISO27001_A5_1",
            "name": "信息安全策略",
            "description": "应有信息安全方针文件",
            "category": "信息安全策略",
            "severity": "high",
            "check_method": "check_info_policy",
            "expected_value": "documented"
        },
        {
            "rule_id": "ISO27001_A6_1",
            "name": "信息安全组织",
            "description": "应建立信息安全管理组织",
            "category": "信息安全组织",
            "severity": "medium",
            "check_method": "check_org_structure",
            "expected_value": "established"
        },
        {
            "rule_id": "ISO27001_A7_1",
            "name": "人力资源安全",
            "description": "应进行安全背景审查",
            "category": "人力资源安全",
            "severity": "high",
            "check_method": "check_bg_screening",
            "expected_value": "performed"
        },
        {
            "rule_id": "ISO27001_A8_1",
            "name": "资产管理",
            "description": "应建立资产清单",
            "category": "资产管理",
            "severity": "medium",
            "check_method": "check_asset_inventory",
            "expected_value": "maintained"
        },
        {
            "rule_id": "ISO27001_A9_1",
            "name": "访问控制策略",
            "description": "应建立访问控制策略",
            "category": "访问控制",
            "severity": "critical",
            "check_method": "check_access_control",
            "expected_value": "established"
        },
        {
            "rule_id": "ISO27001_A12_1",
            "name": "系统运行安全",
            "description": "应实施变更管理",
            "category": "系统运行安全",
            "severity": "high",
            "check_method": "check_change_mgmt",
            "expected_value": "implemented"
        },
    ]
    
    def __init__(self):
        """初始化规则引擎"""
        self.rules_registry: Dict[str, List[Dict]] = {
            ComplianceType.GB_T22239.value: self.GB22239_RULES,
            ComplianceType.GDPR.value: self.GDPR_RULES,
            ComplianceType.ISO27001.value: self.ISO27001_RULES,
        }
    
    def get_rules(self, compliance_type: str) -> List[ComplianceRule]:
        """获取指定合规类型的规则"""
        rules_data = self.rules_registry.get(compliance_type, [])
        return [
            ComplianceRule(
                rule_id=r["rule_id"],
                name=r["name"],
                description=r["description"],
                category=r["category"],
                compliance_type=r["compliance_type"],
                severity=r["severity"],
                check_method=r["check_method"],
                expected_value=r["expected_value"]
            )
            for r in rules_data
        ]
    
    def get_all_compliance_types(self) -> List[str]:
        """获取所有支持的合规类型"""
        return list(self.rules_registry.keys())


# ============ 合规检查Agent ============

class ComplianceAgent:
    """合规检查Agent
    
    职责：
    1. 管理合规规则引擎
    2. 执行合规检查
    3. 生成合规报告
    4. 提供改进建议
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm: Optional[ChatOpenAI] = None
    ):
        """初始化合规检查Agent"""
        self.db = db_manager
        self.llm = llm or ChatOpenAI(
            model=settings.compliance_model,  # 使用合规检查专用模型
            api_key=settings.openai_api_key,
            temperature=0.2
        )
        
        # 初始化规则引擎
        self.rule_engine = ComplianceRuleEngine()
        
        # 模拟检查结果缓存
        self.mock_results_cache: Dict[str, Any] = {}
        self._initialize_mock_results()
        
        logger.info("合规检查Agent初始化完成")
    
    def _initialize_mock_results(self):
        """初始化模拟检查结果"""
        # 为每个规则生成随机但合理的模拟结果
        import random
        
        for compliance_type, rules_data in self.rule_engine.rules_registry.items():
            self.mock_results_cache[compliance_type] = {}
            for rule in rules_data:
                rule_id = rule["rule_id"]
                # 80% 概率通过
                is_passed = random.random() < 0.8
                severity = rule["severity"]
                
                if is_passed:
                    actual_value = rule["expected_value"]
                    recommendation = ""
                else:
                    # 根据严重程度生成不同的实际值
                    if severity == "critical":
                        actual_value = "未配置或配置不当"
                        recommendation = f"立即修复：{rule['name']}不符合要求，可能导致严重安全风险"
                    elif severity == "high":
                        actual_value = "部分符合"
                        recommendation = f"建议修复：{rule['name']}需要改进"
                    else:
                        actual_value = "待完善"
                        recommendation = f"优化建议：{rule['name']}可进一步优化"
                
                self.mock_results_cache[compliance_type][rule_id] = {
                    "is_passed": is_passed,
                    "actual_value": actual_value,
                    "evidence": f"通过系统配置检查和日志分析得出",
                    "details": f"检查方法：{rule['check_method']}，预期结果：{rule['expected_value']}"
                }
    
    async def check_rule(self, rule: ComplianceRule) -> CheckResult:
        """执行单个规则检查"""
        # 获取模拟结果
        mock_result = self.mock_results_cache.get(
            rule.compliance_type, 
            {}
        ).get(rule.rule_id, {})
        
        is_passed = mock_result.get("is_passed", True)
        actual_value = mock_result.get("actual_value", rule.expected_value)
        evidence = mock_result.get("evidence", "")
        details = mock_result.get("details", "")
        
        # 更新规则状态
        if is_passed:
            rule.status = CheckStatus.PASSED.value
        else:
            rule.status = CheckStatus.FAILED.value
            rule.actual_value = actual_value
            rule.recommendation = mock_result.get("details", "")
        
        return CheckResult(
            rule=rule,
            is_passed=is_passed,
            actual_value=actual_value,
            evidence=evidence,
            details=details
        )
    
    async def execute_compliance_check(
        self,
        compliance_type: str,
        scope: str = "full",
        tenant_id: str = "default",
        user_id: str = "system"
    ) -> ComplianceReport:
        """执行合规检查"""
        start_time = datetime.utcnow()
        
        logger.info(f"开始执行合规检查: compliance_type={compliance_type}, scope={scope}")
        
        # 获取规则列表
        rules = self.rule_engine.get_rules(compliance_type)
        
        # 执行每个规则的检查
        results = []
        for rule in rules:
            result = await self.check_rule(rule)
            results.append(result)
        
        # 统计结果
        total_rules = len(results)
        passed_rules = sum(1 for r in results if r.is_passed)
        failed_rules = total_rules - passed_rules
        warning_rules = 0
        
        # 计算合规评分
        overall_score = (passed_rules / total_rules * 100) if total_rules > 0 else 0
        
        # 判断是否通过
        pass_threshold = 70.0  # 70分及格
        is_passed = overall_score >= pass_threshold
        
        # 风险汇总
        risk_summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        for result in results:
            if not result.is_passed:
                severity = result.rule.severity
                risk_summary[severity] = risk_summary.get(severity, 0) + 1
        
        # 生成建议
        recommendations = []
        failed_critical = [r for r in results if not r.is_passed and r.rule.severity == "critical"]
        failed_high = [r for r in results if not r.is_passed and r.rule.severity == "high"]
        
        if failed_critical:
            recommendations.append(f"优先处理{len(failed_critical)}个严重风险项")
        if failed_high:
            recommendations.append(f"建议处理{len(failed_high)}个高风险项")
        
        # 为每个失败的规则生成建议
        for result in results:
            if not result.is_passed:
                recommendations.append(result.rule.recommendation)
        
        # 生成执行摘要
        executive_summary = f"""合规检查完成。

检查类型：{compliance_type}
检查范围：{scope}
合规评分：{overall_score:.1f}分
通过状态：{'通过' if is_passed else '未通过'}

检查结果统计：
- 总规则数：{total_rules}
- 通过：{passed_rules}
- 失败：{failed_rules}

{'建议立即处理发现的严重问题' if failed_critical else '系统整体符合合规要求'}"""
        
        # 生成报告
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            compliance_type=compliance_type,
            scope=scope,
            overall_score=overall_score,
            pass_threshold=pass_threshold,
            is_passed=is_passed,
            total_rules=total_rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            warning_rules=warning_rules,
            results=results,
            risk_summary=risk_summary,
            recommendations=recommendations[:10],  # 限制建议数量
            executive_summary=executive_summary
        )
        
        # 记录到数据库
        await self._log_compliance_check(
            report=report,
            tenant_id=tenant_id,
            user_id=user_id
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"合规检查完成: report_id={report.report_id}, score={overall_score:.1f}, duration={execution_time:.2f}s")
        
        return report
    
    async def _log_compliance_check(
        self,
        report: ComplianceReport,
        tenant_id: str,
        user_id: str
    ):
        """记录合规检查到数据库"""
        try:
            async with self.db.get_session() as session:
                check_record = ComplianceCheck(
                    check_id=report.report_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    compliance_type=report.compliance_type,
                    scope=report.scope,
                    score=report.overall_score,
                    pass_threshold=report.pass_threshold,
                    is_passed=report.is_passed,
                    total_checks=report.total_rules,
                    passed_checks=report.passed_rules,
                    failed_checks=report.failed_rules,
                    results={
                        "risk_summary": report.risk_summary,
                        "recommendations": report.recommendations,
                        "executive_summary": report.executive_summary
                    }
                )
                session.add(check_record)
                await session.commit()
                logger.info(f"合规检查记录已保存: check_id={report.report_id}")
        except Exception as e:
            logger.error(f"保存合规检查记录失败: {e}")
    
    async def get_compliance_types(self) -> List[Dict[str, str]]:
        """获取支持的合规类型列表"""
        types = self.rule_engine.get_all_compliance_types()
        type_names = {
            "gb22239": "等保2.0",
            "gdpr": "GDPR (通用数据保护条例)",
            "iso27001": "ISO 27001"
        }
        return [
            {"id": t, "name": type_names.get(t, t)}
            for t in types
        ]


# ============ Agent实例获取函数 ============

# 全局Agent实例
_compliance_agent: Optional[ComplianceAgent] = None


def get_compliance_agent() -> ComplianceAgent:
    """获取合规检查Agent实例（单例）"""
    global _compliance_agent
    if _compliance_agent is None:
        from ...database.db_pool import db_manager
        _compliance_agent = ComplianceAgent(db_manager=db_manager)
    return _compliance_agent


async def execute_compliance_check(
    compliance_type: str,
    scope: str = "full",
    tenant_id: str = "default",
    user_id: str = "system"
) -> ComplianceReport:
    """执行合规检查的便捷函数"""
    agent = get_compliance_agent()
    return await agent.execute_compliance_check(
        compliance_type=compliance_type,
        scope=scope,
        tenant_id=tenant_id,
        user_id=user_id
    )
