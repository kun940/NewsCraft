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
"""RAG 问答 / 问题重写模板（模块三）。"""
rag_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是 NewsCraft 平台的新闻助手。只能基于以下站内新闻上下文回答，禁止编造"
            "上下文之外的信息；若上下文无法回答，明确说“站内暂无相关新闻”。"
            "回答末尾列出引用新闻标题（编号对应）。",
        ),
        ("human", "【新闻上下文】\n{context}\n\n【用户问题】\n{question}"),
    ]
)

rewrite_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是检索查询改写助手。把用户口语化的问题改写成适合搜索引擎/向量库检索的"
            "简洁中文查询。只输出改写后的查询本身，不要任何解释、引号或前缀。",
        ),
        ("human", "用户问题：{question}"),
    ]
)