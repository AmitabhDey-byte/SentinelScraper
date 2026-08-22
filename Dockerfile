FROM node:22-bookworm-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && npm install --global @brightdata/cli

COPY backend ./backend
COPY scripts ./scripts

EXPOSE 10000
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-10000}"]
