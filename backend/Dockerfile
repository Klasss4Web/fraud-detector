FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential libffi-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install poetry

# 1. Copy BOTH files. If poetry.lock is missing, poetry install will fail.
# If you don't have a lock file yet, run 'poetry lock' locally first.
COPY pyproject.toml poetry.lock* ./

# 2. Key Change: Use --no-root
# This installs only the dependencies and avoids the 'Package not found' error
RUN poetry install --no-root --no-ansi

# 3. Now copy the source code
COPY . .

# 4. Final install to verify the root project
RUN poetry install --no-ansi

EXPOSE 8000

CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]