"""Prompt 模板：摘要加工（模块一）。RAG 问答 / 问题重写模板在模块三再加。"""
from langchain_core.prompts import ChatPromptTemplate

summary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是资深新闻编辑，负责把新闻提炼成结构化内容。要求：\n"
            "1. summary：不超过 80 字的中文摘要，保留核心事实，客观不带评价；\n"
            "2. tags：3~5 个多维度标签（如 科技/财经/民生/政策/国际 等角度）,意思相近或者语义重合的角度只选其中一个；\n"
            "3. keywords：3~5 个核心关键词。",
        ),
        ("human", "标题：{title}\n\n正文：{content}"),
    ]
)