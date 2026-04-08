#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控中间件
用于监控工具和模型调用的性能指标，包括执行时间、成功率、调用频率等
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Callable, Any, Dict, List, Optional
from collections import defaultdict
from functools import wraps

from langchain.agents.middleware import wrap_tool_call, wrap_model_call


logger = logging.getLogger(__name__)


class MetricsCollector:
    """指标收集器"""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        
        # 工具调用指标
        self.tool_call_counts: Dict[str, int] = defaultdict(int)
        self.tool_call_times: Dict[str, List[float]] = defaultdict(list)
        self.tool_error_counts: Dict[str, int] = defaultdict(int)
        
        # 模型调用指标
        self.model_call_counts: Dict[str, int] = defaultdict(int)
        self.model_call_times: Dict[str, List[float]] = defaultdict(list)
        self.model_error_counts: Dict[str, int] = defaultdict(int)
        
        # 调用历史
        self.call_history: List[Dict] = []

    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool):
        """记录工具调用"""
        self.tool_call_counts[tool_name] += 1
        self.tool_call_times[tool_name].append(duration_ms)
        
        if not success:
            self.tool_error_counts[tool_name] += 1
        
        # 限制历史记录大小
        if len(self.tool_call_times[tool_name]) > self.max_history_size:
            self.tool_call_times[tool_name] = self.tool_call_times[tool_name][-self.max_history_size:]
        
        # 添加到调用历史
        self._add_to_history({
            'type': 'tool',
            'name': tool_name,
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.now()
        })

    def record_model_call(self, model_name: str, duration_ms: float, success: bool):
        """记录模型调用"""
        self.model_call_counts[model_name] += 1
        self.model_call_times[model_name].append(duration_ms)
        
        if not success:
            self.model_error_counts[model_name] += 1
        
        # 限制历史记录大小
        if len(self.model_call_times[model_name]) > self.max_history_size:
            self.model_call_times[model_name] = self.model_call_times[model_name][-self.max_history_size:]
        
        # 添加到调用历史
        self._add_to_history({
            'type': 'model',
            'name': model_name,
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.now()
        })

    def _add_to_history(self, record: Dict):
        """添加到调用历史"""
        self.call_history.append(record)
        
        # 限制历史记录大小
        if len(self.call_history) > self.max_history_size:
            self.call_history = self.call_history[-self.max_history_size:]

    def get_tool_stats(self, tool_name: str) -> Dict:
        """获取工具统计信息"""
        if tool_name not in self.tool_call_counts:
            return {}
        
        call_times = self.tool_call_times[tool_name]
        
        if not call_times:
            return {
                'call_count': self.tool_call_counts[tool_name],
                'error_count': self.tool_error_counts[tool_name],
                'success_rate': 1.0 if self.tool_error_counts[tool_name] == 0 else 0.0,
                'avg_duration_ms': 0,
                'min_duration_ms': 0,
                'max_duration_ms': 0
            }
        
        return {
            'call_count': self.tool_call_counts[tool_name],
            'error_count': self.tool_error_counts[tool_name],
            'success_rate': (self.tool_call_counts[tool_name] - self.tool_error_counts[tool_name]) / self.tool_call_counts[tool_name],
            'avg_duration_ms': sum(call_times) / len(call_times),
            'min_duration_ms': min(call_times),
            'max_duration_ms': max(call_times),
            'p95_duration_ms': sorted(call_times)[int(len(call_times) * 0.95)] if len(call_times) >= 20 else max(call_times),
            'p99_duration_ms': sorted(call_times)[int(len(call_times) * 0.99)] if len(call_times) >= 100 else max(call_times)
        }

    def get_model_stats(self, model_name: str) -> Dict:
        """获取模型统计信息"""
        if model_name not in self.model_call_counts:
            return {}
        
        call_times = self.model_call_times[model_name]
        
        if not call_times:
            return {
                'call_count': self.model_call_counts[model_name],
                'error_count': self.model_error_counts[model_name],
                'success_rate': 1.0 if self.model_error_counts[model_name] == 0 else 0.0,
                'avg_duration_ms': 0,
                'min_duration_ms': 0,
                'max_duration_ms': 0
            }
        
        return {
            'call_count': self.model_call_counts[model_name],
            'error_count': self.model_error_counts[model_name],
            'success_rate': (self.model_call_counts[model_name] - self.model_error_counts[model_name]) / self.model_call_counts[model_name],
            'avg_duration_ms': sum(call_times) / len(call_times),
            'min_duration_ms': min(call_times),
            'max_duration_ms': max(call_times),
            'p95_duration_ms': sorted(call_times)[int(len(call_times) * 0.95)] if len(call_times) >= 20 else max(call_times),
            'p99_duration_ms': sorted(call_times)[int(len(call_times) * 0.99)] if len(call_times) >= 100 else max(call_times)
        }

    def get_all_tool_stats(self) -> Dict[str, Dict]:
        """获取所有工具的统计信息"""
        return {tool: self.get_tool_stats(tool) for tool in self.tool_call_counts}

    def get_all_model_stats(self) -> Dict[str, Dict]:
        """获取所有模型的统计信息"""
        return {model: self.get_model_stats(model) for model in self.model_call_counts}

    def get_recent_history(self, minutes: int = 5) -> List[Dict]:
        """获取最近 N 分钟的调用历史"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [record for record in self.call_history if record['timestamp'] >= cutoff]

    def reset(self):
        """重置所有指标"""
        self.tool_call_counts.clear()
        self.tool_call_times.clear()
        self.tool_error_counts.clear()
        self.model_call_counts.clear()
        self.model_call_times.clear()
        self.model_error_counts.clear()
        self.call_history.clear()


class MonitoringMiddleware:
    """监控中间件"""

    def __init__(self, collector: MetricsCollector = None):
        self.collector = collector or MetricsCollector()

    def create_tool_monitoring_middleware(self):
        """创建工具监控中间件"""

        @wrap_tool_call
        def tool_monitoring_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            工具调用监控中间件

            功能：
            1. 记录工具调用的开始和结束时间
            2. 计算执行时间
            3. 记录成功/失败状态
            4. 汇总统计指标
            """
            tool_name = getattr(request, 'tool_name', 'unknown')
            start_time = time.time()
            success = False

            try:
                # 执行工具调用
                response = handler(request)
                success = True
                
                return response

            except Exception as e:
                success = False
                
                # 记录错误
                logger.error(f"[Tool Monitoring] Tool {tool_name} failed: {type(e).__name__}: {e}")
                
                # 重新抛出异常
                raise

            finally:
                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录指标
                self.collector.record_tool_call(tool_name, duration_ms, success)
                
                # 记录日志
                status = "SUCCESS" if success else "FAILED"
                logger.info(
                    f"[Tool Monitoring] Tool: {tool_name} | Status: {status} | "
                    f"Duration: {duration_ms:.2f}ms"
                )

        return tool_monitoring_middleware

    def create_model_monitoring_middleware(self):
        """创建模型监控中间件"""

        @wrap_model_call
        def model_monitoring_middleware(
            request: Any,
            handler: Callable[[Any], Any]
        ) -> Any:
            """
            模型调用监控中间件

            功能：
            1. 记录模型调用的开始和结束时间
            2. 计算执行时间
            3. 记录成功/失败状态
            4. 汇总统计指标
            """
            # 尝试获取模型名称
            model = getattr(request, 'model', None)
            model_name = getattr(model, 'model_name', 'unknown') if model else 'unknown'
            
            start_time = time.time()
            success = False

            try:
                # 执行模型调用
                response = handler(request)
                success = True
                
                return response

            except Exception as e:
                success = False
                
                # 记录错误
                logger.error(f"[Model Monitoring] Model {model_name} failed: {type(e).__name__}: {e}")
                
                # 重新抛出异常
                raise

            finally:
                # 计算执行时间
                duration_ms = (time.time() - start_time) * 1000
                
                # 记录指标
                self.collector.record_model_call(model_name, duration_ms, success)
                
                # 记录日志
                status = "SUCCESS" if success else "FAILED"
                logger.info(
                    f"[Model Monitoring] Model: {model_name} | Status: {status} | "
                    f"Duration: {duration_ms:.2f}ms"
                )

        return model_monitoring_middleware


# 全局监控中间件实例
_global_monitoring_middleware: Optional[MonitoringMiddleware] = None


def get_monitoring_middleware(collector: MetricsCollector = None) -> MonitoringMiddleware:
    """获取监控中间件实例（单例）"""
    global _global_monitoring_middleware
    if _global_monitoring_middleware is None or collector is not None:
        _global_monitoring_middleware = MonitoringMiddleware(collector)
    return _global_monitoring_middleware


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器"""
    return get_monitoring_middleware().collector


def create_tool_monitoring_middleware(collector: MetricsCollector = None) -> Callable:
    """便捷函数：创建工具监控中间件"""
    return get_monitoring_middleware(collector).create_tool_monitoring_middleware()


def create_model_monitoring_middleware(collector: MetricsCollector = None) -> Callable:
    """便捷函数：创建模型监控中间件"""
    return get_monitoring_middleware(collector).create_model_monitoring_middleware()
