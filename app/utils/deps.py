from typing import Annotated
from openai import OpenAI, AsyncOpenAI
from fastapi import Depends
from app.utils.init_helper import get_openai_client
from app.core.config import OpenAIMode


OpenAIClient = Annotated[OpenAI, Depends(lambda: get_openai_client(mode=OpenAIMode.SYNC))]
AsyncOpenAIClient = Annotated[AsyncOpenAI, Depends(lambda: get_openai_client(mode=OpenAIMode.ASYNC))]
