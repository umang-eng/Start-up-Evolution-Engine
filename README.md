# Start-up Evolution Engine 🚀

Start-up Evolution Engine is an AI-assisted platform for turning early-stage startup ideas into structured, investor-ready business blueprints. The product combines a modern Next.js front end with a FastAPI backend, a Gemini-powered generation workflow, and real-time progress streaming so users can watch the blueprint evolve step by step.

## What the platform does

Users can:
- enter a startup idea or concept
- enhance the concept with AI assistance
- generate a multi-stage blueprint across DNA, features, roadmap, team, SWOT, and cost modules
- review the generated outputs in a guided workspace experience
- persist projects and later continue from saved work

## Core technology stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand, TanStack Query
- Backend: Python 3.13+, FastAPI, SQLAlchemy, Pydantic v2, Redis, PostgreSQL
- AI layer: Google Gemini via the GenAI SDK with structured output handling
- Dev workflow: Docker Compose for local services, concurrent frontend/backend development scripts

## Repository structure

```text
.
├── backend/                 # FastAPI application and business logic
│   ├── ai/                  # AI provider and prompt/context helpers
│   ├── api/                 # API routers, middleware, and versioned endpoints
│   ├── app/                 # Application bootstrap and health endpoints
│   ├── cache/               # Redis integration
│   ├── core/                # Config, exceptions, security, logging
│   ├── database/            # Database session and connectivity helpers
│   ├── models/              # SQLAlchemy models
│   ├── modules/             # Blueprint generation modules
│   ├── orchestrator/        # Workflow orchestration logic
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Service layer
│   └── tests/               # Backend test suite
├── public/                  # Static assets
├── src/                     # Next.js app source
│   ├── app/                 # Routes and pages
│   ├── components/          # Shared UI and layout components
│   ├── lib/                 # API client and helpers
│   ├── store/               # Zustand stores
│   └── types/               # Shared TypeScript types
├── docker-compose.yml       # Local PostgreSQL, Redis, backend, and frontend services
├── package.json             # Frontend scripts and dependencies
├── backend/requirements.txt # Backend dependencies
└── README.md
```

## Prerequisites

Make sure the following tools are available:
- Node.js 18+ or newer
- Python 3.13+
- Docker and Docker Compose (recommended for local services)
- PostgreSQL and Redis if you want to run services outside containers

## Environment variables

Create a local environment file for the backend or export the variables in your shell.

```env
ENVIRONMENT=development
SECRET_KEY=change-this-to-a-long-random-secret
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=startup_evolution
REDIS_HOST=localhost
REDIS_PORT=6379
GEMINI_API_KEY=your_gemini_api_key_here
ALLOWED_ORIGINS=http://localhost:3000
```

## Running locally

### Option 1: Docker Compose (recommended)

Start the full stack with:

```bash
docker compose up --build
```

This will expose:
- frontend: http://localhost:3000
- backend: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Option 2: Local development without Docker

Install frontend dependencies:

```bash
npm install
```

Set up the backend environment:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start both services from the project root:

```bash
npm run dev
```

The frontend will run on http://localhost:3000 and the backend API on http://localhost:8000.

## API documentation

Once the backend is running, the FastAPI docs are available at:
- http://localhost:8000/docs
- http://localhost:8000/redoc

## Testing

Run backend tests with:

```bash
cd backend
pytest -v
```

## Useful scripts

From the project root:

```bash
npm run dev            # start frontend and backend together
npm run dev:frontend   # start only the Next.js app
npm run dev:backend    # start only the FastAPI backend
npm run build          # build the frontend for production
npm run lint           # lint the frontend code
```

## Notes

- The app expects a valid Gemini API key for AI generation features.
- In production, replace the default secret values and restrict CORS origins carefully.
- The backend is designed to work with PostgreSQL and Redis, but it can also fall back gracefully during local development if those services are unavailable.
