from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from schemas.response_base import ResponseBase


class FavoriteStateData(BaseModel):
    is_favorite: bool=Field(...,alias="isFavorite")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteStateResponse(ResponseBase):
    data: FavoriteStateData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteAddData(BaseModel):
    id: int =Field(...,alias="id")
    user_id: int =Field(...,alias="userId")
    news_id: int=Field(...,alias="newsId")
    created_at: datetime = Field(...,alias="createTime")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteAddRequest(BaseModel):
    news_id: int =Field(...,alias="newsId")

class FavoriteAddResponse(ResponseBase):
    data: FavoriteAddData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteDeleteResponse(ResponseBase):
    message:str = "取消收藏成功"
    data:Optional[str]=None

class FavoriteNews(BaseModel):
    id: int
    title: str
    description: str
    favorite_time:datetime=Field(...,alias="favoriteTime")
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(serialization_alias="categoryId")
    views: int
    publish_time: datetime = Field(serialization_alias="publishTime")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteListData(BaseModel):
    list: List[FavoriteNews]
    total: int
    has_more: bool=Field(...,alias="hasMore")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class FavoriteListResponse(ResponseBase):
    data:FavoriteListData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
