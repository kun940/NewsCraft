"""Pydantic 输出模型：配合 with_structured_output 把 LLM 输出解析成结构化 JSON。"""
from pydantic import BaseModel, Field


class NewsSummary(BaseModel):
    """新闻 AI 加工的结构化结果，直接回填 MySQL 三个预留字段。"""

    summary: str = Field(description="不超过100字的中文摘要")
    tags: list[str] = Field(description="3~5个多维度标签")
    keywords: list[str] = Field(description="3~5个核心关键词")