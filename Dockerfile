# Study Bible web app — a single stateless container: the Python backend runs
# the Claude tool-use loop and co-locates the MCP server (spawned over stdio),
# with the prebuilt read-only SQLite baked in. Deploy to a container host
# (Cloudflare Containers / Render / Railway); put a user-auth proxy in front.
FROM python:3.12-slim

WORKDIR /app

# Install the package with the web-app extra.
COPY pyproject.toml README.md NOTICE LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[webapp]"

# Bake in the prebuilt database (read-only at runtime) and the web front-end.
COPY db/study_bible.db ./db/study_bible.db
COPY webapp ./webapp

ENV STUDY_BIBLE_DB=/app/db/study_bible.db \
    PORT=8100 \
    PYTHONUNBUFFERED=1
# ANTHROPIC_API_KEY is provided at deploy time as a secret, never baked in.

EXPOSE 8100
CMD ["sh", "-c", "python -m uvicorn webapp.app:app --host 0.0.0.0 --port ${PORT}"]
