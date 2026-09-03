"""
NewsCraft 全局配置加载器（settings.py）

配置来源与优先级（从高到低）：
    1. 初始化参数 init（最高）
    2. 系统环境变量 env（如生产环境 export 的变量）
    3. .env 文件（dotenv，本地敏感配置）
    4. .env / config.yaml 的 secrets（未用）
    5. config.yaml（yaml 配置，支持 ${VAR} 占位符替换）
    6. 字段默认值（最低）

核心机制：
    - config.yaml 中的 ${VAR} 占位符会在「注入前」被 EnvAwareYamlSource
      递归替换成环境变量值（os.environ）。
    - 模块加载时先调用 load_dotenv() 把 .env 灌进 os.environ，
      因此 .env 里的 MYSQL_PASSWORD / SECRET_KEY / DASHSCOPE_API_KEY
      能直接填进 yaml 对应的占位符，实现「yaml 定结构、.env 管密钥」。
"""
from __future__ import annotations

import os,yaml
from pathlib import Path
from typing import Any, Tuple, Type

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

BASE_DIR = Path(__file__).resolve().parent       # 后端代码/backend/config/（config.yaml 所在）
PROJECT_ROOT = BASE_DIR.parent.parent.parent     # 项目根目录（.env / .env.example 所在处）

# 先把 .env 加载进 os.environ，供 yaml 占位符 ${VAR} 替换使用
load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8")


def _resolve_env(value: Any) -> Any:
    """递归替换 dict/list/str 中的 ${ENV_NAME} 占位符。"""
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


class EnvAwareYamlSource(YamlConfigSettingsSource):
    """在 yaml 数据注入前，先把 ${VAR} 占位符替换成环境变量值。"""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as yaml_file:
            data = yaml.safe_load(yaml_file) or {}
        # 关键：注入前必须做 ${VAR} → 环境变量 的替换
        return _resolve_env(data)


# ---------------- 配置模型（与 config.yaml 各 section 一一对应）----------------

class AppSettings(BaseModel):
    name: str = "NewsCraft"
    env: str = "dev"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    name: str = "newscraft_app"
    charset: str = "utf8mb4"


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""


class AuthSettings(BaseModel):
    token_expire_days: int = 7
    secret_key: str = ""


class LLMSettings(BaseModel):
    provider: str = "dashscope"
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    chat_model: str = "qwen-plus"
    timeout: int = 60
    max_retries: int = 3


class EmbeddingSettings(BaseModel):
    provider: str = "dashscope"
    model: str = "text-embedding-v3"
    dimensions: int = 1024


class VectorDBSettings(BaseModel):
    type: str = "in_memory"
    collection: str = "news_vectors"
    top_k: int = 5


class RAGSettings(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    recall_top_k: int = 5
    max_context_len: int = 3000
    enable_question_rewrite: bool = True
    enable_context_dedup: bool = True
    enable_citation: bool = True


class TaskSettings(BaseModel):
    concurrency: int = 4


class Settings(BaseSettings):
    """NewsCraft 全局配置，聚合 config.yaml + .env + 环境变量。"""

    model_config = SettingsConfigDict(
        yaml_file=BASE_DIR / "config.yaml",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    auth: AuthSettings = AuthSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    vector_db: VectorDBSettings = VectorDBSettings()
    rag: RAGSettings = RAGSettings()
    tasks: TaskSettings = TaskSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # 优先级从高到低：init > 系统环境变量 > .env > secrets > yaml(含${VAR}替换)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            EnvAwareYamlSource(settings_cls),
        )


# 模块级单例：其它模块直接 from config.settings import settings
settings = Settings()

if __name__ == "__main__":
    print(settings.database.password)