# openai-batch-tracker
openai batch processing tracker

---

# OpenAI Batch Job Tracker API

A FastAPI application to track and monitor OpenAI batch processing jobs, containerized using Docker and Docker Compose.

## Features

* **Track Batches:** Store information about submitted OpenAI batch jobs.
* **Monitor Status:** View the current status of tracked jobs via a web dashboard.
* **API Endpoints:** RESTful API for creating, reading, and updating batch records.
* **Database:** Uses PostgreSQL for persistent storage.
* **Dockerized:** Runs the application and database in Docker containers using Docker Compose.
* **Logging:** Configured daily rotating file logs.

## Project Structure

Here's the recommended directory layout for this project:
```
openai-batch-tracker/
├── app/                    # Main application source code directory
│   ├── core/               # Core application logic (config, logging)
│   │   ├── init.py
│   │   ├── config.py       # Application settings management
│   │   └── logging_config.py # Logging setup
│   ├── crud/               # Database Create, Read, Update, Delete operations
│   │   ├── init.py
│   │   └── batch.py        # CRUD functions specific to batch requests
│   ├── db/                 # Database related code (models, session)
│   │   ├── init.py
│   │   ├── models.py       # SQLAlchemy ORM models (e.g., BatchRequest table)
│   │   └── session.py      # Database engine and session setup
│   ├── routers/            # API endpoint definitions (FastAPI routers)
│   │   ├── init.py
│   │   └── batches.py      # Routes for /batches endpoint and dashboard
│   ├── schemas/            # Pydantic schemas for data validation and serialization
│   │   ├── init.py
│   │   └── batch.py        # Pydantic models for batch data (request/response)
│   ├── templates/          # HTML templates (rendered by Jinja2)
│   │   └── dashboard.html  # Template for the web dashboard
│   └── main.py             # FastAPI application entry point and setup
│
├── logs/                   # Directory for log files (created automatically, mapped by volume)
│   └── app.log             # Example log file (rotates daily)
│
├── .env                    # Environment variables (!!! DO NOT COMMIT SECRETS !!!)
├── .gitignore              # Specifies intentionally untracked files that Git should ignore
├── Dockerfile              # Instructions to build the FastAPI app Docker image
├── docker-compose.yml      # Defines and orchestrates Docker services (app, db)
├── requirements.txt        # Python package dependencies
└── README.md               # This file - project documentation

```

*(Note: The `logs/` directory and its contents will be created automatically when the application runs inside the container and writes logs. You typically add `logs/` and `.env` to your `.gitignore` file.)*

## Prerequisites

* Docker: [Install Docker](https://docs.docker.com/get-docker/)
* Docker Compose: Usually included with Docker Desktop. [Install Docker Compose](https://docs.docker.com/compose/install/)

## Setup and Running

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd openai-batch-tracker # Or your chosen repo name
    ```

2.  **Create `.env` file:**
    * Copy the example `.env` content provided or create your own `.env` file in the project root (`openai-batch-tracker/`).
    * **Important:** Update the `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` variables. Ensure these match the `DATABASE_URL`.
    * *(Optional)* Add your `OPENAI_API_KEY` if you plan to implement status fetching from OpenAI.

3.  **Create `.gitignore` file:**
    * Create a file named `.gitignore` in the project root

4.  **Build and Run with Docker Compose:**
    * Open a terminal in the project root directory (where `docker-compose.yml` is located).
    * Run the following command:
        ```bash
        docker-compose up --build -d
        ```
        * `--build`: Forces Docker to rebuild the application image based on the `Dockerfile`.
        * `-d`: Runs the containers in detached mode (in the background).

5.  **Access the Application:**
    * **API Docs (Swagger UI):** Open your web browser and navigate to [http://localhost:8000/docs](http://localhost:8000/docs)
    * **Dashboard:** Navigate to [http://localhost:8000/batches/dashboard](http://localhost:8000/batches/dashboard)
    * **Root:** Navigate to [http://localhost:8000/](http://localhost:8000/)

6.  **Stopping the Application:**
    ```bash
    docker-compose down
    ```
    * This stops and removes the containers. Add `-v` if you also want to remove the named volumes (database data and logs): `docker-compose down -v`

## Usage

- Doc Batches: https://platform.openai.com/docs/api-reference/batch
- Doc Files: https://platform.openai.com/docs/api-reference/files

* **Adding a Batch Record (POST `/batches/`):**
    * After you create a batch job via the OpenAI API, you register it in this tracker.
    * Send a POST request with a JSON body containing at least the required fields from the OpenAI response:
    ```json
    {
      "openai_batch_id": "batch_abc123xyz", // Required: ID from OpenAI
      "input_file_id": "file_input456",   // Required: Input file ID used
      "endpoint": "/v1/chat/completions", // Required: Endpoint targetted
      "completion_window": "24h",         // Optional: Defaults to "24h" if not sent
      "status": "validating",             // Optional: Defaults to "pending", update with OpenAI status
      "openai_created_at": 1678886400,    // Optional: Unix timestamp from OpenAI
      "metadata": {                       // Optional: Metadata sent to OpenAI
        "customer_id": "cust_123",
        "description": "Weekly report generation"
       }
    }
    ```
* **Updating a Batch Record (PATCH `/batches/{openai_batch_id}`):**
    * Used to update the status, file IDs, timestamps, errors, etc., typically after polling the OpenAI API for the batch status.
    * Send a PATCH request with a JSON body containing only the fields you want to update:
    ```json
    {
      "status": "completed",
      "output_file_id": "file_output789",
      "completed_at": 1678890000, // Unix timestamp
      "request_counts": {
         "total": 100,
         "completed": 98,
         "failed": 2
       }
    }
    ```
    * Or for a failed batch:
    ```json
    {
        "status": "failed",
        "error_file_id": "file_err_abc",
        "failed_at": 1678891000, // Unix timestamp
        "errors": {
            "data": [
                {
                    "code": "invalid_input",
                    "message": "Missing required field on line 42.",
                    "param": null,
                    "line": 42
                }
            ]
        },
        "request_counts": {
            "total": 50,
            "completed": 10,
            "failed": 40
        }
    }
    ```

* **Viewing Batches:** Access the dashboard URL (`/batches/dashboard`) or use the GET API endpoints (`/batches/` or `/batches/{openai_batch_id}`).

## Development

* For local development without rebuilding the image constantly, you can uncomment the volume mount in `docker-compose.yml` (`- ./app:/app/app`). Uvicorn's hot reload (used when running `uvicorn app.main:app --reload`) will pick up code changes.
* to load the dummy main file use `uvicorn app.dummy_main:app --reload --port 8001`  cmd.
* To access the database directly (e.g., using `psql` or a GUI client), connect to `localhost:5433` (or the host port you mapped in `docker-compose.yml`) using the credentials from your `.env` file.

## Future Enhancements

* **Automated Status Polling:** Implement background tasks (e.g., using Celery, ARQ, or FastAPI's `BackgroundTasks`) to periodically query the OpenAI API (`client.batches.retrieve(batch_id)`) for status updates and automatically PATCH the results to the `/batches/{openai_batch_id}` endpoint.
* **File Content Retrieval:** Add API endpoints to fetch and potentially display content from the OpenAI output/error files using the Files API (`client.files.content(file_id)`). Requires handling OpenAI API key securely.
* **Batch Creation Trigger:** Add an endpoint to *initiate* the OpenAI batch creation process (uploading the file via `client.files.create` and then creating the batch via `client.batches.create`), automatically registering the new batch in this tracker upon success.
* **User Authentication/Authorization:** Secure the dashboard and API endpoints.
* **Database Migrations:** Implement Alembic for managing database schema changes.
* **Improved Dashboard:** Add filtering, sorting, pagination, direct links to OpenAI file content (if implemented), and a manual refresh button per batch.
* **Testing:** Add unit and integration tests.

