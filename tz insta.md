# TEXNIK TOPSHIRIQ (Technical Specification v6.0 - Instagram DM Automation)
## AI-Asosidagi LegalTech Instagram DM Automation Bot & Web CRM Platformasi (Yurist)

---

### 1. Loyiha umumiy tavsifi va falsafasi (Project Overview)
#### 1.1. Maqsad va savdo strategiyasi
Ushbu platforma yuridik firmalar, advokatlik byurolari va mustaqil amaliyotchi advokatlar uchun mo'ljallangan gibrid **LegalTech & Sales-Funnel** tizimining **Instagram DM Automation** modulidir [cite: 1, 4]. Platformaning asosiy vazifasi Instagram sahifasiga keluvchi obunachilar va yangi auditoriyani (Reels, Postlar, Stories va Ads orqali) qamrab olish hamda:
1. **Instagram Direct (DM) orqali lildarni avtomatlashtirilgan saralash (Client Intake & Triage)** [cite: 1, 4];
2. Har bir murojaatda mijozning yuridik **xavf darajasini (Risk Level)** va masalaning dolzarbligini aniqlash;
3. Mijozni advokatning pullik, yuqori chekli (**High-Ticket**) xizmatlariga (shaxsiy konsultatsiya, sudda vakillik, shartnoma auditi) yo'naltirish hamda savdoni amalga oshirish [cite: 4];
4. **24-soatlik bepul muloqot oynasi (Standard Messaging Window)** davomida mijozning kontakt ma'lumotlarini (Telefon raqami va Ismi) yig'ib, CRM va ko'p kanalli re-engajment tizimiga uzatish [cite: 1, 2, 6].

#### 1.2. Sun'iy intellektni sezilmas qilish (Undetectable AI Persona)
* Instagram DM'da murojaatchilar bilan muloqot qilganda, tizim **hech qachon o'zini bot yoki sun'iy intellekt (AI) deb tanishtirmasligi shart** [cite: 4, 12].
* Muloqot uslubi, ohangi va strukturasi 100% professional inson-advokatdek bo'lishi kerak.
* **Advokat personasi:** Advokatning ismi — **Iqboljon**. Ism so'ralganda *"Ismim Iqboljon, professional huquqshunosman"* deb tanishadi, ammo yosh, oilaviy holat, shaxsiy yashash manzili kabi noo'rin shaxsiy savollarga javob bermay, muloyimlik bilan yuridik mavzuga qaytaradi.
* *"Men sun'iy intellektman"*, *"AI yordamchiman"*, *"Bot sifatida javob beryapman"* kabi iboralar **qat'iyan taqiqlanadi**.
* *Izoh:* Meta siyosatiga ko'ra xizmat ko'rsatish boshida yoki umumiy shartlarda avtomatlashtirilgan tizim qo'llanishi haqida umumiy xabardorlik berilishi mumkin, lekin chatbot matnida insoniy persona ("Iqboljon") saqlanadi [cite: 4, 12].

#### 1.3. Yuridik yurisdiksiya
Tizim faqat va faqat **O'zbekiston Respublikasining amaldagi qonunchiligi** (Lex.uz milliy qonunchilik bazasi, Kodekslar va normativ-huquqiy hujjatlar) doirasida ish yuritadi.

---

### 2. Instagram Messaging API va Meta Qoidalari
Meta Graph API arxitekturasi va operatsion chegaralari quyidagi qat'iy talablarga asoslanadi [cite: 1]:

```
                       ┌───────────────────────────────────────────────┐
                       │          INSTAGRAM PLATFORM TRIGGERS          │
                       │ (DM Text/Voice, Story Reply, Comment, Ads)   │
                       └───────────────────────┬───────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       │                                               │
                       ▼                                               ▼
      [1. Comment-to-DM Private Reply]               [2. Direct Message / Inbound Action]
        (Post/Reel Sharhiga avto-javob)                (24-Soatlik Standard Messaging Window)
                       │                                               │
     - 1 ta xabar yuborish imkoni (7 kun ichida)      - To'liq AI muloqot va avtomatizatsiya
     - Foydalanuvchi javob bergach -> Window ochiladi - Bepul va reklamasiz rich-media xabarlar
                       │                               - Telefon raqamni zudlik bilan olish (Capture)
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │
                                               ▼
                           ┌───────────────────────────────────────┐
                           │   FastAPI + Instagram Webhook Engine  │
                           │   (InquiryService, RAG, Gemini LLM)   │
                           └───────────────────────────────────────┘
```

#### 2.1. 24-Soatlik Standard Messaging Window
* **Muloqot oynasining ochilishi:** Mijoz Instagram Direct'ga matnli yoki ovozli xabar yozganda, Story'ga javob berganda (Story Reply), sahifani belgilaganda (Story Mention), `ig.me` havolasini bossa yoki Click-to-Direct reklamasidan kirganda 24 soatlik muloqot oynasi ochiladi [cite: 1, 2, 3, 4].
* **Imkoniyatlar:** Ushbu 24 soat ichida bot har qanday turdagi avtomatlashtirilgan xabarlarni (matn, quick replies, tugmalar, havola va media) yuborishi mumkin [cite: 3, 4].
* **Oynani uzaytirish:** Mijozdan har bir yangi xabar kelganda 24 soatlik taymer qayta nollanadi (rolling window) [cite: 1, 3].
* **Click-to-Direct Reklamalari:** Reklama orqali kelgan murojaatlar uchun muloqot oynasi 7 kungacha amal qiladi [cite: 4].

#### 2.2. Comment-to-DM (Post va Reel Sharhlaridan DM'ga)
* **Qoida:** Foydalanuvchi Instagram Post, Reel yoki Reklamaga kalit so'z bo'lgan sharh (comment) qoldirganda, tizim 7 kun ichida foydalanuvchiga **1 marta** avtomatik shaxsiy xabar (Private Reply) yuboradi [cite: 1, 3, 4].
* **Cheklov:** Sharhga beriladigan Private Reply soatiga maksimal **750 ta** xabar bilan cheklanadi (har 5 soniyada 1 ta xabar) [cite: 1].
* **Konversiya:** Foydalanuvchi ushbu Private Reply xabariga Direct'da javob qaytargan lahzada to'liq 24 soatlik Standard Messaging Window ochiladi va AI konsultatsiya jarayoni boshlanadi [cite: 3].

#### 2.3. 7-Kunlik Human Agent Oynasi (`HUMAN_AGENT` Tag)
* **Qo'lda aralashuv (Human Handoff):** Murakkab yuridik holatlarda yoki dam olish kunlarida inson-advokat javob berishi uchun Meta `HUMAN_AGENT` tagidan foydalanishga ruxsat beradi (so'nggi xabardan boshlab 7 kun) [cite: 1, 2, 3, 5].
* **Taqiq:** `HUMAN_AGENT` tagidan avtomatik bot xabarlari, reklama va ommaviy tarqatmalarda foydalanish **qat'iyan taqiqlanadi** [cite: 1, 5, 6].
* **Xatolik kodi:** 24 soatlik oyna yopilgandan so'ng bot orqali xabar yuborishga urinish Meta API Error 10 (Subcode 2534022) xatoligini qaytaradi [cite: 1].

---

### 3. Tizim arxitekturasi va texnologik stek
#### 3.1. Backend
* **Til & Freymvork:** Python 3.12+, FastAPI (Asinxron Web API va Webhook Handler).
* **Instagram API Handler:** httpx / aiohttp (Meta Graph API v21.0 bilan asinxron muloqot).
* **ORM & DB:** SQLAlchemy 2.0 (AsyncIO), PostgreSQL (asyncpg drayveri, pgvector kengaytmasi).
* **Kesh & Message Queue:** Redis (FSM storage, debounsing, Meta rate limitlarini boshqarish navbati).
* **Vazifalar rejalashtiruvchisi:** APScheduler / Celery (24 soatlik oyna tugashidan oldin eslatma yuborish va CRM sinxronizatsiyasi).

#### 3.2. Sun'iy Intellekt va RAG (Retrieval-Augmented Generation)
* **Asosiy LLM:** Google Gemini (gemini-3.5-flash-lite).
* **Zaxira LLM (Fallback):** Google Gemini (gemini-3.1-flash-lite) yoki OpenAI API (gpt-4o-mini).
* **Embedding modeli:** Google gemini-embedding-2.
* **Nutqni matnga aylantirish (Multimodal Audio STT):** Gemini Multimodal Audio (Instagram ovozli DM xabarlarini tahlil qilish uchun).
* **Vektorli qidiruv:** pgvector orqali Lex.uz moddalari bo'yicha semantik qidiruv.

#### 3.3. Frontend (Web Admin Panel & Live Chat Inbox)
* **Freymvork:** Next.js 16 (App Router).
* **UI & Stillash:** React 19, Tailwind CSS v4, Lucide Icons.
* **Live Chat Handoff:** Advokat va operatorlar uchun Instagram DM xabarlarini o'qish, AI rejimini pauzaga qo'yish va inson sifatida javob berish interfeysi.

---

### 4. Funktsional Talablar (Functional Requirements)

#### 4.1. Trigger va Avtomatizatsiya Dvigateli
1. **Keyword Triggers:** Post/Reel sharhlarida yoki DM'da kelgan kalit so'zlarni (masalan: *"sud"*, *"fidoiy"*, *"ajrashish"*, *"shartnoma"*, *"konsultatsiya"*) tanib olish va tegishli avto-javob zanjirini ishga tushirish.
2. **Story Mention & Story Reply:** Foydalanuvchi advokat sahifasini Story'da belgilaganda yoki Story'ga javob yozganda minnatdorchilik xabari va bepul yuridik yordam taklifi bilan muloqotni boshlash [cite: 1, 3].
3. **Contact Capture (Zero-Party Data Collection):** Muloqotning dastlabki 3 ta savoli ichida foydalanuvchining Telefon raqami va Ismini so'rab olish [cite: 2, 6]. Bu ma'lumotlar 24 soatlik oyna yopilgandan keyin ham mijoz bilan SMS yoki Telegram orqali bog'lanish imkonini beradi [cite: 2, 6].

#### 4.2. Freemium va Legal Intake Mantiqi
* **3 ta Bepul Savol Limit:** Murojaatchiga Instagram DM'da 3 ta bepul yuridik savol berish imkoniyati taqdim etiladi.
* **Risk Level Assessment:** Har bir murojaat bo'yicha AI xavf darajasini belgilaydi:
  * `LOW` (Oddiy huquqiy ma'lumot);
  * `MEDIUM` (Hujjatlashtirish va shartnoma masalalari);
  * `HIGH` (Sud nizolari, mulkiy da'volar);
  * `CRITICAL / SOS` (Huquqni muhofaza qiluvchi organlar, hibs, favqulodda holatlar).
* **SOS Favqulodda Yordam:** `CRITICAL` holatlarda 30 soniyalik tezkor huquqiy yo'riqnoma va advokatning shoshilinch telefon raqamini taqdim etish.
* **Pullik Konsultatsiyaga Yo'naltirish:** 3 ta bepul savoldan so'ng yoki `HIGH` xavf darajasida advokatning shaxsiy konsultatsiyasini taklif qilish va to'lov havolasini uzatish.

#### 4.3. Manual Takeover (Advokat Aralashuvi)
* Advokat Web Admin Paneldan yoki ulangan Meta Business Inbox'dan mijozga **shaxsan xabar yozsa**, AI ushbu chat uchun **30 daqiqaga avtomatik ravishda pauza rejimiga o'tadi**.
* 30 daqiqa ichida inson tomonidan yangi xabar yuborilmasa, AI avtomatik qayta faollashadi.

---

### 5. Nofunktsional va Texnik Talablar (Non-Functional Requirements & SLA)

#### 5.1. Meta API Tezlik va Reaktsiya SLA
* **Meta Responsiveness SLA:** Meta dasturchilar siyosatiga muvofiq, bot foydalanuvchi xabariga maksimal **30 soniya** ichida javob qaytarishi shart [cite: 4, 12].
* **Send API Cheklovi:** Matnli xabarlar uchun sekundiga maksimal **100 ta so'rov** [cite: 1]. Media xabarlar uchun sekundiga maksimal **10 ta so'rov** [cite: 1].
* **Conversations Read API:** Sekundiga maksimal **2 ta so'rov** [cite: 1].
* **Sharhlarga Private Reply Cheklovi:** Soatiga maksimal **750 ta xabar** (daqiqasiga ~12 ta xabar) [cite: 1].

#### 5.2. Payload va Kodlash Cheklovlari
* **Max UTF-8 hajmi:** Bir outbound matn xabari maksimal **1,000 UTF-8 bayt/belgi** bo'lishi kerak [cite: 1]. Emojilar va kirill/lotin alifbosidagi ko'p baytli belgilardan foydalanganda matn uzunligi avtomatik qisqartirilishi (truncate) shart [cite: 1].

#### 5.3. Kiberxavfsizlik va Ma'lumotlar Himoyasi
* Barcha Webhook so'rovlari Meta App Secret orqali `X-Hub-Signature-256` HMAC-SHA256 sarlavhasida tekshirilishi shart.
* Foydalanuvchilarning shaxsiy ma'lumotlari va telefon raqamlari shifrlangan holda PostgreSQL bazasida saqlanadi.
