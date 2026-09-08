from datetime import datetime,timedelta

from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crud.users import register, upsert_token, check_username, get_current_active_user, update_user_info, set_password
from schemas.users import UserInfoResponse, UserInfoData, RegisterRequest, LoginRequest, UserInfoBase, \
    UserInfoOnlyResponse, UserUpdateInfo, PasswordResponse, UserPassword
from utils.get_db_session import get_db
from utils.security import create_token

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register",response_model=UserInfoResponse)
async def user_register(req:RegisterRequest,db:AsyncSession=Depends(get_db)):
    #把用户信息写进数据库
    registered_user=await register(db,username=req.username,password=req.password)
    #生成token
    user_token=await create_token()
    #把token写进数据库
    expires_at = datetime.now() + timedelta(days=1)
    user_token=await upsert_token(db,registered_user.id,user_token,expires_at)
    #返回响应
    user_info_data=UserInfoData(
        token = user_token,
        userinfo=registered_user
    )
    user_info_response=UserInfoResponse(data=user_info_data)
    return user_info_response

@router.post("/login",response_model=UserInfoResponse)
async def user_login(req:LoginRequest,db:AsyncSession=Depends(get_db)):
    #从数据库里校对用户信息
    login_user=await check_username(db,req.username,req.password)
    if not login_user:
        raise HTTPException(status_code=401,detail="用户名或密码错误")
    #生成token
    new_token=await create_token()
    # 把token写进数据库
    expires_at = datetime.now() + timedelta(days=1)
    user_token=await upsert_token(db,login_user.id,new_token,expires_at)
    # 返回响应
    user_info_data = UserInfoData(
        token=user_token,
        userinfo=login_user
    )
    user_info_response = UserInfoResponse(data=user_info_data)
    return user_info_response

@router.get("/info",response_model=UserInfoOnlyResponse)
async def get_userinfo(current_active_user=Depends(get_current_active_user)):
    if not current_active_user:
        raise HTTPException(status_code=401,detail="无用户令牌或令牌已过期")
    user_info_data:UserInfoBase=current_active_user
    user_info_response=UserInfoOnlyResponse(data=user_info_data)
    return user_info_response

@router.put("/update",response_model=UserInfoOnlyResponse)
async def update_userinfo(update_info:UserUpdateInfo,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    if not current_active_user:
        raise HTTPException(status_code=401,detail="无用户令牌或令牌已过期")
    updated_user=await update_user_info(db,update_info,current_active_user)
    update_response=UserInfoOnlyResponse(data=updated_user)
    return update_response

@router.put("/password",response_model=PasswordResponse)
async def update_password(password:UserPassword,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    if not current_active_user:
        raise HTTPException(status_code=401,detail="无用户令牌或令牌已过期")
    if await set_password(db,password,current_active_user):
        password_response=PasswordResponse()
        return password_response
