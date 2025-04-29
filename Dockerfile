# === Build Stage ===
# Use an official Python runtime as a parent image
# Choose a version compatible with your requirements (>= 3.10.12 as requested)
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1       # Force stdout/stderr streams to be unbuffered

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by Python packages (e.g., psycopg2 needs libpq-dev)
# Using slim image, so need to install build tools first if compiling
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry (or just use pip if you prefer) - Using pip directly here for simplicity
# RUN pip install --upgrade pip
# RUN pip install poetry

# Copy only the dependency definition files first to leverage Docker cache
COPY requirements.txt .
# COPY pyproject.toml poetry.lock* ./ # If using Poetry

# Install Python dependencies
# Using a virtual environment is good practice even in Docker
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies into the virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# RUN poetry install --no-dev --no-interaction --no-ansi # If using Poetry

# Copy the rest of the application code into the container
COPY ./app /app/app


# === Final Stage ===
# Use a smaller base image for the final container
FROM python:3.11-slim

# Set environment variables (same as builder)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install only necessary runtime dependencies (psycopg2 needs libpq5)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
COPY --from=builder /app/app /app/app
# Copy templates if they are outside the app directory (adjust path if needed)
# COPY ./templates /app/templates

# Make port 80 available to the world outside this container
# The actual port mapping happens in docker-compose.yml
EXPOSE 8000

# Set the path to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Define the command to run the application using Uvicorn
# Use 0.0.0.0 to bind to all network interfaces within the container
# The number of workers can be adjusted based on your server resources
# Gunicorn with Uvicorn workers is common for production:
# CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "/app/gunicorn_conf.py", "app.main:app"]
# For simplicity, we'll use Uvicorn directly here:
# TODO: Validate the templates path for docker setup
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

