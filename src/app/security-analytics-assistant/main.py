#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能安全数据分析助手 - 主程序入口
"""

import sys
import argparse
from config import get_config, AppConfig
from core.agent import QueryExplanationAgent
from core.rag_agent import ScoringExplanationAgent


def query_mode(args, config: AppConfig):
    """
    场景一：日志查询解释模式
    """
    print("=" * 60)
    print("场景一：日志查询解释（Agent 模式）")
    print("=" * 60)
    print("用于分析月报数据和日志中心查询数据不一致的问题。")
    print()
    
    # 创建 Agent
    agent = QueryExplanationAgent(config=config, model=args.model)
    
    # 如果提供了具体参数
    if args.report_id and args.metric_name:
        # 分析特定的月报
        question = f"为什么我查的{args.metric_name}数量比月报少？"
        answer = agent.query(
            user_question=question,
            report_id=args.report_id,
            metric_name=args.metric_name
        )
    elif args.user_id:
        # 分析用户的查询
        question = f"我查的日志数量是正确的吗？"
        answer = agent.query(
            user_question=question,
            user_id=args.user_id,
            query_time_range=args.time_range
        )
    else:
        # 交互式模式
        print("交互式模式（输入 'quit' 或 'exit' 退出）")
        print()
        
        while True:
            try:
                user_input = input("请输入您的问题：").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n感谢使用智能安全数据分析助手。再见！")
                    break
                
                # 处理用户问题
                answer = agent.query(user_input)
                print(f"\n回答：\n{answer}\n")
            
            except KeyboardInterrupt:
                print("\n\n程序已中断。")
                break
            except Exception as e:
                print(f"\n错误：{str(e)}")


def scoring_mode(args, config: AppConfig):
    """
    场景二：安全评分解读模式（RAG 模式）
    """
    print("=" * 60)
    print("场景二：安全评分解读（RAG 模式）")
    print("=" * 60)
    print("用于解读安全评分的计算方法和得分明细。")
    print()
    
    # 创建 Agent
    agent = ScoringExplanationAgent(config=config, model=args.model)
    
    # 如果提供了具体问题
    if args.question:
        answer = agent.query(args.question)
        print(f"\n回答：\n{answer}\n")
    else:
        # 交互式模式
        print("交互式模式（输入 'quit' 或 'exit' 退出）")
        print()
        
        while True:
            try:
                user_input = input("请输入您关于安全评分的问题：").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n感谢使用智能安全数据分析助手。再见！")
                    break
                
                # 处理用户问题
                answer = agent.query(user_input)
                print(f"\n回答：\n{answer}\n")
            
            except KeyboardInterrupt:
                print("\n\n程序已中断。")
                break
            except Exception as e:
                print(f"\n错误：{str(e)}")


def auto_mode(args, config: AppConfig):
    """
    自动识别模式：根据用户问题自动判断使用哪个场景
    """
    print("=" * 60)
    print("自动识别模式")
    print("=" * 60)
    print("根据您的问题，自动判断使用日志查询解释或安全评分解读。")
    print()
    
    # 创建两个 Agent
    query_agent = QueryExplanationAgent(config=config, model=args.model)
    scoring_agent = ScoringExplanationAgent(config=config, model=args.model)
    
    print("交互式模式（输入 'quit' 或 'exit' 退出）")
    print("示例问题：")
    print("  - 日志查询：'为什么我查的攻击数量比月报少？'")
    print("  - 评分解读：'这个月的安全评分78分，是怎么算的？'")
    print()
    
    while True:
        try:
            user_input = input("请输入您的问题：").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n感谢使用智能安全数据分析助手。再见！")
                break
            
            # 简化判断：使用关键词
            question_lower = user_input.lower()
            
            # 判断是否是日志查询问题
            log_keywords = ['为什么', '对不上', '不一致', '差', '少', '多', 'sql注入', '攻击', '日志', '查询']
            is_log_query = any(kw in question_lower for kw in log_keywords)
            
            # 判断是否是评分问题
            score_keywords = ['评分', '分数', '分', '多少', '怎么算', '计算', '78分', '90分']
            is_score_query = any(kw in question_lower for kw in score_keywords)
            
            if is_log_query:
                # 使用日志查询 Agent
                print("\n[场景：日志查询解释]")
                answer = query_agent.query(user_input)
                print(f"\n回答：\n{answer}\n")
            elif is_score_query:
                # 使用评分解读 Agent
                print("\n[场景：安全评分解读]")
                answer = scoring_agent.query(user_input)
                print(f"\n回答：\n{answer}\n")
            else:
                print("\n无法确定问题类型，请尝试更明确的表述。")
        
        except KeyboardInterrupt:
            print("\n\n程序已中断。")
            break
        except Exception as e:
            print(f"\n错误：{str(e)}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="智能安全数据分析助手")
    parser.add_argument('--mode', '-m', choices=['query', 'scoring', 'auto'], 
                        default='auto', help='运行模式：query(日志查询）、scoring(评分解读）、auto(自动识别）')
    parser.add_argument('--model', type=str, default=None, 
                        help='指定使用的模型（如 gpt-4o, gpt-4o-mini）')
    parser.add_argument('--report-id', type=str, default=None, 
                        help='月报ID（仅 query 模式）')
    parser.add_argument('--metric-name', type=str, default=None, 
                        help='指标名称（仅 query 模式）')
    parser.add_argument('--user-id', type=str, default=None, 
                        help='用户ID（仅 query 模式）')
    parser.add_argument('--time-range', type=str, default=None, 
                        help='查询时间范围（仅 query 模式）')
    parser.add_argument('--question', '-q', type=str, default=None, 
                        help='具体问题（仅 scoring 模式）')
    
    args = parser.parse_args()
    
    # 加载配置
    config = get_config()
    
    # 验证 API Key
    if not config.api_key:
        print("错误：未找到 OPENAI_API_KEY，请设置环境变量或在 .env 文件中配置")
        sys.exit(1)
    
    # 根据模式执行
    if args.mode == 'query':
        query_mode(args, config)
    elif args.mode == 'scoring':
        scoring_mode(args, config)
    else:
        auto_mode(args, config)


if __name__ == "__main__":
    main()
