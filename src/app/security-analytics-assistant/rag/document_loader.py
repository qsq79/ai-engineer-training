#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档加载模块
用于加载和分割评分定义文档
"""

import os
from typing import List
from langchain_core.documents import Document


def load_scoring_document(file_path: str) -> Document:
    """
    加载评分定义文档
    
    Args:
        file_path: 文档路径
    
    Returns:
        Document 对象
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"评分定义文档不存在：{file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return Document(
        page_content=content,
        metadata={
            "source": file_path,
            "type": "scoring_definition"
        }
    )


def split_documents_by_chunk(document: Document, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """
    按章节切分文档
    
    Args:
        document: 要切分的文档
        chunk_size: 每个 chunk 的大小
        chunk_overlap: chunk 之间的重叠大小
    
    Returns:
        切分后的文档列表
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "  ", ""],
        length_function=len
    )
    
    chunks = text_splitter.split_documents([document])
    
    # 为每个 chunk 添加来源信息
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "chunk_index": i,
            "total_chunks": len(chunks)
        })
    
    return chunks
