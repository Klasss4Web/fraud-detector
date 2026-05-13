FROM python:3.10-slim

# 1. Environment setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 2. Install system tools and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && \
    pip install poetry && \
    rm -rf /var/lib/apt/lists/*

# 3. Copy only the pyproject.toml
COPY pyproject.toml ./

# 4. EXPORT AND INSTALL
# We tell poetry to ignore the missing lock file and just install 
# what's in the pyproject.toml directly into the system python.
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root --only main

# 5. Copy the rest of your code
COPY . .

# 6. Final check: Ensure src is in the python path
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]