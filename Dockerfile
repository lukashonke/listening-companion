# ── Stage 1: Build frontend ───────────────────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Backend runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS backend

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/backend
COPY backend/pyproject.toml ./
COPY backend/.python-versi[on] ./
RUN uv sync --no-dev

COPY backend/ ./

# Copy built frontend into the location backend expects
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

ENV FRONTEND_DIST=/app/frontend/dist
ENV DATABASE_PATH=/data/listening_companion.db

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
