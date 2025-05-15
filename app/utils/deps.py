import logging
from typing import Annotated
from sqlalchemy.orm import Session
from openai import OpenAI, AsyncOpenAI
from fastapi import Depends
from app.utils.init_helper import get_global_openai_client, get_openai_client
from app.core.config import get_settings, Settings
from app.db.session import get_db


# Type alias for dependencies to improve readability in endpoint signatures
DBSession = Annotated[Session, Depends(get_db)]

# Type alias for OpenAI client dependency
# Use this if you want to use cache method
OpenAIClient = Annotated[OpenAI, Depends(get_openai_client)]
# This is initialized in the app startup event
OpenAIClientDep = Annotated[OpenAI, Depends(get_global_openai_client)]

