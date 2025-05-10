import logging

from sqlalchemy import Column, Integer, String, BigInteger, Text, Index
from sqlalchemy.orm import relationship

from app.db.base_class import Base

logger = logging.getLogger(__name__)


class File(Base):
    """
    SQLAlchemy model for storing file information.

    This table stores details about files that are uploaded to OpenAI,
    primarily for use in batch processing jobs.
    The 'id', 'created_at', and 'updated_at' columns are inherited from Base.
    """

    __tablename__ = "files"  # Explicitly defining, though Base would generate it

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    openai_file_id = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="The unique identifier for the file on OpenAI's servers (e.g., 'file-xxxx').",
    )

    filename = Column(
        String(255),
        nullable=False,
        comment="The name of the file (e.g., 'my_batch_input.jsonl').",
    )

    bytes_size = Column(
        BigInteger, nullable=False, comment="Size of the file in bytes."
    )

    purpose = Column(
        String(50),
        nullable=False,
        index=True,
        comment="The intended purpose of the file (e.g., 'batch', 'fine-tune').",
    )

    status = Column(
        String(50),
        nullable=True,
        index=True,
        comment="The current status of the file on OpenAI (e.g., 'uploaded', 'processed', 'error').",
    )

    status_details = Column(
        Text,
        nullable=True,
        comment="Additional details about the file's status, especially for errors.",
    )

    openai_created_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp of when the file was created on OpenAI's servers.",
    )

    # --- Relationships ---
    # If a File can be an input to multiple Batches, and an output/error for one Batch.
    # This defines the 'one' side of a one-to-many relationship from File to BatchFileLink.
    # A single file can be linked to multiple batch jobs (e.g. as an input_file_id).
    # The `BatchFileLink` association table will handle these many-to-many type relationships.
    # batch_links = relationship("BatchFileLink", back_populates="file")

    # If we want to directly link files to batches (e.g., if a file is an input to ONE batch, or output of ONE batch)
    # This depends on the exact relationship modeling with the `Batch` table.
    # For now, we'll assume a more flexible approach might be needed via an association table or
    # foreign keys on the Batch table itself (e.g., input_file_id, output_file_id, error_file_id on Batch pointing to File.id).

    # If a file is an input to a batch, the Batch model might have an `input_file_id`
    # If a file is an output of a batch, the Batch model might have an `output_file_id`
    # If a file is an error file of a batch, the Batch model might have an `error_file_id`
    # These would be ForeignKey columns in the `Batch` model pointing to `File.id` or `File.openai_file_id`.

    # For now, keeping the File model simple. Relationships will be more clearly defined
    # when the Batch model and its interactions are built.

    __table_args__ = (
        Index("idx_files_openai_file_id", "openai_file_id", unique=True),
        Index("idx_files_purpose_status", "purpose", "status"),
        {
            "comment": "Stores information about files uploaded to OpenAI for batch processing."
        },
    )

    def __repr__(self) -> str:
        return (
            f"<File(id={self.id}, openai_file_id='{self.openai_file_id}', "
            f"filename='{self.filename}', purpose='{self.purpose}', status='{self.status}')>"
        )


if __name__ == "__main__":
    # This block is for illustrative purposes and won't run in the app context.
    # It demonstrates how the model might be used or inspected.
    logger.info("File model definition.")

    # Example: Accessing column information (requires SQLAlchemy context to be fully functional)
    # for column in File.__table__.columns:
    #     logger.info(f"Column: {column.name}, Type: {column.type}, Nullable: {column.nullable}")

    # Creating an instance (in a real app, this happens within a DB session)
    # try:
    #     example_file = File(
    #         openai_file_id="file-example123",
    #         filename="example.jsonl",
    #         bytes_size=1024,
    #         purpose="batch",
    #         status="uploaded",
    #         openai_created_at=1678886400  # Example Unix timestamp
    #     )
    #     logger.info(f"Example instance: {example_file}")
    # except TypeError as e:
    #     logger.error(f"Error creating File instance (likely due to missing SQLAlchemy session or Base metadata binding): {e}")
    pass
