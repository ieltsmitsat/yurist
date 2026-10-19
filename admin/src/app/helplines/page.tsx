"use client";

import { useEffect, useState } from "react";
import { getHelplines, createHelpline, updateHelpline, deleteHelpline, type Helpline } from "@/lib/api";

const PRESET_CATEGORIES = [
  { uz: "Huquqni muhofaza qiluvchi organlar", ru: "Правоохранительные органы" },
  { uz: "Sud tizimi", ru: "Судебная система" },
  { uz: "Davlat organlari va vazirliklar", ru: "Государственные органы и министерства" },
  { uz: "Favqulodda va ijtimoiy yordam", ru: "Экстренные службы и социальная помощь" },
];

export default function HelplinesPage() {
  const [items, setItems] = useState<Helpline[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [form, setForm] = useState({
    category_uz: PRESET_CATEGORIES[0].uz,
    category_ru: PRESET_CATEGORIES[0].ru,
    organization_uz: "",
    organization_ru: "",
    phone_number: "",
    description_uz: "",
    description_ru: "",
    order: "1",
    is_active: true,
  });

  async function load() {
    setLoading(true);
    try {
      setItems(await getHelplines());
    } catch (err) {
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
      category_uz: PRESET_CATEGORIES[0].uz,
      category_ru: PRESET_CATEGORIES[0].ru,
      organization_uz: "",
      organization_ru: "",
      phone_number: "",
      description_uz: "",
      description_ru: "",
      order: "1",
      is_active: true,
    });
    setShowModal(true);
  }

  function handleOpenEdit(h: Helpline) {
    setEditId(h.id);
    setError(null);
    setForm({
      category_uz: h.category_uz || PRESET_CATEGORIES[0].uz,
      category_ru: h.category_ru || PRESET_CATEGORIES[0].ru,
      organization_uz: h.organization_uz,
      organization_ru: h.organization_ru,
      phone_number: h.phone_number,
      description_uz: h.description_uz || "",
      description_ru: h.description_ru || "",
      order: h.order.toString(),
      is_active: h.is_active,
    });
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        category_uz: form.category_uz.trim(),
        category_ru: form.category_ru.trim(),
        organization_uz: form.organization_uz.trim(),
        organization_ru: form.organization_ru.trim(),
        phone_number: form.phone_number.trim(),
        description_uz: form.description_uz.trim() || null,
        description_ru: form.description_ru.trim() || null,
        order: parseInt(form.order) || 0,
        is_active: form.is_active,
      };

      if (editId) {
        await updateHelpline(editId, payload);
      } else {
        await createHelpline(payload);
      }
      setShowModal(false);
      load();
    } catch (err: any) {
      setError(err.message || "Saqlashda xatolik yuz berdi");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Haqiqatan ham "${name}" ishonch telefonini o'chirmoqchimisiz?`)) return;
    try {
      await deleteHelpline(id);
      load();
    } catch (err: any) {
      alert(err.message || "O'chirishda xatolik yuz berdi");
    }
  }

  // Categories list for filter tabs
  const uniqueCategories = Array.from(
    new Set(items.map((i) => i.category_uz).filter((c): c is string => Boolean(c)))
  );

  const filteredItems = items.filter((h) => {
    const matchesCat = filterCategory === "all" || h.category_uz === filterCategory;
    const query = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !query ||
      h.organization_uz.toLowerCase().includes(query) ||
      h.organization_ru.toLowerCase().includes(query) ||
      h.phone_number.toLowerCase().includes(query) ||
      (h.description_uz && h.description_uz.toLowerCase().includes(query));
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <span>📞</span> Ishonch Telefonlari va Kataloglar
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Telegram botdagi reply tugmalar ko&apos;rinishida chiquvchi ishonch telefonlari katalogi boshqaruvi
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 shadow-sm transition-all active:scale-95"
        >
          <span>➕</span> Yangi Telefon Qo&apos;shish
        </button>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center justify-between">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
          <button
            onClick={() => setFilterCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              filterCategory === "all"
                ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-sm"
                : "text-slate-600 hover:bg-slate-100 border border-transparent"
            }`}
          >
            🌐 Barchasi ({items.length})
          </button>
          {uniqueCategories.map((cat) => {
            const count = items.filter((i) => i.category_uz === cat).length;
            return (
              <button
                key={cat}
                onClick={() => setFilterCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  filterCategory === cat
                    ? "bg-blue-50 text-blue-700 border border-blue-200 shadow-sm"
                    : "text-slate-600 hover:bg-slate-100 border border-transparent"
                }`}
              >
                📂 {cat} ({count})
              </button>
            );
          })}
        </div>

        <div className="w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tashkilot yoki raqam qidirish..."
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 placeholder:text-slate-400 bg-white"
          />
        </div>
      </div>

      {/* Main Table / Cards */}
      {loading ? (
        <div className="p-12 text-center text-sm text-slate-500 bg-white rounded-xl border border-slate-200">
          Yuklanmoqda...
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {/* Desktop Table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="p-4 w-12 text-center">#</th>
                  <th className="p-4">Katalog (Kategoriya)</th>
                  <th className="p-4">Tashkilot nomi</th>
                  <th className="p-4">Ishonch telefoni</th>
                  <th className="p-4">Tavsif</th>
                  <th className="p-4 text-center">Holat</th>
                  <th className="p-4 text-right">Amallar</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredItems.map((h, idx) => (
                  <tr key={h.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 text-center text-xs text-slate-400 font-mono">{idx + 1}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                        📂 {h.category_uz}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="font-semibold text-slate-900">{h.organization_uz}</div>
                      {h.organization_ru && (
                        <div className="text-xs text-slate-400 mt-0.5">{h.organization_ru}</div>
                      )}
                    </td>
                    <td className="p-4">
                      <span className="font-mono font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded-md text-xs">
                        📞 {h.phone_number}
                      </span>
                    </td>
                    <td className="p-4 text-xs text-slate-500 max-w-xs truncate">
                      {h.description_uz || h.description_ru || "—"}
                    </td>
                    <td className="p-4 text-center">
                      {h.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Faol
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
                          Faol emas
                        </span>
                      )}
                    </td>
                    <td className="p-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEdit(h)}
                          className="px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Tahrirlash"
                        >
                          ✏️ Tahrirlash
                        </button>
                        <button
                          onClick={() => handleDelete(h.id, h.organization_uz)}
                          className="px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="O'chirish"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredItems.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-sm text-slate-400">
                      Hech qanday ishonch telefoni topilmadi.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards */}
          <div className="md:hidden divide-y divide-slate-100">
            {filteredItems.map((h) => (
              <div key={h.id} className="p-4 space-y-2.5 hover:bg-slate-50/50">
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                      📂 {h.category_uz}
                    </span>
                    <div className="font-semibold text-sm text-slate-900 mt-1">{h.organization_uz}</div>
                  </div>
                  {h.is_active ? (
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold rounded-full">
                      Faol
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-semibold rounded-full">
                      Faol emas
                    </span>
                  )}
                </div>

                <div className="font-mono text-xs font-semibold text-blue-600 bg-blue-50/70 p-2 rounded-lg flex items-center justify-between">
                  <span>📞 {h.phone_number}</span>
                  <span className="text-[10px] font-normal text-slate-400">Tartib: #{h.order}</span>
                </div>

                {h.description_uz && (
                  <p className="text-xs text-slate-500 leading-relaxed italic">{h.description_uz}</p>
                )}

                <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
                  <button
                    onClick={() => handleOpenEdit(h)}
                    className="flex-1 py-1.5 text-xs font-semibold bg-slate-100 text-slate-700 rounded-lg hover:bg-blue-50 hover:text-blue-600"
                  >
                    ✏️ Tahrirlash
                  </button>
                  <button
                    onClick={() => handleDelete(h.id, h.organization_uz)}
                    className="px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
                  >
                    🗑️ O&apos;chirish
                  </button>
                </div>
              </div>
            ))}
            {filteredItems.length === 0 && (
              <div className="p-8 text-center text-sm text-slate-400">
                Hech qanday ishonch telefoni topilmadi.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal Add / Edit Form */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <span>{editId ? "✏️" : "➕"}</span>
                  {editId ? "Ishonch Telefonini Tahrirlash" : "Yangi Ishonch Telefoni Qo'shish"}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Telegram botdagi tegishli katalog tugmasi ostida ko&apos;rinadi
                </p>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 flex items-center justify-center"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
                  {error}
                </div>
              )}

              {/* Category Quick Presets */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Katalog / Kategoriya tanlash:
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
                  {PRESET_CATEGORIES.map((preset) => (
                    <button
                      key={preset.uz}
                      type="button"
                      onClick={() =>
                        setForm({
                          ...form,
                          category_uz: preset.uz,
                          category_ru: preset.ru,
                        })
                      }
                      className={`px-3 py-2 text-xs rounded-lg text-left border transition-all ${
                        form.category_uz === preset.uz
                          ? "bg-blue-50 border-blue-300 text-blue-700 font-semibold"
                          : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      📂 {preset.uz}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Category Input (if needed) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Kategoriya nomi (O&apos;zbekcha)
                  </label>
                  <input
                    required
                    value={form.category_uz}
                    onChange={(e) => setForm({ ...form, category_uz: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Kategoriya nomi (Ruscha)
                  </label>
                  <input
                    required
                    value={form.category_ru}
                    onChange={(e) => setForm({ ...form, category_ru: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Organization names */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Tashkilot / Idora nomi (O&apos;zbekcha)
                  </label>
                  <input
                    required
                    value={form.organization_uz}
                    onChange={(e) => setForm({ ...form, organization_uz: e.target.value })}
                    placeholder="Masalan: Bosh prokuratura ishonch telefoni"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Tashkilot nomi (Ruscha)
                  </label>
                  <input
                    required
                    value={form.organization_ru}
                    onChange={(e) => setForm({ ...form, organization_ru: e.target.value })}
                    placeholder="Например: Генеральная прокуратура РУз"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Phone and Order */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Ishonch telefon raqami
                  </label>
                  <input
                    required
                    value={form.phone_number}
                    onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                    placeholder="Masalan: 1007 yoki +998 71 123 45 67"
                    className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Ko&apos;rsatilish tartibi (Order)
                  </label>
                  <input
                    type="number"
                    value={form.order}
                    onChange={(e) => setForm({ ...form, order: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Descriptions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Qisqacha tavsif (O&apos;zbekcha)
                  </label>
                  <textarea
                    rows={2}
                    value={form.description_uz}
                    onChange={(e) => setForm({ ...form, description_uz: e.target.value })}
                    placeholder="Masalan: Qonun buzilishi va korrupsiya holatlari bo'yicha"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Qisqacha tavsif (Ruscha)
                  </label>
                  <textarea
                    rows={2}
                    value={form.description_ru}
                    onChange={(e) => setForm({ ...form, description_ru: e.target.value })}
                    placeholder="Краткое описание на русском"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Active Toggle */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                />
                <label htmlFor="is_active" className="text-xs font-medium text-slate-700">
                  Ushbu ishonch telefoni botda faol ko&apos;rinsin
                </label>
              </div>

              {/* Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 text-xs font-semibold bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "Saqlanmoqda..." : "Saqlash"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
