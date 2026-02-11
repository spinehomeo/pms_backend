FROM python:3.12
ENV PYTHONUNBUFFERED=1

# Use the repository root as the working directory
WORKDIR /

# Install uv tooling from the official uv image (copies /uv and /uvx into /bin)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Ensure virtualenv executables (created by uv) are first in PATH
ENV PATH="/.venv/bin:$PATH"

# uv settings
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency manifests first to leverage Docker cache
COPY pyproject.toml uv.lock alembic.ini /

# Install dependencies using uv. NOTE: these RUNs use BuildKit mount features.
# Build command requires BuildKit enabled (DOCKER_BUILDKIT=1) when building.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=/uv.lock,readonly \
    uv sync --frozen --no-install-project

# Copy application source into the image root
COPY ./ /

# Final sync to ensure environment reflects project (uses cache for speed)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Expose the port the app will listen on
EXPOSE 8000

# Runtime command: run the FastAPI app using Uvicorn. The FastAPI app object
# is defined in `main.py` at the repository root as `app`.
CMD ["uvicorn", "pms_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
