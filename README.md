# 🛡️ Agentic Enterprise Knowledge Copilot

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=flat)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-Production--Ready-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector--DB-DC2626?style=flat)](https://qdrant.tech)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-Caching-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub--Actions-2088FF?style=flat&logo=githubactions&logoColor=white)](.github/workflows/ci.yml)

> **Production-grade GenAI Multi-Agent Copilot over enterprise unstructured documents, relational operational databases, and live external APIs with hybrid retrieval, security guardrails, LangSmith observability, streaming SSE, and automated RAGAS/DeepEval evaluation gating.**

---

## 📌 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [System Architecture Diagram](#-system-architecture-diagram)
- [Key Features](#-key-features)
  - [1. Multi-Agent Orchestration (LangGraph)](#1-multi-agent-orchestration-langgraph)
  - [2. Hybrid Retrieval & Cross-Encoder Reranking](#2-hybrid-retrieval--cross-encoder-reranking)
  - [3. Zero-Trust SQL Agent](#3-zero-trust-sql-agent)
  - [4. Defense-in-Depth Guardrails](#4-defense-in-depth-guardrails)
  - [5. Full-Stack Observability & Cost Auditing](#5-full-stack-observability--cost-auditing)
  - [6. Real-Time Streaming SSE](#6-real-time-streaming-sse)
  - [7. Enterprise Caching Layer](#7-enterprise-caching-layer)
- [Automated Evaluation Framework (RAGAS / DeepEval)](#-automated-evaluation-framework-ragas--deepeval)
- [Directory Structure](#-directory-structure)
- [API Reference](#-api-reference)
- [Quickstart & Local Setup](#-quickstart--local-setup)
- [Docker Deployment](#-docker-deployment)
- [Production Cloud Deployment (AWS & GCP)](#-production-cloud-deployment-aws--gcp)
- [CI/CD Pipeline & Evaluation Gate](#-cicd-pipeline--evaluation-gate)
- [Verification & Testing](#-verification--testing)

---

## 🏗️ Architectural Overview

Standard naive RAG systems suffer from three major production bottlenecks:
1. **Uncertainty in Intent**: Inability to differentiate between qualitative document synthesis, quantitative database metrics, or external tool execution.
2. **Retrieval Blindspots**: Dense embeddings miss precise lexical identifiers (such as product codes, medical terms, and filing clauses), while BM25 misses semantic nuance.
3. **Hallucination & Vulnerabilities**: Susceptibility to prompt injections, lack of strict source verification, and absent observability over per-query latency and token costs.

The **Agentic Enterprise Knowledge Copilot** addresses these issues with an end-to-end, multi-agent architecture built on **LangGraph**, **FastAPI**, **Qdrant**, **PostgreSQL**, and **Redis**.

```
                           ┌────────────────────────┐
                           │    User Request / UI   │
                           └───────────┬────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │    Redis / In-Memory Cache Check  │
                     └───────┬───────────────────┬───────┘
                     HIT     │                   │ MISS
             ┌───────────────┘                   └──────────────┐
             ▼                                                  ▼
┌─────────────────────────┐                   ┌───────────────────────────────────┐
│ Return Cached Response  │                   │ Pre-Execution Guardrails Node     │
│ (<5ms Latency)          │                   │ - Prompt Injection Detection      │
└─────────────────────────┘                   │ - Off-Topic Boundary Enforcement │
                                              │ - PII Masking                     │
                                              └─────────────────┬─────────────────┘
                                                                │ PASSED
                                                                ▼
                                              ┌───────────────────────────────────┐
                                              │   Intelligent Router Agent        │
                                              └─────┬───────────┬───────────┬─────┘
                                                    │           │           │
                    ┌───────────────────────────────┘           │           └──────────────────────────┐
                    ▼                                           ▼                                      ▼
     ┌─────────────────────────────┐             ┌─────────────────────────────┐        ┌─────────────────────────────┐
     │      Hybrid RAG Agent       │             │       Zero-Trust SQL        │        │      Tool Dispatcher        │
     │  - Dense: sentence-xfmrs    │             │  - NL-to-SQL Generator      │        │  - Open-Meteo Weather API   │
     │  - Sparse: BM25 (tokenized) │             │  - AST & Regex Validator    │        │  - Parameter Validation     │
     │  - Reciprocal Rank Fusion   │             │  - Read-Only Enforcement    │        └──────────────┬──────────────┘
     │  - Cross-Encoder Reranker   │             │  - Whitelist & Auto-LIMIT   │                       │
     └──────────────┬──────────────┘             └──────────────┬──────────────┘                       │
                    │                                           │                                      │
                    ▼                                           │                                      │
     ┌─────────────────────────────┐                            │                                      │
     │   LLM Generation & Grounding│                            │                                      │
     │  - Source [Source N] check  │                            │                                      │
     │  - Citation Normalization   │                            │                                      │
     └──────────────┬──────────────┘                            │                                      │
                    │                                           │                                      │
                    └───────────────────────────┬───────────────┴──────────────────────────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │   Observability & Cost Auditor  │
                               │   - LangSmith Distributed Trace │
                               │   - Token Counting & Cost (USD) │
                               │   - Latency Spans & Metrics     │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │ Streaming SSE / JSON Response   │
                               └─────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. Multi-Agent Orchestration (LangGraph)
- Built on a stateful **LangGraph** `StateGraph`.
- Modular routing mechanism that safely inspects queries and routes them to:
  - **`rag`**: Unstructured guideline, policy, and document search.
  - **`sql`**: Enterprise analytics over relational PostgreSQL tables.
  - **`tool`**: Live enterprise API tools (e.g. telemetry, external weather).
  - **`direct`**: Conversational system capabilities and operational greetings.
  - **`refusal`**: Deterministic termination when safety guardrails are violated.

### 2. Hybrid Retrieval & Cross-Encoder Reranking
- **Dense Vector Retrieval**: High-dimensional semantic search powered by `sentence-transformers` (`all-MiniLM-L6-v2`) indexed in **Qdrant**.
- **Sparse Lexical Retrieval**: Exact keyword precision via **BM25** (`rank-bm25`).
- **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse ranks dynamically ($RRF_{score} = \sum \frac{1}{k + rank_i}$).
- **Cross-Encoder Reranker**: Employs `cross-encoder/ms-marco-MiniLM-L-6-v2` to score candidate query-document pairs, eliminating semantic false-positives before context injection.
- **Strict Grounding & Citation Validation**: Forces citations in the format `[Source N]`, validates citations against actually retrieved chunks, and automatically suppresses ungrounded answers.

### 3. Zero-Trust SQL Agent
- Natural language to PostgreSQL translation for corporate schemas (`users`, `customer_profiles`, `documents`, `approval_requests`).
- **Pre-execution SQL Firewall**:
  - Rejects all mutating queries (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, etc.).
  - Blocks system catalog discovery (`information_schema`, `pg_catalog`, `pg_toast`).
  - Table whitelisting: only explicitly authorized enterprise tables are accessible.
  - Prohibits unbounded `SELECT *` queries.
  - Automatically appends `LIMIT 100` to non-aggregate queries to prevent query exhaustion attacks.

### 4. Defense-in-Depth Guardrails
- **Prompt Injection & Jailbreak Detector**: Intercepts direct instruction overrides ("ignore previous instructions", "act as DAN", delimiter injection like `<|im_start|>`, `### instruction`, system exfiltration).
- **Topic Boundary Guard**: Rejects queries requesting creative fiction, malicious scripts, personal entertainment, or irrelevant activities outside authorized enterprise scope.
- **PII Masking**: Automatically detects and redacts emails, SSNs, credit card numbers, and phone numbers before ingestion into the agent state.

### 5. Full-Stack Observability & Cost Auditing
- **Distributed Tracing**: Native support for **LangSmith** (`LANGCHAIN_TRACING_V2=true`).
- **Granular Latency Spans**: Millisecond breakdown across cache checks, guardrails, routing, vector search, reranking, and generation.
- **Token & Cost Tracking**: Live estimation of prompt tokens, completion tokens, and real-time query cost calculation in USD based on model pricing ($0.075 / 1M prompt, $0.30 / 1M completion).
- **Metrics Endpoint**: `/api/v1/metrics` exposes rolling latency averages, cache hit ratios, routing distributions, and total cumulative costs.

### 6. Real-Time Streaming SSE
- The `/api/v1/query/stream` endpoint streams **Server-Sent Events (SSE)** in real time:
  - `event: status` — Real-time progress updates.
  - `event: route` — Transparent router decisions and reasoning.
  - `event: sources` — Number of relevant enterprise documents retrieved.
  - `event: token` — Progressive word tokens delivered to UI.
  - `event: citations` — Verified citation index references.
  - `event: done` — Full trace ID, total latency in ms, and token usage summary.

### 7. Enterprise Caching Layer
- Primary **Redis** key-value caching with SHA-256 hashed query keys and configurable TTL (default: 3600s).
- **Graceful Degradation**: Automatically falls back to an internal high-performance in-memory TTL cache if Redis is unavailable, ensuring zero downtime.

---

## 📊 Automated Evaluation Framework (RAGAS / DeepEval)

To guarantee production quality and prevent regressions, the copilot includes an automated evaluation suite running on a **50-sample golden enterprise benchmark dataset** (`app/evaluation/golden_dataset.json`).

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Router Accuracy** | `>= 90.0%` | Correct routing across RAG, SQL, Tool, and Direct categories. |
| **Faithfulness (Groundedness)** | `>= 85.0%` | Percentage of generated claims directly supported by retrieved context passages. |
| **Answer Relevance** | `>= 80.0%` | Semantic cosine similarity between the user question and the final response. |
| **Context Precision (MAP@K)** | `>= 75.0%` | Mean Average Precision of ground-truth relevant passages in top retrieval ranks. |
| **Guardrail Safety Accuracy** | `>= 95.0%` | Interception rate for adversarial prompt injections and off-topic queries. |

### Running Evals Locally

```bash
# Evaluate golden set with regression thresholds
python scripts/run_evals.py --limit 20 --threshold-router 0.85 --threshold-guardrail 0.90
```

Evaluation outputs are formatted as:
- Markdown report: `eval_results/evaluation_report.md`
- Machine-readable JSON: `eval_results/evaluation_report.json`

---

## 📂 Directory Structure

```
agentic-enterprise-copilot/
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated CI test & eval regression gate
├── app/
│   ├── agents/
│   │   ├── graph.py             # LangGraph StateGraph, router, RAG node, citations
│   │   └── sql_agent.py         # NL-to-SQL generator & safe runner
│   ├── api/
│   │   └── routes.py            # FastAPI endpoints (/query, /stream, /health, /metrics)
│   ├── cache/
│   │   └── redis_cache.py       # Redis cache with in-memory TTL fallback
│   ├── database/
│   │   ├── postgres.py          # PostgreSQL connection & pool management
│   │   └── sql_executor.py      # Zero-trust read-only SQL validation engine
│   ├── evaluation/
│   │   ├── evaluator.py         # RAGAS / DeepEval metric evaluator
│   │   └── golden_dataset.json  # 50-sample golden evaluation benchmark set
│   ├── guardrails/
│   │   ├── guardrail_manager.py # Central guardrail orchestrator
│   │   ├── injection_detector.py# Regex & heuristic prompt injection detector
│   │   ├── pii_masker.py        # PII regex masking engine
│   │   └── topic_guard.py       # Enterprise topic boundary enforcer
│   ├── ingestion/
│   │   ├── chunker.py           # Document chunking with metadata
│   │   └── pdf_extractor.py     # PyMuPDF PDF parser
│   ├── llm/
│   │   └── gemini.py            # Gemini client wrapper & prompt templates
│   ├── observability/
│   │   └── tracer.py            # Trace recorder, cost calculator, LangSmith hook
│   ├── retrieval/
│   │   ├── bm25.py              # BM25 sparse indexer & search
│   │   ├── embeddings.py        # Sentence-transformers embedding wrapper
│   │   ├── indexer.py           # Vector & BM25 ingestion coordinator
│   │   ├── reranker.py          # Cross-encoder candidate reranker
│   │   ├── search.py            # Hybrid search & Reciprocal Rank Fusion (RRF)
│   │   └── vector_store.py      # Qdrant client & collection management
│   ├── tools/
│   │   ├── base.py              # Tool abstract base class
│   │   ├── registry.py          # Dynamic tool registration
│   │   └── weather.py           # Open-Meteo external weather tool
│   ├── config.py                # Pydantic v2 application settings
│   └── main.py                  # FastAPI application entrypoint
├── data/
│   └── raw/                     # Raw enterprise PDFs & documents
├── docker/
│   └── init.sql                 # PostgreSQL enterprise schema & sample seed data
├── docker-compose.yml           # Full multi-container Docker compose
├── Dockerfile                   # Multi-stage production container build
├── eval_results/                # Benchmark evaluation reports (.md, .json)
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Locked project dependencies
├── scripts/                     # Operational verification & test scripts
└── tests/
    ├── test_api.py              # API endpoint integration tests
    ├── test_citations.py        # Citation normalization & grounding tests
    └── test_evaluation.py       # Evaluation metric unit tests
```

---

## 🔌 API Reference

### 1. `POST /api/v1/query` — Synchronous Query
Executes the full agent graph with caching, guardrails, routing, grounding, and trace auditing.

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Fasting Plasma Glucose threshold for diabetes diagnosis?"}'
```

**Response (`200 OK`):**
```json
{
  "query": "What is the Fasting Plasma Glucose threshold for diabetes diagnosis?",
  "route": "rag",
  "response": "According to the guideline, Fasting Plasma Glucose (FPG) >= 126 mg/dL confirms diagnosis [Source 1].",
  "citations": [1],
  "sources": [
    {
      "source_number": 1,
      "filename": "01_Diabetes_Clinical_Guideline.pdf",
      "page": 2,
      "score": 0.892
    }
  ],
  "sql": null,
  "trace_id": "8f7b2c91-9a3d-4c3e-821b-6cb7f015b61e",
  "latency_ms": 342.15,
  "tokens_used": 184,
  "cached": false,
  "guardrail_status": "passed"
}
```

### 2. `POST /api/v1/query/stream` — Real-Time SSE Stream
Streams sub-agent lifecycle states, router decisions, source discovery, tokens, and verified citations.

```bash
curl -N -X POST "http://localhost:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "How many users are in the database?"}'
```

**SSE Events Output:**
```
event: status
data: {"message": "Executing security guardrails & query router..."}

event: route
data: {"route": "sql", "reasoning": "Detected structured relational database analytics query"}

event: token
data: {"token": "Database query result "}

event: token
data: {"token": "(count): 5 "}

event: done
data: {"trace_id": "0d1808fb-...", "latency_ms": 28.4, "tokens_used": 68, "cached": false}
```

### 3. `GET /api/v1/health` — Deep Health Probe
Validates connectivity across PostgreSQL, Qdrant vector store, and Redis cache.

```bash
curl "http://localhost:8000/api/v1/health"
```

### 4. `GET /api/v1/metrics` — Observability & Token Cost Metrics
```bash
curl "http://localhost:8000/api/v1/metrics"
```

**Sample Metrics Output:**
```json
{
  "observability": {
    "total_queries": 45,
    "avg_latency_ms": 112.4,
    "total_tokens_consumed": 12840,
    "total_cost_usd": 0.003182,
    "cache_hit_ratio": 0.3556,
    "route_distribution": {
      "rag": 24,
      "sql": 12,
      "direct": 6,
      "blocked": 3
    }
  },
  "cache": {
    "backend": "redis",
    "hits": 16,
    "misses": 29,
    "total_requests": 45,
    "hit_ratio": 0.3556
  }
}
```

### 5. `POST /api/v1/documents/upload` — Ingest & Index PDF Document
Uploads an enterprise PDF document, extracts text using PyMuPDF, chunks content, generates dense vectors, and updates both Qdrant and the BM25 index.

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@path/to/enterprise_document.pdf"
```

**Response (`200 OK`):**
```json
{
  "status": "success",
  "message": "Successfully ingested and indexed 'enterprise_document.pdf'",
  "document_id": "a91b8d27e4c3",
  "filename": "enterprise_document.pdf",
  "chunks_indexed": 24
}
```

### 6. `GET /api/v1/documents` — List Ingested Knowledge Base Documents
Lists all currently ingested and searchable documents in the knowledge base.

```bash
curl "http://localhost:8000/api/v1/documents"
```

---

## ⚡ Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Git
- Google Gemini API Key (`GEMINI_API_KEY`)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/your-username/agentic-enterprise-copilot.git
cd agentic-enterprise-copilot

python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your configuration:
```ini
ENVIRONMENT=development
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-2.5-flash

DATABASE_URL=postgresql://aegis_readonly:aegis_readonly_password@localhost:5432/aegisdb
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PREFER_MEMORY=true   # Allows local testing without running external Qdrant

REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true
GUARDRAILS_ENABLED=true

# Optional: LangSmith Observability
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=agentic-enterprise-copilot
```

### 3. Run the Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs).  
Interactive Web UI & Real-Time Telemetry Dashboard is available at: [http://localhost:8000/ui](http://localhost:8000/ui).

---

## 🐳 Docker Deployment

The system is containerized with a production multi-container `docker-compose.yml` including:
- **`app`**: FastAPI Agentic Copilot application.
- **`qdrant`**: Qdrant vector database on port `6333`.
- **`postgres`**: PostgreSQL 16 on port `5432` with pre-seeded enterprise tables.
- **`redis`**: Redis 7 Alpine cache on port `6379`.
- **`jaeger`**: Jaeger Distributed Tracing & Observability dashboard on port `16686` with OTLP receivers on `4317`/`4318`.

### Launch Full Stack
```bash
# Build and start all services in detached mode
docker compose up -d --build

# Inspect running containers
docker compose ps

# View real-time application logs
docker compose logs -f app
```

Access services:
- **Web UI & Telemetry**: [http://localhost:8000/ui](http://localhost:8000/ui)
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Jaeger Tracing Dashboard**: [http://localhost:16686](http://localhost:16686)
- **Qdrant Vector Console**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## ☁️ Production Cloud Deployment (AWS & GCP)

### Option A: AWS Deployment Architecture
- **Compute**: **AWS ECS (Fargate)** hosting the FastAPI Docker container with Application Load Balancer (ALB).
- **Relational DB**: **Amazon Aurora PostgreSQL** (Read-Replica endpoint for read-only SQL queries).
- **Vector DB**: **Qdrant Cloud** or **AWS OpenSearch Serverless / pgvector**.
- **Cache**: **Amazon ElastiCache for Redis** (multi-AZ cluster).
- **Secrets & Observability**: AWS Secrets Manager & LangSmith / Amazon CloudWatch.

```bash
# Push container to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
docker tag agentic-enterprise-copilot:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/agentic-copilot:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/agentic-copilot:latest
```

### Option B: Google Cloud Platform (GCP)
- **Compute**: **Cloud Run** (Serverless container deployment with auto-scaling to zero).
- **Relational DB**: **Cloud SQL for PostgreSQL**.
- **Vector DB**: **Qdrant Cloud** on GCP Marketplace or Cloud Run sidecar.
- **Cache**: **Memorystore for Redis**.

```bash
# Deploy directly to Cloud Run
gcloud builds submit --tag gcr.io/<PROJECT_ID>/enterprise-copilot
gcloud run deploy enterprise-copilot \
  --image gcr.io/<PROJECT_ID>/enterprise-copilot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="secret",QDRANT_HOST="qdrant.internal"
```

---

## 🔄 CI/CD Pipeline & Evaluation Gate

The `.github/workflows/ci.yml` pipeline runs on every pull request and push to `main`:
1. **Unit & Integration Suite**: Executes all 30 Pytest unit, integration, and security tests across routing, caching, SSE streaming, citations, SQL injection firewall, tool dispatch allowlists, and adversarial guardrails.
2. **Automated Evaluation Regression Gate**: Runs `scripts/run_evals.py` on the golden dataset. If router accuracy drops below **85%** or guardrail accuracy drops below **90%**, the pipeline **blocks the PR from merging**.
3. **Docker Smoke Test**: Verifies that the production Docker image builds successfully.

---

## 🧪 Verification & Testing

Run all automated test suites locally:
```bash
# Run complete integration test suite
pytest -v

# Run router & agent verification script
python scripts/router_test.py

# Run SQL safety and injection verification
python scripts/sql_security_test.py

# Run hybrid retrieval and reranking verification
python scripts/hybrid_test.py

# Run the 50-question golden evaluation benchmark
python scripts/run_evals.py --limit 10
```

---

## 📄 License & Attribution

Designed and maintained as a production-grade Agentic GenAI reference architecture for enterprise multi-agent RAG, SQL analytics, and automated LLM evaluation.
