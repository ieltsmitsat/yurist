# TEXNIK TOPSHIRIQ (Technical Specification v5.0)
## AI-Asosidagi LegalTech Telegram Bot & Web CRM Platformasi (Yurist)

---

## 1. Loyiha umumiy tavsifi va falsafasi (Project Overview)

### 1.1. Maqsad va savdo strategiyasi
Ushbu platforma yuridik firmalar, advokatlik byurolari va mustaqil amaliyotchi advokatlar uchun mo'ljallangan gibrid **LegalTech & Sales-Funnel** tizimidir. Platformaning asosiy vazifasi nafaqat yuridik savollarga javob berish, balki:
1. **Lidlarni avtomatlashtirilgan saralash (Client Intake & Triage)**;
2. Har bir murojaatda mijozning yuridik **xavf darajasini (Risk Level)** aniqlash;
3. Mijozni advokatning pullik, yuqori chekli (**High-Ticket**) xizmatlariga (shaxsiy konsultatsiya, sudda vakillik, shartnoma auditi) yo'naltirish va sotuvni amalga oshirish.

### 1.2. Sun'iy intellektni sezilmas qilish (Undetectable AI Persona)
* Advokat nomidan muloqot qilganda (ayniqsa Telegram Business rejimida), tizim **hech qachon o'zini bot yoki sun'iy intellekt (AI) deb tanishtirmasligi shart**.
* Muloqot uslubi, ohangi va strukturasi 100% professional inson-advokatdek bo'lishi kerak.
* **Advokat personasi:** Advokatning ismi — **Iqboljon**. Ism so'ralganda "Ismim Iqboljon, professional huquqshunosman" deb tanishadi, ammo yosh, oilaviy holat, shaxsiy yashash manzili kabi noo'rin shaxsiy savollarga javob bermay, muloyimlik bilan yuridik mavzuga qaytaradi.
* *"Men sun'iy intellektman"*, *"AI yordamchiman"*, *"Bot sifatida javob beryapman"* kabi iboralar **qat'iyan taqiqlanadi**.

### 1.3. Yuridik yurisdiksiya
Tizim faqat va faqat **O'zbekiston Respublikasining amaldagi qonunchiligi** (Lex.uz milliy qonunchilik bazasi, Kodekslar va normativ-huquqiy hujjatlar) doirasida ish yuritadi.

---

## 2. Tizim arxitekturasi va texnologik stek

### 2.1. Backend
- **Til & Freymvork:** Python 3.12+, FastAPI (Asinxron Web API).
- **Telegram Bot:** Aiogram 3.x (Routerlar, Middleware, FSM).
- **ORM & DB:** SQLAlchemy 2.0 (AsyncIO), PostgreSQL (`asyncpg` drayveri, `pgvector` kengaytmasi) / lokal SQLite (`aiosqlite`) fallback.
- **Kesh & Xabarlar:** Redis (FSM storage, obuna holatini keshlashtirish, 3 soniyalik so'rovlar debounsingi).
- **Vazifalar rejalashtiruvchisi:** APScheduler (24h/48h retargeting xabarlari uchun).

### 2.2. Sun'iy Intellekt va RAG (Retrieval-Augmented Generation)
- **Asosiy LLM:** Google Gemini (`gemini-3.5-flash-lite`).
- **Zaxira LLM (Fallback):** Google Gemini (`gemini-3.1-flash-lite`) yoki OpenAI API (`gpt-4o-mini`).
- **Embedding modeli:** Google `gemini-embedding-2` (yoki OpenAI `text-embedding-3-small`).
- **Nutqni matnga aylantirish (Multimodal STT):** Gemini Multimodal Audio / OpenAI Whisper API (ovozli xabarlar uchun).
- **Vektorli qidiruv:** `pgvector` orqali Lex.uz moddalari va qonunlari bo'yicha semantik o'xshashlik qidiruvi.

### 2.3. Frontend (Web Admin Panel)
- **Freymvork:** Next.js 16 (App Router, Turbopack).
- **UI & Stillash:** React 19, Tailwind CSS v4, Lucide Icons, Recharts (grafiklar uchun).
- **API integratsiyasi:** FastAPI backend bilan to'g'ridan-to'g'ri REST integratsiya va Next.js rewrites (`/api/v1/*`).

---

## 3. Telegram Bot integratsiyasi va ikki tomonlama ish rejimi

Tizim Telegram'da parallel ravishda **2 xil rejimda** ishlaydi:

```
                  ┌───────────────────────────────────────────────┐
                  │                 TELEGRAM PLATFORM             │
                  └───────────────────────┬───────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  │                                               │
                  ▼                                               ▼
     [1. Ommaviy Bot Rejimi]                       [2. Telegram Business Rejimi]
       (@yuristIqboljonbot)                         (Advokatning shaxsiy chati)
                  │                                               │
    - /start va til tanlash                         - Mijoz advokatga to'g'ridan-to'g'ri yozadi
    - Majburiy kanal obunasi                        - AI advokat nomidan "Iqboljon" bo'lib javob beradi
    - Bepul 3 ta savol (Freemium)                   - AI o'zini bot deb oshkor qilmaydi
    - Xizmatlar katalogi va to'lov                  - Advokat o'zi yozsa -> 30 daqiqa AI to'xtaydi
    - SOS Favqulodda yordam                                       │
                  │                                               │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    FastAPI + Aiogram + SQLAlchemy     │
                      │   (InquiryService, RAG, Gemini LLM)   │
                      └───────────────────────────────────────┘
```

### 3.1. Rejim 1: Ommaviy Telegram Bot (`@bot_username`)
- **Vazifasi:** Yangi mijozlarni jalb qilish, tahlil qilish, savollariga javob berish va pullik xizmatlarni taklif qilish.
- **Funksiyalari:**
  1. `/start` buyrug'i: Til tanlash (O'zbekcha / Ruscha).
  2. **Majburiy kanal/guruh obunasi:** Foydalanuvchi ma'muriyat belgilagan kanal va guruhlarga a'zo bo'lmaguncha botdan foydalana olmaydi.
  3. **Telefon raqamni olish:** `contact` tugmasi yoki matn shaklida telefon so'raladi va CRM'ga saqlanadi.
  4. **3 ta bepul savol:** Freemium tizimi bo'yicha limit boshqariladi.
  5. **Xizmatlar katalogi va To'lov:** Narxlar, Telegram Stars yoki karta orqali to'lovlar.
  6. **SOS Tugmasi:** IIB, Prokuratura yoki favqulodda vaziyatlarda 30 soniyalik huquqiy yo'riqnoma va advokat chaqirish.

### 3.2. Rejim 2: Telegram Business Rejimi (`business_connection_id`)
- **Vazifasi:** Advokatning shaxsiy Telegram akkauntiga (`business_message`) mijozlar yozganda advokat nomidan avtomatik javob berish.
- **Undetectable Qoidalari:**
  - AI faqat advokatning uslubida, o'zini inson advokatdek tutib javob qaytaradi.
  - Majburiy obuna cheklovi **Telegram Business mijozlariga qo'llanilmaydi** (advokatning to'g'ridan-to'g'ri mijozlari hech qachon bloklanmaydi).
- **Manual Takeover (Advokat aralashuvi):**
  - Agar advokat mijoz chatiga shaxsan o'zi biror xabar yozsa, AI ushbu chat uchun avtomatik ravishda **30 daqiqaga o'chadi (pauza)**.

---

## 4. Ma'lumotlar bazasi sxemasi (Database Models)

```
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│              users              │       │            inquiries            │
├─────────────────────────────────┤       ├─────────────────────────────────┤
│ id (PK)                         │1     *│ id (PK)                         │
│ telegram_id (BigInt, Unique)    ├───────┤ user_id (FK -> users.id)        │
│ full_name, phone_number         │       │ question_text, answer_text      │
│ language ('uz' | 'ru')          │       │ detected_category, risk_level   │
│ lead_status (new,contacted,...) │       │ risk_score, article_references  │
│ business_connection_id          │       │ is_clarification, created_at    │
│ referral_code, referred_by_id   │       └─────────────────────────────────┘
│ free_questions_left (def: 3)    │
│ is_subscribed (Boolean)         │       ┌─────────────────────────────────┐
│ created_at                      │       │       mandatory_channels        │
└────────────────┬────────────────┘       ├─────────────────────────────────┤
                 │1                       │ id (PK)                         │
                 │                        │ title, chat_id (@..., -100...)  │
                 │*                       │ url, order, is_active           │
┌────────────────┴────────────────┐       │ created_at                      │
│          transactions           │       └─────────────────────────────────┘
├─────────────────────────────────┤
│ id (PK)                         │       ┌─────────────────────────────────┐
│ user_id (FK -> users.id)        │       │          system_access          │
│ service_id (FK -> services.id)  │       ├─────────────────────────────────┤
│ amount, payment_method, status  │       │ id (PK)                         │
│ created_at                      │       │ telegram_id, role, is_active    │
└─────────────────────────────────┘       │ lead_topic_id, contact_topic_id │
                                          │ payment_topic_id                │
                                          └─────────────────────────────────┘
```

### Modellar ro'yxati:
1. **`User`**: Foydalanuvchi ma'lumotlari, tili, telefon raqami, referal kodi, lidiya holati (`lead_status`: `new`, `contacted`, `in_progress`, `converted`, `lost`), bepul savollar qoldig'i, biznes ulanish ID.
2. **`Inquiry`**: Har bir berilgan yuridik savol va AI javobi, tahlil qilingan xavf darajasi (`low`, `medium`, `high`), qonun moddalari ro'yxati, aniqlashtiruvchi savol flagi.
3. **`ChatMessage`**: Foydalanuvchi va AI/advokat o'rtasidagi har bir individual xabar tarixi (CRM chat ko'rinishi uchun).
4. **`Service`**: Yuridik xizmatlar katalogi (`title_uz`, `title_ru`, `price`, `description`, `service_type`, `is_active`).
5. **`Appointment`**: Konsultatsiya va uchrashuvlarni bron qilish.
6. **`Transaction`**: To'lovlar tarixi (Stars, Payme, Click, P2P).
7. **`MandatoryChannel`**: Majburiy a'zo bo'linishi kerak bo'lgan kanallar va guruhlar (`title`, `chat_id`, `url`, `order`, `is_active`).
8. **`Helpline`**: Tezkor davlat va yuridik ishonch telefonlari bazasi (102, 1002, 1155 va h.k.).
9. **`LegalChunk`**: Lex.uz qonun moddalari matni va 1536-o'lchamli vektor embeddinglari (`pgvector`).
10. **`OrgSettings`**: Advokatlik firmasi nomi, advokat ismi ("Iqboljon"), karta rekvizitlari, bepul savollar limiti, 30 daqiqalik pauza vaqti.
11. **`SystemAccess`**: Tizim advokatlari, adminlari va notifikatsiya guruhlari (Forum topic ID'lari bilan).

---

## 5. Asosiy biznes mexanizmlari va mantiqiy talablar

### 5.1. Xabarlarni birlashtirish (Debouncing)
* **Muammo:** Telegram foydalanuvchilari bitta savolni 3-4 ta qisqa xabar qilib ("Assalomu alaykum", "menda bir masala bor edi", "mashinamni jarimaga tortishdi") ketma-ket yozishadi.
* **Mantiq:** Redis orqali **3.0 soniyalik taymer** ishlatiladi. Foydalanuvchi yozishdan to'xtaganidan keyin barcha xabarlar bitta yaxlit savol sifatida yig'ilib, AI'ga uzatiladi. Bu ortiqcha token sarfini va savol limitining behuda ketishini oldini oladi.

### 5.2. Majburiy obuna quyi tizimi (Mandatory Subscription)
* Foydalanuvchi xabar yuborganda yoki tugma bosganda `MandatorySubscriptionMiddleware` ishga tushadi:
  1. Bazadagi barcha `is_active = True` bo'lgan kanallar olinadi.
  2. Bot `bot.get_chat_member()` orqali tekshiradi (`member`, `administrator`, `creator`).
  3. Obunasi tasdiqlangan foydalanuvchilar Redis'da **300 soniya (5 daqiqa)** keshlanadi (Telegram API limitini tejash uchun).
  4. A'zo bo'lmagan foydalanuvchiga barcha kanallar tugmalari va **"✅ Obunani tekshirish"** tugmasi ko'rsatiladi.
  5. **Graceful Degradation:** Agar bot kanalda admin bo'lmasa yoki noto'g'ri ID kiritilgan bo'lsa, xatolik foydalanuvchini bloklamaydi, log yozilib, keyingi kanalga o'tiladi.
  6. **Istisnolar:** Advokatlar, adminlar va Telegram Business orqali yozgan mijozlar hech qachon bloklanmaydi.

### 5.3. RAG & Xavf tahlili (Risk Scoring)
Har bir javob quyidagi 4 ta majburiy blokdan iborat bo'ladi:
1. **Muloyim insoniy salomlashuv va vaziyat mohiyati.**
2. **Qonuniy asos (Lex.uz moddalari havola bilan).**
3. **Xavf darajasi (Risk Level):**
   - 🟢 *Past xavf:* Jarima yoki kichik nizo;
   - 🟡 *O'rta xavf:* Mol-mulk yo'qotish yoki shartnoma buzilishi xavfi;
   - 🔴 *Yuqori xavf:* Jinoiy javobgarlik, qamoq yoki katta moliyaviy zarar xavfi.
4. **Dinamik Call-to-Action (CTA):**
   - Vaziyatga mos pullik xizmat taklifi (*"Ushbu holatda darhol shartnoma auditini buyurtma qilishni tavsiya qilaman"*, *"Qarshi da'vo arizasi tayyorlash uchun bog'laning"*).

### 5.4. Referal dasturi va virusli o'sish
* Har bir foydalanuvchiga unikal taklif havolasi beriladi: `https://t.me/bot_username?start=ref_{user_id}`.
* Yangi do'sti kirib ro'yxatdan o'tganda:
  - Taklif qilgan foydalanuvchiga **+1 ta bepul savol** balansi qo'shiladi.
  - Ikkala foydalanuvchiga Telegram orqali xushxabar bildirishnomasi boradi.

### 5.5. Avtomatlashtirilgan Retargeting (Lead Nurturing)
APScheduler foni har soatda ishlaydi:
- Agar foydalanuvchi oxirgi 24 soat ichida savol berib, xizmat sotib olmagan bo'lsa:
  Advokat nomidan samimiy xabar yuboriladi: *"Assalomu alaykum! Kecha murojaat qilgan masalangiz bo'yicha qonuniy muddatlarni o'tkazib yubormadingizmi? Yordam kerak bo'lsa, xizmatdaman."*
- 48 soatdan keyin ikkinchi eslatma yuboriladi.

### 5.6. Admin Forum-Guruhlariga Topic-xabarnomalar
Yurist guruhida har xil voqealar o'zining maxsus mavzulariga (Topic / Thread) yuboriladi:
1. **Lidlar mavzusi (`lead_topic_id`):** Yangi foydalanuvchi savol berganda, xavf darajasi yuqori bo'lsa tezkor ogohlantirish.
2. **Aloqa mavzusi (`contact_topic_id`):** Foydalanuvchi telefon raqamini yuborganda to'liq mijoz kartochkasi.
3. **To'lovlar mavzusi (`payment_topic_id`):** Har qanday to'lov muvaffaqiyatli o'tganda tushum xabari.

---

## 6. Web Admin Panel talablari (Next.js Dashboard)

Admin panel quyidagi bo'limlardan iborat:

1. **Dashboard (`/`):**
   - Jami mijozlar, faol lidlar, xavf darajalari statistikasi (pirog grafik).
   - O'tgan 30 kunlik lidlar dinamikasi (chiziqli grafik).
2. **CRM Lidlar bo'limi (`/crm`):**
   - Qidiruv, status bo'yicha filter (`Yangi`, `Bog'lanildi`, `Jarayonda`, `Muvaffaqiyatli`, `Yo'qotildi`).
   - Telefon raqami, xavf darajasi, advokat izohi (notes) qoldirish imkoniyati.
3. **Chatlar bo'limi (`/chats`):**
   - Real-vaqt rejimida mijoz va bot/advokat o'rtasidagi yozishmalarni ko'rish.
4. **Xizmatlar katalogi (`/services`):**
   - Xizmat nomi (uz/ru), tavsifi, narxi (so'mda yoki kelishuv asosida), statusini o'zgartirish.
5. **📢 Majburiy Obuna (`/channels`):**
   - Botga a'zolik talab qilinadigan kanallar va guruhlar ro'yxati.
   - Yangi kanal qo'shish modal oynasi (`Kanal nomi`, `@username yoki ID`, `Taklif havolasi`, `Tartib raqami`).
   - Bir klikda yoqish/o'chirish (Toggle Switch) va o'chirish imkoniyati.
6. **Ishonch telefonlari (`/helplines`):**
   - Favqulodda xizmatlar va davlat idoralari raqamlarini boshqarish.
7. **Sozlamalar (`/settings`):**
   - Advokat ismi, tashkilot nomi, bepul savollar soni va sun'iy intellekt xatti-harakati sozlamalari.

---

## 7. Xavfsizlik va Barqarorlik talablari (Non-Functional Requirements)

1. **Telegram API xatolariga chidamlilik:**
   - Bot ishga tushayotganda `TelegramConflictError` (ikki nusxa ishlaganda) yoki `TelegramUnauthorizedError` (token xato bo'lsa) butun FastAPI serverini qulatmasligi, xavfsiz kutish sikliga ega bo'lishi shart.
2. **Tarmoq nosozliklari:**
   - Har qanday `TelegramNetworkError` yuz berganda 3-5 soniya ichida avtomatik qayta ulanishi kerak.
3. **Yashirin kalitlar:**
   - Barcha API kalitlar (`BOT_TOKEN`, `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL`) faqat `.env` orqali berilishi, git repozitoriyasiga hech qachon tushmasligi shart.
4. **Kod sifat me'yorlari:**
   - Barcha Python funksiyalari to'liq Type Hinting (`mypy`) bilan qoplanishi kerak.
   - Kod `ruff` linter qoidalariga to'liq mos bo'lishi va barcha `pytest` unit/integratsion testlaridan 100% muvaffaqiyatli o'tishi shart.

---

## 8. Ishga tushirish va Deployment buyruqlari

```bash
# 1. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. Testlarni ishga tushirish
pytest

# 3. Kod sifatini tekshirish
ruff check app tests run.py
mypy app tests run.py

# 4. Bot va Backendni ishga tushirish
python run.py

# 5. Admin Panelni ishga tushirish (alohida terminalda)
cd admin
npm install
npm run dev
```
