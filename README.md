# Enterprise Agentic RAG

A modular, production-ready framework for building enterprise-grade Retrieval-Augmented Generation (RAG) applications with **FastAPI**, **LangGraph**, and managed cloud services.

[![Python](https://img.shields.io/badge/python-3.11.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1.10-purple.svg)](https://langchain-ai.github.io/langgraph/)

---

## Overview

Enterprise teams need assistants that answer technical questions grounded in internal documentation — not generic LLM responses. This project delivers a **domain-focused RAG API** that retrieves context from a vector store, reranks results, and synthesizes answers through an agentic LangGraph workflow.

The system is built for **Kubernetes, Intel hardware, and enterprise networking** documentation. It combines:

- **NeMo Guardrails** for input safety (off-topic, jailbreak, and dialog flows)
- **LangGraph** for planner → retriever → responder orchestration
- **Qdrant** for vector search
- **Portkey** as an LLM gateway (routing, caching, and fallback configured in Portkey)
- **Groq** models for reasoning and guardrail classification
- **Jina AI** for embeddings and semantic reranking

A **Streamlit chat UI** and a separate **evaluation suite** (RAGAS metrics + guardrails tests) round out the developer experience. Production deployment targets **AWS ECS Fargate** via GitHub Actions.

---

## Features

### RAG & Agent Pipeline

- **LangGraph agent workflow** with three nodes: Planner, Retriever, and Responder
- **Conversational routing** — greetings and memory-only questions skip retrieval
- **Technical query routing** — planner refines the search query before retrieval
- **Vector search** via Qdrant (`query_points`, cosine similarity)
- **Semantic reranking** via Jina Reranker API (`jina-reranker-v3`, top 5 from 15 candidates)
- **Context-aware response generation** with conversation history and retrieved chunks
- **Portkey gateway caching** — cache hit status surfaced in the agent plan

### Safety & API

- **NeMo Guardrails** gate on `/query` (off-topic, jailbreak, greeting, farewell, capabilities flows)
- **Optional Bearer token auth** (`RAG_API_KEY`) on protected endpoints
- **Rate limiting** via SlowAPI — Redis-backed (Upstash) with in-memory fallback
- **Health endpoints** — `/health` (liveness) and `/ready` (dependency readiness)
- **Prometheus metrics** at `/metrics` (request counts, latency, guardrail blocks)

### Persistence & Observability

- **Postgres checkpointer** (Neon) for LangGraph conversation state, with in-memory fallback
- **Pydantic Logfire** distributed tracing (API, UI, ingestion, evals)
- **LangSmith** tracing when `LANGSMITH_API_KEY` is configured
- **Connection health checker** for Postgres, Redis, Qdrant, Portkey, Jina, Logfire, and LangSmith

### Document Ingestion

- **Multi-format loaders**: PDF (pypdf + pdfplumber fallback), HTML (BeautifulSoup), TXT, DOCX/PPTX (Unstructured)
- **Paragraph-based chunking** (default 1,500 characters)
- **Batch embedding** via Jina API with local fallback (`mixedbread-ai/mxbai-embed-large-v1`)
- **Qdrant indexing** with source metadata (`text`, `source`, `source_type`)
- **CLI ingestion**: `python -m app.ingestion.processor DATA --wipe`

### Frontend & Evaluation

- **Streamlit chat UI** (`ui/app.py`) with agent thought process, source chunks, and session memory
- **Eval suite** (`evals/app.py`) — golden dataset, live pipeline against `/query`, RAGAS metrics, guardrails precision/recall

### DevOps

- **Docker** multi-stage build with `uv` for dependency installation
- **docker-compose** — Qdrant, API, and UI services
- **GitHub Actions CI** — Ruff lint/format + pytest
- **GitHub Actions CD** — build/push to ECR, deploy to ECS Fargate

---

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    External Services                     │
                    │  Neon Postgres │ Upstash Redis │ Qdrant │ Portkey/Groq  │
                    │  Jina Embeddings/Reranker │ Logfire │ LangSmith         │
                    └─────────────────────────────────────────────────────────┘
                                              ▲
User ──► Streamlit UI ──► FastAPI API ────────┤
                              │               │
                              ▼               │
                         NeMo Guardrails      │
                              │               │
                              ▼               │
                         LangGraph Agent     │
                         ┌────┴────┐          │
                         │ Planner │          │
                         └────┬────┘          │
                    conversational?           │
                    ┌────yes───┴───no──┐      │
                    ▼                  ▼      │
               Responder          Retriever ──┤──► Qdrant + Jina Reranker
                    │                  │      │
                    └────────┬─────────┘      │
                             ▼                │
                        Responder ────────────┘──► Portkey → Groq LLM
                             │
                             ▼
                          Response
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Uvicorn, Pydantic Settings |
| **Agent framework** | LangGraph, LangChain |
| **Frontend** | Streamlit |
| **Vector database** | Qdrant |
| **Relational database** | Neon PostgreSQL (LangGraph checkpointer) |
| **Cache / rate limiting** | Upstash Redis |
| **LLM gateway** | Portkey AI |
| **LLMs** | Groq (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`) |
| **Embeddings** | Jina `jina-embeddings-v3` (1024-dim); fallback: `mixedbread-ai/mxbai-embed-large-v1` |
| **Reranker** | Jina `jina-reranker-v3` |
| **Guardrails** | NVIDIA NeMo Guardrails |
| **Observability** | Pydantic Logfire, LangSmith, Prometheus |
| **Ingestion** | pypdf, pdfplumber, BeautifulSoup, Unstructured |
| **Evaluation** | RAGAS, DeepEval (dev deps), custom guardrails eval |
| **Package manager** | uv |
| **Deployment** | Docker, AWS ECS Fargate, ECR, ALB, Secrets Manager |

---

## Project Structure

```
enterprise-grade-rag-applications/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entrypoint, lifespan, routers
│   ├── config.py                 # Pydantic settings (env validation)
│   ├── logging.py                # Request ID context helpers
│   ├── agents/
│   │   ├── graph.py              # LangGraph build + Postgres checkpointer
│   │   ├── state.py              # AgentState TypedDict
│   │   └── nodes/
│   │       ├── planner.py        # Intent routing / query refinement
│   │       ├── retriever.py      # Qdrant search + reranking
│   │       └── responder.py      # LLM synthesis via Portkey
│   ├── api/
│   │   ├── auth.py               # Bearer token verification
│   │   ├── rate_limit.py         # SlowAPI + Redis/in-memory limiter
│   │   ├── metrics.py            # Prometheus counters/histograms
│   │   └── routers/
│   │       ├── health.py         # /health, /ready
│   │       └── query.py          # POST /query
│   ├── gateway/
│   │   └── client.py             # Portkey / LangChain client factory
│   ├── guardrails/
│   │   ├── rails.py              # NeMo Guardrails init + gate
│   │   └── colang_rules.py       # Colang flows (off-topic, jailbreak, etc.)
│   ├── ingestion/
│   │   ├── processor.py          # Universal ingestion CLI
│   │   ├── chunking/splitter.py  # Paragraph-based chunker
│   │   └── loaders/              # PDF, HTML, TXT, Office parsers
│   └── services/
│       ├── health/connection_checker.py
│       └── retrieval/
│           ├── embedding.py      # Jina API + local fallback
│           ├── qdrant_service.py   # Vector search
│           └── ranking_service.py  # Jina reranker
├── ui/
│   ├── app.py                    # Primary Streamlit chat UI
│   └── st_cloud_ui.py            # Streamlit Cloud variant
├── evals/
│   ├── app.py                    # Streamlit eval dashboard
│   ├── pipeline.py               # Live /query runner
│   ├── metrics.py                # RAGAS metric experiments
│   ├── guardrails_eval.py        # Guardrails TP/TN/FP/FN scoring
│   └── golden_dataset.json       # Golden Q&A + guardrails test cases
├── tests/                        # pytest suite
├── DATA/                         # Sample documents (true_data, noisy_data)
├── docs/                         # AWS deployment & contributing guides
├── .aws/task-definitions/        # ECS task definition templates
├── .github/workflows/            # CI and CD pipelines
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

---

## How It Works

### Request lifecycle (`POST /query`)

1. **User question** arrives with optional `thread_id` for conversation memory.
2. **Rate limiter** checks the client IP (Redis or in-memory).
3. **API key** is verified when `RAG_API_KEY` is set.
4. **NeMo Guardrails** classifies the input. If a rail fires, the request returns immediately with a canned response — the LangGraph pipeline is skipped.
5. **LangGraph Planner** reads full conversation history and decides:
   - `CONVERSATIONAL` → skip retrieval, go to Responder
   - Refined search query → go to Retriever
6. **Retriever** embeds the query, searches Qdrant (15 results), reranks to top 5 via Jina.
7. **Responder** builds a prompt with technical context (up to ~25K chars) and conversation history, calls Portkey → Groq, and returns the answer.
8. **Postgres checkpointer** persists graph state keyed by `thread_id`.
9. **Response** includes `answer`, `thought_process`, `status`, and `sources`.

```
User Question
     │
     ▼
  Rate Limit + Auth
     │
     ▼
  NeMo Guardrails ──blocked──► Canned Response
     │ (pass)
     ▼
  LangGraph Planner
     │
     ├── CONVERSATIONAL ──► Responder (memory-only)
     │
     └── Technical Query
              │
              ▼
         Retriever
              │
              ├── Embed query (Jina / fallback)
              ├── Qdrant search (15 chunks)
              └── Jina rerank (top 5)
              │
              ▼
         Responder (Portkey → Groq)
              │
              ▼
         JSON Response
```

---

## Installation

### Prerequisites

- Python **3.11.12+** (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager
- Running instances or accounts for: Qdrant, Neon Postgres, Upstash Redis, Groq, Portkey, Jina AI

### Clone and install

```bash
git clone https://github.com/<your-org>/enterprise-grade-rag-applications.git
cd enterprise-grade-rag-applications

uv sync
```

For development (tests, linting, evals):

```bash
uv sync --extra dev
```

### Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and service URLs
```

### Ingest documents

Place documents under `DATA/` (subfolders like `true_data` and `noisy_data` are auto-detected), then run:

```bash
uv run python -m app.ingestion.processor DATA --wipe
```

This creates the Qdrant collection, chunks documents, embeds them, and upserts vectors.

### Run locally

**Terminal 1 — API:**

```bash
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — UI:**

```bash
uv run streamlit run ui/app.py --server.port 8501
```

Open `http://localhost:8501` for the chat UI. The API is at `http://localhost:8000`.

### Verify connections

```bash
uv run python -m app.services.health.connection_checker
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JINA_API_KEY` | Jina AI API key for embeddings and reranking | Yes |
| `GROQ_API_KEY` | Groq API key for guardrails LLM | Yes |
| `PORTKEY_API_KEY` | Portkey gateway API key | Yes |
| `PORTKEY_PRIMARY_CONFIG_ID` | Portkey saved config ID (`pc-...`) | Yes |
| `QDRANT_URL` or `QDRANT_CLUSTER_ENDPOINT` | Qdrant cluster URL | Yes |
| `NEON_DB_URL` | PostgreSQL connection string (Neon) for LangGraph checkpointer | Yes |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL | Yes |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token | Yes |
| `QDRANT_API_KEY` | Qdrant API key (omit for local Qdrant without auth) | No |
| `QDRANT_COLLECTION` | Qdrant collection name (default: `enterprise_rag`) | No |
| `RAG_API_KEY` | Bearer token for `/query` and `/graph`; omit to disable auth | No |
| `RATE_LIMIT_PER_MINUTE` | Max requests per IP per minute (default: `20`) | No |
| `STRICT_STARTUP` | Fail startup if any dependency check fails (default: `false`) | No |
| `PORTKEY_PRIMARY_SLUG` | Portkey virtual key slug (default: `rag-project`) | No |
| `PORTKEY_FALLBACK_SLUG` | Portkey fallback slug (default: `rag-project2`) | No |
| `GROQ_MODEL` | Main reasoning model (default: `llama-3.3-70b-versatile`) | No |
| `GROQ_MODEL_INSTANT` | Guardrails model (default: `llama-3.1-8b-instant`) | No |
| `JUDGE_GROQ_API_KEY` | Separate Groq key for eval judge LLM | No |
| `EMBEDDING_DIM` | Vector dimension (default: `1024`) | No |
| `JINA_MODEL` | Jina embedding model (default: `jina-embeddings-v3`) | No |
| `JINA_FALLBACK_MODEL` | Local fallback model (default: `mixedbread-ai/mxbai-embed-large-v1`) | No |
| `JINA_BATCH_SIZE` | Embedding batch size (default: `64`) | No |
| `CHUNK_SIZE` | Ingestion chunk size in characters (default: `1500`) | No |
| `LOGFIRE_TOKEN` | Pydantic Logfire token | No |
| `LOGFIRE_BASE_URL` | Logfire endpoint (auto-inferred for EU tokens) | No |
| `LANGSMITH_TRACING` | Enable LangSmith tracing (default: `true`) | No |
| `LANGSMITH_API_KEY` | LangSmith API key | No |
| `LANGSMITH_PROJECT` | LangSmith project name (default: `rag_scale_test`) | No |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint | No |
| `BACKEND_URL` | FastAPI URL for Streamlit UI (default: `http://localhost:8000`) | No |
| `JUDGE_GROQ` | Groq key for RAGAS eval judge (falls back to `GROQ_API_KEY`) | No |
| `LOGFIRE_IGNORE_NO_CONFIG` | Suppress Logfire config warnings (used in Docker/CI) | No |

---

## Running the Project

### Local development

```bash
# Start Qdrant locally (optional — or use Qdrant Cloud)
docker compose up qdrant -d

# Ingest documents
uv run python -m app.ingestion.processor DATA --wipe

# Run API + UI
uv run uvicorn app.main:app --reload --port 8000
uv run streamlit run ui/app.py --server.port 8501

# Run eval suite (requires running API)
uv run streamlit run evals/app.py
```

### Docker

```bash
cp .env.example .env   # configure all required keys

docker compose up --build
```

| Service | Port | Description |
|---------|------|-------------|
| `qdrant` | 6333, 6334 | Local vector database |
| `api` | 8000 → 8080 | FastAPI backend |
| `ui` | 8501 | Streamlit chat UI |

The API container reads secrets from `.env`. Map `QDRANT_URL` to `http://qdrant:6333` when using the bundled Qdrant service.

### Production (AWS ECS Fargate)

Production deployment uses:

- **ECR** for container images
- **ECS Fargate** for `rag-api` and `rag-ui` services
- **Secrets Manager** for credentials
- **Managed services**: Qdrant Cloud, Neon Postgres, Upstash Redis

See [docs/aws.md](docs/aws.md) and [docs/AWS_ECS_Fargate_Deployment_Documentation.md](docs/AWS_ECS_Fargate_Deployment_Documentation.md) for full infrastructure setup. CD runs automatically after successful CI on `main` or `deployment`, or via manual workflow dispatch.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | No | API status message |
| `GET` | `/health` | No | Liveness probe — returns `{"status": "ok"}` |
| `GET` | `/ready` | No | Readiness probe — checks Postgres, Redis, Qdrant, Portkey, Jina, Logfire, LangSmith |
| `POST` | `/query` | Bearer (if `RAG_API_KEY` set) | Run the RAG pipeline |
| `GET` | `/graph` | Bearer (if `RAG_API_KEY` set) | Return LangGraph workflow as PNG (Mermaid) |
| `GET` | `/metrics` | No | Prometheus metrics (excluded from OpenAPI schema) |

### `POST /query`

**Request body:**

```json
{
  "q": "How do you start Redis for a Kubernetes work queue?",
  "thread_id": "default_user"
}
```

**Response (success):**

```json
{
  "question": "...",
  "answer": "...",
  "thought_process": ["Start", "Intent: Technical", "Search Term: ...", "Context Retrieved"],
  "status": "Response generated.",
  "sources": ["CONTENT: ..."]
}
```

**Response (guardrails block):**

```json
{
  "question": "...",
  "answer": "I'm an Enterprise IT Assistant...",
  "thought_process": ["Intent: Guardrails Fired", "Retrieval: Skipped"],
  "status": "Blocked by guardrails.",
  "sources": []
}
```

When `RAG_API_KEY` is configured, include the header:

```
Authorization: Bearer <your-api-key>
```

---

## AI Pipeline

### Embedding model

- **Primary**: Jina `jina-embeddings-v3` (1024 dimensions, normalized, task-specific: `retrieval.query` / `retrieval.passage`)
- **Fallback**: Local `mixedbread-ai/mxbai-embed-large-v1` via Sentence Transformers when the Jina API is unavailable

### Chunking

- Paragraph-based splitter (`\n\n` boundaries)
- Default chunk size: **1,500 characters**
- Chunks stored in Qdrant with payload fields: `text`, `source`, `source_type`

### Retrieval

1. Query embedded via active embedding provider
2. Qdrant `query_points` with cosine distance — **15 candidates**
3. Payload `text` extracted from results

### Reranking

- **Jina Reranker v3** API re-scores the 15 candidates
- Returns **top 5** most relevant chunks
- Falls back to original Qdrant order if reranking fails or `JINA_API_KEY` is missing

### Prompt construction

- **Conversational path**: conversation history + latest user message
- **RAG path**: reranked context (truncated to ~25K chars) + conversation history + user question
- Responder uses the native Portkey client to read `x-portkey-cache-status`

### LLM

- **Planner**: Portkey → `@PORTKEY_PRIMARY_SLUG/llama-3.3-70b-versatile` via LangChain `ChatOpenAI`
- **Guardrails**: Direct Groq `llama-3.1-8b-instant` via `ChatGroq`
- **Responder**: Portkey → `@PORTKEY_PRIMARY_SLUG/llama-3.3-70b-versatile` with retry (3 attempts, exponential backoff)

### Response generation

Final answer is stored in graph state as `final_answer` and appended to the message history for subsequent turns within the same `thread_id`.

---

## Data Flow

### Ingestion

```
Document (PDF/HTML/TXT/DOCX/PPTX)
        │
        ▼
   Format-specific parser
        │
        ▼
   Paragraph chunker (1500 chars)
        │
        ├──► processed_data/<source_type>/*.json  (local metadata)
        │
        ▼
   Jina embeddings (batched)
        │
        ▼
   Qdrant upsert (uuid point IDs)
```

### Query

```
User query
    │
    ▼
Guardrails (Groq 8B)
    │
    ▼
Planner (Portkey/Groq 70B) ──► refined query or CONVERSATIONAL
    │
    ▼
Embed query (Jina) ──► Qdrant search ──► Jina rerank
    │
    ▼
Responder (Portkey/Groq 70B) ──► answer + sources
    │
    ▼
Postgres checkpointer (thread state)
```

---

## Screenshots

> Screenshots are not included in the repository. Add images here after capturing:
>
> - Streamlit chat UI (`ui/app.py`)
> - Agent thought process and source chunks panel
> - Eval suite dashboard (`evals/app.py`)
> - LangGraph workflow (`GET /graph`)

<!-- 
![Chat UI](docs/images/chat-ui.png)
![Eval Suite](docs/images/eval-suite.png)
-->

---

## Future Improvements

These are realistic extensions based on the current architecture — none are implemented yet:

- Async `/query` endpoint using the existing `get_async_openai_client`
- Wire Streamlit UI to send `RAG_API_KEY` when auth is enabled
- Remove unused `flashrank` dependency or integrate it as a reranker fallback
- Expand golden dataset coverage beyond the current enterprise document set
- Add structured citation metadata (source filenames) in API responses instead of raw `CONTENT:` prefixes
- Helm/Kubernetes manifests for self-hosted deployment alongside ECS

---

## Contributing

This project follows [Conventional Commits](https://www.conventionalcommits.org/). See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for commit message format, scopes, and examples.

```bash
# Lint
uv run ruff check app tests evals
uv run ruff format --check app tests evals

# Test
uv run pytest tests/
```

---

## License

License not specified.
