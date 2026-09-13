from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI

from config.settings import settings


def create_chat_model(llm=None):
    """按 settings.llm.provider 返回聊天模型。"""
    llm = llm or settings.llm
    common = {"model": llm.chat_model, "temperature": 0.3}
    if llm.provider == "ollama":
        return ChatOllama(base_url=llm.base_url, **common)

    # openai / dashscope / deepseek：全部走 OpenAI 兼容协议
    return ChatOpenAI(base_url=llm.base_url, api_key=llm.api_key, **common,
                      extra_body={
        "thinking": {"type": "disabled"} # 关闭思考模式，即可支持tool_choice
    })

def create_embeddings(embedding=None):
    embedding = embedding or settings.embedding
    return OllamaEmbeddings(model=embedding.model)