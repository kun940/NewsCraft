from datetime import datetime
from typing import Optional, List

from pydantic import Field, BaseModel, ConfigDict

from schemas.response_base import ResponseBase


class AddHistoryRequest(BaseModel):
    news_id:int=Field(...,alias="newsId")

class HistoryData(BaseModel):
    id:int=Field(...,alias="id")
    user_id:int=Field(...,alias="userId")
    news_id:int=Field(...,alias="newsId")
    view_time:datetime=Field(...,alias="viewTime")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AddHistoryResponse(ResponseBase):
    data:HistoryData

class HistoryNews(BaseModel):
    id: int
    title: str
    description: str
    view_time:datetime=Field(serialization_alias="viewTime")
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    publish_time: datetime = Field(serialization_alias="publishTime")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class HistoryListData(BaseModel):
    list:List[HistoryNews]
    total: int
    has_more: bool = Field(..., alias="hasMore")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class HistoryListResponse(ResponseBase):
    data: HistoryListData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class HistoryDeleteResponse(ResponseBase):
    message:str = "删除浏览记录成功"
    data:Optional[str]=None