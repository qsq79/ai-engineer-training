"""
评分解读Agent
负责解读安全评分，解释评分逻辑，提供改进建议
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from src.config.settings import settings
from src.utils.logger import logger
from src.database.db_pool import DatabaseManager
from src.database.models import AgentCall


# ============ 数据结构定义 ============

@dataclass
class ScoreDimension:
    """评分维度"""
    name: str
    score: float
    weight: float
    description: str
    max_score: float = 100.0
    
    @property
    def weighted_score(self) -> float:
        """加权分数"""
        return self.score * self.weight
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "weighted_score": self.weighted_score,
            "description": self.description,
            "max_score": self.max_score
        }


@dataclass
class ScoreBreakdown:
    """评分明细"""
    overall_score: float
    dimensions: List[ScoreDimension]
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "overall_score": self.overall_score,
            "dimensions": [dim.to_dict() for dim in self.dimensions],
            "calculated_at": self.calculated_at.isoformat()
        }


@dataclass
class ScoreExplanation:
    """评分解释"""
    explanation: str
    score_logic: str
    calculation_method: str
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "explanation": self.explanation,
            "score_logic": self.score_logic,
            "calculation_method": self.calculation_method,
            "references": self.references
        }


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    priority: str  # high, medium, low
    dimension: str
    suggestion: str
    expected_impact: float
    estimated_effort: str  # hours, days, weeks
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "priority": self.priority,
            "dimension": self.dimension,
            "suggestion": self.suggestion,
            "expected_impact": self.expected_impact,
            "estimated_effort": self.estimated_effort
        }


@dataclass
class ScoreInterpretationResult:
    """评分解读结果"""
    breakdown: ScoreBreakdown
    explanation: ScoreExplanation
    suggestions: List[ImprovementSuggestion]
    retrieval_docs: List[Document] = field(default_factory=list)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "breakdown": self.breakdown.to_dict(),
            "explanation": self.explanation.to_dict(),
            "suggestions": [sug.to_dict() for sug in self.suggestions],
            "retrieval_docs": [
                {"content": doc.page_content, "metadata": doc.metadata}
                for doc in self.retrieval_docs
            ],
            "execution_time": self.execution_time
        }


# ============ 评分解读Agent ============

class ScoringAgent:
    """评分解读Agent
    
    职责：
    1. 集成向量数据库，实现文档向量化
    2. 实现向量索引建立和相似度查询
    3. 实现文档检索功能，基于向量数据库检索评分相关文档和知识
    4. 实现评分解释功能，用自然语言解释评分逻辑和计算方法
    5. 实现评分明细展示，展示各维度的得分和权重
    6. 实现改进建议生成功能
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm: Optional[ChatOpenAI] = None,
        embeddings: Optional[OpenAIEmbeddings] = None,
        vector_store_path: Optional[str] = None
    ):
        """初始化评分解读Agent"""
        self.db = db_manager
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3
        )
        self.embeddings = embeddings or OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key
        )
        
        # 向量数据库配置
        self.vector_store_path = vector_store_path or settings.vector_db_path
        self.vector_store: Optional[Chroma] = None
        
        # 初始化向量数据库和知识库
        self._initialize_vector_store()
        
        logger.info("评分解读Agent初始化完成")
    
    def _initialize_vector_store(self):
        """初始化向量数据库和知识库"""
        logger.info("初始化向量数据库")
        
        try:
            # 创建或加载向量数据库
            self.vector_store = Chroma(
                collection_name="scoring_knowledge",
                embedding_function=self.embeddings,
                persist_directory=str(self.vector_store_path)
            )
            
            # 检查是否已有文档，如果没有则加载示例文档
            if not self._has_documents():
                self._load_sample_documents()
            
            logger.info("向量数据库初始化完成")
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {str(e)}", exc_info=True)
            self.vector_store = None
    
    def _has_documents(self) -> bool:
        """检查向量数据库是否已有文档"""
        if self.vector_store is None:
            return False
        
        try:
            # 尝试查询一个文档
            results = self.vector_store.similarity_search("test", k=1)
            return len(results) > 0
        except:
            return False
    
    def _load_sample_documents(self):
        """加载示例文档到向量数据库"""
        logger.info("加载示例文档到向量数据库")
        
        # 示例文档：安全评分知识库
        sample_docs = [
            Document(
                page_content="""安全评分是根据系统的安全配置、漏洞情况、合规性等多个维度综合计算得出。评分范围为0-100分，分数越高表示安全性越好。评分采用加权平均算法，各维度根据重要性分配不同的权重。""",
                metadata={"category": "general", "type": "overview"}
            ),
            Document(
                page_content="""漏洞评分维度：根据系统中已发现的安全漏洞数量、严重程度分布、修复情况来计算。高严重级别漏洞对评分影响最大，需要优先修复。漏洞评分权重为30%。""",
                metadata={"category": "dimension", "type": "vulnerability"}
            ),
            Document(
                page_content="""配置评分维度：评估系统的安全配置是否符合最佳实践，包括密码策略、访问控制、日志审计等方面。配置评分权重为25%。""",
                metadata={"category": "dimension", "type": "configuration"}
            ),
            Document(
                page_content="""合规评分维度：检查系统是否符合相关安全标准和法规要求，如等保2.0、GDPR等。合规评分权重为25%。""",
                metadata={"category": "dimension", "type": "compliance"}
            ),
            Document(
                page_content="""威胁情报评分维度：基于外部威胁情报数据，评估系统面临的潜在威胁风险。威胁情报评分权重为20%。""",
                metadata={"category": "dimension", "type": "threat_intelligence"}
            ),
            Document(
                page_content="""提高漏洞评分的建议：及时安装安全补丁、定期进行漏洞扫描、建立漏洞修复流程、优先处理高严重级别漏洞。实施这些措施可以将漏洞评分提高5-15分。""",
                metadata={"category": "suggestion", "type": "vulnerability"}
            ),
            Document(
                page_content="""提高配置评分的建议：启用多因素认证、配置密码复杂度策略、定期轮换密钥、限制管理员权限、启用安全审计日志。实施这些措施可以将配置评分提高5-10分。""",
                metadata={"category": "suggestion", "type": "configuration"}
            ),
            Document(
                page_content="""提高合规评分的建议：对照等保2.0要求进行全面检查、建立合规管理体系、定期进行合规评估、保留合规审计记录。实施这些措施可以将合规评分提高5-10分。""",
                metadata={"category": "suggestion", "type": "compliance"}
            ),
            Document(
                page_content="""提高威胁情报评分的建议：部署威胁情报平台、订阅威胁情报源、建立威胁响应流程、进行威胁狩猎活动。实施这些措施可以将威胁情报评分提高5-10分。""",
                metadata={"category": "suggestion", "type": "threat_intelligence"}
            ),
            Document(
                page_content="""评分计算方法：总评分 = Σ(各维度评分 × 维度权重)。各维度评分范围为0-100分，权重总和为1.0。例如：漏洞80分×0.3 + 配置75分×0.25 + 合规85分×0.25 + 威胁70分×0.2 = 77.75分。""",
                metadata={"category": "calculation", "type": "formula"}
            )
        ]
        
        # 添加文档到向量数据库
        if self.vector_store:
            self.vector_store.add_documents(sample_docs)
            logger.info(f"已加载 {len(sample_docs)} 个示例文档到向量数据库")
    
    async def retrieve_documents(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """基于向量数据库检索相关文档
        
        Args:
            query: 查询文本
            k: 返回的文档数量
            filter_metadata: 元数据过滤条件
        
        Returns:
            相关文档列表
        """
        logger.info(f"检索相关文档: query={query}, k={k}")
        
        if self.vector_store is None:
            logger.warning("向量数据库未初始化，返回空结果")
            return []
        
        try:
            # 执行相似度搜索
            if filter_metadata:
                results = self.vector_store.similarity_search(
                    query=query,
                    k=k,
                    filter=filter_metadata
                )
            else:
                results = self.vector_store.similarity_search(
                    query=query,
                    k=k
                )
            
            logger.info(f"检索到 {len(results)} 个相关文档")
            return results
            
        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}", exc_info=True)
            return []
    
    def calculate_score_breakdown(
        self,
        scores: Dict[str, float]
    ) -> ScoreBreakdown:
        """计算评分明细
        
        Args:
            scores: 各维度评分，格式为 {维度名: 分数}
        
        Returns:
            评分明细
        """
        logger.info(f"计算评分明细: scores={scores}")
        
        # 定义维度和权重
        dimension_configs = {
            "vulnerability": {
                "name": "漏洞评分",
                "weight": 0.3,
                "description": "根据系统中已发现的安全漏洞数量、严重程度分布、修复情况来计算"
            },
            "configuration": {
                "name": "配置评分",
                "weight": 0.25,
                "description": "评估系统的安全配置是否符合最佳实践"
            },
            "compliance": {
                "name": "合规评分",
                "weight": 0.25,
                "description": "检查系统是否符合相关安全标准和法规要求"
            },
            "threat_intelligence": {
                "name": "威胁情报评分",
                "weight": 0.2,
                "description": "基于外部威胁情报数据，评估系统面临的潜在威胁风险"
            }
        }
        
        # 构建维度对象
        dimensions = []
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for dim_key, config in dimension_configs.items():
            score = scores.get(dim_key, 0.0)
            dimension = ScoreDimension(
                name=config["name"],
                score=score,
                weight=config["weight"],
                description=config["description"]
            )
            dimensions.append(dimension)
            
            total_weighted_score += dimension.weighted_score
            total_weight += dimension.weight
        
        # 计算总分
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        breakdown = ScoreBreakdown(
            overall_score=round(overall_score, 2),
            dimensions=dimensions
        )
        
        logger.info(f"评分明细计算完成: overall_score={breakdown.overall_score}")
        return breakdown
    
    async def generate_score_explanation(
        self,
        breakdown: ScoreBreakdown,
        retrieval_docs: List[Document]
    ) -> ScoreExplanation:
        """生成评分解释
        
        Args:
            breakdown: 评分明细
            retrieval_docs: 检索到的相关文档
        
        Returns:
            评分解释
        """
        logger.info("生成评分解释")
        
        # 构建提示词
        prompt = f"""请为以下安全评分生成解释：

总体评分: {breakdown.overall_score}分

各维度评分:
"""
        
        for dim in breakdown.dimensions:
            prompt += f"\n{dim.name}: {dim.score}分 (权重{dim.weight*100}%, 加权分数{dim.weighted_score:.2f}分)"
            prompt += f"\n  说明: {dim.description}"
        
        # 添加检索到的文档作为参考
        if retrieval_docs:
            prompt += "\n\n参考文档:"
            for i, doc in enumerate(retrieval_docs[:3], 1):
                prompt += f"\n{i}. {doc.page_content}"
        
        prompt += """

请生成一个评分解释，包括：
1. 总体评分的含义
2. 各维度评分的逻辑和计算方法
3. 评分的计算公式

解释要专业、准确，长度控制在300字以内。"""
        
        try:
            # 使用LLM生成解释
            response = await self.llm.ainvoke(prompt)
            
            # 构建评分解释对象
            explanation = ScoreExplanation(
                explanation=response.content,
                score_logic="各维度评分 × 权重加权平均",
                calculation_method=f"总评分 = Σ(各维度评分 × 维度权重)，其中 Σ权重 = {sum(dim.weight for dim in breakdown.dimensions):.2f}",
                references=[doc.metadata.get("category", "unknown") for doc in retrieval_docs]
            )
            
            logger.info(f"评分解释生成完成: {len(explanation.explanation)} 字符")
            return explanation
            
        except Exception as e:
            logger.error(f"生成评分解释失败: {str(e)}", exc_info=True)
            
            # 回退到简单解释
            explanation = ScoreExplanation(
                explanation=f"您的安全评分为{breakdown.overall_score}分。这是根据漏洞、配置、合规和威胁情报四个维度综合计算得出的结果。各维度根据重要性分配了不同的权重。",
                score_logic="各维度评分 × 权重加权平均",
                calculation_method="总评分 = Σ(各维度评分 × 维度权重)",
                references=[]
            )
            
            return explanation
    
    async def generate_improvement_suggestions(
        self,
        breakdown: ScoreBreakdown,
        retrieval_docs: List[Document]
    ) -> List[ImprovementSuggestion]:
        """生成改进建议
        
        Args:
            breakdown: 评分明细
            retrieval_docs: 检索到的相关文档
        
        Returns:
            改进建议列表
        """
        logger.info("生成改进建议")
        
        # 基于低分维度生成建议
        suggestions = []
        
        # 找出评分最低的维度
        sorted_dims = sorted(breakdown.dimensions, key=lambda d: d.score)
        low_score_dims = [d for d in sorted_dims if d.score < 80]
        
        for dim in low_score_dims:
            # 确定优先级
            if dim.score < 50:
                priority = "high"
                estimated_effort = "weeks"
            elif dim.score < 70:
                priority = "medium"
                estimated_effort = "days"
            else:
                priority = "low"
                estimated_effort = "hours"
            
            # 生成建议
            suggestion_map = {
                "漏洞评分": "及时安装安全补丁、定期进行漏洞扫描、建立漏洞修复流程、优先处理高严重级别漏洞",
                "配置评分": "启用多因素认证、配置密码复杂度策略、定期轮换密钥、限制管理员权限、启用安全审计日志",
                "合规评分": "对照等保2.0要求进行全面检查、建立合规管理体系、定期进行合规评估、保留合规审计记录",
                "威胁情报评分": "部署威胁情报平台、订阅威胁情报源、建立威胁响应流程、进行威胁狩猎活动"
            }
            
            suggestion_text = suggestion_map.get(dim.name, "请参考相关文档进行改进")
            
            # 计算预期影响
            expected_impact = (100 - dim.score) * dim.weight * 0.5  # 估算可以达到的一半提升
            
            suggestions.append(ImprovementSuggestion(
                priority=priority,
                dimension=dim.name,
                suggestion=suggestion_text,
                expected_impact=round(expected_impact, 2),
                estimated_effort=estimated_effort
            ))
        
        logger.info(f"生成 {len(suggestions)} 条改进建议")
        return suggestions
    
    async def execute(
        self,
        input_params: Dict[str, Any],
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ScoreInterpretationResult:
        """执行评分解读
        
        Args:
            input_params: 输入参数
                - scores: 各维度评分字典，格式为 {维度名: 分数}
                - query: 查询文本（用于文档检索）
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            评分解读结果
        """
        call_id = f"call_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        
        logger.info(f"开始执行评分解读 [{call_id}]")
        
        try:
            # 1. 获取各维度评分
            scores = input_params.get("scores", {})
            if not scores:
                raise ValueError("缺少scores参数")
            
            # 2. 计算评分明细
            breakdown = self.calculate_score_breakdown(scores)
            
            # 3. 检索相关文档
            query = input_params.get("query", f"安全评分 {breakdown.overall_score}分")
            retrieval_docs = await self.retrieve_documents(query, k=5)
            
            # 4. 生成评分解释
            explanation = await self.generate_score_explanation(breakdown, retrieval_docs)
            
            # 5. 生成改进建议
            suggestions = await self.generate_improvement_suggestions(breakdown, retrieval_docs)
            
            # 6. 构建结果
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            result = ScoreInterpretationResult(
                breakdown=breakdown,
                explanation=explanation,
                suggestions=suggestions,
                retrieval_docs=retrieval_docs,
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
                f"评分解读执行完成 [{call_id}]: "
                f"耗时={execution_time:.2f}s, 评分={breakdown.overall_score}分, "
                f"建议数={len(suggestions)}"
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.error(f"评分解读执行失败 [{call_id}]: {str(e)}", exc_info=True)
            
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
        output_result: Optional[ScoreInterpretationResult],
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
                agent_name="ScoringAgent",
                intent="scoring_explanation",
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

# 全局评分解读Agent实例
_scoring_agent: Optional[ScoringAgent] = None


def get_scoring_agent(
    db_manager: DatabaseManager,
    llm: Optional[ChatOpenAI] = None,
    embeddings: Optional[OpenAIEmbeddings] = None,
    vector_store_path: Optional[str] = None
) -> ScoringAgent:
    """获取评分解读Agent实例（单例模式）
    
    Args:
        db_manager: 数据库管理器
        llm: LLM实例（可选）
        embeddings: 嵌入模型实例（可选）
        vector_store_path: 向量数据库路径（可选）
    
    Returns:
        评分解读Agent实例
    """
    global _scoring_agent
    
    if _scoring_agent is None:
        _scoring_agent = ScoringAgent(
            db_manager=db_manager,
            llm=llm,
            embeddings=embeddings,
            vector_store_path=vector_store_path
        )
    
    return _scoring_agent


# 导出
__all__ = [
    "ScoreDimension",
    "ScoreBreakdown",
    "ScoreExplanation",
    "ImprovementSuggestion",
    "ScoreInterpretationResult",
    "ScoringAgent",
    "get_scoring_agent"
]
