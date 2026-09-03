from pydantic import BaseModel, ConfigDict


#通用成功响应
class ResponseBase(BaseModel):
    code:int=200
    message:str="success"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
