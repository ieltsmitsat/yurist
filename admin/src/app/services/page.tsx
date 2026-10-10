"use client";

import { useEffect, useState } from "react";
import { getServices, createService, updateService, deleteService, type Service } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({
    title_uz: "",
    title_ru: "",
    description_uz: "",
    description_ru: "",
    price: "",
    service_type: "consultation",
    is_active: true,
  });

  async function load() {
    setLoading(true);
    try {
      setServices(await getServices());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function resetForm() {
    setForm({ title_uz: "", title_ru: "", description_uz: "", description_ru: "", price: "", service_type: "consultation", is_active: true });
    setEditId(null);
    setShowForm(false);
  }

  function startEdit(s: Service) {
    setForm({
      title_uz: s.title_uz,
      title_ru: s.title_ru,
      description_uz: s.description_uz || "",
      description_ru: s.description_ru || "",
      price: String(s.price),
      service_type: s.service_type,
      is_active: s.is_active,
    });
    setEditId(s.id);
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = { ...form, price: parseFloat(form.price) };
    try {
      if (editId) {
        await updateService(editId, data);
      } else {
        await createService(data);
      }
      resetForm();
      load();
    } catch (err) {
      console.error(err);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Xizmatni o'chirishni tasdiqlaysizmi?")) return;
    try {
      await deleteService(id);
      load();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Xizmatlar</h1>
          <p className="text-sm text-slate-500 mt-1">Yuridik xizmatlar katalogi boshqaruvi</p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm flex items-center gap-2"
        >
          <span>+</span> Yangi xizmat
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-slate-100">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-lg">
              {editId ? "✏️" : "✨"}
            </div>
            <h3 className="text-lg font-bold text-slate-800">{editId ? "Xizmatni tahrirlash" : "Yangi xizmat qo'shish"}</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Nomi (UZ)</label>
              <input
                value={form.title_uz}
                onChange={(e) => setForm({ ...form, title_uz: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                placeholder="Xizmat nomi o'zbek tilida"
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Nomi (RU)</label>
              <input
                value={form.title_ru}
                onChange={(e) => setForm({ ...form, title_ru: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                placeholder="Xizmat nomi rus tilida"
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Tavsif (UZ)</label>
              <textarea
                value={form.description_uz}
                onChange={(e) => setForm({ ...form, description_uz: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                placeholder="Batafsil tavsif o'zbek tilida"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Tavsif (RU)</label>
              <textarea
                value={form.description_ru}
                onChange={(e) => setForm({ ...form, description_ru: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                placeholder="Batafsil tavsif rus tilida"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Narxi (so'm)</label>
              <input
                type="number"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                placeholder="0"
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-semibold text-slate-700 mb-1.5 uppercase tracking-wide">Turi</label>
              <select
                value={form.service_type}
                onChange={(e) => setForm({ ...form, service_type: e.target.value })}
                className="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="consultation">Konsultatsiya</option>
                <option value="audit">Audit</option>
                <option value="claim">Da'vo ariza</option>
                <option value="court">Sud himoyasi</option>
                <option value="retainer">Oylik hamrohlik</option>
              </select>
            </div>
            <div className="col-span-1 md:col-span-2 flex items-center gap-2 mt-2">
              <input
                type="checkbox"
                id="is_active"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="is_active" className="text-sm font-medium text-slate-700 cursor-pointer">
                Ushbu xizmat faol va mijozlarga ko'rinadi
              </label>
            </div>
          </div>
          
          <div className="flex gap-3 mt-6 pt-5 border-t border-slate-100">
            <button type="submit" className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors">
              {editId ? "Saqlash" : "Qo'shish"}
            </button>
            <button type="button" onClick={resetForm} className="px-5 py-2.5 bg-white border border-slate-300 text-slate-700 text-sm font-semibold rounded-xl hover:bg-slate-50 transition-colors">
              Bekor qilish
            </button>
          </div>
        </form>
      )}

      {/* Services Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Xizmat nomi</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Turi</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Narxi</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Holati</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider text-right">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-16 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full" />
                      Yuklanmoqda...
                    </div>
                  </td>
                </tr>
              ) : services.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-16 text-slate-400 font-medium">
                    Hozircha xizmatlar mavjud emas
                  </td>
                </tr>
              ) : (
                services.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{s.title_uz}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{s.title_ru}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-[11px] font-semibold bg-indigo-50 border border-indigo-100 text-indigo-700 px-2.5 py-1 rounded-md uppercase tracking-wide">
                        {s.service_type}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-bold text-slate-900">{formatCurrency(s.price)}</td>
                    <td className="px-5 py-4">
                      <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md uppercase tracking-wide ${
                        s.is_active 
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200" 
                          : "bg-red-50 text-red-700 border border-red-200"
                      }`}>
                        {s.is_active ? "Faol" : "Nofaol"}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button 
                          onClick={() => startEdit(s)} 
                          className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 hover:text-indigo-600 transition-colors text-[13px] font-medium shadow-sm flex items-center gap-1.5"
                        >
                          ✏️ Tahrir
                        </button>
                        <button 
                          onClick={() => handleDelete(s.id)} 
                          className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors text-[13px] font-medium shadow-sm flex items-center gap-1.5"
                        >
                          🗑 O'chirish
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
