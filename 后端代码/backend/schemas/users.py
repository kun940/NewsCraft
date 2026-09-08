from typing import Optional
from pydantic import BaseModel,Field,ConfigDict

from schemas.response_base import ResponseBase

class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=64)

class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=64)


class UserInfoBase(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    # 模型类配置
    model_config = ConfigDict(
        populate_by_name=True,  # alias/字段名兼容
        from_attributes=True,  # 允许从ORM对象属性中取值
    )

class UserInfoData(BaseModel):
    token:Optional[str]
    userinfo: UserInfoBase=Field(serialization_alias="userInfo")

class UserInfoResponse(ResponseBase):
    data: UserInfoData
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class UserInfoOnlyResponse(ResponseBase):
    data: UserInfoBase

class UserUpdateInfo(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone:Optional[str]= Field(None, max_length=20, description="手机号")
    # 模型类配置
    model_config = ConfigDict(
        populate_by_name=True,  # alias/字段名兼容
        from_attributes=True,  # 允许从ORM对象属性中取值
    )

class UserPassword(BaseModel):
    old_password: str = Field(alias="oldPassword", min_length=1, max_length=64)
    new_password: str = Field(alias="newPassword", min_length=6, max_length=64)
    model_config = ConfigDict(populate_by_name=True)

class PasswordResponse(ResponseBase):
    message:str = "密码修改成功"
    data:Optional[str]=None