from datetime import datetime

from pydantic import BaseModel, ConfigDict,Field

from schemas.response_base import ResponseBase
from typing import List, Optional


class CategoryData(BaseModel):
    created_at: datetime
    updated_at: datetime
    id:int
    name:str
    sort_order:int
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class CategoryResponse(ResponseBase):
    data:List[CategoryData]
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NewsList(BaseModel):
    id: int
    title: str
    description: str
    content: str
    image: Optional[str] = None
    author:Optional[str] = None
    category_id:int=Field(serialization_alias="categoryId")
    views: int
    publish_time: datetime= Field(serialization_alias="publishTime")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NewsListData(BaseModel):
    datalist:list[NewsList]= Field(serialization_alias="list")
    total:int
    has_more: bool= Field(serialization_alias="hasMore")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NewsListResponse(ResponseBase):
    data:NewsListData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NewsDetailData(BaseModel):
    id: int
    title: str
    content: str
    image: Optional[str]
    author: Optional[str]
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    publish_time: datetime = Field(serialization_alias="publishTime")
    relatedNews:list=Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NewsDetailResponse(ResponseBase):
    data:NewsDetailData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)