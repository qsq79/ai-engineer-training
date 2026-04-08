#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟数据
用于模拟月报查询条件、用户查询条件和SQL生成
"""

from typing import Dict, Any


# 模拟的月报数据
_report_data = {
    "monthly_report_001": {
        "time_range": "2026-02-01 00:00:00 to 2026-02-28 23:59:59",
        "asset_groups": ["group_A", "group_B"],
        "resource_groups": ["prod", "staging"],
        "attack_types": ["sql_injection", "xss"],
        "excluded_ips": ["192.168.1.0/24"]
    },
    "monthly_report_002": {
        "time_range": "2026-02-01 00:00:00 to 2026-02-28 23:59:59",
        "asset_groups": ["group_A", "group_B", "group_C"],
        "resource_groups": ["prod"],
        "attack_types": ["sql_injection", "xss", "csrf"],
        "excluded_ips": ["192.168.1.0/24", "192.168.2.0/24"]
    }
}


# 模拟的用户查询数据
_user_query_data = {
    "user_001": {
        "time_range": "2026-02-01 to 2026-02-28",
        "asset_groups": [],
        "resource_groups": [],
        "attack_types": [],
        "excluded_ips": []
    },
    "user_002": {
        "time_range": "2026-02-01 to 2026-02-28",
        "asset_groups": ["group_A"],
        "resource_groups": ["prod"],
        "attack_types": ["sql_injection"],
        "excluded_ips": []
    }
}


def get_report_conditions(report_id: str, metric_name: str) -> Dict[str, Any]:
    """
    获取月报生成时用的查询条件
    
    Args:
        report_id: 月报ID
        metric_name: 指标名称
    
    Returns:
        月报使用的查询条件
    """
    report_key = None
    for key in _report_data:
        if key.startswith(report_id):
            report_key = key
            break
    
    if not report_key:
        # 返回默认的月报数据
        return _report_data.get("monthly_report_001", {})
    
    return _report_data.get(report_key, {})


def get_user_conditions(user_id: str, query_time_range: str) -> Dict[str, Any]:
    """
    获取用户在日志中心的查询条件
    
    Args:
        user_id: 用户ID
        query_time_range: 查询时间范围
    
    Returns:
        用户使用的查询条件
    """
    user_key = None
    for key in _user_query_data:
        if key.startswith(user_id):
            user_key = key
            break
    
    if not user_key:
        # 返回默认的用户数据
        return _user_query_data.get("user_001", {})
    
    # 使用传入的时间范围
    user_data = _user_query_data.get(user_key, {}).copy()
    if query_time_range:
        user_data['time_range'] = query_time_range
    
    return user_data


def generate_sql(conditions: Dict[str, Any]) -> str:
    """
    根据条件生成可在日志中心执行的 SQL
    
    Args:
        conditions: 查询条件
    
    Returns:
        SQL 查询语句
    """
    time_range = conditions.get('time_range', '')
    asset_groups = conditions.get('asset_groups', [])
    resource_groups = conditions.get('resource_groups', [])
    attack_types = conditions.get('attack_types', [])
    excluded_ips = conditions.get('excluded_ips', [])
    
    # 解析时间范围
    start_date = None
    end_date = None
    if 'to' in time_range:
        parts = time_range.split(' to ')
        if len(parts) == 2:
            start_date = parts[0]
            end_date = parts[1]
    
    # 构建 SQL
    sql_parts = ["SELECT COUNT(*) FROM attack_logs"]
    where_parts = []
    
    # 添加攻击类型条件
    if attack_types:
        attack_types_str = "', '".join(attack_types)
        where_parts.append(f"attack_type IN ('{attack_types_str}')")
    
    # 添加资产组条件
    if asset_groups:
        assets_str = "', '".join(asset_groups)
        where_parts.append(f"asset_group IN ('{assets_str}')")
    
    # 添加资源组条件
    if resource_groups:
        resources_str = "', '".join(resource_groups)
        where_parts.append(f"resource_group IN ('{resources_str}')")
    
    # 添加IP排除条件
    if excluded_ips:
        ip_conditions = []
        for ip in excluded_ips:
            ip_conditions.append(f"src_ip NOT LIKE '{ip.replace('.0/', '.%')}'")
        where_parts.append(" OR ".join(ip_conditions))
    
    # 添加时间范围条件
    if start_date and end_date:
        where_parts.append(f"timestamp BETWEEN '{start_date}' AND '{end_date}'")
    
    # 组合 WHERE 子句
    if where_parts:
        sql_parts.append("WHERE " + " AND ".join(where_parts))
    
    return "\n".join(sql_parts)


def add_mock_report_data(report_id: str, data: Dict[str, Any]):
    """
    添加模拟的月报数据（用于测试）
    
    Args:
        report_id: 月报ID
        data: 月报数据
    """
    _report_data[report_id] = data


def add_mock_user_data(user_id: str, data: Dict[str, Any]):
    """
    添加模拟的用户查询数据（用于测试）
    
    Args:
        user_id: 用户ID
        data: 用户查询数据
    """
    _user_query_data[user_id] = data
