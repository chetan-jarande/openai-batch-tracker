import logging
from typing import Annotated
from openai import OpenAI, AsyncOpenAI
from fastapi import Depends
from app.utils.init_helper import get_global_openai_client, get_openai_client
from app.core.config import get_settings, Settings


logger = logging.getLogger(__name__)

# Type alias for OpenAI client dependency
# Use this if you want to use cache method
OpenAIClient = Annotated[OpenAI, Depends(get_openai_client)]
# This is initialized in the app startup event
OpenAIClientDep = Annotated[OpenAI, Depends(get_global_openai_client)]

