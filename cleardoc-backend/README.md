# ClearDoc Backend

Production-grade FastAPI backend for ClearDoc — a document simplification service that helps people understand official documents using AI.

## Features

- **Document Simplification**: Upload PDFs, images, or paste text — get plain-English explanations
- **Follow-up Questions**: Ask questions about your document and get contextual answers
- **Document Comparison**: Flag unusual or unfair clauses in documents
- **Reminders**: Set deadline reminders with email notifications
- **History**: Save and revisit past document analyses
- **Rate Limiting**: Sliding window rate limiter using Redis
- **Caching**: Document results cached for 24 hours (same doc = instant response)
- **OCR**: Extract text from scanned PDFs and images using Tesseract

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Stitch Frontend │────▶│  FastAPI Backend  │────▶│  PostgreSQL  │
│  (Mobile/Web)    │◀────│  (async workers)  │◀────│  (persistent)│
└─────────────────┘     └────────┬─────────┘     └─────────────┘
                                 │
                                 ▼
                         ┌──────────────┐
                         │    Redis      │
                         │  (cache/queue)│
                         └──────────────┘
                                 │
                                 ▼
                         ┌──────────────┐
                         │  Anthropic    │
                         │  (Claude API) │
                         └──────────────┘
```

## Tech Stack

- **Framework**: FastAPI (async Python)
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Cache/Queue**: Redis
- **Background Jobs**: Celery
- **AI**: Anthropic Claude API
- **OCR**: Tesseract
- **PDF**: PyMuPDF

## Quick Start

### Using Docker (Recommended)

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# The API is now running at http://localhost:8000
# Docs available at http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start PostgreSQL and Redis
# (or use docker-compose for just the database)

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (in separate terminal)
celery -A app.tasks.celery_tasks worker --loglevel=info
```

## API Endpoints

### Explain Document
```bash
POST /explain
Content-Type: multipart/form-data

Fields:
- text: Document text (or upload file)
- language: Response language (default: "en")
- user_id: Device UUID from localStorage
- file: PDF/JPG/PNG file (optional)
```

### Get History
```bash
GET /history?user_id={uuid}&limit=20&offset=0
```

### Save to History
```bash
POST /history/save
Content-Type: application/json

{
  "document_id": "uuid",
  "user_id": "device-uuid"
}
```

### Follow-up Question
```bash
POST /followup
Content-Type: application/json

{
  "document_id": "uuid",
  "question": "What if I can't pay by the deadline?",
  "language": "en"
}
```

### Set Reminder
```bash
POST /reminders
Content-Type: application/json

{
  "user_id": "device-uuid",
  "document_id": "uuid",
  "email": "user@example.com",
  "deadline_text": "January 15, 2025",
  "remind_before": "3_days"
}
```

### Compare Document
```bash
GET /compare/{document_id}
```

### Health Check
```bash
GET /health
```

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL async URL | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | Claude API key | Required |
| `RATE_LIMIT_PER_MINUTE` | Requests per minute | `10` |
| `RATE_LIMIT_PER_DAY` | Requests per day | `50` |

## Database Schema

- **users**: Anonymous users identified by device UUID
- **documents**: Uploaded/pasted documents with type classification
- **results**: AI-generated analysis (summary, key points, next steps)
- **reminders**: Deadline reminder configurations
- **rate_limits**: Rate limiting tracking

## Performance

- **Connection Pool**: 20 persistent + 40 overflow = 60 concurrent DB connections
- **Caching**: Document results cached 24h, history cached 60s
- **Rate Limiting**: Redis-based sliding window (<1ms check)
- **Async**: All I/O operations are async — never blocks
- **Background Jobs**: Email reminders via Celery workers

## Deployment

### Production Docker

```bash
# Build and start
docker-compose -f docker-compose.yml up -d --build

# Scale workers (if needed)
docker-compose up -d --scale celery=3
```

### Environment Variables (Production)

```bash
APP_ENV=production
SECRET_KEY=<generate-random-64-chars>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/cleardoc
ANTHROPIC_API_KEY=sk-ant-...
```

## License

MIT
