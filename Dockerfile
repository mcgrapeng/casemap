FROM python:3.11-slim

# ponytail: uv in its own layer keeps the app layer small when only src
# changes; rebuilding a 12 MB base image every commit would be wasteful.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install deps first so src-only changes don't re-resolve the lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY examples ./examples

EXPOSE 8765

CMD ["uv", "run", "casemap", "serve", "--host", "0.0.0.0", "--port", "8765"]