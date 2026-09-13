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

# Bake the model2vec query-embedder into the image cache so grounding + generation embed queries
# fully offline at runtime (HF_HUB_OFFLINE=1 below) — no HuggingFace call on the query path.
RUN python -c "from model2vec import StaticModel; StaticModel.from_pretrained('minishlab/potion-retrieval-32M')"

# The web front-end. The SQLite DBs (study_bible.db, theology.db) are NOT baked in — they are
# distributed via R2 and boot-fetched to the Fly volume (/data) by webapp.app._ensure_r2_dbs,
# which keeps the image small and deploys fast.
COPY webapp ./webapp

# Runtime data the web app reads from the project root:
#   resource-generators.yaml  -> generator.py loads it at import (boot-critical)
#   docs/                     -> the /course and /calendar views read the John
#                                lessons, materials, and calendar JSON from here
COPY resource-generators.yaml ./resource-generators.yaml
COPY docs ./docs

ENV STUDY_BIBLE_DB=/data/study_bible.db \
    PORT=8100 \
    PYTHONUNBUFFERED=1
# ANTHROPIC_API_KEY is provided at deploy time as a secret, never baked in.

EXPOSE 8100
CMD ["sh", "-c", "python -m uvicorn webapp.app:app --host 0.0.0.0 --port ${PORT}"]
