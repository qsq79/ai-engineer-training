#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运维工具模块
定义 LangChain Agent 使用的工具

现在通过 HTTP 调用 ops-assistant-api 微服务
"""

import os
from typing import Optional
import httpx
from langchain_core.tools import tool


# API base URL configuration
API_BASE_URL = os.getenv("OPS_API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = int(os.getenv("OPS_API_TIMEOUT", "30"))


def _format_user_info(response_data: dict) -> str:
    """Format user info JSON response into readable string"""
    if "error" in response_data.get("detail", "").lower():
        return f"Error: {response_data.get('detail', 'Unknown error')}"

    info = f"""User Information:
-----------------
User ID: {response_data.get('user_id')}
Username: {response_data.get('username')}
Email: {response_data.get('email')}
Department: {response_data.get('department')}
Role: {response_data.get('role')}
Status: {response_data.get('status')}
"""

    if response_data.get('locked_reason'):
        info += f"Lock Reason: {response_data.get('locked_reason')}\n"
    if response_data.get('locked_at'):
        info += f"Locked At: {response_data.get('locked_at')}\n"

    info += f"""Created At: {response_data.get('created_at')}
MFA Enabled: {response_data.get('mfa_enabled')}
"""

    if response_data.get('last_login'):
        info += f"Last Login: {response_data.get('last_login')}\n"

    if response_data.get('password_expire_days') is not None:
        days = response_data.get('password_expire_days')
        info += f"Password Expires: {'Expired' if days == 0 else f'{days} days'}\n"

    return info.strip()


def _format_login_logs(response_data: dict) -> str:
    """Format login logs JSON response into readable string"""
    if "error" in response_data.get("detail", "").lower():
        return f"Error: {response_data.get('detail', 'Unknown error')}"

    user_id = response_data.get('user_id')
    logs = response_data.get('logs', [])
    total_failed = response_data.get('total_failed_attempts', 0)
    last_success = response_data.get('last_success_login')

    result = f"""Login Records for User {user_id}:
{'='*60}
"""

    if not logs:
        result += "No login records found.\n"
    else:
        for log in logs:
            status_icon = "[OK]" if log['status'] == 'success' else '[FAIL]'
            result += f"""
{status_icon} {log['timestamp']}
   IP: {log['ip']}
   Status: {log['status']}
"""
            if log.get('reason'):
                result += f"   Reason: {log['reason']}\n"

    if total_failed > 0:
        result += f"\nTotal Failed Attempts: {total_failed}\n"

    if last_success:
        result += f"Last Successful Login: {last_success}\n"

    return result.strip()


async def _call_api(method: str, endpoint: str, params: Optional[dict] = None) -> dict:
    """Make HTTP request to the ops-assistant-api"""
    url = f"{API_BASE_URL}{endpoint}"

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            else:
                response = await client.post(url, json=params)

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": "not_found", "detail": f"Resource not found: {endpoint}"}
            return {"error": "http_error", "detail": str(e)}
        except httpx.RequestError as e:
            return {"error": "request_error", "detail": f"Failed to connect to API: {str(e)}"}


def _call_api_sync(method: str, endpoint: str, params: Optional[dict] = None) -> dict:
    """Synchronous wrapper for HTTP requests"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_call_api(method, endpoint, params))


@tool
def get_user_info(user_identifier: str) -> str:
    """
    Get user information by user ID or username.

    Returns comprehensive user info including:
    - User ID, username, email
    - Account status (active/locked/inactive)
    - Role and department
    - Account creation time
    - Last login timestamp
    - MFA status
    - Password expiration days
    - Lock reason and timestamp (if locked)

    Args:
        user_identifier: User ID (e.g., 'U001') or username (e.g., 'alice')

    Returns:
        Formatted string description of user information
    """
    response_data = _call_api_sync("GET", f"/api/v1/users/{user_identifier}")

    if "error" in response_data:
        return f"Error: {response_data.get('detail', 'Unknown error')}"

    return _format_user_info(response_data)


@tool
def check_login_log(user_identifier: str) -> str:
    """
    Check user login logs by user ID or username.

    Query user login records including:
    - Login timestamps
    - IP addresses
    - Login status (success/failed)
    - Failure reasons
    - Total failed attempts count
    - Last successful login timestamp

    Can be used to analyze user login failure patterns and causes.

    Args:
        user_identifier: User ID (e.g., 'U001') or username (e.g., 'alice')

    Returns:
        Formatted string description of login logs
    """
    response_data = _call_api_sync("GET", f"/api/v1/users/{user_identifier}/login-logs")

    if "error" in response_data:
        return f"Error: {response_data.get('detail', 'Unknown error')}"

    return _format_login_logs(response_data)


# Export tools list
TOOLS = [get_user_info, check_login_log]
