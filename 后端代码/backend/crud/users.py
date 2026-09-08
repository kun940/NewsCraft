from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,update
from fastapi import HTTPException,Header,Depends
from models.users_models import User, UserToken
from schemas.users import UserUpdateInfo, UserPassword

from utils.get_db_session import get_db
from utils.security import get_hash_password, verify_password


#用户注册
async def register(db:AsyncSession,username:str,password:str):
    #先根据用户名查数据库，防止重复
    query=select(User).where(User.username==username)
    query_result=await db.execute(query)
    if query_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    #用户信息写进数据库（密码用bycrypt加密）
    user=User(username=username,password=get_hash_password(password))
    db.add(user)
    await db.flush()
    await db.refresh(user)  # 从数据库读回最新的user
    return user

#更新用户token
async def upsert_token(db:AsyncSession, user_id:int, token:str, expires_at: datetime):
    # 查询token表中有无该用户的token
    query = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()
    # 有则更新token
    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
    # 无则增加
    else:
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)
    await db.flush()
    await db.refresh(user_token)
    return user_token.token

#用户登录
#校对用户是否存在
async def check_username(db:AsyncSession,username:str,password:str):
    query=select(User).where(User.username==username)
    query_result=await db.execute(query)
    user=query_result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password,user.password):
        return None
    return user

#检查认证状态获取当前用户
async def get_current_active_user(db:AsyncSession=Depends(get_db),authorization: str=Header(...,alias="Authorization")):
    token = authorization.replace("Bearer ", "")
    stmt=select(UserToken).where(UserToken.token==token)
    result=await db.execute(stmt)
    current_active_user=result.scalar_one_or_none()
    if not current_active_user:
        return None
    if current_active_user.expires_at < datetime.now():
        return None
    query=select(User).where(User.id==current_active_user.user_id)
    query_result=await db.execute(query)
    current_user=query_result.scalar_one_or_none()
    return current_user

#更新用户信息
async def update_user_info(db:AsyncSession,update_info:UserUpdateInfo,current_active_user:User):
    update_dict = update_info.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(current_active_user, k, v)
    await db.flush()
    await db.refresh(current_active_user)
    return current_active_user

#修改用户密码
async def set_password(db:AsyncSession,update_password:UserPassword,current_active_user:User):
    if update_password.old_password == update_password.new_password:
        raise HTTPException(status_code=400, detail="新密码不能和旧密码相同")

    if not verify_password(update_password.old_password,current_active_user.password):
        raise HTTPException(status_code=400, detail="旧密码错误")
    current_active_user.password=get_hash_password(update_password.new_password)
    await db.flush()
    await db.refresh(current_active_user)
    return current_active_user