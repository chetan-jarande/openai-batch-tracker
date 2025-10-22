# OpenAI Batch Tracker

An advanced FastAPI application designed to track, monitor, and manage OpenAI batch processing jobs, featuring a modern, interactive dashboard and a full-fledged documentation viewer.

---

## Features

- **Modern UI:** An interactive, dark-themed homepage for easy navigation.
- **Batch & File Dashboards:** Separate, detailed dashboards for visualizing mock batch jobs and files.
- **Documentation Viewer:** An integrated system to render and view project documentation (`/docs`) and the `LICENSE` file.
- **Dockerized Environment:** Fully containerized with Docker and managed via a `Makefile` for consistent development and production environments.
- **Robust API:** A well-documented API for managing batches and files, built with FastAPI.

## Prerequisites

- **Docker & Docker Compose:** Required for running the application in a containerized environment.
  - [Install Docker](https://docs.docker.com/get-docker/)

- **Pyenv**
  - [Pyenv](https://github.com/pyenv/pyenv.git)
  - Install `pyenv` using the commands below.
    <details>
    <summary>
      Click to see installation commands
    </summary>

    ```bash
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n eval "$(pyenv init -)"\nfi' >> ~/.bashrc
    exec "$SHELL"
    ```

    </details>

- **OpenAI Documentation:** Familiarity with the OpenAI Batch API is recommended.
  - [OpenAI Batch API Docs](https://platform.openai.com/docs/api-reference/batch)
  - [OpenAI Files API Docs](https://platform.openai.com/docs/api-reference/files)

## Setup & Installation

This project uses a `Makefile` to simplify all setup and execution steps.

### 1. Local Development (Python & Pyenv)

This method is for running the application directly on your machine without Docker.

1. **Set up the Environment:**
    This command creates a virtual environment, installs all dependencies (including development tools), and prepares your local setup.

    ```bash
    make dev
    ```

2. **Configure Environment Variables:**
    Copy the example `.env` file and add your OpenAI API key.

    ```bash
    cp .env.example .env
    ```

    Now, edit the `.env` file to include your `OPENAI_API_KEY` and any other necessary settings.

### 2. Docker-Based Development

This is the recommended approach for a consistent and isolated development environment.

1. **Build and Start the Services:**
    - These commands will build the necessary Docker images and start the development containers in the background.

    ```bash
    make docker-build-dev
    make docker-up-dev
    ```

    - Refer other commands to know more about prod development and env.

## How to Start the Service

- **If running locally:**

    ```bash
    make run-local
    ```

  - This will start the server at 8000 port.

- **If running with Docker:**
  - The service is already running after `make docker-up-dev`. You can view logs with `make docker-logs-dev`.
  - This will start the server at 8001 port.

Once the service is running, visit **[http://localhost:8000](http://localhost:8000)**. The homepage will guide you to all available resources, including API documentation and dashboards.

## Usage

### API Usage

The application provides a comprehensive REST API for managing batch jobs and files. For detailed information on all available endpoints, request bodies, and responses, please refer to the interactive API documentation:

- **Swagger UI:** [/docs](/docs)
- **ReDoc:** [/redoc](/redoc)

### Input/Output File Structure

For reference, the `resources/` directory contains examples of the input and output file structures used by the OpenAI Batch API. These files can serve as a guide when you are creating your own batch jobs.

## Contribution & Code of Conduct

We welcome contributions from the community! Whether it's reporting a bug, suggesting a feature, or submitting a pull request, your help is greatly appreciated.

Please read our **[Contribution Guidelines](CONTRIBUTING.md)** to get started.

This project is governed by our **[Code of Conduct](CODE_OF_CONDUCT.md)**. By participating, you are expected to uphold this code.

## Contact & Thank You

Thank you for your interest in the OpenAI Batch Tracker. If you have any questions, feel free to open an issue on GitHub. We look forward to your contributions!
