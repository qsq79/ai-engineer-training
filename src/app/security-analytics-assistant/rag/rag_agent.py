#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全评分解读 Agent（RAG 模式）
"""

from typing import Optional, Dict, Any
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from config import get_config, AppConfig
from rag.document_loader import load_scoring_document, split_documents_by_chunk
from rag.vector_store import create_vector_store
from rag.retriever import ScoringRetriever


class ScoringExplanationAgent:
    """安全评分解读 Agent"""
    
    def __init__(self, config: AppConfig = None, model: str = None):
        """
        初始化 Agent
        
        Args:
            config: 配置对象
            model: 模型名称（可选）
        """
        self.config = config or get_config()
        
        # 创建向量存储
        self.vector_store = create_vector_store(self.config)
        self.retriever = ScoringRetriever(
            self.vector_store,
            top_k=self.config.rag_top_k
        )
        
        # 获取模型配置
        model_name = model or self.config.default_model
        llm_params = {
            "model": model_name,
            "api_key": self.config.api_key,
            "api_base": self.config.api_base,
            "temperature": 0.3,  # 使用中等温度以平衡创造性和准确性
            "max_tokens": self.config.max_tokens
        }
        
        self.llm = ChatOpenAI(**llm_params)
        
        # 初始化向量存储（首次运行时加载文档）
        self._vector_store_initialized = False
    
    def _initialize_vector_store(self):
        """初始化向量存储（首次运行时加载文档）"""
        if self._vector_store_initialized:
            return
        
        # 加载评分定义文档
        try:
            doc_path = "data/scoring_definition.md"
            document = load_scoring_document(doc_path)
            
            # 切分文档
            chunks = split_documents_by_chunk(
                document,
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
            
            # 添加到向量存储
            self.vector_store.add_documents(chunks)
            self.vector_store.persist()
            
            self._vector_store_initialized = True
            print("向量存储初始化完成，文档已加载。")
        
        except FileNotFoundError as e:
            print(f"警告：{str(e)}")
    
    def _extract_score_from_question(self, question: str) -> Optional[int]:
        """
        从用户问题中提取评分值
        
        Args:
            question: 用户问题
        
        Returns:
            评分值（如果找到）
        """
        import re
        
        # 查找数字模式（如"78分"、"评分78"等）
        patterns = [
            r'(\d+)分',
            r'评分(\d+)',
            r'分是(\d+)',
            r'得分(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                return int(match.group(1))
        
        return None
    
    def _build_context(self, question: str, score_value: int) -> str:
        """
        构建上下文信息
        
        Args:
            question: 用户问题
            score_value: 评分值
        
        Returns:
            上下文字符串
        """
        # 检索相关文档
        documents = self.retriever.retrieve(question, score_value)
        
        if not documents:
            return "未找到相关的评分定义信息。"
        
        # 合并文档内容
        context_parts = []
        for doc in documents:
            context_parts.append(doc.page_content)
        
        return "\n\n".join(context_parts)
    
    def explain(self, question: str) -> str:
        """
        解释安全评分
        
        Args:
            question: 用户问题（如"这个月的安全评分78分，是怎么算的？"）
        
        Returns:
            评分解释
        """
        # 确保向量存储已初始化
        self._initialize_vector_store()
        
        # 提取评分值
        score_value = self._extract_score_from_question(question)
        
        # 如果没有找到评分值，直接使用问题进行检索
        if score_value is None:
            context = self.retriever.get_relevant_content(question)
        else:
            context = self._build_context(question, score_value)
        
        # 构建 RAG 链
        from langchain.chains import create_retrieval_chain
        
        # 创建提示模板
        prompt_template = """你是一个专业的安全分析助手。请根据以下信息，回答用户关于安全评分的问题。

用户问题：{question}

评分定义文档：
{context}

请用清晰、专业、友好的语言解释评分的计算方法和具体得分情况。如果用户提到了具体的评分值（如78分），请结合文档内容解释该分数的原因和各维度得分情况。"""
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # 创建 RAG 链
        rag_chain = (
            {
                "question": RunnablePassthrough(),
                "context": lambda x: x["context"]
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        # 执行链
        try:
            result = rag_chain.invoke({
                "question": question,
                "context": context
            })
            
            return result
        
        except Exception as e:
            return f"处理评分解释时出错：{str(e)}"
    
    def query(self, user_question: str) -> str:
        """
        处理用户查询
        
        Args:
            user_question: 用户问题
        
        Returns:
            Agent 的回答
        """
        return self.explain(user_question)
    
    def query_stream(self, user_question: str):
        """
        流式处理用户查询
        
        Args:
            user_question: 用户问题
        
        Yields:
            Agent 的流式回答
        """
        # 确保向量存储已初始化
        self._initialize_vector_store()
        
        # 简化版本：直接返回结果
        yield self.explain(user_question)
