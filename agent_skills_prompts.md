# AI Coding Agent Skills & System Prompts
## AI Yurist Telegram Bot va Web CRM Platformasini Qurish Uchun Maxsus Promptlar To'plami

Ushbu hujjat AI koding agentlariga (**Cursor, Claude Code, Gemini CLI, OpenAI Codex, Windsurf**) beriladigan maxsus yo'riqnomalar (**Skills / Rules / System Prompts**) to'plamidir. Ushbu promptlarni loyihangiz ildizidagi `.cursor/rules/`, `AGENTS.md` yoki `CLAUDE.md` fayllariga nusxalab joylashtirishingiz mumkin.

---

### 1. `AGENTS.md` — Asosiy Loyiha Konfiguratsiyasi va Arxitektura Qoidalari

> **Qayerga joylashtirish kerak:** Loyihaning ildiz papkasida `AGENTS.md` yoki `CLAUDE.md` fayli ko'rinishida.

```markdown
# Project Context & Engineering Standards

## Tech Stack
- Backend: Python 3.12, FastAPI, Aiogram 3.x, SQLAlchemy 2.0 (Async), Pydantic v2
- Database: PostgreSQL (with pgvector extension), Redis (FSM, Cache & Timers)
- AI & RAG: OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet, OpenAI Whisper API, Qdrant / pgvector
- Frontend: React.js / Next.js, Tailwind CSS, Shadcn UI
- Deployment: Docker, Docker Compose, Nginx, Linux VPS

## Core Principles
1. NEVER invent or hallucinate legal facts or non-existent python packages.
2. ALWAYS implement async/await patterns for database queries and HTTP requests.
3. Write clean, modular, and typed code (type hints required for all Python functions).
4. Do NOT modify `.env`, database migrations, or authentication logic without explicit user approval.
5. Keep function implementations concise and focused on single responsibilities.

## Commands
- Run Tests: `pytest`
- Type Check: `mypy src/`
- Lint & Format: `ruff check src/`
```

---

### 2. `aiogram-v3-expert.mdc` — Telegram Bot va Telegram Business Mode Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/aiogram-v3-expert.mdc` yoki Claude Code Skill sifatida.

```markdown
---
description: Aiogram 3.x va Telegram Business API bilan ishlash bo'yicha ko'rsatmalar
globs: "src/bot/**/*.py"
---

# Aiogram 3.x & Telegram Business API Rules

When writing code for the Telegram Bot module (`src/bot/`):

1. **Aiogram 3.x Architecture:**
   - Always use `Router` instances for modular handler distribution (`src/bot/handlers/`).
   - Use `Aiogram FSMContext` for state management instead of global variables.
   - Use Pydantic models or `CallbackData` classes for inline keyboard callback parsing.

2. **Telegram Business Mode (`business_connection_id`):**
   - Implement handlers listening to `business_message` and `business_connection` events.
   - Always store `business_connection_id` in Redis or PostgreSQL session context when sending replies on behalf of a user/lawyer.
   - Example dispatch:
     ```python
     @router.business_message()
     async def handle_business_msg(message: Message, state: FSMContext):
         connection_id = message.business_connection_id
         # Process message via AI Engine...
     ```

3. **Instant Manual Takeover Timer:**
   - If a manual message event is received from the lawyer in a business chat, set a Redis key `pause_ai:{chat_id}` with an expiration of 1800 seconds (30 minutes).
   - Before AI generates a reply, check `await redis.exists(f"pause_ai:{chat_id}")`. If active, skip AI response generation.
```

---

### 3. `rag-lexuz-engineer.mdc` — RAG Tizimi va Lex.uz Baza Integratsiyasi Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/rag-lexuz-engineer.mdc`

```markdown
---
description: Lex.uz O'zbekiston qonunchilik bazasi RAG va Vektor qidiruvi ko'rsatmalari
globs: "src/rag/**/*.py", "src/services/ai/**/*.py"
---

# Legal RAG & Vector Search Engine Rules

1. **Vector Embedding & Chunking:**
   - Split Uzbek legal texts (Kodekslar, Qonunlar) into semantic chunks preserving article integrity (Modda bo'yicha bo'lish).
   - Store metadata: `{law_name, article_number, source_url: "lex.uz/...", date_updated}`.

2. **Retrieval & Zero-Hallucination Constraints:**
   - Use Hybrid Search (BM25 Keyword Search + Vector Cosine Similarity via pgvector/Qdrant).
   - Set distance threshold to at least 0.78 for vector matches.
   - If context distance is below threshold, fallback gracefully to a human lawyer review status (`status = 'pending_lawyer'`).

3. **Context Injection:**
   - Always inject retrieved Lex.uz legal passages into the LLM system prompt as context blocks:
     ```text
     <legal_context>
     {retrieved_articles}
     </legal_context>
     ```
```

---

### 4. `undetectable-legal-persona.mdc` — Insoniy Muloqot va Botlikni Yashirish Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/undetectable-legal-persona.mdc`

```markdown
---
description: Humanlike persona, zero-AI disclosure va Telegram Business chat prompt ko'rsatmalari
globs: "src/services/ai/prompts.py"
---

# Human Lawyer Persona & Undetectable AI Prompt Rules

When constructing System Prompts for AI Legal Responses in Telegram Business Mode:

1. **STRICT PROHIBITIONS (Zero AI Disclosure):**
   - NEVER use words: "AI", "Bot", "Sun'iy intellekt", "Avtomatik javob", "Virtual yordamchi".
   - NEVER start messages with robotic greetings like "Assalomu alaykum! Men yuridik botman...".

2. **Conversational Tone & Formatting:**
   - Write in warm, empathetic, professional Uzbek as a human lawyer typing a personal Telegram message.
   - Use clean, natural paragraphs. Avoid heavy markdown grids, excessive emojis, or robotic option menus.
   - Keep sentences natural, concise, and focused on the client's problem.

3. **System Prompt Template:**
   ```text
   Siz — professional O'zbekiston yuristisiz. Telegram chatida mijoz bilan shaxsan muloqot qilayotgandek yozing.
   
   QOIDALAR:
   1. Hech qachon o'zingizni AI, bot, sun'iy intellekt yoki avtomatlashtirilgan tizim deb atamang.
   2. Muloqot uslubingiz professional, vazmin, samimiy va insoniy bo'lishi shart.
   3. Sun'iy belgilardan, botlarga xos bo'lgan shablonli menyulardan foydalanmang.
   4. Javobingiz mijozda aynan tajribali yurist bilan jonli muloqot qilayotganlik ishonchini uyg'otishi kerak.
   5. Har doim mijozning muammosiga hamdardlik bildiring, yuridik xavfni tushuntiring va shaxsiy konsultatsiya belgilashni taklif qiling.
   ```
```

---

### 5. `sales-conversion-funnel.mdc` — Legal Risk Assessment va Sotuv Triggerlari Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/sales-conversion-funnel.mdc`

```markdown
---
description: Huquqiy xavf diagnostikasi, Dynamic CTA va sotuv voronkasi ko'rsatmalari
globs: "src/services/sales/**/*.py", "src/bot/keyboards/**/*.py"
---

# Sales Conversion & Legal Risk Assessment Rules

1. **Risk Level Evaluation:**
   - Every AI analysis must output a JSON schema containing `risk_level`: `LOW` (Green), `MEDIUM` (Yellow), `HIGH` (Red).
   - Attach a humanized risk narrative explaining legal consequences (e.g., statute of limitations expiring, financial loss risk).

2. **Dynamic Call-to-Action (CTA) Generation:**
   - Attach contextual CTA buttons based on `risk_level` and inquiry type:
     - High Risk -> `📞 Advokat bilan shaxsiy uchrashuv / konsultatsiya`
     - Contract Issue -> `📑 Shartnomani ekspertizadan o'tkazish`
     - Court Dispute -> `💼 Sudda vakillik qilish xizmati`

3. **Lead Nurturing & Retargeting Background Tasks:**
   - Schedule Celery / APScheduler tasks for unconverted leads at T+24h and T+48h.
   - Retargeting messages must feel like a friendly personal check-in from the lawyer.
```

---

### 6. `fastapi-crm-backend.mdc` — FastAPI & Web CRM Dashboard Backend Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/fastapi-crm-backend.mdc`

```markdown
---
description: FastAPI REST API, WebSockets va CRM Dashboard backend ko'rsatmalari
globs: "src/api/**/*.py"
---

# FastAPI Backend & Web CRM Rules

1. **API Design & OpenAPI:**
   - Structure endpoints logically under `/api/v1/inquiries`, `/api/v1/clients`, `/api/v1/services`, `/api/v1/appointments`.
   - Use Pydantic v2 schemas for all request validation and response filtering.

2. **Real-time WebSockets:**
   - Implement WebSocket endpoint `/ws/crm/inbox` for live updates when new Telegram inquiries or voice/document transcripts arrive.
   - Broadcast events: `NEW_INQUIRY`, `DRAFT_READY`, `MANUAL_TAKEOVER`, `PAYMENT_COMPLETED`.

3. **Async Database Operations:**
   - Use SQLAlchemy 2.0 `AsyncSession` with `select()`, `join()`, and async context managers (`async with get_db() as session:`).
```

---

### 7. `security-pii-masker.mdc` — PII Redaction va OWASP Xavfsizlik Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/security-pii-masker.mdc`

```markdown
---
description: Shaxsiy ma'lumotlarni (PII) maskalash va OWASP xavfsizlik standartlari
globs: "src/security/**/*.py", "src/middleware/**/*.py"
---

# Security & PII Redaction Rules

1. **Local PII Redaction:**
   - Before passing user text, voice transcripts, or documents to third-party LLMs (OpenAI/Anthropic), run local regex and NER filters.
   - Redact: Passport numbers (`[PASSPORT_REDACTED]`), Uzbek phone numbers (`[PHONE_REDACTED]`), Pinfl (`[PINFL_REDACTED]`), and Credit card numbers.

2. **OWASP Security Standards:**
   - Use bcrypt / Argon2 for admin password hashing.
   - Validate and sanitize all file uploads (PDF, Word, Images) to prevent Remote Code Execution (RCE).
   - Enforce CORS policy allowing only authorized Web CRM domain origins.
```

---

### 8. `test-driven-development.mdc` — TDD va Quality Gate Skill

> **Qayerga joylashtirish kerak:** `.cursor/rules/test-driven-development.mdc`

```markdown
---
description: Test-Driven Development (TDD) va avtomatik sifat nazorati
globs: "tests/**/*.py", "src/**/*.py"
---

# Test-Driven Development (TDD) Workflow

1. **Red-Green-Refactor Cycle:**
   - When requested to build a feature, write failing unit tests in `tests/` first.
   - Execute `pytest` to confirm tests fail as expected.
   - Write minimum necessary code in `src/` to make tests pass.
   - Refactor code without breaking existing tests.

2. **Key Coverage Areas:**
   - RAG Retrieval & Vector Thresholds.
   - Telegram Business manual takeover timer functionality.
   - PII Masking regex correctness.
   - Payment webhook processing idempotency.
```
