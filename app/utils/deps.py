from typing import Annotated
from openai import OpenAI, AsyncOpenAI
from fastapi import Depends
from app.utils.init_helper import get_openai_client
from app.utils.config import OpenAIMode


def get_sync_openai_client() -> OpenAI:
    return get_openai_client(mode=OpenAIMode.SYNC)


def get_async_openai_client() -> AsyncOpenAI:
    return get_openai_client(mode=OpenAIMode.ASYNC)


OpenAIClient = Annotated[OpenAI, Depends(get_sync_openai_client)]
AsyncOpenAIClient = Annotated[AsyncOpenAI, Depends(get_async_openai_client)]
