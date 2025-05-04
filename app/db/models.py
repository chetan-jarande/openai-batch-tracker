from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Text,
    Enum as SQLEnum,
    BigInteger,
)
from sqlalchemy.sql import func  # For default timestamps
from sqlalchemy.orm import relationship  # If you add related models later
import enum

from .session import Base  # Import Base from our session setup


# Define an Enum for the status field - Checked against OpenAI docs
# Values match: validating, failed, in_progress, finalizing, completed, expired, cancelling, cancelled
class BatchStatus(str, enum.Enum):
    """
    Doc: https://platform.openai.com/docs/guides/batch#4-check-the-status-of-a-batch
    """
    PENDING = "pending"  # Internal status: Batch request created in our system
    VALIDATING = "validating"  # OpenAI status: Validating input file
    FAILED = "failed"  # OpenAI status: Batch failed validation or processing
    IN_PROGRESS = "in_progress"  # OpenAI status: Batch processing underway
    FINALIZING = "finalizing"  # OpenAI status: Preparing results
    COMPLETED = "completed"  # OpenAI status: Batch finished successfully
    EXPIRED = "expired"  # OpenAI status: Batch expired before completion
    CANCELLING = "cancelling"  # OpenAI status: Cancellation in progress
    CANCELLED = "cancelled"  # OpenAI status: Batch successfully cancelled


class BatchRequest(Base):
    """
    SQLAlchemy model representing an OpenAI Batch Request tracked by this application.
    Updated based on OpenAI Batch API documentation. Fields ordered similar to OpenAI object.
    Doc Batch Object: https://platform.openai.com/docs/api-reference/batch/object
    """

    __tablename__ = "batch_requests"

    # --- Internal Database Fields ---
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="Internal primary key for the database record."
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created in this system.",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when the record was last updated.",
    )


    # --- OpenAI Batch Fields (Mirrored from API - Ordered like JSON example) ---
    openai_batch_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
        comment="The unique ID returned by OpenAI Batch API (e.g., batch_abc123). Corresponds to 'id' in OpenAI object.",
    )
    object_type = Column(
        String,
        default="batch",
        nullable=True,
        comment="Object type from OpenAI, typically 'batch'. Corresponds to 'object'.",
    )
    endpoint = Column(
        String,
        nullable=False,
        comment="The OpenAI API endpoint used for the batch (e.g., /v1/chat/completions).",
    )
    errors = Column(
        JSON,
        nullable=True,
        comment="Structured error data from OpenAI (list of error objects).",
    )
    input_file_id = Column(
        String, index=True, nullable=False, comment="OpenAI File ID for the input data."
    )
    completion_window = Column(
        String,
        nullable=False,
        default="24h",
        comment="The requested completion window (e.g., 24h).",
    )
    status = Column(
        SQLEnum(BatchStatus),
        default=BatchStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current status of the batch job (maps to OpenAI statuses).",
    )
    output_file_id = Column(
        String,
        index=True,
        nullable=True,
        comment="OpenAI File ID for the output results (available when completed).",
    )
    error_file_id = Column(
        String,
        index=True,
        nullable=True,
        comment="OpenAI File ID for detailed errors (available when failed).",
    )
    openai_created_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp (seconds) when the batch was created by OpenAI. Corresponds to 'created_at'.",
    )
    in_progress_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'in_progress'.",
    )
    expires_at = Column(
        BigInteger, nullable=True, comment="Unix timestamp when the batch will expire."
    )
    finalizing_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'finalizing'.",
    )
    completed_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'completed'.",
    )
    failed_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'failed'.",
    )
    # Added based on example JSON
    expired_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'expired'.",
    )
    # Added based on example JSON
    cancelling_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'cancelling'.",
    )
    cancelled_at = Column(
        BigInteger,
        nullable=True,
        comment="Unix timestamp when the batch moved to 'cancelled'.",
    )
    request_counts = Column(
        JSON,
        nullable=True,
        comment="JSON object from OpenAI containing counts: total, completed, failed.",
    )
    metadata_ = Column(
        "metadata", # Column name in DB
        JSON,
        nullable=True,
        comment="Optional key-value metadata associated with the OpenAI batch. Corresponds to 'metadata'.",
    )


    def __repr__(self):
        # Use the OpenAI ID for representation as it's more meaningful externally
        return f"<BatchRequest(id={self.id}, openai_batch_id='{self.openai_batch_id}', status='{self.status.value}')>"

