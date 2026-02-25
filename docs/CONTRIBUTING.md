# How to Contribute to OpenAI Batch Tracker

First off, thank you for considering contributing to this project! Your help is greatly appreciated. By working together, we can make this tool even better.

This document provides a set of guidelines for contributing to the OpenAI Batch Tracker. These are mostly guidelines, not strict rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior.

## How Can I Contribute?

There are many ways to contribute, from writing tutorials or blog posts, improving the documentation, submitting bug reports and feature requests, or writing code which can be incorporated into the main project.

### Reporting Bugs

- **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/chetan-jarande/openai-batch-tracker/issues).
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/chetan-jarande/openai-batch-tracker/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements

- Open a new issue to discuss your enhancement. Clearly describe the proposed enhancement, why it's needed, and provide examples of how it would be used.
- This allows us to discuss the potential feature and ensure it aligns with the project's goals before you invest a lot of time in development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker and Docker Compose:** For the containerized development environment.
- **Pyenv:** For managing Python versions if you choose to run the project locally without Docker.

## Local Development Setup

The primary guide for setting up and running the project (both with Docker and locally) is the main **[README.md](README.md)** file. Please follow the instructions there to get your environment up and running.

This guide will focus on the contribution workflow *after* your environment is set up.

## Pull Request Process

1. **Create a new branch** for your feature or bug fix:

    ```bash
    git checkout -b feature/your-feature-name
    ```

2. **Make your changes** and add or update tests as appropriate.
3. **Ensure the test suite passes** by running the test command inside the Docker container:

    ```bash
    make test
    ```

4. **Format your code**. The project uses `ruff` for formatting and linting. You can run it with:

    ```bash
    make format
    make lint
    ```

5. **Commit your changes** with a clear and descriptive commit message.
6. **Push your branch** to your fork on GitHub:

    ```bash
    git push origin feature/your-feature-name
    ```

7. **Open a pull request** to the `main` branch of the original repository.
8. **Clearly describe your pull request**, including the problem it solves and the changes you've made. Link to any relevant issues.

## Licensing

By contributing to this project, you agree that your contributions will be licensed under its [Apache 2.0 License](../LICENSE).

Thank you again for your contribution!
