from sqlalchemy.orm import Session
from sqlalchemy import select, update, func # Import select and update for modern SQLAlchemy
from typing import List, Optional

from app.db import models # Import database models
from app.schemas import batch as batch_schemas # Import Pydantic schemas

import logging

logger = logging.getLogger(__name__)

# === Create Operations ===

def create_batch(db: Session, batch: batch_schemas.OpenAIBatchCreate) -> models.BatchRequest:
    """
    Creates a new batch request record in the database.

    Args:
        db: The SQLAlchemy database session.
        batch: Pydantic schema containing the data for the new batch record.

    Returns:
        The newly created SQLAlchemy BatchRequest object.

    Raises:
        Exception: If a database error occurs during creation.
    """
    logger.info(f"Creating new batch record for OpenAI ID: {batch.openai_batch_id}")
    # Create a dictionary from the Pydantic model, handling the 'metadata' alias
    # Use exclude_unset=True to avoid overriding model defaults with None from schema
    db_batch_data = batch.model_dump(exclude_unset=True, by_alias=True) # Use by_alias for metadata

    # Rename 'metadata' key from alias back to 'metadata_' for the model if present
    if 'metadata' in db_batch_data:
        db_batch_data['metadata_'] = db_batch_data.pop('metadata')

    db_batch = models.BatchRequest(**db_batch_data)
    try:
        db.add(db_batch)
        db.commit()
        db.refresh(db_batch) # Refresh to get DB-generated values like id, created_at
        logger.info(f"Successfully created batch record with DB ID: {db_batch.id}")
        return db_batch
    except Exception as e:
        logger.error(f"Failed to create batch record for OpenAI ID {batch.openai_batch_id}: {e}", exc_info=True)
        db.rollback() # Rollback transaction on error
        raise # Re-raise the exception to be handled by the caller (API endpoint)


# === Read Operations === (No changes needed based on OpenAI docs review)

def get_batch_by_id(db: Session, batch_id: int) -> Optional[models.BatchRequest]:
    """
    Retrieves a specific batch request record by its internal database ID.

    Args:
        db: The SQLAlchemy database session.
        batch_id: The internal primary key ID of the batch record.

    Returns:
        The SQLAlchemy BatchRequest object if found, otherwise None.
    """
    logger.debug(f"Fetching batch record by DB ID: {batch_id}")
    statement = select(models.BatchRequest).where(models.BatchRequest.id == batch_id)
    result = db.execute(statement).scalar_one_or_none()
    if result:
        logger.debug(f"Found batch record with DB ID: {batch_id}")
    else:
        logger.debug(f"No batch record found with DB ID: {batch_id}")
    return result

def get_batch_by_openai_id(db: Session, openai_batch_id: str) -> Optional[models.BatchRequest]:
    """
    Retrieves a specific batch request record by its OpenAI Batch ID.

    Args:
        db: The SQLAlchemy database session.
        openai_batch_id: The unique ID assigned by OpenAI.

    Returns:
        The SQLAlchemy BatchRequest object if found, otherwise None.
    """
    logger.debug(f"Fetching batch record by OpenAI ID: {openai_batch_id}")
    statement = select(models.BatchRequest).where(models.BatchRequest.openai_batch_id == openai_batch_id)
    result = db.execute(statement).scalar_one_or_none()
    if result:
        logger.debug(f"Found batch record for OpenAI ID: {openai_batch_id}")
    else:
        logger.debug(f"No batch record found for OpenAI ID: {openai_batch_id}")
    return result

def get_batches(db: Session, skip: int = 0, limit: int = 100) -> List[models.BatchRequest]:
    """
    Retrieves a list of batch request records, with optional pagination.

    Args:
        db: The SQLAlchemy database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return (for pagination).

    Returns:
        A list of SQLAlchemy BatchRequest objects.
    """
    logger.debug(f"Fetching batch records with skip={skip}, limit={limit}")
    statement = select(models.BatchRequest).order_by(models.BatchRequest.created_at.desc()).offset(skip).limit(limit)
    results = db.execute(statement).scalars().all()
    logger.debug(f"Retrieved {len(results)} batch records.")
    return results

def count_batches(db: Session) -> int:
    """
    Counts the total number of batch request records in the database.

    Args:
        db: The SQLAlchemy database session.

    Returns:
        The total count of batch records.
    """
    logger.debug("Counting total batch records.")
    statement = select(func.count()).select_from(models.BatchRequest)
    total_count = db.execute(statement).scalar_one()
    logger.debug(f"Total batch records count: {total_count}")
    return total_count


# === Update Operations ===

def update_batch(db: Session, db_batch: models.BatchRequest, batch_update: batch_schemas.BatchUpdate) -> Optional[models.BatchRequest]:
    """
    Updates an existing batch request record in the database.

    Args:
        db: The SQLAlchemy database session.
        db_batch: The existing SQLAlchemy BatchRequest object to update.
        batch_update: Pydantic schema containing the fields to update.

    Returns:
        The updated SQLAlchemy BatchRequest object, or None if the input object was None.

    Raises:
        Exception: If a database error occurs during update.
    """
    if not db_batch:
        logger.warning("Attempted to update a non-existent batch record.")
        return None

    logger.info(f"Updating batch record with DB ID: {db_batch.id} (OpenAI ID: {db_batch.openai_batch_id})")
    # Get update data, excluding unset fields to allow partial updates
    # Use by_alias=True to correctly handle 'metadata' alias if present in update
    update_data = batch_update.model_dump(exclude_unset=True, by_alias=True)

    # Rename 'metadata' key from alias back to 'metadata_' for the model if present
    if 'metadata' in update_data:
        update_data['metadata_'] = update_data.pop('metadata')

    if not update_data:
        logger.info(f"No fields provided for update for batch DB ID: {db_batch.id}")
        return db_batch # Return the object unmodified if no update data

    try:
        # Update attributes on the existing model instance
        for key, value in update_data.items():
            # Check if the key exists as an attribute in the model before setting
            if hasattr(db_batch, key):
                setattr(db_batch, key, value)
            else:
                logger.warning(f"Attempted to update non-existent attribute '{key}' on BatchRequest model.")


        # Note: updated_at is handled automatically by the DB `onupdate=func.now()`

        db.add(db_batch) # Add the modified object to the session
        db.commit()
        db.refresh(db_batch) # Refresh to get any DB-generated changes (like updated_at)
        logger.info(f"Successfully updated batch record with DB ID: {db_batch.id}")
        return db_batch
    except Exception as e:
        logger.error(f"Failed to update batch record DB ID {db_batch.id}: {e}", exc_info=True)
        db.rollback()
        raise

# === Delete Operations (Placeholder - Not implemented for now) ===
# (No changes needed)
