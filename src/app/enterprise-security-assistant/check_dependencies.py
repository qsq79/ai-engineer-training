#!/usr/bin/env python3
"""
检查依赖包版本是否为最新稳定版
"""

import subprocess
import sys
from packaging import version

# 从requirements.txt中读取依赖包
with open('requirements.txt', 'r') as f:
    dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]

print("检查依赖包版本...\n")

for dep in dependencies:
    # 提取包名和版本约束
    if '>=' in dep:
        package, constraint = dep.split('>=', 1)
        package = package.strip()
        constraint = constraint.strip()
    else:
        package = dep.strip()
        constraint = None
    
    try:
        # 获取当前安装版本
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', package],
            capture_output=True,
            text=True
        )
        
        installed_version = None
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                installed_version = line.split(':', 1)[1].strip()
                break
        
        # 获取PyPI上的最新版本
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'index', 'versions', package],
            capture_output=True,
            text=True
        )
        
        latest_version = None
        for line in result.stdout.split('\n'):
            if line.startswith('Available versions:'):
                versions = line.split(':', 1)[1].strip().split(', ')
                # 过滤掉预发布版本
                stable_versions = [v for v in versions if '-' not in v]
                if stable_versions:
                    latest_version = stable_versions[0]
                break
        
        if installed_version and latest_version:
            print(f"{package}:")
            print(f"  当前安装版本: {installed_version}")
            print(f"  最新稳定版本: {latest_version}")
            print(f"  约束版本: {constraint or '无'}")
            
            # 检查是否需要更新
            if version.parse(installed_version) < version.parse(latest_version):
                print("  状态: 需要更新")
            else:
                print("  状态: 已为最新版本")
            print()
        else:
            print(f"{package}: 无法获取版本信息")
            print()
            
    except Exception as e:
        print(f"{package}: 检查失败 - {str(e)}")
        print()

print("依赖包版本检查完成！")
