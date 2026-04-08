"""
威胁分析Agent
负责威胁情报查询、攻击模式分析、攻击图构建、威胁链路识别、威胁评估
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from langchain_openai import ChatOpenAI

from src.config.settings import settings
from src.utils.logger import logger
from src.database.db_pool import DatabaseManager
from src.database.models import AgentCall, ThreatIntelligence


# ============ 数据结构定义 ============

class ThreatLevel(str, Enum):
    """威胁等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AttackStage(str, Enum):
    """攻击阶段（MITRE ATT&CK）"""
    RECONNAISSANCE = "reconnaissance"
    RESOURCE_DEVELOPMENT = "resource_development"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


@dataclass
class ThreatIntel:
    """威胁情报"""
    indicator_type: str  # ip, domain, hash, url
    indicator_value: str
    threat_level: ThreatLevel
    source: str
    confidence: float
    description: str
    first_seen: datetime
    last_seen: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "indicator_type": self.indicator_type,
            "indicator_value": self.indicator_value,
            "threat_level": self.threat_level.value,
            "source": self.source,
            "confidence": self.confidence,
            "description": self.description,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "attributes": self.attributes
        }


@dataclass
class AttackPattern:
    """攻击模式"""
    attack_stage: AttackStage
    techniques: List[str]  # MITRE ATT&CK技术ID
    related_cves: List[str]
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "attack_stage": self.attack_stage.value,
            "techniques": self.techniques,
            "related_cves": self.related_cves,
            "description": self.description
        }


@dataclass
class GraphNode:
    """攻击图节点"""
    id: str
    type: str  # ip, domain, user, process, file
    value: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "value": self.value,
            "attributes": self.attributes
        }


@dataclass
class GraphEdge:
    """攻击图边"""
    source: str
    target: str
    relation: str  # connected_to, accessed, downloaded, executed
    weight: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AttackPath:
    """威胁链路"""
    path: List[str]  # 节点ID列表
    start_time: datetime
    end_time: datetime
    threat_level: ThreatLevel
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "threat_level": self.threat_level.value
        }


@dataclass
class ThreatAssessment:
    """威胁评估"""
    threat_level: ThreatLevel
    confidence: float
    impact_scope: List[str]  # system, data, user, network
    affected_assets: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "threat_level": self.threat_level.value,
            "confidence": self.confidence,
            "impact_scope": self.impact_scope,
            "affected_assets": self.affected_assets,
            "recommendations": self.recommendations
        }


@dataclass
class ThreatAnalysisResult:
    """威胁分析结果"""
    threat_intel: List[ThreatIntel]
    attack_patterns: List[AttackPattern]
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    paths: List[AttackPath]
    assessment: ThreatAssessment
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "threat_intel": [intel.to_dict() for intel in self.threat_intel],
            "attack_patterns": [pattern.to_dict() for pattern in self.attack_patterns],
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "paths": [path.to_dict() for path in self.paths],
            "assessment": self.assessment.to_dict(),
            "execution_time": self.execution_time
        }


# ============ 威胁分析Agent ============

class ThreatAnalysisAgent:
    """威胁分析Agent
    
    职责：
    1. 威胁情报查询（IP、域名、Hash、IOC等多维度查询）
    2. 攻击模式分析（识别攻击阶段、分析TTP、映射CVE漏洞）
    3. 攻击图构建（创建节点和边、计算权重）
    4. 威胁链路识别（追踪威胁链路、识别因果关系、分析时间序列）
    5. 威胁评估（评估威胁等级、分析影响范围、提供处置建议）
    6. MITRE ATT&CK映射
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        llm: Optional[ChatOpenAI] = None
    ):
        """初始化威胁分析Agent"""
        self.db = db_manager
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3
        )
        
        # MITRE ATT&CK映射表
        self._mitre_attack_mapping = {
            AttackStage.RECONNAISSANCE: {
                "techniques": ["T1595", "T1598"],
                "description": "侦察阶段，攻击者收集目标信息"
            },
            AttackStage.RESOURCE_DEVELOPMENT: {
                "techniques": ["T1583", "T1584"],
                "description": "资源开发阶段，攻击者准备攻击工具"
            },
            AttackStage.INITIAL_ACCESS: {
                "techniques": ["T1190", "T1566"],
                "description": "初始访问阶段，攻击者获取系统访问权限"
            },
            AttackStage.EXECUTION: {
                "techniques": ["T1059", "T1204"],
                "description": "执行阶段，攻击者在目标系统执行代码"
            },
            AttackStage.PERSISTENCE: {
                "techniques": ["T1547", "T1053"],
                "description": "持久化阶段，攻击者保持访问权限"
            },
            AttackStage.DEFENSE_EVASION: {
                "techniques": ["T1562", "T1564"],
                "description": "防御规避阶段，攻击者绕过安全检测"
            },
            AttackStage.CREDENTIAL_ACCESS: {
                "techniques": ["T1056", "T1110"],
                "description": "凭证访问阶段，攻击者窃取认证信息"
            },
            AttackStage.DISCOVERY: {
                "techniques": ["T1082", "T1083"],
                "description": "发现阶段，攻击者探索系统"
            },
            AttackStage.LATERAL_MOVEMENT: {
                "techniques": ["T1021", "T1077"],
                "description": "横向移动阶段，攻击者在网络中传播"
            },
            AttackStage.COLLECTION: {
                "techniques": ["T1005", "T1113"],
                "description": "收集阶段，攻击者收集数据"
            },
            AttackStage.COMMAND_CONTROL: {
                "techniques": ["T1102", "T1071"],
                "description": "命令控制阶段，攻击者控制被入侵系统"
            },
            AttackStage.EXFILTRATION: {
                "techniques": ["T1041", "T1048"],
                "description": "数据窃取阶段，攻击者导出数据"
            },
            AttackStage.IMPACT: {
                "techniques": ["T1489", "T1491"],
                "description": "影响阶段，攻击者造成破坏"
            }
        }
        
        # 模拟威胁情报数据
        self._threat_intel_db: Dict[str, List[ThreatIntel]] = {}
        self._initialize_threat_intel_db()
        
        logger.info("威胁分析Agent初始化完成")
    
    def _initialize_threat_intel_db(self):
        """初始化模拟威胁情报数据库"""
        logger.info("初始化威胁情报数据库")
        
        # IP地址威胁情报
        ip_intels = [
            ThreatIntel(
                indicator_type="ip",
                indicator_value="192.168.1.100",
                threat_level=ThreatLevel.HIGH,
                source="internal_honeypot",
                confidence=0.9,
                description="内部蜜罐检测到来自该IP的异常连接",
                first_seen=datetime.utcnow() - timedelta(days=7),
                last_seen=datetime.utcnow() - timedelta(hours=2),
                attributes={"connection_count": 150, "failed_attempts": 89}
            ),
            ThreatIntel(
                indicator_type="ip",
                indicator_value="10.0.0.5",
                threat_level=ThreatLevel.CRITICAL,
                source="external_threat_feed",
                confidence=0.95,
                description="外部威胁情报源标记为已知的攻击者IP",
                first_seen=datetime.utcnow() - timedelta(days=30),
                last_seen=datetime.utcnow() - timedelta(hours=1),
                attributes={"campaign": "APT-28", "attack_type": "brute_force"}
            )
        ]
        
        # 域名威胁情报
        domain_intels = [
            ThreatIntel(
                indicator_type="domain",
                indicator_value="malicious-domain.com",
                threat_level=ThreatLevel.CRITICAL,
                source="external_threat_feed",
                confidence=0.98,
                description="已知的恶意域名，用于C&C通信",
                first_seen=datetime.utcnow() - timedelta(days=60),
                last_seen=datetime.utcnow() - timedelta(hours=6),
                attributes={"category": "c2", "tactics": ["command_and_control"]}
            ),
            ThreatIntel(
                indicator_type="domain",
                indicator_value="phishing-site.net",
                threat_level=ThreatLevel.HIGH,
                source="external_threat_feed",
                confidence=0.92,
                description="钓鱼网站域名，窃取用户凭证",
                first_seen=datetime.utcnow() - timedelta(days=15),
                last_seen=datetime.utcnow() - timedelta(hours=12),
                attributes={"category": "phishing", "target": "financial_sector"}
            )
        ]
        
        # Hash威胁情报
        hash_intels = [
            ThreatIntel(
                indicator_type="hash",
                indicator_value="d41d8cd98f00b204e9800998ecf8427e",
                threat_level=ThreatLevel.MEDIUM,
                source="malware_analysis",
                confidence=0.88,
                description="已知的恶意软件样本Hash",
                first_seen=datetime.utcnow() - timedelta(days=45),
                last_seen=datetime.utcnow() - timedelta(days=10),
                attributes={"malware_family": "Emotet", "file_type": "exe"}
            )
        ]
        
        self._threat_intel_db["ip"] = ip_intels
        self._threat_intel_db["domain"] = domain_intels
        self._threat_intel_db["hash"] = hash_intels
        
        logger.info(f"初始化 {len(ip_intels)} 个IP、{len(domain_intels)} 个域名、{len(hash_intels)} 个Hash威胁情报")
    
    async def query_threat_intel(
        self,
        indicator_type: str,
        indicator_value: str
    ) -> List[ThreatIntel]:
        """查询威胁情报
        
        Args:
            indicator_type: 指示器类型（ip, domain, hash）
            indicator_value: 指示器值
        
        Returns:
            威胁情报列表
        """
        logger.info(f"查询威胁情报: type={indicator_type}, value={indicator_value}")
        
        # 从模拟数据库查询
        intels = self._threat_intel_db.get(indicator_type, [])
        
        # 精确匹配
        matched_intels = [
            intel for intel in intels
            if intel.indicator_value == indicator_value
        ]
        
        # 如果没有精确匹配，尝试模糊匹配（IP前缀匹配）
        if not matched_intels and indicator_type == "ip":
            matched_intels = [
                intel for intel in intels
                if intel.indicator_value.startswith(indicator_value.rsplit(".", 1)[0])
            ]
        
        logger.info(f"匹配到 {len(matched_intels)} 条威胁情报")
        return matched_intels
    
    async def analyze_attack_patterns(
        self,
        logs: List[Dict[str, Any]]
    ) -> List[AttackPattern]:
        """分析攻击模式
        
        Args:
            logs: 安全日志列表
        
        Returns:
            攻击模式列表
        """
        logger.info(f"分析攻击模式: log_count={len(logs)}")
        
        patterns = []
        
        # 分析日志中的攻击阶段
        for log in logs:
            log_type = log.get("type", "")
            description = log.get("description", "")
            
            # 识别攻击阶段
            if "port_scan" in log_type or "reconnaissance" in description:
                stage = AttackStage.RECONNAISSANCE
            elif "exploit" in log_type or "initial_access" in description:
                stage = AttackStage.INITIAL_ACCESS
            elif "execution" in log_type or "code_injection" in description:
                stage = AttackStage.EXECUTION
            elif "persistence" in log_type or "backdoor" in description:
                stage = AttackStage.PERSISTENCE
            elif "lateral" in log_type or "movement" in description:
                stage = AttackStage.LATERAL_MOVEMENT
            elif "data_exfil" in log_type or "exfiltration" in description:
                stage = AttackStage.EXFILTRATION
            else:
                continue
            
            # 获取MITRE ATT&CK映射
            mitre_info = self._mitre_attack_mapping.get(stage, {})
            
            # 构建攻击模式
            pattern = AttackPattern(
                attack_stage=stage,
                techniques=mitre_info.get("techniques", []),
                related_cves=log.get("related_cves", []),
                description=mitre_info.get("description", "")
            )
            
            patterns.append(pattern)
        
        # 去重
        unique_patterns = []
        seen = set()
        for pattern in patterns:
            pattern_key = (pattern.attack_stage, tuple(pattern.techniques))
            if pattern_key not in seen:
                seen.add(pattern_key)
                unique_patterns.append(pattern)
        
        logger.info(f"识别到 {len(unique_patterns)} 种攻击模式")
        return unique_patterns
    
    async def build_attack_graph(
        self,
        logs: List[Dict[str, Any]]
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """构建攻击图
        
        Args:
            logs: 安全日志列表
        
        Returns:
            节点列表和边列表
        """
        logger.info(f"构建攻击图: log_count={len(logs)}")
        
        nodes = []
        edges = []
        node_dict = {}  # {value: node_id}
        
        # 提取实体（节点）
        for log in logs:
            # IP地址
            src_ip = log.get("src_ip")
            if src_ip and src_ip not in node_dict:
                node_id = f"ip_{len(nodes)}"
                node = GraphNode(
                    id=node_id,
                    type="ip",
                    value=src_ip,
                    attributes={"log_count": 1}
                )
                nodes.append(node)
                node_dict[src_ip] = node_id
            elif src_ip and src_ip in node_dict:
                nodes[node_dict[src_ip]].attributes["log_count"] += 1
            
            # 域名
            domain = log.get("domain")
            if domain and domain not in node_dict:
                node_id = f"domain_{len(nodes)}"
                node = GraphNode(
                    id=node_id,
                    type="domain",
                    value=domain,
                    attributes={"log_count": 1}
                )
                nodes.append(node)
                node_dict[domain] = node_id
            elif domain and domain in node_dict:
                nodes[node_dict[domain]].attributes["log_count"] += 1
            
            # 用户
            user = log.get("user")
            if user and user not in node_dict:
                node_id = f"user_{len(nodes)}"
                node = GraphNode(
                    id=node_id,
                    type="user",
                    value=user,
                    attributes={"log_count": 1}
                )
                nodes.append(node)
                node_dict[user] = node_id
            elif user and user in node_dict:
                nodes[node_dict[user]].attributes["log_count"] += 1
        
        # 提取关系（边）
        for log in logs:
            src_ip = log.get("src_ip")
            dst_ip = log.get("dst_ip")
            user = log.get("user")
            domain = log.get("domain")
            timestamp = log.get("timestamp", datetime.utcnow())
            
            # IP连接关系
            if src_ip and dst_ip:
                if src_ip in node_dict and dst_ip in node_dict:
                    edge = GraphEdge(
                        source=node_dict[src_ip],
                        target=node_dict[dst_ip],
                        relation="connected_to",
                        weight=1.0,
                        timestamp=timestamp
                    )
                    edges.append(edge)
            
            # 用户访问关系
            if user and src_ip:
                if user in node_dict and src_ip in node_dict:
                    edge = GraphEdge(
                        source=node_dict[user],
                        target=node_dict[src_ip],
                        relation="accessed",
                        weight=1.0,
                        timestamp=timestamp
                    )
                    edges.append(edge)
            
            # 域名连接关系
            if domain and dst_ip:
                if domain in node_dict and dst_ip in node_dict:
                    edge = GraphEdge(
                        source=node_dict[domain],
                        target=node_dict[dst_ip],
                        relation="resolved_to",
                        weight=1.0,
                        timestamp=timestamp
                    )
                    edges.append(edge)
        
        logger.info(f"构建攻击图: nodes={len(nodes)}, edges={len(edges)}")
        return nodes, edges
    
    async def identify_threat_paths(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge]
    ) -> List[AttackPath]:
        """识别威胁链路
        
        Args:
            nodes: 节点列表
            edges: 边列表
        
        Returns:
            威胁链路列表
        """
        logger.info("识别威胁链路")
        
        if not edges:
            return []
        
        # 构建邻接表
        adjacency = {node.id: [] for node in nodes}
        for edge in edges:
            adjacency[edge.source].append((edge.target, edge.timestamp))
        
        # 找到所有简单路径（深度优先搜索）
        paths = []
        visited = set()
        
        def dfs(current_node: str, current_path: List[str], start_time: datetime):
            """深度优先搜索"""
            if len(current_path) > 5:  # 限制路径长度
                return
            
            visited.add(current_node)
            
            # 记录路径
            if len(current_path) > 1:
                path = AttackPath(
                    path=current_path.copy(),
                    start_time=start_time,
                    end_time=edges[-1].timestamp if edges else datetime.utcnow(),
                    threat_level=ThreatLevel.MEDIUM  # 简化处理
                )
                paths.append(path)
            
            # 继续探索
            for neighbor, timestamp in sorted(adjacency.get(current_node, []), key=lambda x: x[1]):
                if neighbor not in visited:
                    dfs(neighbor, current_path + [neighbor], timestamp)
            
            visited.remove(current_node)
        
        # 从每个节点开始搜索
        for node in nodes[:3]:  # 限制起始节点数量
            dfs(node.id, [node.id], datetime.utcnow())
        
        # 去重
        unique_paths = []
        seen_path = set()
        for path in paths:
            path_key = tuple(path.path)
            if path_key not in seen_path and len(path.path) >= 2:
                seen_path.add(path_key)
                unique_paths.append(path)
        
        logger.info(f"识别到 {len(unique_paths)} 条威胁链路")
        return unique_paths
    
    async def assess_threat(
        self,
        threat_intels: List[ThreatIntel],
        attack_patterns: List[AttackPattern],
        paths: List[AttackPath]
    ) -> ThreatAssessment:
        """评估威胁
        
        Args:
            threat_intels: 威胁情报
            attack_patterns: 攻击模式
            paths: 威胁链路
        
        Returns:
            威胁评估
        """
        logger.info("评估威胁")
        
        # 计算威胁等级
        if not threat_intels:
            threat_level = ThreatLevel.LOW
            confidence = 0.5
        else:
            # 基于最高威胁等级
            max_level = max(
                [self._get_threat_level_value(intel.threat_level) for intel in threat_intels],
                default=0
            )
            
            if max_level >= 4:
                threat_level = ThreatLevel.CRITICAL
            elif max_level >= 3:
                threat_level = ThreatLevel.HIGH
            elif max_level >= 2:
                threat_level = ThreatLevel.MEDIUM
            else:
                threat_level = ThreatLevel.LOW
            
            # 计算置信度
            confidence = sum(intel.confidence for intel in threat_intels) / len(threat_intels)
        
        # 确定影响范围
        impact_scope = []
        affected_assets = []
        
        for intel in threat_intels:
            if intel.attributes.get("campaign"):
                impact_scope.append("system")
                affected_assets.append("campaign:" + intel.attributes["campaign"])
            
            if intel.indicator_type == "ip":
                impact_scope.append("network")
                affected_assets.append(f"ip:{intel.indicator_value}")
            
            if intel.indicator_type == "hash":
                impact_scope.append("data")
                affected_assets.append(f"file:{intel.indicator_value}")
        
        impact_scope = list(set(impact_scope))
        affected_assets = list(set(affected_assets))
        
        # 生成处置建议
        recommendations = []
        
        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            recommendations.append("立即隔离受影响的系统")
            recommendations.append("暂停所有可疑的网络连接")
            recommendations.append("联系安全团队进行应急响应")
        
        if threat_level == ThreatLevel.MEDIUM:
            recommendations.append("监控可疑活动的持续进行")
            recommendations.append("加强日志审计和分析")
        
        if attack_patterns:
            recommendations.append(f"检测到{len(attack_patterns)}种攻击模式，建议更新防护规则")
        
        if paths:
            recommendations.append(f"识别到{len(paths)}条威胁链路，建议追踪完整攻击链")
        
        assessment = ThreatAssessment(
            threat_level=threat_level,
            confidence=round(confidence, 2),
            impact_scope=impact_scope,
            affected_assets=affected_assets,
            recommendations=recommendations
        )
        
        logger.info(f"威胁评估完成: level={threat_level}, confidence={confidence:.2f}")
        return assessment
    
    def _get_threat_level_value(self, level: ThreatLevel) -> int:
        """获取威胁等级数值"""
        mapping = {
            ThreatLevel.INFO: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4
        }
        return mapping.get(level, 0)
    
    async def execute(
        self,
        input_params: Dict[str, Any],
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ThreatAnalysisResult:
        """执行威胁分析
        
        Args:
            input_params: 输入参数
                - indicator_type: 指示器类型（可选）
                - indicator_value: 指示器值（可选）
                - logs: 安全日志列表（可选）
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            威胁分析结果
        """
        call_id = f"call_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        
        logger.info(f"开始执行威胁分析 [{call_id}]")
        
        try:
            # 1. 查询威胁情报
            threat_intels = []
            indicator_type = input_params.get("indicator_type")
            indicator_value = input_params.get("indicator_value")
            
            if indicator_type and indicator_value:
                threat_intels = await self.query_threat_intel(
                    indicator_type,
                    indicator_value
                )
            
            # 2. 分析攻击模式
            attack_patterns = []
            logs = input_params.get("logs", [])
            if logs:
                attack_patterns = await self.analyze_attack_patterns(logs)
            
            # 3. 构建攻击图
            nodes, edges = [], []
            if logs:
                nodes, edges = await self.build_attack_graph(logs)
            
            # 4. 识别威胁链路
            paths = []
            if nodes and edges:
                paths = await self.identify_threat_paths(nodes, edges)
            
            # 5. 评估威胁
            assessment = await self.assess_threat(
                threat_intels,
                attack_patterns,
                paths
            )
            
            # 6. 构建结果
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            result = ThreatAnalysisResult(
                threat_intel=threat_intels,
                attack_patterns=attack_patterns,
                nodes=nodes,
                edges=edges,
                paths=paths,
                assessment=assessment,
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
                f"威胁分析执行完成 [{call_id}]: "
                f"耗时={execution_time:.2f}s, 威胁等级={assessment.threat_level.value}"
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.error(f"威胁分析执行失败 [{call_id}]: {str(e)}", exc_info=True)
            
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
        output_result: Optional[ThreatAnalysisResult],
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
                agent_name="ThreatAnalysisAgent",
                intent="threat_analysis",
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
            
            # 同时保存威胁情报到威胁情报表
            if output_result and output_result.threat_intel:
                for intel in output_result.threat_intel:
                    threat_intel = ThreatIntelligence(
                        intel_id=f"intel_{uuid.uuid4().hex[:16]}",
                        tenant_id=tenant_id,
                        indicator_type=intel.indicator_type,
                        indicator_value=intel.indicator_value,
                        threat_level=intel.threat_level.value,
                        confidence=intel.confidence,
                        source=intel.source,
                        description=intel.description,
                        attributes=intel.attributes,
                        first_seen=intel.first_seen,
                        last_seen=intel.last_seen,
                        is_active=True
                    )
                    session.add(threat_intel)
                
                await session.commit()
            
            logger.debug(f"记录Agent调用: {call_id}")


# ============ 便捷函数 ============

# 全局威胁分析Agent实例
_threat_analysis_agent: Optional[ThreatAnalysisAgent] = None


def get_threat_analysis_agent(
    db_manager: DatabaseManager,
    llm: Optional[ChatOpenAI] = None
) -> ThreatAnalysisAgent:
    """获取威胁分析Agent实例（单例模式）
    
    Args:
        db_manager: 数据库管理器
        llm: LLM实例（可选）
    
    Returns:
        威胁分析Agent实例
    """
    global _threat_analysis_agent
    
    if _threat_analysis_agent is None:
        _threat_analysis_agent = ThreatAnalysisAgent(
            db_manager=db_manager,
            llm=llm
        )
    
    return _threat_analysis_agent


# 导出
__all__ = [
    "ThreatLevel",
    "AttackStage",
    "ThreatIntel",
    "AttackPattern",
    "GraphNode",
    "GraphEdge",
    "AttackPath",
    "ThreatAssessment",
    "ThreatAnalysisResult",
    "ThreatAnalysisAgent",
    "get_threat_analysis_agent"
]
