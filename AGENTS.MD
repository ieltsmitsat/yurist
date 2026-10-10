# Project Context & Engineering Standards

## Tech Stack
- Backend: Python 3.12, FastAPI, Aiogram 3.x, SQLAlchemy 2.0 (Async), Pydantic v2
- Database: PostgreSQL (with pgvector extension) / SQLite (aiosqlite for local dev), Redis (FSM, Cache & Timers)
- AI & RAG: Google Gemini (gemini-3.5-flash / gemini-3.1-flash-lite) / OpenAI fallback, Gemini Multimodal STT, pgvector
- Frontend: React.js / Next.js, Tailwind CSS, Shadcn UI
- Deployment: Docker, Docker Compose, Nginx, Linux VPS

## Core Principles
1. NEVER invent or hallucinate legal facts or non-existent python packages.
2. ALWAYS implement async/await patterns for database queries and HTTP requests.
3. Write clean, modular, and typed code (type hints required for all Python functions).
4. Do NOT modify `.env`, database migrations, or authentication logic without explicit user approval.
5. Keep function implementations concise and focused on single responsibilities.
6. Off-limits: API keys in `.env` and payment integration modules (Click/Payme/Stars external gateways) are off-limits.
7. Verification: Run tests (`pytest`), typecheck (`mypy`), and linter (`ruff`) after every function/code generation.

## Commands
- Run Tests: `pytest`
- Type Check: `mypy app tests run.py`
- Lint & Format: `ruff check app tests run.py`
- Run Bot & API: `python run.py`