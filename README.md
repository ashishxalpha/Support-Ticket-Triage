<div align="center">

# 🤖 AI Support Ticket Triage System

**Production-grade AI-powered support ticket management and triage platform**

[![CI](https://github.com/yourusername/support-triage-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/support-triage-ai/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](https://docs.docker.com/compose/)

*An enterprise-level AI support system that classifies tickets, predicts priority, routes to teams, generates responses, and provides semantic search — all processed asynchronously with real-time updates.*

</div>

---

## ✨ Features

### 🧠 AI Triage Engine
- **Automatic Classification** — Categorizes tickets into 8 categories using LLM
- **Priority Prediction** — Assesses urgency based on sentiment, keywords, and customer tier
- **AI Summarization** — Generates concise summaries for support agents
- **Response Generation** — Drafts professional responses using RAG with similar tickets
- **Sentiment Analysis** — Detects customer emotion and urgency level
- **Confidence Scoring** — Shows AI prediction confidence for all classifications

### 🔍 Vector Search / RAG
- **Semantic Search** — Find similar tickets using pgvector embeddings
- **RAG Pipeline** — Uses retrieved tickets as context for response generation
- **Similarity Scoring** — Quantified similarity with adjustable thresholds

### 📋 Ticket Management
- Full CRUD with comments, attachments, and activity audit log
- Status transitions with SLA tracking
- Bulk actions and CSV export ready
- Real-time updates via WebSocket

### 🔐 Authentication & Authorization
- JWT with access/refresh tokens
- 4-tier RBAC: Admin, Manager, Agent, Customer
- Role-based UI rendering and API protection
- Secure password hashing with bcrypt

### 📊 Analytics Dashboard
- Ticket volume trends, category/priority distribution
- SLA metrics (response time, resolution time)
- Agent workload distribution
- AI triage accuracy metrics

### ⚡ Async Processing
- Celery workers for all AI operations
- Redis-backed task queue with retry policies
- Real-time WebSocket notifications on task completion

---

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React 19   │────▶│    Nginx     │────▶│   FastAPI    │
│  TypeScript  │     │  Rev. Proxy  │     │   Backend    │
│  TailwindCSS │     └──────────────┘     └──────┬───────┘
└──────────────┘                                 │
                                    ┌────────────┼────────────┐
                                    ▼            ▼            ▼
                              ┌──────────┐ ┌──────────┐ ┌──────────┐
                              │PostgreSQL│ │  Redis   │ │ Celery   │
                              │ pgvector │ │  Cache   │ │ Workers  │
                              └──────────┘ └──────────┘ └────┬─────┘
                                                             │
                                                      ┌──────▼──────┐
                                                      │  OpenAI API │
                                                      │  (GPT-4o)   │
                                                      └─────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache/Queue** | Redis 7, Celery |
| **AI/ML** | OpenAI GPT-4o-mini, text-embedding-3-small |
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS |
| **State** | TanStack Query, Zustand |
| **UI** | Recharts, Framer Motion, Lucide Icons |
| **Auth** | JWT (access + refresh), bcrypt |
| **DevOps** | Docker, Docker Compose, Nginx, GitHub Actions |
| **Logging** | structlog (JSON) |
| **Linting** | Ruff, mypy, ESLint |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose v2
- OpenAI API key

### Setup

```bash
# Clone
git clone https://github.com/yourusername/support-triage-ai.git
cd support-triage-ai

# Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# Launch
docker compose up --build

# Access
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs
# Nginx:     http://localhost:80
```

### Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@support-triage.ai | admin123! |
| Manager | manager@support-triage.ai | manager123! |
| Agent | alex.johnson@support-triage.ai | agent123! |
| Customer | customer1@acmecorp.com | customer123! |

---

## 📁 Project Structure

```
support-triage-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Versioned REST endpoints
│   │   ├── ai/              # LLM provider abstraction
│   │   ├── core/            # Config, security, DB, logging
│   │   ├── middleware/       # Request logging, rate limiting
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # Business logic layer
│   │   ├── workers/         # Celery async tasks
│   │   └── main.py          # FastAPI app entrypoint
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages
│   │   ├── services/        # API client layer
│   │   ├── stores/          # Zustand state stores
│   │   └── types/           # TypeScript definitions
│   └── Dockerfile
├── nginx/nginx.conf
├── docker-compose.yml
├── Makefile
└── .github/workflows/ci.yml
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user |
| GET | `/api/v1/tickets` | List tickets (paginated, filterable) |
| POST | `/api/v1/tickets` | Create ticket + enqueue AI triage |
| GET | `/api/v1/tickets/{id}` | Get ticket details |
| PATCH | `/api/v1/tickets/{id}` | Update ticket |
| POST | `/api/v1/tickets/{id}/comments` | Add comment |
| GET | `/api/v1/tickets/{id}/similar` | Find similar tickets |
| GET | `/api/v1/analytics/overview` | Dashboard metrics |
| GET | `/api/v1/analytics/tickets` | Ticket analytics |
| GET | `/api/v1/analytics/ai-performance` | AI accuracy metrics |
| WS | `/api/v1/ws?token=...` | Real-time WebSocket |
| GET | `/health` | Health check |
| GET | `/health/ready` | Readiness probe |

Full API documentation available at `/docs` (Swagger UI) when running in development.

---

## 🧪 Testing

```bash
# Run all backend tests
make test-backend

# Run with coverage
docker compose exec backend pytest -v --cov=app --cov-report=html

# Run frontend tests
make test-frontend
```

---

## 📈 Scaling Considerations

- **Horizontal scaling**: Backend is stateless — scale via load balancer
- **Worker scaling**: Add Celery workers with `--concurrency` flag
- **Database**: Connection pooling configured, read replicas supported
- **Vector search**: pgvector IVFFlat index for sub-linear similarity search
- **Caching**: Redis for rate limiting, session cache, pub/sub
- **File storage**: Swap local uploads to S3/GCS via storage abstraction

---

## 🔮 Future Improvements

- [ ] SLA breach prediction with ML
- [ ] Email ingestion webhook (Sendgrid/Mailgun)
- [ ] Slack bot integration
- [ ] Knowledge base with RAG
- [ ] Multi-tenant support
- [ ] Ollama local LLM support
- [ ] Advanced reporting with exports
- [ ] Kubernetes deployment manifests

