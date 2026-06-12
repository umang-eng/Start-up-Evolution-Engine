# Start-up Evolution Engine 🚀

The **Start-up Evolution Engine** is an AI-powered SaaS platform that transforms startup ideas into investor-ready blueprints. It uses a structured 7-stage compilation pipeline to generate business strategies, product architectures, roadmap milestones, org charts, SWOT analyses, and financial projections.

---

## 🛠️ Technology Stack

*   **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Zustand, TanStack Query, Motion, Recharts.
*   **Backend:** Python 3.13+, FastAPI, PostgreSQL (asyncpg), Redis (caching and Pub/Sub), SQLAlchemy 2.0, Alembic, Pydantic V2, jose (JWT).
*   **AI Engine:** Gemini API (GenAI SDK) with strict Pydantic structured output models.

---

## 📁 Repository Structure

```
.
├── backend/                  # FastAPI Application
│   ├── app/                  # Main server and health routes
│   ├── api/                  # Versioned routers and middlewares
│   ├── core/                 # Configs, Security, Loggers, Exceptions
│   ├── database/             # Async session configurations
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic serialization models
│   ├── repositories/         # Generic CRUD repository pattern
│   ├── services/             # Domain service layer coordinator
│   ├── cache/                # Redis connection manager
│   ├── tests/                # PyTest suite and test databases
│   └── requirements.txt      # Backend dependencies
├── src/                      # Next.js Application
│   ├── app/                  # App routes and stylesheets
│   ├── components/           # UI elements and layout panels
│   ├── lib/                  # Diagnostic generators and utils
│   ├── store/                # Zustand global state slices
│   └── types/                # TypeScript schema structures
├── package.json              # Workspace script executor
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
Make sure you have the following installed:
*   [Node.js](https://nodejs.org/) (v18.0.0 or higher)
*   [Python](https://www.python.org/) (v3.13.0 or higher)
*   [PostgreSQL](https://www.postgresql.org/) (running locally or remotely)
*   [Redis](https://redis.io/) (running locally or remotely)

### 2. Environment Variables Configuration
Create a `.env` file in the `backend/` directory or set the variables in your shell:
```env
# Server Env
ENVIRONMENT=development
SECRET_KEY=generate_a_secure_jwt_random_key_here

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=startup_evolution

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Gemini AI API Key
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Backend Dependencies
Navigate to the `backend` directory, create a virtual environment, and install package dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies
Run the package installation command at the workspace root:
```bash
npm install
```

---

## 🚀 Running the Platform

To run both the **Next.js Frontend** and **FastAPI Backend** concurrently using a single command, execute the following at the workspace root:

```bash
npm run dev
```

*   **Next.js Workspace UI:** Access at [http://localhost:3000](http://localhost:3000)
*   **FastAPI Backend Server:** Running at [http://localhost:8000](http://localhost:8000)
*   **Swagger API Docs:** Accessible at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Testing the Backend

The backend includes a unit testing foundation configured to run database queries inside an isolated in-memory SQLite database. To run unit tests:

```bash
cd backend
pytest -v
```
