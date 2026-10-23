"use client";

import { useEffect, useState } from "react";
import {
  getMandatoryChannels,
  createMandatoryChannel,
  updateMandatoryChannel,
  deleteMandatoryChannel,
  toggleMandatoryChannel,
  type MandatoryChannel,
} from "@/lib/api";

export default function MandatoryChannelsPage() {
  const [items, setItems] = useState<MandatoryChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const [form, setForm] = useState({
    title: "",
    chat_id: "",
    url: "",
    order: "1",
    is_active: true,
  });

  async function load() {
    setLoading(true);
    try {
      const data = await getMandatoryChannels();
      setItems(data);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleOpenAdd() {
    setEditId(null);
    setError(null);
    setForm({
      title: "",
      chat_id: "",
      url: "",
      order: (items.length + 1).toString(),
      is_active: true,
    });
    setShowModal(true);
  }

  function handleOpenEdit(ch: MandatoryChannel) {
    setEditId(ch.id);
    setError(null);
    setForm({
      title: ch.title,
      chat_id: ch.chat_id,
      url: ch.url,
      order: ch.order.toString(),
      is_active: ch.is_active,
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    let chat_id = form.chat_id.trim();
    if (!chat_id.startsWith("@") && !chat_id.startsWith("-") && !chat_id.startsWith("https://")) {
      chat_id = "@" + chat_id;
    }

    let url = form.url.trim();
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      if (chat_id.startsWith("@")) {
        url = `https://t.me/${chat_id.replace("@", "")}`;
      } else {
        url = `https://${url}`;
      }
    }

    try {
      const payload = {
        title: form.title.trim(),
        chat_id: chat_id,
        url: url,
        order: parseInt(form.order) || 0,
        is_active: form.is_active,
      };

      if (editId) {
        await updateMandatoryChannel(editId, payload);
      } else {
        await createMandatoryChannel(payload);
      }

      setShowModal(false);
      await load();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Xatolik yuz berdi";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggle(id: number) {
    try {
      await toggleMandatoryChannel(id);
      setItems((prev) =>
        prev.map((i) => (i.id === id ? { ...i, is_active: !i.is_active } : i))
      );
    } catch (err: unknown) {
      alert("Holatni o'zgartirishda xatolik yuz berdi");
    }
  }

  async function handleDelete(id: number, title: string) {
    if (!confirm(`Haqiqatan ham «${title}» kanalini ro'yxatdan o'chirmoqchimisiz?`)) {
      return;
    }
    try {
      await deleteMandatoryChannel(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "O'chirishda xatolik yuz berdi";
      alert(msg);
    }
  }

  const filteredItems = items.filter((ch) => {
    const query = searchQuery.toLowerCase().trim();
    if (!query) return true;
    return (
      ch.title.toLowerCase().includes(query) ||
      ch.chat_id.toLowerCase().includes(query) ||
      ch.url.toLowerCase().includes(query)
    );
  });

  const activeCount = items.filter((i) => i.is_active).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <span>📢</span> Majburiy Obuna (Kanal va Guruhlar)
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Mijozlar botdan foydalanishi uchun obuna bo&apos;lishi shart bo&apos;lgan rasmiy Telegram kanallar va guruhlar
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 shadow-sm transition-all active:scale-95"
        >
          <span>➕</span> Yangi Kanal / Guruh Qo&apos;shish
        </button>
      </div>

      {/* Info Notice Banner */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-start gap-3">
        <span className="text-amber-600 text-lg">💡</span>
        <div className="text-xs text-amber-800 leading-relaxed">
          <p className="font-semibold text-amber-900 mb-0.5">
            Muhim texnik talab:
          </p>
          Bot a&apos;zolikni tekshira olishi uchun ushbu kanal yoki guruhda <b>Administrator</b> qilib qo&apos;shilishi kerak.
          Agar kanal yopiq (private) bo&apos;lsa, Chat ID sifatida raqamli ID (masalan <code>-1001234567890</code>) kiritilishi lozim.
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 font-medium">Jami Kanallar</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{items.length}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-lg">
            📢
          </div>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 font-medium">Faol (Majburiy)</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{activeCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center text-lg">
            ✅
          </div>
        </div>

        <div className="p-4 bg-white border border-slate-200 rounded-2xl shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 font-medium">Nofaol (To&apos;xtatilgan)</p>
            <p className="text-2xl font-bold text-slate-400 mt-1">{items.length - activeCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center text-lg">
            ⏸️
          </div>
        </div>
      </div>

      {/* Search & Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
        <div className="relative flex-1 max-w-sm">
          <input
            type="text"
            placeholder="Nomi yoki ID bo'yicha qidirish..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-sm"
          />
          <span className="absolute left-3 top-2.5 text-xs text-slate-400">🔍</span>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-2 text-xs text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Channels List Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"></div>
            <p>Kanallar ro&apos;yxati yuklanmoqda...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <span className="text-3xl block mb-2">📭</span>
            <p className="text-sm font-medium text-slate-800">Majburiy kanal yoki guruhlar topilmadi</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Hozircha majburiy obuna o&apos;rnatilmagan. Yuqoridagi tugma orqali yangi kanal yoki guruh qo&apos;shishingiz mumkin.
            </p>
            <button
              onClick={handleOpenAdd}
              className="mt-4 px-3.5 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg text-xs font-semibold transition-colors"
            >
              + Birinchi kanalni qo&apos;shish
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4 w-12 text-center">#</th>
                  <th className="py-3 px-4">Kanal / Guruh Nomi</th>
                  <th className="py-3 px-4">Username / Chat ID</th>
                  <th className="py-3 px-4">Havola (Link)</th>
                  <th className="py-3 px-4 w-28 text-center">Holati</th>
                  <th className="py-3 px-4 w-32 text-right">Amallar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {filteredItems.map((ch, idx) => (
                  <tr key={ch.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 text-center font-medium text-slate-400">
                      {ch.order || idx + 1}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      <div className="flex items-center gap-2">
                        <span className="text-blue-500">📢</span>
                        <span>{ch.title}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-mono text-[11px]">
                      <span className="px-2 py-0.5 bg-slate-100 rounded text-slate-700 border border-slate-200/60">
                        {ch.chat_id}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <a
                        href={ch.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline max-w-xs truncate"
                      >
                        <span className="truncate">{ch.url}</span>
                        <span className="text-[10px]">↗</span>
                      </a>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => handleToggle(ch.id)}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer ${
                          ch.is_active
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100"
                            : "bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200"
                        }`}
                        title="Holatni almashtirish"
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            ch.is_active ? "bg-emerald-500" : "bg-slate-400"
                          }`}
                        />
                        {ch.is_active ? "Faol" : "Nofaol"}
                      </button>
                    </td>
                    <td className="py-3 px-4 text-right space-x-1 whitespace-nowrap">
                      <button
                        onClick={() => handleOpenEdit(ch)}
                        className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Tahrirlash"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(ch.id, ch.title)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                        title="O'chirish"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>{editId ? "✏️" : "➕"}</span>
                {editId ? "Kanalni Tahrirlash" : "Yangi Kanal / Guruh Qo'shish"}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg leading-none p-1 rounded-lg hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Kanal / Guruh Nomi *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Masalan: Yurist Rasmiy Kanali"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Username yoki Chat ID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="@kanal_username yoki -1001234567890"
                  value={form.chat_id}
                  onChange={(e) => setForm({ ...form, chat_id: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
                <span className="text-[11px] text-slate-400 mt-1 block">
                  Ochiq kanallar uchun <code>@username</code>, yopiq kanallar uchun <code>-100...</code> ID
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Havola (URL Link) *
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://t.me/kanal_username yoki https://t.me/+inviteHash"
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Tartib raqami
                  </label>
                  <input
                    type="number"
                    value={form.order}
                    onChange={(e) => setForm({ ...form, order: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
                <div className="flex items-center pt-5">
                  <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700">
                    <input
                      type="checkbox"
                      checked={form.is_active}
                      onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                      className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                    />
                    <span>Faol (Majburiy)</span>
                  </label>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 shadow-sm transition-all disabled:opacity-50"
                >
                  {submitting ? "Saqlanmoqda..." : editId ? "Saqlash" : "Qo'shish"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
