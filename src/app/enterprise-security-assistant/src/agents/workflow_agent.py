"""
工作流协调Agent
负责任务调度、依赖管理、并行执行、结果聚合
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from src.config.settings import settings
from src.utils.logger import logger
from src.database.db_pool import DatabaseManager
from src.database.redis_pool import RedisManager
from src.database.models import WorkflowExecution, WorkflowTask, AgentCall


# ============ 数据结构定义 ============

class TaskState(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class WorkflowState(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TaskConfig:
    """任务配置"""
    task_id: str
    agent_name: str
    intent: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    task_order: int = 0


@dataclass
class WorkflowConfig:
    """工作流配置"""
    workflow_name: str
    tasks: List[TaskConfig]
    mode: str = "sequential"  # sequential, parallel, iterative
    max_concurrent_tasks: int = 5
    enable_retry: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    config: TaskConfig
    state: TaskState = TaskState.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    execution_id: str
    workflow_name: str
    state: WorkflowState
    tasks: Dict[str, TaskInfo]
    result: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    total_duration: float = 0.0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ============ 工作流执行器 ============

class WorkflowExecutor:
    """工作流执行器
    
    职责：
    1. 解析工作流配置并创建任务
    2. 管理任务依赖关系（拓扑排序）
    3. 调度任务执行（支持并行）
    4. 监控任务状态（超时、错误处理）
    5. 聚合执行结果
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_manager: RedisManager,
        llm: Optional[ChatOpenAI] = None
    ):
        """初始化工作流执行器"""
        self.db = db_manager
        self.redis = redis_manager
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3
        )
        self.lock = asyncio.Lock()
        
        # Agent执行器注册表
        self.agent_executors: Dict[str, Any] = {}
        
        logger.info("工作流执行器初始化完成")
    
    def register_agent_executor(self, agent_name: str, executor: Any):
        """注册Agent执行器
        
        Args:
            agent_name: Agent名称
            executor: Agent执行器实例
        """
        self.agent_executors[agent_name] = executor
        logger.info(f"注册Agent执行器: {agent_name}")
    
    def unregister_agent_executor(self, agent_name: str):
        """注销Agent执行器
        
        Args:
            agent_name: Agent名称
        """
        if agent_name in self.agent_executors:
            del self.agent_executors[agent_name]
            logger.info(f"注销Agent执行器: {agent_name}")
    
    async def execute(
        self,
        workflow_config: WorkflowConfig,
        tenant_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> WorkflowResult:
        """执行工作流
        
        Args:
            workflow_config: 工作流配置
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            工作流执行结果
        """
        execution_id = f"wf_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        
        logger.info(f"开始执行工作流 [{execution_id}]: {workflow_config.workflow_name}")
        
        try:
            # 1. 解析和验证工作流配置
            tasks_info = await self._parse_workflow_config(
                workflow_config,
                execution_id
            )
            
            # 2. 创建工作流执行记录
            await self._create_execution_record(
                execution_id,
                tenant_id,
                user_id,
                workflow_config,
                start_time
            )
            
            # 3. 创建任务记录
            await self._create_task_records(
                execution_id,
                tasks_info
            )
            
            # 4. 执行工作流
            result = await self._execute_workflow(
                execution_id,
                workflow_config,
                tasks_info,
                tenant_id,
                user_id,
                session_id
            )
            
            # 5. 聚合结果
            result = await self._aggregate_results(
                execution_id,
                result
            )
            
            # 6. 生成摘要
            result = await self._generate_summary(
                execution_id,
                result
            )
            
            # 7. 更新执行状态
            await self._update_execution_status(
                execution_id,
                result,
                start_time
            )
            
            logger.info(f"工作流执行完成 [{execution_id}]: 状态={result.state}, 成功率={result.success_rate:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"工作流执行失败 [{execution_id}]: {str(e)}", exc_info=True)
            
            # 创建失败结果
            result = WorkflowResult(
                execution_id=execution_id,
                workflow_name=workflow_config.workflow_name,
                state=WorkflowState.FAILED,
                tasks={},
                created_at=start_time,
                completed_at=datetime.utcnow()
            )
            
            await self._update_execution_status(execution_id, result, start_time)
            
            return result
    
    async def _parse_workflow_config(
        self,
        workflow_config: WorkflowConfig,
        execution_id: str
    ) -> Dict[str, TaskInfo]:
        """解析工作流配置
        
        Args:
            workflow_config: 工作流配置
            execution_id: 执行ID
        
        Returns:
            任务信息字典 {task_id: TaskInfo}
        """
        logger.info(f"解析工作流配置: {workflow_config.workflow_name}")
        
        tasks_info: Dict[str, TaskInfo] = {}
        
        for i, task_config in enumerate(workflow_config.tasks):
            # 创建任务信息
            task_info = TaskInfo(
                task_id=task_config.task_id,
                config=task_config,
                state=TaskState.PENDING
            )
            
            tasks_info[task_config.task_id] = task_info
            logger.info(f"  - 任务 [{i+1}]: {task_config.agent_name} ({task_config.task_id})")
        
        return tasks_info
    
    async def _validate_workflow_config(
        self,
        workflow_config: WorkflowConfig
    ) -> bool:
        """验证工作流配置
        
        Args:
            workflow_config: 工作流配置
        
        Returns:
            是否有效
        """
        # 检查工作流模式
        if workflow_config.mode not in ["sequential", "parallel", "iterative"]:
            logger.error(f"无效的工作流模式: {workflow_config.mode}")
            return False
        
        # 检查任务列表
        if not workflow_config.tasks:
            logger.error("工作流配置中没有任务")
            return False
        
        # 检查依赖关系
        task_ids = {task.task_id for task in workflow_config.tasks}
        for task in workflow_config.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    logger.error(f"任务 {task.task_id} 依赖不存在的任务: {dep}")
                    return False
        
        # 检查循环依赖（使用拓扑排序）
        try:
            self._topological_sort(workflow_config.tasks)
        except ValueError as e:
            logger.error(f"工作流配置存在循环依赖: {str(e)}")
            return False
        
        logger.info("工作流配置验证通过")
        return True
    
    async def _create_execution_record(
        self,
        execution_id: str,
        tenant_id: str,
        user_id: Optional[str],
        workflow_config: WorkflowConfig,
        created_at: datetime
    ):
        """创建工作流执行记录
        
        Args:
            execution_id: 执行ID
            tenant_id: 租户ID
            user_id: 用户ID
            workflow_config: 工作流配置
            created_at: 创建时间
        """
        async with self.db.get_session() as session:
            execution = WorkflowExecution(
                execution_id=execution_id,
                tenant_id=tenant_id,
                user_id=user_id,
                workflow_name=workflow_config.workflow_name,
                workflow_config={
                    "mode": workflow_config.mode,
                    "max_concurrent_tasks": workflow_config.max_concurrent_tasks,
                    "enable_retry": workflow_config.enable_retry,
                    "max_retries": workflow_config.max_retries,
                    "retry_delay": workflow_config.retry_delay
                },
                status=WorkflowState.PENDING.value,
                created_at=created_at
            )
            
            session.add(execution)
            await session.commit()
            
            logger.info(f"创建工作流执行记录: {execution_id}")
    
    async def _create_task_records(
        self,
        execution_id: str,
        tasks_info: Dict[str, TaskInfo]
    ):
        """创建任务记录
        
        Args:
            execution_id: 执行ID
            tasks_info: 任务信息字典
        """
        async with self.db.get_session() as session:
            for task_info in tasks_info.values():
                task = WorkflowTask(
                    task_id=task_info.task_id,
                    execution_id=execution_id,
                    task_order=task_info.config.task_order,
                    agent_name=task_info.config.agent_name,
                    intent=task_info.config.intent,
                    input_params=task_info.config.input_params,
                    dependencies=task_info.config.dependencies,
                    status=TaskState.PENDING.value,
                    timeout_seconds=task_info.config.timeout_seconds
                )
                
                session.add(task)
            
            await session.commit()
            
            logger.info(f"创建 {len(tasks_info)} 个任务记录")
    
    def _topological_sort(
        self,
        tasks: List[TaskConfig]
    ) -> List[List[str]]:
        """拓扑排序
        
        Args:
            tasks: 任务列表
        
        Returns:
            排序后的任务层级列表（每一层可以并行执行）
        
        Raises:
            ValueError: 存在循环依赖时抛出
        """
        # 构建依赖图
        in_degree: Dict[str, int] = {}
        graph: Dict[str, List[str]] = {}
        task_ids = [task.task_id for task in tasks]
        
        # 初始化
        for task_id in task_ids:
            in_degree[task_id] = 0
            graph[task_id] = []
        
        # 构建边
        task_map = {task.task_id: task for task in tasks}
        for task in tasks:
            for dep in task.dependencies:
                graph[dep].append(task.task_id)
                in_degree[task.task_id] += 1
        
        # 拓扑排序
        queue = [task_id for task_id in task_ids if in_degree[task_id] == 0]
        layers: List[List[str]] = []
        
        while queue:
            # 当前层的所有任务可以并行执行
            layer = queue.copy()
            layers.append(layer)
            queue.clear()
            
            for task_id in layer:
                for neighbor in graph[task_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        # 检查是否所有节点都访问过（循环依赖检测）
        if sum(len(layer) for layer in layers) != len(task_ids):
            raise ValueError("工作流配置存在循环依赖")
        
        logger.info(f"拓扑排序完成，共 {len(layers)} 层")
        return layers
    
    async def _execute_workflow(
        self,
        execution_id: str,
        workflow_config: WorkflowConfig,
        tasks_info: Dict[str, TaskInfo],
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> WorkflowResult:
        """执行工作流
        
        Args:
            execution_id: 执行ID
            workflow_config: 工作流配置
            tasks_info: 任务信息字典
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            工作流执行结果
        """
        logger.info(f"开始执行工作流 [{execution_id}]: 模式={workflow_config.mode}")
        
        # 更新工作流状态为running
        async with self.db.get_session() as session:
            execution = await session.get(WorkflowExecution, execution_id)
            if execution:
                execution.status = WorkflowState.RUNNING.value
                await session.commit()
        
        try:
            if workflow_config.mode == "sequential":
                result = await self._execute_sequential(
                    execution_id,
                    workflow_config,
                    tasks_info,
                    tenant_id,
                    user_id,
                    session_id
                )
            elif workflow_config.mode == "parallel":
                result = await self._execute_parallel(
                    execution_id,
                    workflow_config,
                    tasks_info,
                    tenant_id,
                    user_id,
                    session_id
                )
            elif workflow_config.mode == "iterative":
                result = await self._execute_iterative(
                    execution_id,
                    workflow_config,
                    tasks_info,
                    tenant_id,
                    user_id,
                    session_id
                )
            else:
                raise ValueError(f"不支持的工作流模式: {workflow_config.mode}")
            
            return result
            
        except Exception as e:
            logger.error(f"工作流执行异常 [{execution_id}]: {str(e)}", exc_info=True)
            
            # 创建失败结果
            return WorkflowResult(
                execution_id=execution_id,
                workflow_name=workflow_config.workflow_name,
                state=WorkflowState.FAILED,
                tasks=tasks_info
            )
    
    async def _execute_sequential(
        self,
        execution_id: str,
        workflow_config: WorkflowConfig,
        tasks_info: Dict[str, TaskInfo],
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> WorkflowResult:
        """串行执行工作流
        
        Args:
            execution_id: 执行ID
            workflow_config: 工作流配置
            tasks_info: 任务信息字典
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            工作流执行结果
        """
        logger.info(f"串行执行工作流 [{execution_id}]")
        
        # 按任务顺序排序
        sorted_tasks = sorted(
            tasks_info.values(),
            key=lambda t: t.config.task_order
        )
        
        for task_info in sorted_tasks:
            await self._execute_task(
                execution_id,
                task_info,
                tenant_id,
                user_id,
                session_id,
                workflow_config
            )
        
        # 计算状态
        state = self._calculate_workflow_state(tasks_info)
        
        return WorkflowResult(
            execution_id=execution_id,
            workflow_name=workflow_config.workflow_name,
            state=state,
            tasks=tasks_info
        )
    
    async def _execute_parallel(
        self,
        execution_id: str,
        workflow_config: WorkflowConfig,
        tasks_info: Dict[str, TaskInfo],
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> WorkflowResult:
        """并行执行工作流（基于依赖关系）
        
        Args:
            execution_id: 执行ID
            workflow_config: 工作流配置
            tasks_info: 任务信息字典
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            工作流执行结果
        """
        logger.info(f"并行执行工作流 [{execution_id}]")
        
        # 拓扑排序
        layers = self._topological_sort([
            task_info.config for task_info in tasks_info.values()
        ])
        
        # 按层级执行
        for layer_idx, layer in enumerate(layers):
            logger.info(f"执行第 {layer_idx + 1} 层，共 {len(layer)} 个任务")
            
            # 并行执行当前层的任务
            tasks_to_execute = [
                tasks_info[task_id] for task_id in layer
            ]
            
            await asyncio.gather(*[
                self._execute_task(
                    execution_id,
                    task_info,
                    tenant_id,
                    user_id,
                    session_id,
                    workflow_config
                )
                for task_info in tasks_to_execute
            ])
        
        # 计算状态
        state = self._calculate_workflow_state(tasks_info)
        
        return WorkflowResult(
            execution_id=execution_id,
            workflow_name=workflow_config.workflow_name,
            state=state,
            tasks=tasks_info
        )
    
    async def _execute_iterative(
        self,
        execution_id: str,
        workflow_config: WorkflowConfig,
        tasks_info: Dict[str, TaskInfo],
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> WorkflowResult:
        """迭代执行工作流（循环直到满足条件）
        
        Args:
            execution_id: 执行ID
            workflow_config: 工作流配置
            tasks_info: 任务信息字典
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            工作流执行结果
        """
        logger.info(f"迭代执行工作流 [{execution_id}]")
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"开始第 {iteration} 次迭代")
            
            # 串行执行所有任务
            for task_info in tasks_info.values():
                await self._execute_task(
                    execution_id,
                    task_info,
                    tenant_id,
                    user_id,
                    session_id,
                    workflow_config
                )
            
            # 检查是否满足停止条件（所有任务都成功）
            all_completed = all(
                task_info.state == TaskState.COMPLETED
                for task_info in tasks_info.values()
            )
            
            if all_completed:
                logger.info(f"第 {iteration} 次迭代完成，所有任务成功")
                break
        
        # 计算状态
        state = self._calculate_workflow_state(tasks_info)
        
        return WorkflowResult(
            execution_id=execution_id,
            workflow_name=workflow_config.workflow_name,
            state=state,
            tasks=tasks_info
        )
    
    async def _execute_task(
        self,
        execution_id: str,
        task_info: TaskInfo,
        tenant_id: str,
        user_id: Optional[str],
        session_id: Optional[str],
        workflow_config: WorkflowConfig
    ):
        """执行单个任务
        
        Args:
            execution_id: 执行ID
            task_info: 任务信息
            tenant_id: 租户ID
            user_id: 用户ID
            session_id: 会话ID
            workflow_config: 工作流配置
        """
        task_id = task_info.task_id
        logger.info(f"开始执行任务 [{execution_id}/{task_id}]: {task_info.config.agent_name}")
        
        # 更新任务状态为running
        task_info.state = TaskState.RUNNING
        task_info.started_at = datetime.utcnow()
        
        await self._update_task_status(execution_id, task_id, TaskState.RUNNING)
        
        try:
            # 获取Agent执行器
            executor = self.agent_executors.get(task_info.config.agent_name)
            
            if executor is None:
                raise ValueError(f"Agent执行器未注册: {task_info.config.agent_name}")
            
            # 执行任务
            timeout = task_info.config.timeout_seconds or 300  # 默认5分钟
            
            task_result = await asyncio.wait_for(
                executor.execute(
                    input_params=task_info.config.input_params or {},
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id
                ),
                timeout=timeout
            )
            
            # 更新任务结果
            task_info.result = task_result
            task_info.state = TaskState.COMPLETED
            task_info.completed_at = datetime.utcnow()
            task_info.duration = (task_info.completed_at - task_info.started_at).total_seconds()
            
            await self._update_task_status(
                execution_id,
                task_id,
                TaskState.COMPLETED,
                result=task_result,
                duration=task_info.duration
            )
            
            logger.info(
                f"任务执行完成 [{execution_id}/{task_id}]: "
                f"状态=COMPLETED, 耗时={task_info.duration:.2f}s"
            )
            
        except asyncio.TimeoutError:
            # 任务超时
            task_info.state = TaskState.TIMEOUT
            task_info.error = "任务执行超时"
            task_info.completed_at = datetime.utcnow()
            task_info.duration = timeout
            
            await self._update_task_status(
                execution_id,
                task_id,
                TaskState.TIMEOUT,
                error_message="任务执行超时"
            )
            
            logger.error(f"任务执行超时 [{execution_id}/{task_id}]")
            
        except Exception as e:
            # 任务失败
            task_info.state = TaskState.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.utcnow()
            
            if task_info.started_at:
                task_info.duration = (task_info.completed_at - task_info.started_at).total_seconds()
            
            await self._update_task_status(
                execution_id,
                task_id,
                TaskState.FAILED,
                error_message=str(e)
            )
            
            logger.error(f"任务执行失败 [{execution_id}/{task_id}]: {str(e)}", exc_info=True)
    
    async def _update_task_status(
        self,
        execution_id: str,
        task_id: str,
        status: TaskState,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration: Optional[float] = None
    ):
        """更新任务状态
        
        Args:
            execution_id: 执行ID
            task_id: 任务ID
            status: 任务状态
            result: 任务结果
            error_message: 错误消息
            duration: 执行时长
        """
        async with self.db.get_session() as session:
            task = await session.get(WorkflowTask, task_id)
            if task:
                task.status = status.value
                
                if result is not None:
                    task.result = result
                
                if error_message is not None:
                    task.error_message = error_message
                
                if duration is not None:
                    task.duration = duration
                
                if status == TaskState.RUNNING:
                    task.started_at = datetime.utcnow()
                elif status in [TaskState.COMPLETED, TaskState.FAILED, TaskState.TIMEOUT]:
                    task.completed_at = datetime.utcnow()
                
                await session.commit()
    
    def _calculate_workflow_state(
        self,
        tasks_info: Dict[str, TaskInfo]
    ) -> WorkflowState:
        """计算工作流状态
        
        Args:
            tasks_info: 任务信息字典
        
        Returns:
            工作流状态
        """
        states = [task.state for task in tasks_info.values()]
        
        # 检查是否有失败的任务
        if TaskState.FAILED in states:
            return WorkflowState.FAILED
        
        # 检查是否有超时的任务
        if TaskState.TIMEOUT in states:
            return WorkflowState.TIMEOUT
        
        # 检查是否所有任务都已完成
        if all(state == TaskState.COMPLETED for state in states):
            return WorkflowState.COMPLETED
        
        # 默认为running
        return WorkflowState.RUNNING
    
    async def _aggregate_results(
        self,
        execution_id: str,
        result: WorkflowResult
    ) -> WorkflowResult:
        """聚合任务结果
        
        Args:
            execution_id: 执行ID
            result: 工作流执行结果
        
        Returns:
            聚合后的工作流执行结果
        """
        logger.info(f"聚合任务结果 [{execution_id}]")
        
        # 收集所有任务结果
        aggregated_result = {
            "tasks": {},
            "errors": [],
            "summary": {}
        }
        
        for task_id, task_info in result.tasks.items():
            task_result = {
                "agent": task_info.config.agent_name,
                "status": task_info.state.value,
                "duration": task_info.duration
            }
            
            if task_info.result is not None:
                task_result["result"] = task_info.result
            
            if task_info.error is not None:
                task_result["error"] = task_info.error
                aggregated_result["errors"].append({
                    "task_id": task_id,
                    "error": task_info.error
                })
            
            aggregated_result["tasks"][task_id] = task_result
        
        # 计算统计信息
        total_tasks = len(result.tasks)
        completed_tasks = sum(
            1 for task in result.tasks.values()
            if task.state == TaskState.COMPLETED
        )
        failed_tasks = sum(
            1 for task in result.tasks.values()
            if task.state == TaskState.FAILED
        )
        timeout_tasks = sum(
            1 for task in result.tasks.values()
            if task.state == TaskState.TIMEOUT
        )
        
        aggregated_result["summary"] = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "timeout_tasks": timeout_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
        }
        
        result.result = aggregated_result
        result.success_rate = aggregated_result["summary"]["success_rate"]
        
        logger.info(
            f"结果聚合完成 [{execution_id}]: "
            f"总数={total_tasks}, 成功={completed_tasks}, "
            f"失败={failed_tasks}, 超时={timeout_tasks}, "
            f"成功率={result.success_rate:.2%}"
        )
        
        return result
    
    async def _generate_summary(
        self,
        execution_id: str,
        result: WorkflowResult
    ) -> WorkflowResult:
        """生成工作流执行摘要
        
        Args:
            execution_id: 执行ID
            result: 工作流执行结果
        
        Returns:
            带摘要的工作流执行结果
        """
        logger.info(f"生成执行摘要 [{execution_id}]")
        
        # 构建提示词
        prompt = f"""请为以下工作流执行结果生成执行摘要：

工作流名称: {result.workflow_name}
执行状态: {result.state.value}
任务总数: {len(result.tasks)}
成功任务数: {sum(1 for t in result.tasks.values() if t.state == TaskState.COMPLETED)}
失败任务数: {sum(1 for t in result.tasks.values() if t.state == TaskState.FAILED)}
超时任务数: {sum(1 for t in result.tasks.values() if t.state == TaskState.TIMEOUT)}

任务详情:
"""
        
        for task_id, task_info in result.tasks.items():
            prompt += f"\n{task_id}:\n"
            prompt += f"  Agent: {task_info.config.agent_name}\n"
            prompt += f"  状态: {task_info.state.value}\n"
            if task_info.error:
                prompt += f"  错误: {task_info.error}\n"
        
        prompt += """

请生成一个简洁的执行摘要，包括：
1. 工作流执行的整体情况
2. 成功执行的要点
3. 遇到的问题和错误
4. 建议的改进措施

摘要长度控制在200字以内。"""
        
        try:
            # 使用LLM生成摘要
            response = await self.llm.ainvoke(prompt)
            result.summary = response.content
            
            logger.info(f"执行摘要生成完成 [{execution_id}]")
            
        except Exception as e:
            logger.error(f"生成执行摘要失败 [{execution_id}]: {str(e)}", exc_info=True)
            result.summary = None
        
        return result
    
    async def _update_execution_status(
        self,
        execution_id: str,
        result: WorkflowResult,
        start_time: datetime
    ):
        """更新工作流执行状态
        
        Args:
            execution_id: 执行ID
            result: 工作流执行结果
            start_time: 开始时间
        """
        async with self.db.get_session() as session:
            execution = await session.get(WorkflowExecution, execution_id)
            if execution:
                execution.status = result.state.value
                execution.result = result.result
                execution.summary = {"summary": result.summary}
                execution.total_duration = (result.completed_at or datetime.utcnow() - start_time).total_seconds()
                execution.success_rate = result.success_rate
                execution.completed_at = result.completed_at or datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"更新工作流执行状态 [{execution_id}]: {result.state.value}")


# ============ 便捷函数 ============

# 全局工作流执行器实例
_workflow_executor: Optional[WorkflowExecutor] = None


def get_workflow_executor(
    db_manager: DatabaseManager,
    redis_manager: RedisManager,
    llm: Optional[ChatOpenAI] = None
) -> WorkflowExecutor:
    """获取工作流执行器实例（单例模式）
    
    Args:
        db_manager: 数据库管理器
        redis_manager: Redis管理器
        llm: LLM实例（可选）
    
    Returns:
        工作流执行器实例
    """
    global _workflow_executor
    
    if _workflow_executor is None:
        _workflow_executor = WorkflowExecutor(
            db_manager=db_manager,
            redis_manager=redis_manager,
            llm=llm
        )
    
    return _workflow_executor


# 导出
__all__ = [
    "TaskState",
    "WorkflowState",
    "TaskConfig",
    "WorkflowConfig",
    "TaskInfo",
    "WorkflowResult",
    "WorkflowExecutor",
    "get_workflow_executor"
]
