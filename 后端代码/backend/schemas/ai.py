from typing import List

from pydantic import BaseModel,Field,ConfigDict

from schemas.response_base import ResponseBase
from datetime import datetime
from typing import Optional

class VectorRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    news_ids: List[int]| None = Field(default=None, alias="newsIds", description="缺省=处理全部未向量化新闻")

class VectorDetailItem(BaseModel):
    news_id:int=Field(...,alias="newsId")
    status:str

class VectorResponseData(BaseModel):
    task_type:str= Field(default="vectorize",alias="taskType")
    accepted_count:int= Field(...,alias="acceptedCount")
    skipped_count:int= Field(...,alias="skippedCount")
    detail:List[VectorDetailItem]

class VectorResponse(ResponseBase):
    data:VectorResponseData

class SummaryRequest(BaseModel):
    news_ids: list[int] | None = Field(default=None, description="缺省=处理全部未加工（ai_summary 为空）新闻")


class SummaryDetailItem(BaseModel):
    news_id: int = Field(serialization_alias="newsId")
    status: str   # queued / skipped


class SummaryResponseData(BaseModel):
    task_type: str = Field(default="summary", serialization_alias="taskType")
    accepted_count: int = Field(serialization_alias="acceptedCount")
    skipped_count: int = Field(serialization_alias="skippedCount")
    detail: list[SummaryDetailItem] = Field(default_factory=list)


class SummaryResponse(ResponseBase):
    data: SummaryResponseData


class RecommendNewsItem(BaseModel):
    """推荐条目：字段对齐 /api/news/list 列表项 + reason/score + AI 加工字段。"""
    id: int
    title: str
    description: str = ""
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(serialization_alias="categoryId")
    views: int = 0
    publish_time: datetime = Field(serialization_alias="publishTime")
    ai_summary: Optional[str] = Field(default=None, serialization_alias="aiSummary")
    ai_tags: Optional[str] = Field(default=None, serialization_alias="aiTags")
    content_keywords: Optional[str] = Field(default=None, serialization_alias="contentKeywords")
    reason: Optional[str] = None
    score: Optional[float] = None
    model_config = ConfigDict(populate_by_name=True)


class RecommendData(BaseModel):
    strategy: str                       # vector / hot_fallback
    list: list[RecommendNewsItem]
    total: int
    # 注意：服务层 _paginate 返回 camelCase 的 hasMore（不是 has_more），
    # 所以这里必须用 alias（参与输入校验+输出序列化），不能用 serialization_alias（只管输出）
    has_more: bool = Field(alias="hasMore")
    model_config = ConfigDict(populate_by_name=True)


class RecommendResponse(ResponseBase):
    data: RecommendData