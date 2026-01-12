# 1440 Bot - Multimodal RAG for Technical Manuals

This project ingests technical manuals (PDF) from SharePoint, stores text/images + embeddings in Qdrant, and answers technician questions with interleaved text and SAS-image markdown via OpenAI GPT-5.2. It includes a Streamlit chat UI for demo.

---

## What You Get
- **Ingestion**: Fetch PDFs from SharePoint, parse text + images (Docling), upload images to Azure Blob with SAS URLs, store markdown + embeddings in Qdrant.
- **Retrieval**: Hybrid text search over markdown with SAS URLs; small docs inject full markdown.
- **Inference**: OpenAI GPT-5.2 (responses API, multimodal) with low-detail vision to reduce cost; retries + long timeout.
- **UI**: Streamlit chat that renders interleaved text+image markdown.
- **Wrappers/CLI**: Simple entrypoints for ingest and QA.

---

## Prerequisites
1) **Python**: 3.10+ (project uses uv/pyproject).  
2) **System packages**: `python3-dev`, `build-essential`, `poppler-utils` (for PDFs), `libmagic1`.  
3) **Accounts/Keys**:
   - Azure AD app (tenant/client/secret) and SharePoint site/drive IDs.
   - Azure Blob Storage connection string + account key.
   - Qdrant (self-hosted or cloud) URL/API key.
   - OpenAI API key (GPT-5.2).  
4) **Access**: SharePoint library with PDFs; Azure storage container (will create if missing).

---

## Quick Start (Fresh Machine, uv-based)
```bash
# 1) Install uv (self-contained Python/packaging tool)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Ensure ~/.local/bin is on PATH (or follow installer output)

# 2) Clone
git clone https://github.com/harish-bodduna/Assistant_Bot.git
cd Assistant_Bot

# 3) Create virtualenv (managed by uv)
uv venv 1440_env
source 1440_env/bin/activate

# 4) Install deps from pyproject
uv pip install -r <(python - <<'PY'
import tomllib,sys;data=tomllib.load(open("pyproject.toml","rb"))
deps=data["project"]["dependencies"];print("\n".join(deps))
PY)

# 5) Copy env template
cp env.example .env
# Edit .env with your real values (see next section)
```

---

## Configure Environment (.env)
Open `.env` and fill every value (no blanks). Key variables:
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- `SHAREPOINT_SITE_ID`, `SHAREPOINT_DRIVE_ID` (or drive name in settings), `SHAREPOINT_FOLDER_PATH`
- `AZURE_STORAGE_CONNECTION_STRING` (or `AZURE_STORAGE_KEY`)
- `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_VISUAL`, `QDRANT_COLLECTION_TEXT`
- `OPENAI_API_KEY`, `OPENAI_API_BASE` (leave blank for api.openai.com)
- `VLLM_BASE_URL` (optional fallback; currently disabled)

When done:
```bash
set -a && source .env && set +a
```

---

## Ingestion: Index a PDF from SharePoint
This uses the wrapper to pull a PDF from SharePoint, parse, upload images to Azure, and upsert to Qdrant.
```bash
source 1440_env/bin/activate
set -a && source .env && set +a
python - <<'PY'
from src.wrappers.ingest_service import ingest_one

# ingest_one() auto-picks the first PDF in the configured SharePoint folder
res = ingest_one()
print(res)
PY
```
Expected: status ok, and files written under `markdown_exports/<doc_name>/` locally (for inspection) plus data in Qdrant and Azure.

---

## Ask a Question via Wrapper (Terminal)
```bash
source 1440_env/bin/activate
set -a && source .env && set +a
python - <<'PY'
from src.wrappers.qa_service import answer_question
res = answer_question("What is the backup retention policy and schedule?")
print(res["answer_markdown"])
PY
```
If you see “OpenAI primary error: Request timed out,” retry; the code has 3 attempts, 5-min timeout each.

---

## Run the Streamlit Chat UI
```bash
source 1440_env/bin/activate
set -a && source .env && set +a
streamlit run ui/chat.py --server.port 8501
```
Open http://localhost:8501. Enter a question; answers render with interleaved text and SAS images. If OpenAI is slow, you’ll see “Still waiting on OpenAI…”.

---

## Project Structure (Key Files)
- `src/text_indexing/` — parsing (Docling), step building, markdown rendering, storage (Azure), Qdrant writer.
- `src/retrieval/multimodal_service.py` — hybrid search + multimodal inference (Responses API, GPT-5.2).
- `src/orchestration/agent.py` — agent wiring (OpenAI model selection).
- `src/wrappers/` — thin service wrappers: ingest, QA, agent.
- `ui/chat.py` — Streamlit chat demo.
- `tests/` — basic sanity tests.
- `env.example` — template for `.env`.
- `markdown_exports/` — local exports of parsed manuals and answers (ignored by git).

---

## Notes on Costs and Performance
- Vision is set to `detail="low"` to reduce per-image tokens.
- Prompt ordering is cache-friendly (system + context prefix, query last).
- Retries: 3 attempts, 3s backoff, 5-minute timeout per attempt.

---

## Qdrant (Docker Quick Start)
Run Qdrant locally with Docker:
```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  qdrant/qdrant:v1.9.2
```
Then set in `.env`:
```
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=   # leave blank unless you configure auth
```

---

## Troubleshooting
- **Push blocked (secrets)**: `.env` is ignored; never commit real keys. If blocked, remove secrets from history and push again.
- **OpenAI timeouts**: Try again; ensure network allows outbound to api.openai.com; check key validity.
- **Qdrant not reachable**: Verify `QDRANT_URL`/`QDRANT_API_KEY`, and that the service is running.
- **SharePoint fetch fails**: Re-check tenant/app creds and site/drive IDs; ensure the PDF exists in `SHAREPOINT_FOLDER_PATH`.
- **Streamlit shows no images**: Ensure `answer_markdown` is rendered; refresh after long waits; network must allow blob URLs.

---

## Streamlit (Chat UI) Quick Start
```bash
cd /home/stormy/dev-workspace/projects/1440_Bot
source 1440_env/bin/activate
set -a && source .env && set +a
streamlit run ui/chat.py --server.port 8501
```
Open: http://localhost:8501 (or your host IP:8501). If you see “Still waiting on OpenAI…”, the backend may be retrying; try again after a moment.

---

## Optional: Clean Up Local Artifacts
`markdown_exports/` can be large; it’s git-ignored. Safe to delete locally:
```bash
rm -rf markdown_exports/*
```

---

## One-Command Env Load (per shell)
```bash
source 1440_env/bin/activate && set -a && source .env && set +a
```

That’s it—fill `.env`, ingest once, then ask questions via wrappers or Streamlit. Happy debugging! 

