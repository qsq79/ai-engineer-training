#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量存储模块
用于创建和管理向量数据库
"""

import os
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


class VectorStore:
    """向量存储管理器"""
    
    def __init__(self, persist_directory: str, embedding_model: str = None):
        """
        初始化向量存储
        
        Args:
            persist_directory: 持久化目录
            embedding_model: 嵌入模型名称
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # 创建嵌入模型
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model or "text-embedding-3-small"
        )
        
        # 初始化 Chroma 向量数据库
        self.vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name="scoring_documents"
        )
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
        """
        if not documents:
            return
        
        self.vector_store.add_documents(documents)
    
    def similarity_search(self, query: str, k: int = 3) -> List[Document]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回的文档数量
        
        Returns:
            相关文档列表
        """
        return self.vector_store.similarity_search(query, k=k)
    
    def clear(self):
        """清空向量存储"""
        self.vector_store.delete_collection()
    
    def persist(self):
        """持久化向量存储"""
        self.vector_store.persist()


def create_vector_store(config) -> VectorStore:
    """
    创建向量存储实例
    
    Args:
        config: 应用配置
    
    Returns:
        VectorStore 实例
    """
    return VectorStore(
        persist_directory=config.vector_db_path,
        embedding_model=config.default_model
    )
