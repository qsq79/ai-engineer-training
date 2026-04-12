"""
日志查询Agent
负责解释日志数据差异，生成查询SQL和自然语言解释
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI

from src.config.settings import settings
from src.utils.logger import logger
from src.database.db_pool import DatabaseManager
from src.database.models import AgentCall


# ============ 数据结构定义 ============

@dataclass
class QueryCondition:
    """查询条件"""
    field: str
    operator: str  # =, !=, >, <, >=, <=, IN, LIKE, BETWEEN
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryCondition":
        """从字典创建"""
        return cls(
            field=data["field"],
            operator=data["operator"],
            value=data["value"]
        )


@dataclass
class MonthlyReport:
    """月报配置"""
    report_id: str
    report_name: str
    tenant_id: str
    query_conditions: List[QueryCondition]
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "report_name": self.report_name,
            "tenant_id": self.tenant_id,
            "query_conditions": [cond.to_dict() for cond in self.query_conditions],
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ConditionDiff:
    """条件差异"""
    field: str
    monthly_value: Any
    user_value: Any
    diff_type: str  # added, removed, changed, same
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "field": self.field,
            "monthly_value": self.monthly_value,
            "user_value": self.user_value,
            "diff_type": self.diff_type
        }


@dataclass
class QueryResult:
    """查询结果"""
    sql: str
    explanation: str
    conditions_diff: List[ConditionDiff]
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sql": self.sql,
            "explanation": self.explanation,
            "conditions_diff": [diff.to_dict() for diff in self.conditions_diff],
            "execution_time": self.execution_time
        }


# ============ 日志查询Agent ============

class LogQueryAgent:
    """日志查询Agent
    
    职责：
    1. 获取月报配置和查询条件
    2. 获取用户查询条件
    3. 对比月报查询条件和用户查询条件，识别差异
    4. 基于差异分析生成正确的SQL查询语句
    5. 用自然语言解释数据差异的原因
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm: Optional[ChatOpenAI] = None
    ):
        """初始化日志查询Agent"""
        self.db = db_manager
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3
        )
        
        # 模拟月报数据存储（实际应用中应该从数据库读取）
        self._monthly_reports: Dict[str, MonthlyReport] = {}
        self._initialize_mock_reports()
        
        logger.info("日志查询Agent初始化完成")
    
    def _initialize_mock_reports(self):
        """初始化模拟月报数据"""
        # 月报1：2024年1月安全评分月报
        report1 = MonthlyReport(
            report_id="report_2024_01",
            report_name="2024年1月安全评分月报",
            tenant_id="tenant_001",
            query_conditions=[
                QueryCondition(field="time_range", operator="BETWEEN", value=["2024-01-01", "2024-01-31"]),
                QueryCondition(field="score_type", operator="=", value="security_score"),
                QueryCondition(field="metric_category", operator="IN", value=["vulnerability", "configuration", "compliance"])
            ]
        )
        
        # 月报2：2024年2月威胁情报月报
        report2 = MonthlyReport(
            report_id="report_2024_02",
            report_name="2024年2月威胁情报月报",
            tenant_id="tenant_001",
            query_conditions=[
                QueryCondition(field="time_range", operator="BETWEEN", value=["2024-02-01", "2024-02-29"]),
                QueryCondition(field="threat_level", operator="IN", value=["high", "critical"]),
                QueryCondition(field="status", operator="=", value="active")
            ]
        )
        
        self._monthly_reports["report_2024_01"] = report1
        self._monthly_reports["report_2024_02"] = report2
        
        logger.info(f"初始化 {len(self._monthly_reports)} 个模拟月报数据")
    
    async def get_monthly_report(
        self,
        report_id: str,
        tenant_id: str
    ) -> Optional[MonthlyReport]:
        """获取月报配置和查询条件
        
        Args:
            report_id: 月报ID
            tenant_id: 租户ID
        
        Returns:
            月报配置，如果不存在则返回None
        """
        logger.info(f"获取月报配置: report_id={report_id}, tenant_id={tenant_id}")
        
        # 模拟数据库查询（实际应用中应该从数据库读取）
        report = self._monthly_reports.get(report_id)
        
        if report is None:
            logger.warning(f"月报不存在: {report_id}")
            return None
        
        # 验证租户ID
        if report.tenant_id != tenant_id:
            logger.warning(f"月报租户不匹配: report_tenant={report.tenant_id}, request_tenant={tenant_id}")
            return None
        
        logger.info(f"成功获取月报配置: {report.report_name}")
        return report
    
    async def get_user_query_conditions(
        self,
        query_params: Dict[str, Any]
    ) -> List[QueryCondition]:
        """获取用户查询条件
        
        Args:
            query_params: 查询参数
        
        Returns:
            查询条件列表
        """
        logger.info(f"解析用户查询条件: {query_params}")
        
        conditions = []
        
        # 解析时间范围
        if "time_range" in query_params:
            time_range = query_params["time_range"]
            if isinstance(time_range, list) and len(time_range) == 2:
                conditions.append(QueryCondition(
                    field="time_range",
                    operator="BETWEEN",
                    value=time_range
                ))
        
        # 解析评分类型
        if "score_type" in query_params:
            conditions.append(QueryCondition(
                field="score_type",
                operator="=",
                value=query_params["score_type"]
            ))
        
        # 解析指标类别
        if "metric_category" in query_params:
            metric_category = query_params["metric_category"]
            if isinstance(metric_category, list):
                conditions.append(QueryCondition(
                    field="metric_category",
                    operator="IN",
                    value=metric_category
                ))
            else:
                conditions.append(QueryCondition(
                    field="metric_category",
                    operator="=",
                    value=metric_category
                ))
        
        # 解析威胁等级
        if "threat_level" in query_params:
            threat_level = query_params["threat_level"]
            if isinstance(threat_level, list):
                conditions.append(QueryCondition(
                    field="threat_level",
                    operator="IN",
                    value=threat_level
                ))
            else:
                conditions.append(QueryCondition(
                    field="threat_level",
                    operator="=",
                    value=threat_level
                ))
        
        # 解析状态
        if "status" in query_params:
            conditions.append(QueryCondition(
                field="status",
                operator="=",
                value=query_params["status"]
            ))
        
        logger.info(f"解析到 {len(conditions)} 个查询条件")
        return conditions
    
    async def compare_conditions(
        self,
        monthly_conditions: List[QueryCondition],
        user_conditions: List[QueryCondition]
    ) -> List[ConditionDiff]:
        """对比月报查询条件和用户查询条件，识别差异
        
        Args:
            monthly_conditions: 月报查询条件
            user_conditions: 用户查询条件
        
        Returns:
            条件差异列表
        """
        logger.info("对比查询条件差异")
        
        # 构建条件字典（按字段索引）
        monthly_dict = {cond.field: cond for cond in monthly_conditions}
        user_dict = {cond.field: cond for cond in user_conditions}
        
        # 收集所有字段
        all_fields = set(monthly_dict.keys()) | set(user_dict.keys())
        
        # 识别差异
        diffs = []
        for field in all_fields:
            monthly_cond = monthly_dict.get(field)
            user_cond = user_dict.get(field)
            
            if monthly_cond is None:
                # 用户添加了新条件
                diffs.append(ConditionDiff(
                    field=field,
                    monthly_value=None,
                    user_value=user_cond.value,
                    diff_type="added"
                ))
            elif user_cond is None:
                # 用户移除了月报的条件
                diffs.append(ConditionDiff(
                    field=field,
                    monthly_value=monthly_cond.value,
                    user_value=None,
                    diff_type="removed"
                ))
            elif monthly_cond.value != user_cond.value:
                # 条件值发生了变化
                diffs.append(ConditionDiff(
                    field=field,
                    monthly_value=monthly_cond.value,
                    user_value=user_cond.value,
                    diff_type="changed"
                ))
            else:
                # 条件值相同
                diffs.append(ConditionDiff(
                    field=field,
                    monthly_value=monthly_cond.value,
                    user_value=user_cond.value,
                    diff_type="same"
                ))
        
        logger.info(f"识别到 {len(diffs)} 个条件差异")
        return diffs
    
    async def generate_sql(
        self,
        conditions: List[QueryCondition],
        table_name: str = "security_logs"
    ) -> str:
        """基于查询条件生成SQL查询语句
        
        Args:
            conditions: 查询条件列表
            table_name: 表名
        
        Returns:
            SQL查询语句
        """
        logger.info(f"生成SQL查询语句: table_name={table_name}, conditions={len(conditions)}")
        
        where_clauses = []
        params = []
        
        for cond in conditions:
            if cond.operator == "=":
                where_clauses.append(f"{cond.field} = %s")
                params.append(cond.value)
            elif cond.operator == "!=":
                where_clauses.append(f"{cond.field} != %s")
                params.append(cond.value)
            elif cond.operator == ">":
                where_clauses.append(f"{cond.field} > %s")
                params.append(cond.value)
            elif cond.operator == "<":
                where_clauses.append(f"{cond.field} < %s")
                params.append(cond.value)
            elif cond.operator == ">=":
                where_clauses.append(f"{cond.field} >= %s")
                params.append(cond.value)
            elif cond.operator == "<=":
                where_clauses.append(f"{cond.field} <= %s")
                params.append(cond.value)
            elif cond.operator == "IN":
                placeholders = ", ".join(["%s"] * len(cond.value))
                where_clauses.append(f"{cond.field} IN ({placeholders})")
                params.extend(cond.value)
            elif cond.operator == "LIKE":
                where_clauses.append(f"{cond.field} LIKE %s")
                params.append(f"%{cond.value}%")
            elif cond.operator == "BETWEEN":
                where_clauses.append(f"{cond.field} BETWEEN %s AND %s")
                params.extend(cond.value)
        
        # 构建SQL
        sql = f"SELECT * FROM {table_name}"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += ";"
        
        logger.info(f"生成的SQL: {sql}")
        logger.debug(f"SQL参数: {params}")
        
        return sql
    
    async def explain_difference(
        self,
        diffs: List[ConditionDiff],
        monthly_report: MonthlyReport
    ) -> str:
        """用自然语言解释数据差异的原因
        
        Args:
            diffs: 条件差异列表
            monthly_report: 月报配置
        
        Returns:
            自然语言解释
        """
        logger.info("生成差异解释")
        
        # 构建提示词
        prompt = f"""请为以下月报查询条件差异生成解释：

月报名称: {monthly_report.report_name}
月报ID: {monthly_report.report_id}

条件差异:
"""
        
        for diff in diffs:
            if diff.diff_type == "added":
                prompt += f"\n- 新增条件: {diff.field} = {diff.user_value}"
                prompt += f"\n  说明: 您的查询中包含了月报没有的{diff.field}条件"
            elif diff.diff_type == "removed":
                prompt += f"\n- 移除条件: {diff.field} = {diff.monthly_value}"
                prompt += f"\n  说明: 您的查询中移除了月报中的{diff.field}条件"
            elif diff.diff_type == "changed":
                prompt += f"\n- 修改条件: {diff.field}"
                prompt += f"\n  月报值: {diff.monthly_value}"
                prompt += f"\n  您的值: {diff.user_value}"
                prompt += f"\n  说明: 您的查询中{diff.field}条件的值与月报不同"
            elif diff.diff_type == "same":
                prompt += f"\n- 相同条件: {diff.field} = {diff.monthly_value}"
        
        prompt += """

请生成一个简洁的解释，说明：
1. 您的查询条件和月报查询条件的差异
2. 这些差异如何影响查询结果
3. 为什么数据结果会不同

解释长度控制在200字以内，用通俗易懂的语言。"""
        
        try:
            # 使用LLM生成解释
            response = await self.llm.ainvoke(prompt)
            explanation = response.content
            
            logger.info(f"差异解释生成完成: {len(explanation)} 字符")
            return explanation
            
        except Exception as e:
            logger.error(f"生成差异解释失败: {str(e)}", exc_info=True)
            
            # 回退到简单解释
            added_count = sum(1 for d in diffs if d.diff_type == "added")
            removed_count = sum(1 for d in diffs if d.diff_type == "removed")
            changed_count = sum(1 for d in diffs if d.diff_type == "changed")
            
            explanation_parts = []
            if added_count > 0:
                explanation_parts.append(f"您添加了{added_count}个新条件")
            if removed_count > 0:
                explanation_parts.append(f"您移除了{removed_count}个月报条件")
            if changed_count > 0:
                explanation_parts.append(f"您修改了{changed_count}个条件值")
            
            explanation = "和" + "和".join(explanation_parts) + "，这导致查询结果与月报不同。"
            
            return explanation
    
    async def query_diff(
        self,
        query: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """查询差异接口 - 被 query.py 路由调用
        
        Args:
            query: 用户查询文本
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
            parameters: 从意图识别提取的参数
        
        Returns:
            查询结果字典
        """
        import re
        from datetime import datetime
        
        logger.info(f"开始查询差异: query={query}, tenant_id={tenant_id}")
        
        # 1. 从查询中提取年月信息
        year_match = re.search(r'(\d{4})年', query)
        month_match = re.search(r'(\d{1,2})月', query)
        
        year = int(year_match.group(1)) if year_match else datetime.now().year
        month = int(month_match.group(1)) if month_match else datetime.now().month
        
        # 2. 尝试获取最近的月报
        report_id = f"monthly_{year}_{month:02d}"
        
        # 3. 构造输入参数
        input_params = {
            "report_id": report_id,
            "query_params": parameters or {},
            "query_text": query,
            "table_name": "security_logs"
        }
        
        try:
            # 4. 执行查询
            result = await self.execute(
                input_params=input_params,
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id
            )
            
            # 5. 返回结果
            return {
                "query": query,
                "year": year,
                "month": month,
                "sql": result.sql,
                "explanation": result.explanation,
                "diffs": [diff.to_dict() for diff in result.conditions_diff] if result.conditions_diff else [],
                "execution_time": result.execution_time,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"查询差异失败: {str(e)}", exc_info=True)
            # 如果月报不存在，返回模拟结果用于演示
            return {
                "query": query,
                "year": year,
                "month": month,
                "explanation": f"正在分析 {year} 年 {month} 月的查询差异...",
                "diffs": [],
                "status": "in_progress",
                "note": "系统正在初始化数据，请稍后再试"
            }
    
    async def execute(
        self,
        input_params: Dict[str, Any],
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> QueryResult:
        """执行日志查询
        
        Args:
            input_params: 输入参数
                - report_id: 月报ID
                - user_conditions: 用户查询条件（可选，从query_params解析）
                - query_params: 查询参数（字典格式）
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            查询结果
        """
        call_id = f"call_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        
        logger.info(f"开始执行日志查询 [{call_id}]")
        
        try:
            # 1. 获取月报配置
            report_id = input_params.get("report_id")
            if not report_id:
                raise ValueError("缺少月报ID")
            
            monthly_report = await self.get_monthly_report(report_id, tenant_id)
            if not monthly_report:
                raise ValueError(f"月报不存在: {report_id}")
            
            # 2. 获取用户查询条件
            query_params = input_params.get("query_params", {})
            user_conditions = await self.get_user_query_conditions(query_params)
            
            # 3. 对比条件差异
            diffs = await self.compare_conditions(
                monthly_report.query_conditions,
                user_conditions
            )
            
            # 4. 生成SQL查询语句
            table_name = input_params.get("table_name", "security_logs")
            sql = await self.generate_sql(user_conditions, table_name)
            
            # 5. 生成差异解释
            explanation = await self.explain_difference(diffs, monthly_report)
            
            # 6. 构建查询结果
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            result = QueryResult(
                sql=sql,
                explanation=explanation,
                conditions_diff=diffs,
                execution_time=execution_time
            )
            
            # 7. 记录Agent调用
            await self._log_agent_call(
                call_id,
                tenant_id,
                user_id,
                session_id,
                input_params,
                result,
                execution_time,
                None
            )
            
            logger.info(
                f"日志查询执行完成 [{call_id}]: "
                f"耗时={execution_time:.2f}s, 差异数={len(diffs)}"
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.error(f"日志查询执行失败 [{call_id}]: {str(e)}", exc_info=True)
            
            # 记录失败的Agent调用
            await self._log_agent_call(
                call_id,
                tenant_id,
                user_id,
                session_id,
                input_params,
                None,
                execution_time,
                str(e)
            )
            
            raise
    
    async def _log_agent_call(
        self,
        call_id: str,
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str],
        input_params: Dict[str, Any],
        output_result: Optional[QueryResult],
        duration_ms: float,
        error_message: Optional[str]
    ):
        """记录Agent调用到数据库
        
        Args:
            call_id: 调用ID
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
            input_params: 输入参数
            output_result: 输出结果
            duration_ms: 执行时长（秒）
            error_message: 错误消息
        """
        async with self.db.get_session() as session:
            agent_call = AgentCall(
                call_id=call_id,
                tenant_id=tenant_id,
                agent_name="LogQueryAgent",
                intent="query_diff",
                status="completed" if error_message is None else "failed",
                error_message=error_message,
                input_params=input_params,
                output_result=output_result.to_dict() if output_result else None,
                duration_ms=duration_ms * 1000,  # 转换为毫秒
                tokens_used=None,
                cost=None
            )
            
            session.add(agent_call)
            await session.commit()
            
            logger.debug(f"记录Agent调用: {call_id}")


# ============ 便捷函数 ============

# 全局日志查询Agent实例
_log_query_agent: Optional[LogQueryAgent] = None


def get_log_query_agent(
    db_manager: DatabaseManager,
    llm: Optional[ChatOpenAI] = None
) -> LogQueryAgent:
    """获取日志查询Agent实例（单例模式）
    
    Args:
        db_manager: 数据库管理器
        llm: LLM实例（可选）
    
    Returns:
        日志查询Agent实例
    """
    global _log_query_agent
    
    if _log_query_agent is None:
        _log_query_agent = LogQueryAgent(
            db_manager=db_manager,
            llm=llm
        )
    
    return _log_query_agent


# 导出
__all__ = [
    "QueryCondition",
    "MonthlyReport",
    "ConditionDiff",
    "QueryResult",
    "LogQueryAgent",
    "get_log_query_agent"
]
