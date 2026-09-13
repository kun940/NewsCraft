from typing import List

from pydantic import BaseModel,Field,ConfigDict

from schemas.response_base import ResponseBase


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