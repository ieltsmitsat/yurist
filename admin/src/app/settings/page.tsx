"use client";

import { useEffect, useState } from "react";

interface BotSettings {
  lawyer_telegram_id: number | null;
  admin_group_id: number | null;
  admin_telegram_ids: string | null;
}

interface Prompts {
  PERSONA_SYSTEM_PROMPT_UZ: string;
  PERSONA_SYSTEM_PROMPT_RU: string;
  EXPRESS_AUDIT_PROMPT_UZ: string;
  EXPRESS_AUDIT_PROMPT_RU: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<BotSettings>({
    lawyer_telegram_id: null,
    admin_group_id: null,
    admin_telegram_ids: "",
  });
  const [prompts, setPrompts] = useState<Prompts>({
    PERSONA_SYSTEM_PROMPT_UZ: "",
    PERSONA_SYSTEM_PROMPT_RU: "",
    EXPRESS_AUDIT_PROMPT_UZ: "",
    EXPRESS_AUDIT_PROMPT_RU: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPrompts, setSavingPrompts] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [promptMessage, setPromptMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [resSettings, resPrompts] = await Promise.all([
        fetch("/api/v1/settings/bot"),
        fetch("/api/v1/settings/prompts"),
      ]);
      
      if (resSettings.ok) {
        const data = await resSettings.json();
        setSettings({
          lawyer_telegram_id: data.lawyer_telegram_id || null,
          admin_group_id: data.admin_group_id || null,
          admin_telegram_ids: data.admin_telegram_ids || "",
        });
      }
      
      if (resPrompts.ok) {
        const data = await resPrompts.json();
        setPrompts(data.prompts);
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const payload = {
        lawyer_telegram_id: settings.lawyer_telegram_id ? Number(settings.lawyer_telegram_id) : null,
        admin_group_id: settings.admin_group_id ? Number(settings.admin_group_id) : null,
        admin_telegram_ids: settings.admin_telegram_ids,
      };

      const res = await fetch("/api/v1/settings/bot", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setMessage({ type: "success", text: "✅ Sozlamalar muvaffaqiyatli saqlandi!" });
      } else {
        const err = await res.json();
        setMessage({ type: "error", text: `Xatolik: ${err.detail || "Noma'lum xato"}` });
      }
    } catch (error) {
      console.error("Save error:", error);
      setMessage({ type: "error", text: "Tarmoq xatosi yuz berdi" });
    } finally {
      setSaving(false);
    }
  };

  const handleSavePrompts = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPrompts(true);
    setPromptMessage(null);

    try {
      const res = await fetch("/api/v1/settings/prompts", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts }),
      });

      if (res.ok) {
        setPromptMessage({ type: "success", text: "✅ Ko'rsatmalar (prompts) muvaffaqiyatli saqlandi!" });
      } else {
        const err = await res.json();
        setPromptMessage({ type: "error", text: `Xatolik: ${err.detail || "Noma'lum xato"}` });
      }
    } catch (error) {
      console.error("Save error:", error);
      setPromptMessage({ type: "error", text: "Tarmoq xatosi yuz berdi" });
    } finally {
      setSavingPrompts(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400">
        <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
        Yuklanmoqda...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-20">
      {/* 1. System Settings */}
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">⚙️ Bot Sozlamalari</h1>
          <p className="text-sm text-slate-500 mt-1">Telegram bot konfiguratsiyasi va ruxsatlar</p>
        </div>

        {message && (
          <div
            className={`p-4 rounded-xl text-sm font-medium ${
              message.type === "success"
                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <form onSubmit={handleSaveSettings}>
            <div className="divide-y divide-slate-100">
              {/* Lawyer ID */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  👨‍⚖️ Advokat Telegram ID
                </label>
                <input
                  type="number"
                  value={settings.lawyer_telegram_id || ""}
                  onChange={(e) =>
                    setSettings({ ...settings, lawyer_telegram_id: e.target.value ? Number(e.target.value) : null })
                  }
                  placeholder="Masalan: 6236820733"
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Botda advokat huquqlariga ega (cheksiz savollar va javob berish imkoniyati).
                </p>
              </div>

              {/* Admin Group */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  👥 Admin Guruh ID
                </label>
                <input
                  type="number"
                  value={settings.admin_group_id || ""}
                  onChange={(e) =>
                    setSettings({ ...settings, admin_group_id: e.target.value ? Number(e.target.value) : null })
                  }
                  placeholder="Masalan: -1001234567890"
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Bot muhim xabar va leadlarni shu guruhga yuboradi.
                </p>
              </div>

              {/* Admin IDs */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  🔑 Admin Panelga Ruxsatli ID lar
                </label>
                <input
                  type="text"
                  value={settings.admin_telegram_ids || ""}
                  onChange={(e) => setSettings({ ...settings, admin_telegram_ids: e.target.value })}
                  placeholder="Vergul bilan: 111111,222222,333333"
                  className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Admin panelga kirish huquqiga ega Telegram ID lar ro'yxati.
                </p>
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* 2. AI Prompts Settings */}
      <div className="space-y-6 pt-8 border-t border-slate-200">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">🧠 AI Bot Ko'rsatmalari (Prompts)</h2>
          <p className="text-sm text-slate-500 mt-1">Sun'iy intellektning harakteri va qoidalarini shu yerdan o'zgartiring.</p>
        </div>

        {promptMessage && (
          <div
            className={`p-4 rounded-xl text-sm font-medium ${
              promptMessage.type === "success"
                ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                : "bg-red-50 text-red-800 border border-red-200"
            }`}
          >
            {promptMessage.text}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <form onSubmit={handleSavePrompts}>
            <div className="divide-y divide-slate-100">
              
              {/* O'zbekcha Persona Prompt */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center justify-between">
                  <span>🇺🇿 O'zbekcha Bosh Ko'rsatma (Persona)</span>
                </label>
                <textarea
                  rows={8}
                  value={prompts.PERSONA_SYSTEM_PROMPT_UZ}
                  onChange={(e) => setPrompts({ ...prompts, PERSONA_SYSTEM_PROMPT_UZ: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Botning o'zbek tilidagi qoidalari..."
                />
              </div>

              {/* Ruscha Persona Prompt */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center justify-between">
                  <span>🇷🇺 Ruscha Bosh Ko'rsatma (Persona)</span>
                </label>
                <textarea
                  rows={8}
                  value={prompts.PERSONA_SYSTEM_PROMPT_RU}
                  onChange={(e) => setPrompts({ ...prompts, PERSONA_SYSTEM_PROMPT_RU: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Botning rus tilidagi qoidalari..."
                />
              </div>

              {/* O'zbekcha Audit Prompt */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center justify-between">
                  <span>📄 Hujjat Audit Ko'rsatmasi (O'zbekcha)</span>
                </label>
                <textarea
                  rows={6}
                  value={prompts.EXPRESS_AUDIT_PROMPT_UZ}
                  onChange={(e) => setPrompts({ ...prompts, EXPRESS_AUDIT_PROMPT_UZ: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Hujjatlarni o'zbek tilida audit qilish qoidalari..."
                />
              </div>

              {/* Ruscha Audit Prompt */}
              <div className="p-6">
                <label className="block text-sm font-semibold text-slate-700 mb-2 flex items-center justify-between">
                  <span>📄 Hujjat Audit Ko'rsatmasi (Ruscha)</span>
                </label>
                <textarea
                  rows={6}
                  value={prompts.EXPRESS_AUDIT_PROMPT_RU}
                  onChange={(e) => setPrompts({ ...prompts, EXPRESS_AUDIT_PROMPT_RU: e.target.value })}
                  className="w-full px-4 py-3 border border-slate-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Hujjatlarni rus tilida audit qilish qoidalari..."
                />
              </div>

            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                type="submit"
                disabled={savingPrompts}
                className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {savingPrompts ? "Saqlanmoqda..." : "Ko'rsatmalarni Saqlash"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
