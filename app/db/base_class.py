from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, DateTime, func

class_registry: dict = {}

@as_declarative(class_registry=class_registry)
class Base:
    """
    Base class for SQLAlchemy models.

    It includes an automatically generated table name and common audit columns
    (`created_at` and `updated_at`).
    """
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generates the table name automatically from the class name.
        Converts CamelCase class names to snake_case table names.
        Example: UserProfile -> user_profile
        """
        import re
        # Convert CamelCase to snake_case
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name

    # Audit columns
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

