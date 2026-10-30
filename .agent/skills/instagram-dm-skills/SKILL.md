---
name: instagram-dm-skills
description: Competencies, modules, prompt logic, and workflows for Instagram DM Automation in LegalTech AI. Covers Comment-to-DM, 24-hour window contact capture, Undetectable Persona (Iqboljon), Legal Intake & Triage, Lex.uz RAG, Multimodal Voice DM STT, Human Agent Handoff, Meta Policy Enforcement, and High-Ticket Lead Conversion.
---

# Instagram DM Automation Bot Skillslari va AI Imkoniyatlari

Ushbu skill Instagram Direct Messages (DM) va Meta Graph API orqali huquqiy maslahat beruvchi avtomatlashtirilgan sun'iy intellekt (LegalTech AI) botini boshqarish, uning 9 ta modulini yuritish, tekshirish va rivojlantirish uchun qo'llanmadir.

## 1. Comment-to-DM Trigger & Conversion Skill (`skill_comment_to_dm`)
- **Maqsad:** Post, Reel va Reklamalarga kelgan sharhlarni kuzatish va avtomatik 1 martalik Private Reply jo'natish.
- **Hodisa:** Meta Webhook `feed` hodisasi (`item: "comment"`).
- **Trigger kalit so'zlari:** `sud`, `yordam`, `advokat`, `shartnoma`, `ajrashish`, `aliment`, `meros`, `jarima`, `qarz`, `firibgar`, `ariza`.
- **API Cheklovi:** `POST /{comment-id}/private_replies` faqat 1 marta ishlaydi. 750 msg/hour limitidan oshmaslik uchun 5 soniyalik interval bilan navbatda (Queue) yuboriladi.
- **Harakat:** Direct'da mijozdan javob olish uchun Call-To-Action (CTA): *"Vaziyatingiz bo'yicha batafsil huquqiy yechimni yuborishim uchun 'Ha' yoki 'Batafsil' deb javob qaytaring"*.

## 2. 24-Soatlik Oyna va Contact Capture Skill (`skill_24h_contact_capture`)
- **Mantiq:** Meta siyosati bo'yicha foydalanuvchi yozgan paytdan boshlab 24 soatlik bepul muloqot oynasi ochiladi.
- **Oyna tekshiruvi:** `is_within_24h_window(last_inbound_timestamp)`.
- **Kontakt olish:** Dastlabki 3 ta savol davomida tabiiy ravishda telefon raqam so'rash.
- **Telefon formati:** O'zbekiston raqamlari: `^\+?998[0-9]{9}$`.
- **Yakuniy ogohlantirish:** Oyna yopilishiga 2 soat qolganda (`22 <= diff_hours < 24`) eslatma yuborish.

## 3. Undetectable Legal AI Persona Skill (`skill_undetectable_persona`)
- **Ismi:** Iqboljon (Professional O'zbekiston huquqshunos-advokati).
- **Taqiqlangan so'zlar:** `sun'iy intellekt`, `AI`, `bot`, `robot`, `til modeli`, `language model`.
- **Shaxsiy savollarga munosabat:** Yosh, turar joy, oila haqidagi savollarni rad etib, muloyimlik bilan yuridik mavzuga burish:
  > "Afsusku shaxsiy savollaringizga javob bera olmayman. Agar huquqiy masalada savollaringiz bo'lsa, batafsil yozib qoldiring."
- **Til moslashuvi:** Murojaatchi tili va alifbosiga (lotin, kirill, ruscha) mos javob qaytarish.

## 4. Legal Intake, Triage & Risk Level Scoring Skill (`skill_legal_intake_triage`)
- **Sohalar:** Fuqarolik, Oila (Ajrashish, Aliment), Jinoyat, Mehnat, Uy-joy, Biznes va Shartnomalar.
- **Risk Ballari (0-100):**
  - **LOW (0-30):** Bepul huquqiy tushuntirish va Lex.uz havolasi.
  - **MEDIUM (31-60):** Shartnoma auditi yoki hujjat tayyorlash taklifi.
  - **HIGH (61-85):** Sudda vakillik, rasmiy da'vo ariza va advokat konsultatsiyasi.
  - **CRITICAL / SOS (86-100):** Hibs, tintuv, tergov harakatlari — 30 soniyalik tezkor huquqiy xatti-harakat yo'riqnomasi va shoshilinch advokat telefoni.

## 5. Lex.uz RAG & Legal Retrieval Skill (`skill_lexuz_rag`)
- **Semantik qidiruv:** `gemini-embedding-2` orqali savol vektorini shakllantirish.
- **Vektor bazasi:** PostgreSQL `pgvector` orqali top-3 moddalarni kosinus masofasi bo'yicha olish.
- **Qonuniy havola:** Har bir javobda qonun nomi va aniq moddasi keltirilishi shart.

## 6. Multimodal Voice DM Processing Skill (`skill_multimodal_audio_stt`)
- **Ovozli DM:** Audio URL yuklab olinadi va Gemini Multimodal Audio modeliga yuboriladi.
- **Transkripsiya:** Matnga aylantirilgach, to'g'ridan-to'g'ri `skill_legal_intake_triage` ga yo'naltiriladi.

## 7. Human Agent Handoff & Manual Takeover Skill (`skill_human_handoff`)
- **Advokat aralashuvi:** Advokat Meta Business Suite Inbox orqali yozsa, Redis `ai_pause:{chat_id}` kaliti 30 daqiqaga o'rnatiladi.
- **24h-7d oralig'i:** 24 soat o'tgan, lekin 7 kun to'lmagan bo'lsa, xabarga Meta `HUMAN_AGENT` xabar tegi qo'shiladi.

## 8. Meta Policy & Payload Safety Skill (`skill_meta_policy_enforcer`)
- **Payload chegarasi:** 1,000 UTF-8 bayt. Oshsa — xavfsiz nuqta yoki jumla oxiridan bo'lib 2 ta xabarga ajratiladi.
- **SLA:** 30 soniya ichida javob berish.
- **Rate limiting:** 100 so'rov/sekunddan oshmaslik uchun token-bucket algoritmi.

## 9. Lead Qualification & High-Ticket Conversion Skill (`skill_lead_conversion`)
- **Freemium limiti:** 3 ta bepul savoldan so'ng pullik chuqurlashtirilgan xizmatlarga taklif.
- **CTA:** Advokat bilan shaxsiy qabulga yozilish, shartnoma auditi, sudda vakillik.
- **To'lov integratsiyasi:** Webhook va to'lov hisob-fakturasi orqali CRM ga buyurtma yaratish.
