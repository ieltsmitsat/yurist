# Technical Specification (TS v4.0): AI-Powered, Sales-Oriented, Viral Lead Acquisition & Undetectable LegalTech Telegram Bot & Web CRM Dashboard System

---

## 1. Project Overview

### 1.1. Project Goal and Sales Strategy
This project aims to develop a hybrid LegalTech platform designed for law firms, legal agencies, and solo legal practitioners. The system automates **client intake & triage**, provides initial legal consultations, analyzes legal contracts, and **most importantly — drives viral lead acquisition (Growth & Viral Lead Gen) and client conversion to purchase paid high-ticket legal services (Sales Conversion & High-Ticket Upsell)**.

Rather than merely answering legal queries, the system evaluates the severity of the client's case during every interaction, highlights risks, and prepares the client to purchase **high-ticket legal services** such as booking a consultation, court representation, or contract drafting.

### 1.2. Human Emulation Principle
When communicating on behalf of a lawyer or legal practitioner (especially in Telegram Business mode), **the system must never disclose that it is an AI or a bot**. The tone, style, and structure of communication must match that of a professional human lawyer 100%.

### 1.3. Legal Jurisdiction
The system operates strictly within the framework of the **current legislation of the Republic of Uzbekistan** (Lex.uz national legislative database, Codes, and statutory regulations).

---

## 2. Architecture and Telegram Integration (System Topology)

The system operates across two parallel deployment modes on the Telegram platform:

1. **Public Telegram Bot (`@bot_username`):**
   * Used for acquiring new clients from a broader audience, onboarding, language selection, lead capture, services catalog, and payments.
2. **Telegram Business Mode (`business_connection_id` API):**
   * Connects directly to a lawyer's personal Telegram account. When a client messages the lawyer's personal chat, the AI automatically generates responses and sales offers **in a natural human style** on behalf of the lawyer.

### 2.1. Undetectable AI Persona Rules
In lawyer emulation mode, the AI strictly adheres to the following requirements:
* **Zero AI Traces:** Phrases such as *"I am an AI assistant"*, *"As an artificial intelligence..."*, *"I operate as a bot"*, or *"Automated response..."* are **strictly prohibited**.
* **Humanlike Conversational Tone:** Responses must be warm, composed, professional, and empathetic to avoid sounding like machine-generated templates.
* **Natural Formatting:** Avoid overly robotic template menus and emoji overload typical of standard bots. Text is formatted into clean, natural paragraphs as a human would type in Telegram.
* **Personal Profile Authenticity:** Messages originate directly from the lawyer's profile, maintaining their personal brand and tone.

### 2.2. Instant Manual Takeover Mechanism
* The instant a lawyer manually sends a message to a client within a private chat, the system detects the `business_message` event.
* The AI response mechanism automatically enters a **30-minute pause state** for that specific chat (configurable duration).

---

## 3. Growth & Conversion Functional Requirements

### 3.1. Core Sales & Conversion Mechanisms
1. **Automated Legal Risk Assessment:**
   * At the end of every AI response, a **Risk Level** (🟢 *Low*, 🟡 *Medium*, 🔴 *High Risk*) and its legal consequences are explained in plain human language.
2. **Dynamic Call-to-Action (CTA) & Offers:**
   * Contextual CTAs (`📞 Schedule a Personal Consultation`, `📑 Request Contract Audit`, `💼 Book Court Representation`).
3. **Legal Services Catalog & Retainers:**
   * Structured catalog featuring service pricing, scope, and guarantees.
4. **Appointment Booking System:**
   * Clients can view the lawyer's real-time schedule and book/pay for online or offline consultation slots directly within Telegram.

### 3.2. Innovative Lead Acquisition & Viral Features
1. **Interactive Express Legal Audit (Free Legal Audit Tool):**
   * Client uploads a contract or court notice. The bot instantly provides a **Risk Score** (e.g., 45/100) and exposes 2 critical vulnerabilities for free, upselling a full professional audit.
2. **Telegram Mini-App (TMA) Interactive Calculators:**
   * TMA-powered Alimony & Asset Division Calculator and State Court Fee Calculator. Upon calculation, it presents a CTA to draft a formal claim.
3. **Viral Referral Program ("Invite a Friend"):**
   * Deep-linking (`t.me/bot?start=ref_123`). Inviting 2 friends grants 1 extra free question or a 15% discount on consultations.
4. **Automated Lead Nurturing & Abandoned Lead Retargeting:**
   * Friendly follow-up messages sent at 24h and 48h intervals on behalf of the lawyer regarding statutory filing deadlines.
5. **Automated Legislative Monitoring & Alerts (Lex.uz Alerts):**
   * Digest updates on new business/civil laws with CTAs for corporate legal audits.
6. **Emergency Legal SOS Button ("Emergency Hotline"):**
   * Permanent SOS button providing a 30-second guide on top 3 constitutional rights during police stops or raids, plus instant emergency attorney dispatch booking.
7. **Document Generator Teaser Model:**
   * Generates Page 1 and preamble of contracts/claims for free (Teaser), requiring payment to unlock the full editable `.docx` with attorney verification stamp.

### 3.3. Multimodal Inputs
* **Text Messages:** Processed via Natural Language Processing (NLP).
* **Voice Memos:** Transcribed to text (STT) via OpenAI Whisper API.
* **Documents & Images (PDF, Word, JPEG, PNG):** Analyzed via OCR and Vision LLM.

### 3.4. RAG and Strict Legal Compliance (Zero Hallucination)
* **Grounded Knowledge Base:** Vector DB (Qdrant / pgvector) synced with Lex.uz.
* **Natural Human Disclaimer:** Natural attorney phrasing instead of robotic legal disclaimers.

### 3.5. Additional Features
* 📝 Document & Contract Templates (`.docx`/`.pdf`).
* ⚖️ Courts & Judicial Directory.
* ⏱ 24-Hour Clarification Window (1 free follow-up query).

---

## 4. Monetization and Payment Integration

### 4.1. Pricing Models
* **Freemium:** Initial 2–3 free inquiries.
* **Pay-Per-Inquiry:** One-time fee for deep legal analysis or contract audits.
* **Subscription Packages:** Weekly and monthly retainers for individuals and corporate clients.
* **High-Ticket Upsell:** Primary revenue driver through high-value legal retainer services.

### 4.2. Payment Gateway Roadmap
1. **Phase 1 (Non-Entity):** *Telegram Stars*, Automated P2P payment verification.
2. **Phase 2 (Official Merchant Gateways):** **Payme Business API**, **Click Merchant API**, **Uzum Bank API**.

---

## 5. Web Admin, CRM and Sales Dashboard

* **Inquiry Inbox & Context:** Unified chat context, voice transcriptions, and uploaded legal contracts.
* **Legal CRM Pipeline:** *New Lead* ➔ *Express Audit* ➔ *Proposal Sent* ➔ *Appointment Booked* ➔ *Closed Won*.
* **AI Draft & Upsell Editor:** Edit and approve AI-generated legal draft responses and sales proposals.
* **Referral & Retargeting Analytics:** Conversion tracking and lead attribution.

---

## 6. System Prompt Injection and Persona Engineering (AI Rules)

```text
You are a professional attorney in Uzbekistan. Communicate in Telegram chat as if you are personally messaging the client.
RULES:
1. Never refer to yourself as an AI, bot, artificial intelligence, or automated system.
2. Your communication style must be professional, composed, warm, and distinctly human.
3. Avoid artificial bot formatting, emoji clutter, or templated menus.
4. Your response must instill 100% confidence in the client that they are speaking directly with an experienced lawyer.
5. Always empathize with the client's problem, explain the legal risks, and offer a personal consultation or legal service.
```

---

## 7. Expanded Database Schema (PostgreSQL)

```sql
-- 1. Users (Leads & Referrals) Table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(50),
    language VARCHAR(10) DEFAULT 'uz',
    lead_status VARCHAR(50) DEFAULT 'new',
    referred_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    referral_code VARCHAR(50) UNIQUE,
    free_questions_left INT DEFAULT 3,
    is_subscribed BOOLEAN DEFAULT FALSE,
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Services Catalog Table
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    title_uz VARCHAR(255) NOT NULL,
    description_uz TEXT,
    price NUMERIC(12, 2) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Inquiries & Express Audits Table
CREATE TABLE inquiries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    question_text TEXT,
    stt_transcript TEXT,
    risk_level VARCHAR(20),
    risk_score INT, -- 0-100 score
    ai_draft_response TEXT,
    ai_upsell_offer TEXT,
    final_response TEXT,
    status VARCHAR(50) DEFAULT 'pending_review',
    lawyer_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    answered_at TIMESTAMP
);

-- 4. Appointments & TMA Bookings Table
CREATE TABLE appointments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    service_id INT REFERENCES services(id),
    appointment_type VARCHAR(20) DEFAULT 'online',
    scheduled_at TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'pending_payment',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Emergency SOS Requests Table
CREATE TABLE sos_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    location_lat NUMERIC(10, 8),
    location_lon NUMERIC(11, 8),
    sos_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Attachments & Media Table
CREATE TABLE attachments (
    id BIGSERIAL PRIMARY KEY,
    inquiry_id BIGINT REFERENCES inquiries(id) ON DELETE CASCADE,
    file_type VARCHAR(50),
    file_url TEXT NOT NULL,
    extracted_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Transactions & Payments Table
CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    inquiry_id BIGINT REFERENCES inquiries(id) ON DELETE SET NULL,
    appointment_id BIGINT REFERENCES appointments(id) ON DELETE SET NULL,
    amount NUMERIC(12, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending',
    transaction_ref VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 8. Tech Stack and Security

* **Backend Framework:** Python 3.12 (Aiogram 3.x, FastAPI REST API & WebSockets).
* **Telegram Mini App (TMA):** React / Vue + Telegram WebApp SDK.
* **Database:** PostgreSQL + `pgvector` / Qdrant (RAG Vector Database).
* **AI & Persona Engine:** OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet + Custom Persona System Prompt Injection.
* **STT & OCR:** OpenAI Whisper API, GPT-4o Vision / Tesseract OCR.
* **Frontend Dashboard:** React.js / Next.js + Tailwind CSS.
* **Security:** TLS 1.3 encryption, PII Redaction, Webhook secret token.
