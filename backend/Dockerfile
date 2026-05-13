# Change from 3.10 to 3.12 to match your project requirements
FROM python:3.12-slim

# 1. Environment setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app

WORKDIR /app

# 2. Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Poetry
RUN pip install poetry

# 4. Copy dependency file
COPY pyproject.toml ./

# 5. Install dependencies 
# Since you have no lock file, Poetry will resolve them now
RUN poetry install --only main --no-root --no-ansi

# 6. Copy the rest of the code
COPY . .

EXPOSE 8000

# CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]