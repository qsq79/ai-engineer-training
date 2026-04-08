#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件
"""

from core.agent import QueryExplanationAgent
from core.rag_agent import ScoringExplanationAgent
from config import get_config
from tools import add_mock_report_data, add_mock_user_data


def test_query_agent():
    """测试场景一：日志查询解释"""
    print("测试场景一：日志查询解释")
    print("=" * 50)
    
    # 添加测试数据
    add_mock_report_data("monthly_report_001", {
        "time_range": "2026-02-01 00:00:00 to 2026-02-28 23:59:59",
        "asset_groups": ["group_A", "group_B"],
        "resource_groups": ["prod", "staging"],
        "attack_types": ["sql_injection", "xss"],
        "excluded_ips": ["192.168.1.0/24"]
    })
    
    add_mock_user_data("user_001", {
        "time_range": "2026-02-01 to 2026-02-28",
        "asset_groups": [],
        "resource_groups": [],
        "attack_types": [],
        "excluded_ips": []
    })
    
    # 创建 Agent
    config = get_config()
    agent = QueryExplanationAgent(config=config)
    
    # 测试 1：查询差异
    print("\n测试 1：查询月报和用户查询的差异")
    question = "为什么我查的SQL注入攻击数量比月报少？"
    answer = agent.query(
        user_question=question,
        report_id="monthly_report_001",
        metric_name="sql_injection_attacks"
    )
    print(f"用户问题：{question}")
    print(f"Agent 回答：\n{answer}")
    print("\n" + "-" * 50)
    
    # 测试 2：无差异的查询
    print("\n测试 2：查询完全一致的场景")
    question = "我查的攻击日志数量是正确的吗？"
    answer = agent.query(
        user_question=question,
        user_id="user_001"
    )
    print(f"用户问题：{question}")
    print(f"Agent 回答：\n{answer}")
    print("\n" + "-" * 50)
    
    print("场景一测试完成！")


def test_scoring_agent():
    """测试场景二：安全评分解读"""
    print("测试场景二：安全评分解读")
    print("=" * 50)
    
    # 创建 Agent
    config = get_config()
    agent = ScoringExplanationAgent(config=config)
    
    # 测试 1：解释评分 78
    print("\n测试 1：解释评分 78 分")
    question = "这个月的安全评分78分，是怎么算的？"
    answer = agent.query(question)
    print(f"用户问题：{question}")
    print(f"Agent 回答：\n{answer}")
    print("\n" + "-" * 50)
    
    # 测试 2：解释评分 92
    print("\n测试 2：解释评分 92 分")
    question = "这个月的安全评分92分，是怎么算的？"
    answer = agent.query(question)
    print(f"用户问题：{question}")
    print(f"Agent 回答：\n{answer}")
    print("\n" + "-" * 50)
    
    # 测试 3：无评分的问题
    print("\n测试 3：查询评分计算方法")
    question = "安全评分是怎么计算的？"
    answer = agent.query(question)
    print(f"用户问题：{question}")
    print(f"Agent 回答：\n{answer}")
    print("\n" + "-" * 50)
    
    print("场景二测试完成！")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'query':
            test_query_agent()
        elif mode == 'scoring':
            test_scoring_agent()
        else:
            print(f"未知的测试模式：{mode}")
            print("用法：python test.py [query|scoring]")
    else:
        print("请指定测试模式：")
        print("  python test.py query    # 测试场景一：日志查询解释")
        print("  python test.py scoring   # 测试场景二：安全评分解读")


if __name__ == "__main__":
    main()
