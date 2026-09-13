"""新闻摘要链"""
from core.rag_core.models import create_chat_model
from core.rag_core.prompts import summary_prompt
from core.rag_core.schemas import NewsSummary


def get_summary_chain():
    chain=summary_prompt | create_chat_model().with_structured_output(NewsSummary, method="function_calling")
    return chain

