# OpenAI Batch Job Tracker & Dashboard

This FastAPI application serves as a tracker and dashboard for OpenAI Batch API jobs. It allows users (or other systems via API) to register batch jobs submitted to OpenAI, stores their relevant details in a PostgreSQL database, and provides a web dashboard (to be implemented) to visualize their status.

The entire application, including the database, is Dockerized for easy setup and deployment.

## Features

* **Track OpenAI Batch Jobs:** Register, monitor status, cancel, and retrieve details of batch jobs.
* **File Management:** Upload input files for batches and manage file records (list, retrieve, delete).
* **Retrieve Batch Results:** Fetch and parse output/error files from completed batch jobs.
* **PostgreSQL Database:** Persistently store information about batch jobs and associated files using SQLAlchemy.
* **Web Dashboard:** (Planned) A visual interface to view job statuses using Jinja2 templates.
* **Dockerized:** Easy to set up and run using Docker and Docker Compose.
* **Structured Logging:** Configurable and request-correlated logging.
* **Modular Design:** Code is organized into modules for clarity and maintainability (API, core, DB, schemas).
* **Pydantic Schemas:** Robust data validation and serialization for API requests and responses.
* **OpenAI SDK Integration:** Utilizes the official `openai` Python library.

## Project Structure
```
├── app/                                # Main application code
│   ├── api/                            # API endpoint definitions
│   │   ├── init.py
│   │   ├── deps.py                     # Common dependencies (e.g., get_db, get_openai_client)
│   │   ├── files.py                    # Endpoints for file management
│   │   ├── batches.py                  # Endpoints for batch job management
│   │   └── api_v1.py                   # Main API router aggregating other routers
│   ├── core/                           # Core components like configuration, logging
│   │   ├── init.py
│   │   ├── config.py                   # ✅ Pydantic settings management (env vars)
│   │   └── logging_config.py           # ✅ Logging setup
│   ├── db/                             # Database related modules
│   │   ├── init.py
│   │   ├── base_class.py               # Base for SQLAlchemy models (declarative_base)
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   │   ├── init.py
│   │   │   ├── file.py                 # File model (SQLAlchemy)
│   │   │   └── batch.py                # Batch model (SQLAlchemy)
│   │   └── session.py                  # Database session management
│   ├── schemas/                        # Pydantic schemas for data validation & serialization
│   │   ├── init.py
│   │   ├── file.py                     # Schemas for file objects (Pydantic)
│   │   ├── batch.py                    # Schemas for batch objects (Pydantic)
│   │   └── common.py                   # Common/shared schemas (e.g., Msg, PaginatedResponse)
│   ├── services/                       # Business logic/service layer (optional, for complex logic)
│   │   ├── init.py
│   │   ├── file_service.py             # Service functions for file operations
│   │   └── batch_service.py            # Service functions for batch operations
│   ├── templates/                      # Jinja2 templates for the dashboard
│   │   └── dashboard.html              # Placeholder for dashboard
│   ├── utils/                          # Utility functions
│   │   ├── init.py
│   │   └── openai_utils.py             # Utilities for interacting with OpenAI client
│   └── main.py                         # Main FastAPI application instance and startup events
├── .env                                # Environment variables (OPENAI_API_KEY, DATABASE_URL, etc.) - DO NOT COMMIT
├── .env.example                        # Example environment file
├── .gitignore                          # Git ignore file
├── Dockerfile                          # Dockerfile for the FastAPI application
├── docker-compose.yml                  # Docker Compose for running app and DB
├── requirements.txt                    # Python dependencies
└── README.md                           # This file

```

## Tech Stack

* **Backend:** FastAPI, Python 3.11
* **Database:** PostgreSQL 15
* **ORM:** SQLAlchemy
* **Data Validation:** Pydantic
* **Containerization:** Docker, Docker Compose
* **OpenAI SDK:** `openai` library
* **Templating:** Jinja2 (for dashboard)
* **Logging:** Python's built-in `logging` module.

## Setup and Running

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd openai-batch-tracker
    ```

2.  **Set up environment variables:**
    Copy `.env.example` to `.env` and fill in your `OPENAI_API_KEY`, `POSTGRES_*` variables, and other configurations.
    ```bash
    cp .env.example .env
    # Edit .env with your details (e.g., using nano, vim, or VSCode)
    ```
    **Example `.env` content:**
    ```env
    OPENAI_API_KEY="sk-yourkey"
    POSTGRES_SERVER="db"
    POSTGRES_USER="youruser"
    POSTGRES_PASSWORD="yourpassword"
    POSTGRES_DB="openaibatchdb"
    POSTGRES_PORT=5432
    SERVER_PORT=8000
    LOG_LEVEL="INFO"
    # ... other settings from .env.example
    ```

3.  **Build and run with Docker Compose:**
    From the project root directory:
    ```bash
    docker-compose up --build -d
    ```
    * `--build`: Forces Docker to rebuild the images if the Dockerfile or context has changed.
    * `-d`: Runs the containers in detached mode (in the background).

4.  **Accessing the Application:**
    * API will be available at `http://localhost:8000` (or the `SERVER_PORT` configured in `.env`).
    * Interactive API documentation (Swagger UI) will be at `http://localhost:8000/api/v1/docs`.
    * Alternative API documentation (ReDoc) will be at `http://localhost:8000/api/v1/redoc`.

5.  **Stopping the Application:**
    ```bash
    docker-compose down
    ```
    * To remove volumes (and thus delete database data): `docker-compose down -v`

## API Endpoints (`/api/v1`)

### Files (`/files`)

* `POST /upload`: Uploads a batch input file to OpenAI and stores its metadata in the database.
    * **Request:** `multipart/form-data` with a file.
    * **Response:** `schemas.FilePublic` with details of the stored file record.
* `GET /openai/list`: Lists files directly from the user's OpenAI account.
    * **Query Params:** `purpose: Optional[str]`, `limit: Optional[int] = 20`, `after: Optional[str]`, `order: Optional[str] = "desc"`.
    * **Response:** List of OpenAI File objects (as dicts).
* `GET /`: Lists files from the local database. Supports pagination and filtering.
    * **Query Params:** `skip: int = 0`, `limit: int = 100`, `purpose: Optional[str]`, `status: Optional[str]`, `filename_contains: Optional[str]`.
    * **Response:** `schemas.PaginatedFilePublicResponse`.
* `GET /{openai_file_id}`: Retrieves details of a specific file from the local database.
    * **Path Param:** `openai_file_id` (OpenAI File ID).
    * **Response:** `schemas.FilePublic`.
* `DELETE /{openai_file_id}`: Deletes a file from OpenAI and then from the local database.
    * **Path Param:** `openai_file_id` (OpenAI File ID).
    * **Response:** `schemas.Msg` indicating success or failure.

### Batches (`/batches`)

* `POST /`: Creates a new batch job on OpenAI and stores its initial information locally.
    * **Request Body:** `schemas.BatchCreateRequest`.
    * **Response:** `schemas.BatchPublic`.
* `GET /{openai_batch_id}`: Retrieves the latest details of a specific batch job from OpenAI and updates the local DB record.
    * **Path Param:** `openai_batch_id`.
    * **Response:** `schemas.BatchPublic`.
* `POST /{openai_batch_id}/cancel`: Cancels an in-progress batch job on OpenAI and updates its status locally.
    * **Path Param:** `openai_batch_id`.
    * **Response:** `schemas.BatchPublic`.
* `GET /openai/list`: Lists batch jobs directly from the user's OpenAI account. Supports pagination.
    * **Query Params:** `limit: Optional[int] = 20`, `after: Optional[str]`.
    * **Response:** List of `schemas.BatchBase` objects.
* `GET /`: Lists batch jobs from the local database. Supports pagination and filtering.
    * **Query Params:** `skip: int = 0`, `limit: int = 100`, `status: Optional[str]`, `input_file_id: Optional[str]`.
    * **Response:** `schemas.PaginatedBatchPublicResponse`.
* `GET /{openai_batch_id}/results`: Retrieves the results of a completed/failed batch job from its output/error file.
    * **Path Param:** `openai_batch_id`.
    * **Response:** List of `schemas.BatchResultLine` objects.
    * **Note:** OpenAI automatically deletes result files 30 days after batch completion.

## Logging

The application uses structured logging. Logs for the FastAPI application running inside Docker can be viewed using:
```bash
docker-compose logs -f app
```

## Database Migrations
Currently, SQLAlchemy models define the schema, and tables are created on application startup if they don't exist. For production environments and evolving schemas, integrating Alembic for database migrations is highly recommended.

## Development Notes
The openai library requires the OPENAI_API_KEY environment variable.
The psycopg2-binary driver is used for PostgreSQL.
For live code reloading during development with Docker, ensure Uvicorn is run with --reload (the CMD in Dockerfile can be adjusted, or run python app/main.py inside the container if it includes Uvicorn reload logic). The volume mount ./app:/app/app in docker-compose.yml facilitates this.