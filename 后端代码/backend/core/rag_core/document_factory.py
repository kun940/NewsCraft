"""将数据库中的新闻数据转换成langchain的Document文档格式"""
from models.news_models import News
from langchain_core.documents import Document

def news_to_document(news:News,category_name=None):
    """
       一条新闻 → 向量库文档：
           page_content = 标题 + 正文（Embedding 的输入）
           metadata     = 新闻关键字段（过滤 / 溯源 / 调试用）
       """
    return Document(
        page_content=f"{news.title}\n{news.content}",
        metadata={
            "news_id": news.id,
            "title": news.title,
            "category": category_name or "",
            "ai_summary": news.ai_summary or "",
            "ai_tags": news.ai_tags or "",
            "content_keywords": news.content_keywords or "",
            "publish_time": news.publish_time.isoformat() if news.publish_time else "",
        },
    )