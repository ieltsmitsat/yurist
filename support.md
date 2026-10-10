# AI Koding Agentlari (Codex, Gemini, Cursor, Claude Code) Bilan Telegram Bot Yaratish Bo'yicha Yo'riqnoma va Maslahatlar (`support.md`)

Ushbu hujjat sun'iy intellekt koding agentlari (Cursor, OpenAI Codex, Gemini CLI, Claude Code va boshqalar) yordamida AI Yurist Telegram boti va Web CRM platformasini muvaffaqiyatli, xavfsiz hamda texnik qarzlarsiz ishlab chiqish bo'yicha eng muhim amaliy va ilmiy tavsiyalarni o'z ichiga oladi.

---

## 1. Kontekstni Boshqarish va Konfiguratsiya (Context Engineering)

* **Ixcham Kontekst Fayllari (`AGENTS.md`, `GEMINI.md`, `.cursor/rules/*.mdc`, `CLAUDE.md`):**
  * Loyiha ildizida joylashgan konfiguratsiya faylini **50 qatordan oshirmang**.
  * Faylda loyiha steki (Node/Python, PostgreSQL, Redis, Aiogram/FastAPI), ishga tushirish buyruqlari (`pnpm test`, `pytest`, `pnpm typecheck`), uslub qoidalari va xavfsizlik taqiqlari ko'rsatilishi kerak.
* **Statik va Dinamik Kontekstni Ajratish:**
  * Statik konteksni (tizim yo'riqnomalari, agent shaxsi, o'zgarmas qoidalar) promptning bosh qismiga joylashtiring — bu LLM provider'larining *prefix caching* imkoniyatidan samarali foydalanib, xarajat va vaqtni 60-70% ga tejaydi.
  * Dinamik kontekstga faqat joriy vazifa uchun kerakli fayllarni (`@filename`) va oxirgi tool natijalarini kiriting.
* **Kontekstni Muntazam Tozalash (`/clear` va Seanslar):**
  * Har bir yangi modul yoki funksiyani (masalan: 1. DB schema -> 2. Whisper STT -> 3. Telegram Business Mode) yangi chat seansida boshlang.
  * Uzoq davom etgan seanslarda kontekst shishishi (*context bloat*) va xatoliklarning to'planib borishi (*context poisoning*) yuzaga keladi.
* **Ruxsat berilmagan Hududlar (Off-limits Zones):**
  * Konfiguratsiya faylida AI ruxsatsiz o'zgartirishi taqiqlangan yo'nalishlarni aniq ko'rsating: `/src/auth/`, `/src/payments/`, baza migratsiya fayllari va PII redaction modullari.

---

## 2. Rejalashtirish va Qadam-baqadam Ishlash (Plan-First Approach & Vibe Coding)

* **Har Doim Reja Bilan Boshlang (`Plan Mode` / PRD):**
  * Katta va murakkab funksiyalarni bajarishdan oldin agentga reja tuzdiring (`Shift+Tab` orqali Cursor Plan Mode yoki Claude Code plan).
  * Agent fayllarni o'rganib, arxitektura rejasini taqdim etgach, rejani o'zingiz ko'rib chiqing, ortiqcha qadamlarni o'chiring va shundan so'nggina kod yozishga ruxsat bering.
* **Promptlarni Kichik Bo'laklarga Bo'ling:**
  * Bitta mega-prompt bilan butun botni qurishga urinmang. Ishni 5 bosqichga ajrating:
    1. Baza va ORM modellari (`PostgreSQL + pgvector`).
    2. Telegram Bot asosiy handlerlari va FSM.
    3. Whisper STT va OCR integratsiyalari.
    4. RAG Engine va Lex.uz vektor qidiruvi.
    5. Web CRM Dashboard va To'lov Gateway'lari.
* **"Only Implement What Is Explicitly Requested" Tamoyili:**
  * LLM'lar o'z holicha tashlab qo'yilsa, oddiy funksiyaga ham keraksiz murakkabliklar, ortiqcha abstraktsiyalar va ishlamaydigan testlarni kiritib yuboradi (Over-engineering).
  * Promptlarga qat'iy cheklov kiritib, faqat so'ralgan funksionallikni eng sodda usulda yozishni buyuring.

---

## 3. Testga Asoslangan Rivojlantirish (TDD va Agentic Validation)

* **TDFlow / TDD Ish Oqimi:**
  * **1-Qadam:** Agentga kutilayotgan kiruvchi va chiquvchi ma'lumotlar bo'yicha unit/integration testlarni yozdiring.
  * **2-Qadam:** Testlarni ishga tushirib, ularning muvaffaqiyatsiz bo'lganini (`failing tests`) tasdiqlang.
  * **3-Qadam:** Agentga testlarni o'zgartirmasdan, faqat ulardan o'tadigan kodni yozishni buyuring va barcha testlar yashil bo'lguncha iteratsiya qiling.
* **Test Hacking'ning Oldini Olish:**
  * Agent testlarni hal qilish o'rniga test shartlarini o'zgartirmasligini yoki yolg'on mock'lar yaratmasligini nazorat qiling. Test fayllarini o'zgarmas (read-only) qilib belgilang.
* **Har Bir O'zgarishdan Keyin Avtomatik Tekshiruv:**
  * Har bir qabul qilingan diff'dan so'ng darhol `pnpm typecheck`, `pnpm lint` va `pnpm test` buyruqlarini ishga tushiring.

---

## 4. Arxitektura, Modullik va Texnik Qarzni Kamaytirish (The Modular Imperative)

* **Yuza Modullik Tuzog'i (Surface-Level Modularity):**
  * LLM'lar kodingizni alohida fayllarga bo'lgani bilan, modullar o'rtasida yashirin bog'liqliklar (*hidden dependencies*) va xususiy a'zolarga noqonuniy kirish holatlarini yaratadi.
  * Har bir modul uchun aniq API chegarasini (Public Interface) belgilang va agentga xususiy o'zgaruvchilarga to'g'ridan-to'g'ri tegishni taqiqlang.
* **"Vibe, Then Verify" va Diff Review:**
  * AI yaratgan har bir kodni junior dasturchining Pull Request'i kabi ko'rib chiqing.
  * O'chirilayotgan qatatorlarni, yangi qo'shilayotgan kutubxonalarni hamda API nomlanishidagi o'zgarishlarni e'tibor bilan tekshiring.
* **Gollutsinatsiyalangan Paketlar Himoyasi (Package Hallucination):**
  * Agent tavsiya etgan yangi kutubxona (npm / pip package) rostdan ham mavjudligini va ommaviy reyestrda borligini tekshiring (AI mavjud bo'lmagan soxta pakettlarni to'qib chiqarishi mumkin).

---

## 5. Xavfsizlik va PII (Shaxsiy Ma'lumotlar) Muhofazasi

* **LLM Koddagi Asosiy 4 Ta Zaiflik (CWE Top 25):**
  * *Cryptographic & Auth Weaknesses:* Koddagi hardcoded API kalitlar, zaif parollar, eski hesherlar (MD5, SHA1).
  * *Input Validation & Injection:* SQL Injection, OS Command Injection va Path Traversal (fayl yuklashda validator yo'qligi).
  * *Memory Safety & Resource Mismanagement:* Uncontrolled resource consumption, xotira sizib chiqishi (memory leak).
  * *Insecure Error Handling:* Xatolik matnlarida maxfiy tizim ma'lumotlarini yoki baza kalitlarini mijozga ko'rsatib qo'yish.
* **Xavfsiz Prompt Injiniringi:**
  * Oddiy so'rovlar ("Create a login function") 45% hollarda xavfli kod yaratadi.
  * So'rovni: *"Create a secure login function with rate limiting, password hashing (Argon2/Bcrypt), and session validation following OWASP guidelines"* shaklida kiritish xavfsizlikni 66% gacha oshiradi.
* **Klient-Tarafida PII Redaction (Zero-Trust Data Protection):**
  * Telegram botga va AI modelga foydalanuvchilarning pasport seriyalari, telefon raqamlari va manzillari unmasked holatda ketmasligi uchun local RAM'da ishlaydigan PII masking/redaction (PrivacyScrubber / Regex AST) qatlamini yarating.

---

## 6. Sifat Darvozalari (Quality Gates & Static Analysis)

Bosh sahifaga kodingizni birlashtirishdan (`merge`) oldin quyidagi avtomatlashtirilgan darvozalarni o'rnating:

1. **New Bugs & Vulnerabilities Gate:** SonarQube / CodeQL orqali yangi zaifliklar yo'qligini tekshirish.
2. **Complexity Drift Gate:** Bitta funksiyaning siklomatik murakkabligi (*cyclomatic complexity*) bir urinishda 3 baravardan ortiq oshishini taqiqlash.
3. **Duplication Threshold:** `jscpd` yoki shunga o'xshash vositalar orqali 5 qatordan ortiq takrorlanuvchi bloklar qo'shilishini bloslash (kod dublikatsiyasi 3% dan oshmasligi kerak).
4. **Coverage Gate:** Yangi kiritilayotgan modul va logic uchun kamida 80% unit test qoplamasi bo'lishi shart.

---

Ushbu yo'riqnomaga amal qilish orqali siz AI agentlaridan maksimal unumdorlik bilan foydalanasiz va barqaror, xavfsiz hamda yuqori sifatli bot platformasini barpo etasiz!
