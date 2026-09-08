from fastapi import FastAPI


from routers import news,users,favorite

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

#跨域资源共享中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",  #前端地址
    "http://127.0.0.1:5173"],#允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,#允许携带cookie
    allow_methods=["*"],#允许的请求方法
    allow_headers=["*"],#允许的请求头
)

app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)