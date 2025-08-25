# === Build Stage ===
# Use an official Python runtime as a parent image
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1       # Force stdout/stderr streams to be unbuffered

# Set the working directory in the container
WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip in the virtual environment
RUN pip install --upgrade pip

# Copy only the pyproject.toml file to leverage Docker cache
COPY pyproject.toml .
COPY README.md .

# Install all dependencies from pyproject.toml into the virtual environment
# For a pure production build, you might omit the [dev] part.
RUN pip install --no-cache-dir .[dev]

# Copy the rest of the application source code
COPY ./app /app/app
COPY ./app/templates /app/templates


# === Final Stage ===
# Use a smaller base image for the final container
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
COPY --from=builder /app/app /app/app
COPY --from=builder /app/templates /app/templates

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Set the path to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Define the command to run the application using Uvicorn
# Use 0.0.0.0 to bind to all network interfaces within the container
# The number of workers can be adjusted based on your server resources
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
