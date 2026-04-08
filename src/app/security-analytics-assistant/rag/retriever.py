#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检索器模块
用于根据用户问题检索相关文档
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class ScoringRetriever:
    """评分文档检索器"""
    
    def __init__(self, vector_store, top_k: int = 3):
        """
        初始化检索器
        
        Args:
            vector_store: 向量存储
            top_k: 返回的文档数量
        """
        self.vector_store = vector_store
        self.top_k = top_k
    
    def retrieve(self, query: str, score_value: Optional[int] = None) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 用户问题
            score_value: 安全评分值（可选，用于增强检索）
        
        Returns:
            相关文档列表
        """
        # 构建增强的查询
        enhanced_query = query
        if score_value is not None:
            enhanced_query = f"{query} 评分{score_value}分"
        
        # 执行相似度搜索
        documents = self.vector_store.similarity_search(enhanced_query, k=self.top_k)
        
        return documents
    
    def get_relevant_content(self, query: str, score_value: Optional[int] = None) -> str:
        """
        获取相关文档内容
        
        Args:
            query: 用户问题
            score_value: 安全评分值（可选）
        
        Returns:
            相关文档的文本内容
        """
        documents = self.retrieve(query, score_value)
        
        if not documents:
            return "未找到相关的评分定义文档。"
        
        # 合并所有相关文档的内容
        content_parts = []
        for doc in documents:
            content_parts.append(doc.page_content)
        
        return "\n\n".join(content_parts)
