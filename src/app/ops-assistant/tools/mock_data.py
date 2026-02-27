#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟数据存储模块
提供用户和登录日志的模拟数据
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MockUserData:
    """模拟用户数据存储"""

    def __init__(self):
        """初始化模拟用户数据"""
        self.users = {
            "user001": {
                "user_id": "user001",
                "username": "alice",
                "email": "alice@example.com",
                "status": "active",
                "role": "developer",
                "department": "engineering",
                "created_at": "2023-01-15T10:00:00Z"
            },
            "user002": {
                "user_id": "user002",
                "username": "bob",
                "email": "bob@example.com",
                "status": "locked",
                "role": "admin",
                "department": "operations",
                "created_at": "2023-02-20T14:30:00Z",
                "locked_reason": "多次登录失败"
            },
            "user003": {
                "user_id": "user003",
                "username": "charlie",
                "email": "charlie@example.com",
                "status": "active",
                "role": "viewer",
                "department": "sales",
                "created_at": "2023-03-10T09:00:00Z"
            },
            "user004": {
                "user_id": "user004",
                "username": "david",
                "email": "david@example.com",
                "status": "inactive",
                "role": "developer",
                "department": "engineering",
                "created_at": "2023-04-05T16:20:00Z",
                "inactive_reason": "账号过期"
            },
            "user005": {
                "user_id": "user005",
                "username": "eve",
                "email": "eve@example.com",
                "status": "active",
                "role": "analyst",
                "department": "data",
                "created_at": "2023-05-12T11:45:00Z"
            }
        }

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """通过用户ID获取用户信息"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """通过用户名获取用户信息"""
        for user in self.users.values():
            if user["username"] == username:
                return user
        return None

    def get_all_users(self) -> List[Dict]:
        """获取所有用户信息"""
        return list(self.users.values())


class MockLoginLogData:
    """模拟登录日志数据存储"""

    def __init__(self):
        """初始化模拟登录日志数据"""
        now = datetime.now()

        self.login_logs = {
            "user001": [
                {
                    "log_id": "LOG001",
                    "user_id": "user001",
                    "username": "alice",
                    "login_time": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.100",
                    "status": "success",
                    "failure_reason": None
                },
                {
                    "log_id": "LOG002",
                    "user_id": "user001",
                    "username": "alice",
                    "login_time": (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.100",
                    "status": "success",
                    "failure_reason": None
                }
            ],
            "user002": [
                {
                    "log_id": "LOG003",
                    "user_id": "user002",
                    "username": "bob",
                    "login_time": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.101",
                    "status": "failed",
                    "failure_reason": "密码错误"
                },
                {
                    "log_id": "LOG004",
                    "user_id": "user002",
                    "username": "bob",
                    "login_time": (now - timedelta(hours=1, minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.101",
                    "status": "failed",
                    "failure_reason": "密码错误"
                },
                {
                    "log_id": "LOG005",
                    "user_id": "user002",
                    "username": "bob",
                    "login_time": (now - timedelta(hours=1, minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.101",
                    "status": "failed",
                    "failure_reason": "密码错误"
                },
                {
                    "log_id": "LOG006",
                    "user_id": "user002",
                    "username": "bob",
                    "login_time": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.101",
                    "status": "success",
                    "failure_reason": None
                }
            ],
            "user003": [
                {
                    "log_id": "LOG007",
                    "user_id": "user003",
                    "username": "charlie",
                    "login_time": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.102",
                    "status": "success",
                    "failure_reason": None
                }
            ],
            "user004": [
                {
                    "log_id": "LOG008",
                    "user_id": "user004",
                    "username": "david",
                    "login_time": (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.103",
                    "status": "failed",
                    "failure_reason": "账号已过期"
                }
            ],
            "user005": [
                {
                    "log_id": "LOG009",
                    "user_id": "user005",
                    "username": "eve",
                    "login_time": (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.104",
                    "status": "success",
                    "failure_reason": None
                },
                {
                    "log_id": "LOG010",
                    "user_id": "user005",
                    "username": "eve",
                    "login_time": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
                    "ip_address": "192.168.1.105",
                    "status": "failed",
                    "failure_reason": "IP地址不在白名单中"
                }
            ]
        }

    def get_login_logs(self, user_id: str) -> List[Dict]:
        """获取指定用户的登录日志"""
        return self.login_logs.get(user_id, [])

    def get_recent_failures(self, user_id: str, hours: int = 24) -> List[Dict]:
        """获取指定用户最近N小时内的失败登录记录"""
        logs = self.get_login_logs(user_id)
        now = datetime.now()
        recent_failures = []

        for log in logs:
            if log["status"] == "failed":
                log_time = datetime.strptime(log["login_time"], "%Y-%m-%d %H:%M:%S")
                time_diff = (now - log_time).total_seconds() / 3600
                if time_diff <= hours:
                    recent_failures.append(log)

        return recent_failures


# 全局实例
user_data = MockUserData()
login_log_data = MockLoginLogData()
