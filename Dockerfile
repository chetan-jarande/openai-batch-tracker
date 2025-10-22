# === Build Stage ===
# Use an official Python runtime as a parent image
FROM python:3.13.3-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1       # Force stdout/stderr streams to be unbuffered

# Set the working directory
WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install uv
RUN pip install --upgrade pip uv

# Copy files required for package installation
COPY pyproject.toml .
COPY README.md .

# Install only production dependencies
RUN uv pip install --no-cache-dir .

# Copy the application source code
COPY ./app /app/app
COPY ./docs /app/docs
COPY ./app/static /app/app/static
COPY ./app/templates /app/templates


# === Final Stage ===
# Use a smaller, clean base image
FROM python:3.13.3-slim

# Install make so that the CMD can be executed
RUN apt-get update && apt-get install -y make --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user and group for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code from the builder stage
COPY --from=builder /app/app /app/app
COPY --from=builder /app/docs /app/docs
COPY --from=builder /app/app/static /app/app/static
COPY --from=builder /app/templates /app/templates

# Copy the Makefile from the current directory
COPY pyproject.toml .
COPY README.md .
COPY Makefile .

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Set the path to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Define the command to run the application using the Makefile
CMD ["make", "run"]
