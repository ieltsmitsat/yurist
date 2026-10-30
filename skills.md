# INSTAGRAM DM AUTOMATION BOT SKILLSLARI VA AI IMKONIYATLARI (skills.md)

## LegalTech AI Bot uchun Kerakli Modullar, Skillslar va Prompt Logikalari

Ushbu hujjat Instagram DM Automation botining backend va AI dvigateli bajarishi lozim bo'lgan **kompetensiyalar, skillslar, algoritmik funksiyalar va prompt logikalarini** belgilaydi.

---

### 1. Comment-to-DM Trigger & Conversion Skill (`skill_comment_to_dm`)

* **Vazifasi:** Instagram Post, Reel yoki Reklamalarga foydalanuvchilar qoldirgan sharhlarni (comments) tahlil qilish va bir martalik avtomatik shaxsiy xabar (Private Reply) yuborish.
* **Algoritmik qadamlar:**  
  1. Meta `feed` webhook hodisasini tutish (`entry[].changes[].value.item == "comment"`).
  2. Sharh matnida mo'ljallangan kalit so'zlarni (masalan: *"sud"*, *"yordam"*, *"advokat"*, *"shartnoma"*, *"ajrashish"*, *"aliment"*, *"meros"*, *"jarima"*) regex orqali aniqlash.
  3. Graph API `POST /{comment-id}/private_replies` endpointiga 1 ta xabar yuborish.
  4. Xabar matnida foydalanuvchini Direct'da *"Ha"*, *"Batafsil"* deb javob qaytarishga undash (Direct'da foydalanuvchi javob bergandagina 24 soatlik muloqot oynasi ochiladi).
  5. Soatiga 750 ta xabardan oshmaslik uchun Redis queue orqali har bir xabarni 5 soniyalik interval bilan chiqarish (Meta anti-spam rate limiting).

---

### 2. 24-Soatlik Oyna va Contact Capture Skill (`skill_24h_contact_capture`)

* **Vazifasi:** 24 soatlik bepul muloqot oynasi davomida mijozning ism va telefon raqamini olish va 24 soatlik taymerni nazorat qilish.
* **Algoritmik qadamlar:**  
  1. Har bir kiruvchi DM xabarida `last_inbound_timestamp` qiymatini keshda va DB'da yangilash.
  2. Birinchi 3 ta savol-javob davomida foydalanuvchiga tabiiy tarzda: *"Hurmatli mijoz, vaziyatingiz bo'yicha aniqroq yordam berishimiz uchun ismingiz va bog'lanish uchun telefon raqamingizni qoldiring"* deb murojaat qilish.
  3. Kiritilgan telefon raqamini O'zbekiston formatida (`+998XXXXXXXXX`) regex orqali tekshirish va CRM'ga saqlash.
  4. 24 soatlik oyna yopilishiga 2 soat qolganda foydalanuvchiga yakuniy eslatma yoki konsultatsiya taklifini yuborish.

---

### 3. Undetectable Legal AI Persona Skill (`skill_undetectable_persona`)

* **Vazifasi:** Advokat **Iqboljon** personasi nomidan 100% insoniy, samimiy va professional uslubda muloqot qilish.
* **System Prompt Qoidalari:**  
  * **Personaji:** Professional O'zbekiston huquqshunos-advokati Iqboljon.
  * **Taqiqlar:** *"Men AI yordamchiman"*, *"Bot sifatida javob beryapman"*, *"Language model"* kabi so'zlarni ishlatish **qat'iyan man etiladi**.
  * **Shaxsiy savollarga javob:** *"Yoshingiz nechada?"*, *"Qayerda yashaysiz?"* kabi savollarga: *"Men barcha e'tiborimni sizning yuridik masalangizga qaratishni afzal ko'raman. Ayting-chi, muammoingiz nimadan iborat?"* deb muloyimlik bilan huquqiy mavzuga qaytarish.
  * **Muloqot tili:** Murojaatchi qaysi tilda yozsa (o'zbekcha krill, o'zbekcha lotin yoki ruscha), aynan o'sha tilda javob berish.

---

### 4. Legal Intake, Triage & Risk Level Scoring Skill (`skill_legal_intake_triage`)

* **Vazifasi:** Murojaat mazmunini tahlil qilib, huquq sohasini aniqlash va xavf darajasini (Risk Score: 0-100) baholash.
* **Kategoriyalar:** Fuqarolik, Oila (Ajrashish, Aliment), Jinoyat, Mehnat, Uy-joy, Biznes va Shartnomalar.
* **Xavf darajalari bo'yicha harakat:**  
  * **LOW (0-30):** Bepul axborot va Lex.uz moddasidan havola berish.
  * **MEDIUM (31-60):** Shartnoma auditi yoki hujjat tayyorlash xizmatini taklif qilish.
  * **HIGH (61-85):** Sudda vakillik va advokat konsultatsiyasiga yo'naltirish.
  * **CRITICAL / SOS (86-100):** Hibsga olish, tintuv yoki favqulodda vaziyatlarda 30 soniyalik tezkor huquqiy yo'riqnoma va advokatning shoshilinch aloqa raqamini uzatish.

---

### 5. Lex.uz RAG & Legal Retrieval Skill (`skill_lexuz_rag`)

* **Vazifasi:** O'zbekiston Respublikasi qonunchiligi (Lex.uz) ma'lumotlar bazasidan semantik qidiruv o'tkazish va aniq moddalarga tayangan holda javob tuzish.
* **Texnik mexanizm:**  
  1. Foydalanuvchi savolidan qidiruv so'rovini (query embedding) shakllantirish (`gemini-embedding-2`).
  2. PostgreSQL `pgvector` orqali Lex.uz moddalari bazasidan kosinus o'xshashligi bo'yicha top-3 moddani topish.
  3. Javob matnida aniq modda nomini ko'rsatish (Masalan: *"O'zbekiston Respublikasi Fuqarolik Kodeksining 354-moddasiga muvofiq..."*).

---

### 6. Multimodal Voice DM Processing Skill (`skill_multimodal_audio_stt`)

* **Vazifasi:** Instagram Direct'ga kelgan ovozli xabarlarni (Voice DMs) matnga aylantirish va tahlil qilish.
* **Qadamlar:**  
  1. Meta Webhook orqali audio fayl URL manzilini olish.
  2. Audio faylni yuklab olib, Google Gemini Multimodal API'ga uzatish.
  3. Ovozli xabar matnini transkripsiya qilish va `skill_legal_intake_triage`ga uzatish.
  4. Javobni matn shaklida va zarurat bo'lsa Audio sintetik ovoz ko'rinishida yuborish.

---

### 7. Human Agent Handoff & Manual Takeover Skill (`skill_human_handoff`)

* **Vazifasi:** Inson-advokat muloqotga aralashganda AI'ni pauza qilish va 24 soatdan oshgan xabarlarga `HUMAN_AGENT` tagi bilan javob berishni boshqarish.
* **Pauza Mantiqi:**  
  * Advokat Meta Business Suite Inbox yoki Web Admin Paneldan xabar yuborsa, Redis'da `ai_pause:{chat_id} = true` kaliti 30 daqiqaga o'rnatiladi.
  * 30 daqiqa davomida kelgan barcha mijoz xabarlari AI ishlovidan o'tkazilmaydi.
* **Human Agent Tag:**  
  * 24 soatlik oyna yopilgan, ammo 7 kun ichida advokat javob berishi kerak bo'lganda, yuborilayotgan API so'roviga `"messaging_type": "MESSAGE_TAG", "tag": "HUMAN_AGENT"` parametri qo'shiladi.

---

### 8. Meta Policy & Payload Safety Skill (`skill_meta_policy_enforcer`)

* **Vazifasi:** Meta API cheklovlari va xatoliklarining oldini olish.
* **Tekshiruvlar:**  
  1. **Payload Truncation:** Outbound xabar matni 1,000 UTF-8 baytdan oshsa, uni xavfsiz nuqtadan qisqartirish yoki 2 ta ketma-ket xabarga bo'lish.
  2. **Response SLA:** Har bir kelgan xabarga AI 30 soniyadan kechikmagan holda javob qaytarishini ta'minlash.
  3. **Rate Limit Buffer:** Sekundiga 100 ta so'rov limitidan oshmaslik uchun outbound HTTP so'rovlarini token bucket algoritmi orqali tarqatish.

---

### 9. Lead Qualification & High-Ticket Conversion Skill (`skill_lead_conversion`)

* **Vazifasi:** Malakali lidlarni (Qualified Leads) pullik konsultatsiyaga va uchrashuvga aylantirish.
* **Mexanizm:**  
  1. Bepul 3 ta savol tugagach, mijozga tahlil natijalarini qisqacha taqdim etish.
  2. Advokatning shaxsiy qabuliga yozilish yoki pullik chuqurlashtirilgan tahlil xizmatini taklif qilish.
  3. Payme/Click to'lov havolasini uzatish va to'lov tasdiqlangach Web Admin Panelga buyurtmani saqlash.
