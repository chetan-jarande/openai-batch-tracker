import logging
from sqlalchemy.orm import Session
from typing import Optional
from app.db.models.file import File as DBFileModel
from app.schemas import file as file_schema
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


logger = logging.getLogger(__name__)


def get_db_file_by_openai_id(db: Session, openai_file_id: str) -> Optional[DBFileModel]:
    """
    Retrieves a file record from the database by its OpenAI File ID.

    Args:
        db: The SQLAlchemy database session.
        openai_file_id: The OpenAI File ID to search for.

    Returns:
        The DBFileModel instance if found, otherwise None.
    """
    return (
        db.query(DBFileModel)
        .filter(DBFileModel.openai_file_id == openai_file_id)
        .first()
    )


def create_db_file_record(
    db: Session, file_data: file_schema.FileCreate
) -> DBFileModel:
    """
    Creates a new file record in the database.

    Args:
        db: The SQLAlchemy database session.
        file_data: Pydantic schema containing the file data.

    Returns:
        The created DBFileModel instance.

    Raises:
        HTTPException: If there's an integrity error (e.g., duplicate openai_file_id).
    """
    db_file = DBFileModel(**file_data.model_dump())
    try:
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        logger.info(
            f"File record created in DB with ID {db_file.id} for OpenAI file ID {db_file.openai_file_id}"
        )
        return db_file
    except IntegrityError as e:
        db.rollback()
        logger.error(
            f"Integrity error creating file record for OpenAI ID {file_data.openai_file_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File with OpenAI ID {file_data.openai_file_id} already exists in the database.",
        )
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            f"Database error creating file record for OpenAI ID {file_data.openai_file_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save file information to the database.",
        )
