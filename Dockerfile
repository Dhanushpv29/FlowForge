FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies and the package first so this layer is cached between code edits.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic ./alembic
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 flowforge
USER flowforge

EXPOSE 8000
CMD ["uvicorn", "flowforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
