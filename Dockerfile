FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies only (no dev dependencies for production)
RUN poetry install --no-root --no-dev --no-interaction

# Copy application code
COPY . .

# Install the project
RUN poetry install --only-root --no-interaction

EXPOSE 8001

CMD ["python", "-m", "app.mcp.server"]
