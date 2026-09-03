from sqlalchemy.ext.asyncio import create_async_engine,AsyncSession,async_sessionmaker
from config import settings
database=settings.settings.database
#数据库连接参数
#数据库URL
ASYNC_DATABASE_URL = f"mysql+aiomysql://{database.user}:{database.password}@{database.host}:{database.port}/{database.name}?charset=utf8"
#创建异步引擎
async_engine=create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20
)
#创建异步会话工厂
AsyncSessionLocal=async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

#依赖项，获取数据库对话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
