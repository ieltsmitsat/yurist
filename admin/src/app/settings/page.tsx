"use client";

import { useEffect, useState } from "react";
import {
  getBotSettings,
  updateBotSettings,
  getPrompts,
  updatePrompts,
  getSystemAccessList,
  createSystemAccess,
  updateSystemAccess,
  deleteSystemAccess,
  type BotSettings,
  type Prompts,
  type SystemAccessItem,
} from "@/lib/api";

type RoleFilter = "all" | "lawyer" | "group" | "admin";
type SettingsSection = "bot" | "access" | "prompts";

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("bot");

  // Access Management State
  const [accessList, setAccessList] = useState<SystemAccessItem[]>([]);
  const [activeTab, setActiveTab] = useState<RoleFilter>("all");
  const [showAccessModal, setShowAccessModal] = useState(false);
  const [editingAccess, setEditingAccess] = useState<SystemAccessItem | null>(null);
  const [accessSaving, setAccessSaving] = useState(false);
  const [accessError, setAccessError] = useState<string | null>(null);

  const [accessForm, setAccessForm] = useState({
    telegram_id: "",
    role: "lawyer" as "lawyer" | "group" | "admin",
    name: "",
    description: "",
    is_active: true,
    lead_topic_id: null as number | null,
    contact_topic_id: null as number | null,
    payment_topic_id: null as number | null,
  });

  // Global Bot Settings State
  const [settings, setSettings] = useState<BotSettings>({
    lawyer_telegram_id: null,
    admin_group_id: null,
    admin_telegram_ids: "",
    inquiry_debounce_seconds: 3.0,
  });

  // Prompts State
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
      const [settingsRes, promptsRes, accessRes] = await Promise.allSettled([
        getBotSettings(),
        getPrompts(),
        getSystemAccessList(),
      ]);

      if (settingsRes.status === "fulfilled" && settingsRes.value) {
        setSettings({
          lawyer_telegram_id: settingsRes.value.lawyer_telegram_id || null,
          admin_group_id: settingsRes.value.admin_group_id || null,
          admin_telegram_ids: settingsRes.value.admin_telegram_ids || "",
          inquiry_debounce_seconds: settingsRes.value.inquiry_debounce_seconds ?? 3.0,
        });
      }

      if (promptsRes.status === "fulfilled" && promptsRes.value?.prompts) {
        setPrompts(promptsRes.value.prompts);
      }

      if (accessRes.status === "fulfilled" && accessRes.value) {
        setAccessList(accessRes.value);
      } else if (accessRes.status === "rejected") {
        console.warn("Could not fetch access list from API:", accessRes.reason);
      }
    } catch (error) {
      console.error("Failed to fetch settings data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAddModal = (defaultRole?: "lawyer" | "group" | "admin") => {
    setEditingAccess(null);
    setAccessError(null);
    setAccessForm({
      telegram_id: "",
      role: defaultRole || (activeTab !== "all" ? activeTab : "lawyer"),
      name: "",
      description: "",
      is_active: true,
      lead_topic_id: null,
      contact_topic_id: null,
      payment_topic_id: null,
    });
    setShowAccessModal(true);
  };

  const handleOpenEditModal = (item: SystemAccessItem) => {
    setEditingAccess(item);
    setAccessError(null);
    setAccessForm({
      telegram_id: item.telegram_id.toString(),
      role: item.role,
      name: item.name,
      description: item.description || "",
      is_active: item.is_active,
      lead_topic_id: item.lead_topic_id ?? null,
      contact_topic_id: item.contact_topic_id ?? null,
      payment_topic_id: item.payment_topic_id ?? null,
    });
    setShowAccessModal(true);
  };

  const handleSaveAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    setAccessSaving(true);
    setAccessError(null);

    const tgId = Number(accessForm.telegram_id.trim());
    if (isNaN(tgId) || tgId === 0) {
      setAccessError("To'g'ri Telegram ID raqamini kiriting!");
      setAccessSaving(false);
      return;
    }

    if (!accessForm.name.trim()) {
      setAccessError("Iltimos, ism yoki nomini kiriting!");
      setAccessSaving(false);
      return;
    }

    try {
      const isGroup = accessForm.role === "group";
      const leadTopic = isGroup ? accessForm.lead_topic_id : null;
      const contactTopic = isGroup ? accessForm.contact_topic_id : null;
      const paymentTopic = isGroup ? accessForm.payment_topic_id : null;

      if (editingAccess) {
        const updated = await updateSystemAccess(editingAccess.id, {
          telegram_id: tgId,
          role: accessForm.role,
          name: accessForm.name.trim(),
          description: accessForm.description.trim() || null,
          is_active: accessForm.is_active,
          lead_topic_id: leadTopic,
          contact_topic_id: contactTopic,
          payment_topic_id: paymentTopic,
        });
        setAccessList((prev) => prev.map((item) => (item.id === editingAccess.id ? updated : item)));
      } else {
        const created = await createSystemAccess({
          telegram_id: tgId,
          role: accessForm.role,
          name: accessForm.name.trim(),
          description: accessForm.description.trim() || null,
          is_active: accessForm.is_active,
          lead_topic_id: leadTopic,
          contact_topic_id: contactTopic,
          payment_topic_id: paymentTopic,
        });
        setAccessList((prev) => [...prev, created]);
      }
      setShowAccessModal(false);
    } catch (err: any) {
      console.error("Save access error:", err);
      setAccessError(err.message || "Saqlashda xatolik yuz berdi");
    } finally {
      setAccessSaving(false);
    }
  };

  const handleDeleteAccess = async (id: number, name: string) => {
    if (!confirm(`Haqiqatan ham "${name}" ni ro'yxatdan o'chirmoqchimisiz?`)) {
      return;
    }

    try {
      await deleteSystemAccess(id);
      setAccessList((prev) => prev.filter((item) => item.id !== id));
    } catch (err: any) {
      alert(`O'chirishda xatolik: ${err.message || "Noma'lum xato"}`);
    }
  };

  const handleToggleAccessStatus = async (item: SystemAccessItem) => {
    try {
      const updated = await updateSystemAccess(item.id, { is_active: !item.is_active });
      setAccessList((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch (err: any) {
      alert(`Holatni o'zgartirishda xatolik: ${err.message}`);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const payload: BotSettings = {
        lawyer_telegram_id: settings.lawyer_telegram_id ? Number(settings.lawyer_telegram_id) : null,
        admin_group_id: settings.admin_group_id ? Number(settings.admin_group_id) : null,
        admin_telegram_ids: settings.admin_telegram_ids,
        inquiry_debounce_seconds:
          settings.inquiry_debounce_seconds !== undefined
            ? Number(settings.inquiry_debounce_seconds)
            : 3.0,
      };

      await updateBotSettings(payload);
      setMessage({ type: "success", text: "✅ Sozlamalar muvaffaqiyatli saqlandi!" });
    } catch (error: any) {
      console.error("Save error:", error);
      setMessage({ type: "error", text: `Xatolik: ${error.message || "Tarmoq xatosi"}` });
    } finally {
      setSaving(false);
    }
  };

  const handleSavePrompts = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPrompts(true);
    setPromptMessage(null);

    try {
      await updatePrompts(prompts);
      setPromptMessage({ type: "success", text: "✅ Ko'rsatmalar (prompts) muvaffaqiyatli saqlandi!" });
    } catch (error: any) {
      console.error("Save error:", error);
      setPromptMessage({ type: "error", text: `Xatolik: ${error.message || "Tarmoq xatosi"}` });
    } finally {
      setSavingPrompts(false);
    }
  };

  // Filtered access list
  const filteredAccessList = accessList.filter((item) => {
    if (activeTab === "all") return true;
    return item.role === activeTab;
  });

  const countLawyers = accessList.filter((i) => i.role === "lawyer").length;
  const countGroups = accessList.filter((i) => i.role === "group").length;
  const countAdmins = accessList.filter((i) => i.role === "admin").length;

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "lawyer":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <span>👨‍⚖️</span> Huquqshunos
          </span>
        );
      case "group":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-semibold bg-blue-50 text-blue-800 border border-blue-200">
            <span>👥</span> Guruh
          </span>
        );
      case "admin":
        return (
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-semibold bg-purple-50 text-purple-800 border border-purple-200">
            <span>🔑</span> Admin
          </span>
        );
      default:
        return (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
            {role}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400">
        <div className="animate-spin h-7 w-7 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3" />
        Sozlamalar yuklanmoqda...
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-24">
      {/* 1. Header & Section Tabs */}
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">⚙️ Tizim Sozlamalari</h1>
          <p className="text-sm text-slate-500 mt-1">
            Bot konfiguratsiyasi, xabarlarni yig&apos;ish (debounce), ruxsatlar va AI ko&apos;rsatmalari.
          </p>
        </div>

        {/* Section Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-3 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveSection("bot")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
              activeSection === "bot"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <span>🤖</span> Bot Sozlamalari &amp; Debounce
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("access")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
              activeSection === "access"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <span>👥</span> Rollar va Ruxsatlar ({accessList.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveSection("prompts")}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
              activeSection === "prompts"
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <span>🧠</span> AI Ko&apos;rsatmalari (Prompts)
          </button>
        </div>
      </div>

      {/* 2. Unified Access Management Section */}
      {activeSection === "access" && (
        <div className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <span>👥</span> Ruxsatlar va Rollar Boshqaruvi
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Huquqshunoslar, bildirishnoma guruhlari va admin panel ruxsatlari ro'yxati
            </p>
          </div>

          <button
            onClick={() => handleOpenAddModal()}
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 shadow-sm transition-all active:scale-95"
          >
            <span>➕</span> Yangi Qo'shish
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === "all"
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            🌐 Barchasi ({accessList.length})
          </button>

          <button
            onClick={() => setActiveTab("lawyer")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === "lawyer"
                ? "bg-amber-50 text-amber-800 border border-amber-200 shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            👨‍⚖️ Huquqshunoslar ({countLawyers})
          </button>

          <button
            onClick={() => setActiveTab("group")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === "group"
                ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            👥 Guruhlar ({countGroups})
          </button>

          <button
            onClick={() => setActiveTab("admin")}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              activeTab === "admin"
                ? "bg-purple-50 text-purple-700 border border-purple-200 shadow-sm"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            🔑 Adminlar ({countAdmins})
          </button>
        </div>

        {/* Table / Cards View */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    ID
                  </th>
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Rol
                  </th>
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Nomi / Ism
                  </th>
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Telegram ID
                  </th>
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Tavsifi
                  </th>
                  <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Holat
                  </th>
                  <th className="text-right px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Amallar
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredAccessList.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-400">
                      Hech qanday ma'lumot topilmadi. Yuqoridagi "+ Yangi Qo'shish" tugmasi orqali kiriting.
                    </td>
                  </tr>
                ) : (
                  filteredAccessList.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3.5 font-mono text-slate-400 text-xs">#{item.id}</td>
                      <td className="px-4 py-3.5">{getRoleBadge(item.role)}</td>
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-900">{item.name}</div>
                        {item.role === "group" && (
                          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                            {item.lead_topic_id && (
                              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200" title="Leadlar Topiki">
                                📌 Lead: #{item.lead_topic_id}
                              </span>
                            )}
                            {item.contact_topic_id && (
                              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200" title="Aloqa Topiki">
                                📞 Aloqa: #{item.contact_topic_id}
                              </span>
                            )}
                            {item.payment_topic_id && (
                              <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-purple-50 text-purple-800 border border-purple-200" title="To'lovlar Topiki">
                                💳 To&apos;lov: #{item.payment_topic_id}
                              </span>
                            )}
                            {!item.lead_topic_id && !item.contact_topic_id && !item.payment_topic_id && (
                              <span className="text-[10px] text-slate-400 italic">
                                Topiklar sozlanmagan
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-700 bg-slate-50/70 rounded-md">
                        {item.telegram_id}
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-500 max-w-xs truncate">
                        {item.description || "—"}
                      </td>
                      <td className="px-4 py-3.5">
                        <button
                          onClick={() => handleToggleAccessStatus(item)}
                          title="Holatni o'zgartirish"
                          className="cursor-pointer transition-transform hover:scale-105"
                        >
                          {item.is_active ? (
                            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                              Faol
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-500 border border-slate-200">
                              Nofaol
                            </span>
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3.5 text-right space-x-2">
                        <button
                          onClick={() => handleOpenEditModal(item)}
                          className="px-2.5 py-1 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors"
                        >
                          ✏️ Tahrirlash
                        </button>
                        <button
                          onClick={() => handleDeleteAccess(item.id, item.name)}
                          className="px-2.5 py-1 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                        >
                          🗑️ O'chirish
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards View */}
          <div className="md:hidden divide-y divide-slate-100">
            {filteredAccessList.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-sm">
                Hech qanday ma'lumot topilmadi.
              </div>
            ) : (
              filteredAccessList.map((item) => (
                <div key={item.id} className="p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-400">#{item.id}</span>
                      {getRoleBadge(item.role)}
                    </div>
                    <button
                      onClick={() => handleToggleAccessStatus(item)}
                      className="cursor-pointer text-xs"
                    >
                      {item.is_active ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Faol
                        </span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-500">
                          Nofaol
                        </span>
                      )}
                    </button>
                  </div>

                  <div>
                    <h3 className="font-semibold text-slate-900 text-sm">{item.name}</h3>
                    <p className="text-xs font-mono text-slate-500 mt-0.5">ID: {item.telegram_id}</p>
                    {item.role === "group" && (
                      <div className="flex flex-wrap items-center gap-1.5 mt-2">
                        {item.lead_topic_id && (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            📌 Lead: #{item.lead_topic_id}
                          </span>
                        )}
                        {item.contact_topic_id && (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-blue-50 text-blue-800 border border-blue-200">
                            📞 Aloqa: #{item.contact_topic_id}
                          </span>
                        )}
                        {item.payment_topic_id && (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-mono font-bold bg-purple-50 text-purple-800 border border-purple-200">
                            💳 To&apos;lov: #{item.payment_topic_id}
                          </span>
                        )}
                        {!item.lead_topic_id && !item.contact_topic_id && !item.payment_topic_id && (
                          <span className="text-[10px] text-slate-400 italic">
                            Topiklar sozlanmagan
                          </span>
                        )}
                      </div>
                    )}
                    {item.description && (
                      <p className="text-xs text-slate-500 mt-1.5 bg-slate-50 p-2 rounded-lg border border-slate-100">
                        {item.description}
                      </p>
                    )}
                  </div>

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      onClick={() => handleOpenEditModal(item)}
                      className="px-3 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 rounded-lg"
                    >
                      ✏️ Tahrirlash
                    </button>
                    <button
                      onClick={() => handleDeleteAccess(item.id, item.name)}
                      className="px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 rounded-lg"
                    >
                      🗑️ O'chirish
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      )}

      {/* 3. Global / Bot Settings & Debounce */}
      {activeSection === "bot" && (
        <div className="space-y-6 pt-2">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <span>🤖</span> Bot Konfiguratsiyasi va Xabarlarni Yig&apos;ish (Debounce)
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Mijoz ketma-ket yozgan xabarlarini bitta savolga umumlashtirish vaqti va tizim sozlamalari
            </p>
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
                {/* 1. Message Debounce Time (Highlighted at Top) */}
                <div className="p-6 bg-gradient-to-r from-indigo-50/60 via-white to-white">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label className="block text-base font-bold text-slate-900">
                        ⏱ Xabarlarni yig&apos;ish (Debounce) vaqti
                      </label>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Mijoz bir nechta xabar yozganda ularni bitta savolga birlashtirish uchun kutish vaqti
                      </p>
                    </div>
                    <span className="text-sm font-mono font-bold px-3 py-1 rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200 shadow-xs">
                      {settings.inquiry_debounce_seconds ?? 3.0} soniya
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 mt-3">
                    <div className="relative">
                      <input
                        type="number"
                        step="0.5"
                        min="0.5"
                        max="30"
                        value={settings.inquiry_debounce_seconds ?? 3.0}
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            inquiry_debounce_seconds: e.target.value ? Number(e.target.value) : 3.0,
                          })
                        }
                        className="w-36 px-4 py-2.5 pr-12 border-2 border-indigo-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400 font-mono font-bold text-indigo-950 bg-white"
                      />
                      <span className="absolute right-3 top-2.5 text-xs font-semibold text-slate-400 pointer-events-none">
                        sek
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {[1, 2, 3, 4, 5, 8, 10].map((sec) => (
                        <button
                          key={sec}
                          type="button"
                          onClick={() =>
                            setSettings({
                              ...settings,
                              inquiry_debounce_seconds: sec,
                            })
                          }
                          className={`px-3 py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
                            (settings.inquiry_debounce_seconds ?? 3.0) === sec
                              ? "bg-indigo-600 text-white border-indigo-600 shadow-xs scale-105"
                              : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                          }`}
                        >
                          {sec}s
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="mt-3 p-3 bg-amber-50/80 border border-amber-200/80 rounded-xl text-xs text-amber-900 leading-relaxed">
                    💡 <b>Qanday ishlaydi:</b> Mijoz Telegram&apos;da ketma-ket bir nechta xabar yozganda (masalan: <i>&quot;Salom yaxshimisiz&quot;</i>, so&apos;ng <i>&quot;Menda meros bo&apos;yicha savol bor edi&quot;</i>), bot har biriga alohida-alohida javob qaytarmaydi. Belgilangan soniya ichida barcha xabarlar bitta to&apos;liq savol sifatida yig&apos;iladi va AI yuristga yuboriladi.
                  </div>
                </div>

                {/* 2. Lawyer ID */}
                <div className="p-6">
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    👨‍⚖️ Birlamchi Huquqshunos Telegram ID
                  </label>
                  <input
                    type="number"
                    value={settings.lawyer_telegram_id || ""}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        lawyer_telegram_id: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    placeholder="Masalan: 6236820733"
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                  />
                  <p className="mt-1.5 text-xs text-slate-400">
                    Asosiy huquqshunos hisobi. (Qo&apos;shimcha huquqshunoslarni &quot;Rollar va Ruxsatlar&quot; bo&apos;limidan kiritishingiz mumkin).
                  </p>
                </div>

                {/* 3. Admin Group */}
                <div className="p-6">
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    👥 Birlamchi Admin Guruh ID
                  </label>
                  <input
                    type="number"
                    value={settings.admin_group_id || ""}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        admin_group_id: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    placeholder="Masalan: -1001234567890"
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                  />
                  <p className="mt-1.5 text-xs text-slate-400">
                    Bot muhim xabarlar, to&apos;lovlar va SOS lidlarini yuboradigan asosiy Telegram guruhi.
                  </p>
                </div>

                {/* 4. Admin IDs */}
                <div className="p-6">
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    🔑 Birlamchi Admin Telegram ID lari
                  </label>
                  <input
                    type="text"
                    value={settings.admin_telegram_ids || ""}
                    onChange={(e) => setSettings({ ...settings, admin_telegram_ids: e.target.value })}
                    placeholder="Masalan: 111111,222222,333333"
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                  />
                  <p className="mt-1.5 text-xs text-slate-400">
                    Admin panelga kirish huquqiga ega asosiy Telegram ID lari ro&apos;yxati.
                  </p>
                </div>
              </div>

              <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm cursor-pointer"
                >
                  {saving ? "Saqlanmoqda..." : "Bot Sozlamalarini Saqlash"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 4. AI Prompts Settings */}
      {activeSection === "prompts" && (
        <div className="space-y-6 pt-2">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span>🧠</span> AI Huquqshunos Ko'rsatmalari (Prompts)
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Sun'iy intellektning harakteri, huquqiy tahlili va savdo takliflarini sozlang.
          </p>
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
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  🇺🇿 O'zbekcha Huquqshunos Personasi (Bosh Ko'rsatma)
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
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  🇷🇺 Ruscha Huquqshunos Personasi (Bosh Ko'rsatma)
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
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  📄 Hujjatlarni Audit Qilish Ko'rsatmasi (O'zbekcha)
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
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  📄 Hujjatlarni Audit Qilish Ko'rsatmasi (Ruscha)
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
      )}

      {/* 5. Add / Edit Access Modal */}
      {showAccessModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="font-bold text-lg text-slate-900">
                {editingAccess ? "✏️ Ruxsatni Tahrirlash" : "➕ Yangi Ruxsat / Rol Qo'shish"}
              </h3>
              <button
                onClick={() => setShowAccessModal(false)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold px-2 py-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {accessError && (
              <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
                {accessError}
              </div>
            )}

            <form onSubmit={handleSaveAccess} className="space-y-4 mt-4">
              {/* Role Select */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Ruxsat Turi (Rol)
                </label>
                <select
                  value={accessForm.role}
                  onChange={(e) =>
                    setAccessForm({
                      ...accessForm,
                      role: e.target.value as "lawyer" | "group" | "admin",
                    })
                  }
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="lawyer">👨‍⚖️ Huquqshunos (Lawyer — cheksiz savollar va mijozga javob)</option>
                  <option value="group">👥 Bildirishnoma Guruhi (Yangi lidlar va to'lovlar guruhi)</option>
                  <option value="admin">🔑 Admin Panel Ruxsati (Boshqaruv paneli administratori)</option>
                </select>
              </div>

              {/* Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Ism yoki Guruh Nomi
                </label>
                <input
                  type="text"
                  required
                  value={accessForm.name}
                  onChange={(e) => setAccessForm({ ...accessForm, name: e.target.value })}
                  placeholder="Masalan: Huquqshunos Alisher Qodirov yoki Toshkent Filiali Guruhi"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
              </div>

              {/* Telegram ID */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Telegram ID (Foydalanuvchi yoki Guruh ID si)
                </label>
                <input
                  type="text"
                  required
                  value={accessForm.telegram_id}
                  onChange={(e) => setAccessForm({ ...accessForm, telegram_id: e.target.value })}
                  placeholder="Shaxs uchun: 6236820733 | Guruh uchun: -1001234567890"
                  className="w-full px-3.5 py-2.5 font-mono border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Eslatma: Telegram guruh ID lari odatda <code>-100...</code> bilan boshlanadi.
                </p>
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Tavsifi / Izoh
                </label>
                <textarea
                  rows={2}
                  value={accessForm.description}
                  onChange={(e) => setAccessForm({ ...accessForm, description: e.target.value })}
                  placeholder="Masalan: Fuqarolik ishlari bo'yicha mas'ul huquqshunos yoki Asosiy arizalar tushadigan guruh"
                  className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                />
              </div>

              {/* Forum Supergroup Topics Configuration (when role is group) */}
              {accessForm.role === "group" && (
                <div className="p-4 bg-indigo-50/60 rounded-xl border border-indigo-200/80 space-y-3.5">
                  <div className="flex items-center gap-2">
                    <span className="text-base">💬</span>
                    <div>
                      <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider">
                        Telegram Forum Topiklari (Thread ID)
                      </h4>
                      <p className="text-[11px] text-indigo-700/80 mt-0.5">
                        Xabarlarni guruhning maxsus mavzulariga (topiklariga) avtomatik yo&apos;naltirish.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3 pt-1">
                    {/* Lead Topic ID */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                        <span>📌</span> Leadlar Topik ID:
                      </label>
                      <input
                        type="number"
                        value={accessForm.lead_topic_id || ""}
                        onChange={(e) =>
                          setAccessForm({
                            ...accessForm,
                            lead_topic_id: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                        placeholder="Masalan: 12 (bo'sh qolsa yuborilmaydi)"
                        className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
                      />
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        Botdan ro&apos;yxatdan o&apos;tgan mijozlar (Ism, telefon, yozishdan maqsadi)
                      </p>
                    </div>

                    {/* Contact Topic ID */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                        <span>📞</span> Aloqa Topik ID:
                      </label>
                      <input
                        type="number"
                        value={accessForm.contact_topic_id || ""}
                        onChange={(e) =>
                          setAccessForm({
                            ...accessForm,
                            contact_topic_id: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                        placeholder="Masalan: 14 (bo'sh qolsa yuborilmaydi)"
                        className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
                      />
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        To&apos;lov qilgan mijozlar bilan huquqshunos tezkor bog&apos;lanishi uchun (Ism, telefon, xizmat turi, muammo)
                      </p>
                    </div>

                    {/* Payment Topic ID */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
                        <span>💳</span> To&apos;lovlar Topik ID:
                      </label>
                      <input
                        type="number"
                        value={accessForm.payment_topic_id || ""}
                        onChange={(e) =>
                          setAccessForm({
                            ...accessForm,
                            payment_topic_id: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                        placeholder="Masalan: 16 (bo'sh qolsa yuborilmaydi)"
                        className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400"
                      />
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        Mijoz to&apos;lov chekini yuborganda skrinshot/chek rasmi va to&apos;lov rekvizitlari
                      </p>
                    </div>
                  </div>

                  <div className="p-2.5 bg-amber-50/90 border border-amber-200/90 rounded-lg text-[11px] text-amber-900 leading-snug">
                    💡 <b>Topik ID sini qanday olish mumkin:</b> Telegram guruhdagi kerakli topik ustiga o&apos;ng tugmani bosib <b>«Copy Link»</b> qiling. Havola oxiridagi raqam (masalan: <code>t.me/c/1234567890/<b>45</b></code>) — topik ID si bo&apos;ladi. Agar topik ID kiritilmasa, ushbu turdagi xabarlar guruhga yuborilmaydi.
                  </div>
                </div>
              )}


              {/* Active Toggle */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="access_active"
                  checked={accessForm.is_active}
                  onChange={(e) => setAccessForm({ ...accessForm, is_active: e.target.checked })}
                  className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                />
                <label htmlFor="access_active" className="text-xs font-semibold text-slate-700 cursor-pointer">
                  Ushbu ruxsat darhol faol (ishlaydigan) bo'lsin
                </label>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAccessModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={accessSaving}
                  className="px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                >
                  {accessSaving ? "Saqlanmoqda..." : editingAccess ? "O'zgartirish" : "Qo'shish"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
