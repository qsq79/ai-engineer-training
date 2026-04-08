#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志查询工具
用于场景一：复杂日志查询解释
"""

from typing import Dict, Any
from .mock_data import (
    get_report_conditions,
    get_user_conditions,
    generate_sql
)


def get_report_query_conditions(report_id: str, metric_name: str) -> Dict[str, Any]:
    """
    获取月报生成时用的查询条件
    
    Args:
        report_id: 月报ID
        metric_name: 指标名称（如攻击次数、SQL注入攻击数等）
    
    Returns:
        月报使用的查询条件
    """
    return get_report_conditions(report_id, metric_name)


def get_user_query_conditions(user_id: str, query_time_range: str) -> Dict[str, Any]:
    """
    获取用户在日志中心的查询条件
    
    Args:
        user_id: 用户ID
        query_time_range: 查询时间范围
    
    Returns:
        用户使用的查询条件
    """
    return get_user_conditions(user_id, query_time_range)


def generate_sql_with_conditions(conditions: Dict[str, Any]) -> str:
    """
    根据条件生成可在日志中心执行的 SQL
    
    Args:
        conditions: 查询条件
    
    Returns:
        SQL 查询语句
    """
    return generate_sql(conditions)


def compare_conditions(report_conditions: Dict[str, Any], user_conditions: Dict[str, Any]) -> Dict[str, Any]:
    """
    对比月报条件和用户查询条件，找出差异
    
    Args:
        report_conditions: 月报查询条件
        user_conditions: 用户查询条件
    
    Returns:
        差异分析结果
    """
    differences = []
    
    # 对比时间范围
    report_time = report_conditions.get('time_range', '')
    user_time = user_conditions.get('time_range', '')
    if report_time != user_time:
        differences.append({
            'field': 'time_range',
            'report_value': report_time,
            'user_value': user_time,
            'type': 'different'
        })
    
    # 对比资产组
    report_assets = set(report_conditions.get('asset_groups', []))
    user_assets = set(user_conditions.get('asset_groups', []))
    
    if report_assets != user_assets:
        # 找出月报有但用户没有选择的
        missing_assets = report_assets - user_assets
        if missing_assets:
            differences.append({
                'field': 'asset_groups',
                'report_value': list(report_assets),
                'user_value': list(user_assets),
                'type': 'filter',
                'description': f'月报只统计了这些资产组：{", ".join(missing_assets)}'
            })
    
    # 对比资源组
    report_resources = set(report_conditions.get('resource_groups', []))
    user_resources = set(user_conditions.get('resource_groups', []))
    
    if report_resources != user_resources:
        missing_resources = report_resources - user_resources
        if missing_resources:
            differences.append({
                'field': 'resource_groups',
                'report_value': list(report_resources),
                'user_value': list(user_resources),
                'type': 'filter',
                'description': f'月报只统计了这些资源组：{", ".join(missing_resources)}'
            })
    
    # 对比攻击类型
    report_attacks = set(report_conditions.get('attack_types', []))
    user_attacks = set(user_conditions.get('attack_types', []))
    
    if report_attacks != user_attacks:
        filtered_attacks = report_attacks - user_attacks
        if filtered_attacks:
            differences.append({
                'field': 'attack_types',
                'report_value': list(report_attacks),
                'user_value': list(user_attacks),
                'type': 'filter',
                'description': f'月报只统计了这些攻击类型：{", ".join(filtered_attacks)}'
            })
    
    # 对比IP排除规则
    report_excluded = report_conditions.get('excluded_ips', [])
    user_excluded = user_conditions.get('excluded_ips', [])
    
    if report_excluded and not user_excluded:
        differences.append({
            'field': 'excluded_ips',
            'report_value': report_excluded,
            'user_value': user_excluded,
            'type': 'filter',
            'description': f'月报排除了这些IP段：{", ".join(report_excluded)}'
        })
    
    return {
        'differences': differences,
        'has_differences': len(differences) > 0,
        'summary': _generate_summary(differences)
    }


def _generate_summary(differences: list) -> str:
    """生成差异摘要"""
    if not differences:
        return "查询条件完全一致，数据应该匹配。"
    
    summary_parts = []
    for diff in differences:
        if diff['type'] == 'filter':
            summary_parts.append(f"• {diff['description']}")
        elif diff['type'] == 'different':
            summary_parts.append(f"• 时间范围不同：月报使用 {diff['report_value']}，您使用 {diff['user_value']}")
    
    return "\n".join(summary_parts)
