"use client";

import { useEffect, useState } from "react";
import { getHelplines, createHelpline, updateHelpline, deleteHelpline, type Helpline } from "@/lib/api";

export default function HelplinesPage() {
  const [items, setItems] = useState<Helpline[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({
    category_uz: "Boshqa",
    category_ru: "Другие",
    organization_uz: "",
    organization_ru: "",
    phone_number: "",
    description_uz: "",
    description_ru: "",
    order: "0",
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        order: parseInt(form.order) || 0,
      };

      if (editId) {
        await updateHelpline(editId, payload);
      } else {
        await createHelpline(payload);
      }
      setShowForm(false);
      load();
    } catch (err) {
      alert("Xatolik yuz berdi");
    }
  }

  function handleEdit(h: Helpline) {
    setEditId(h.id);
    setForm({
      category_uz: h.category_uz || "Boshqa",
      category_ru: h.category_ru || "Другие",
      organization_uz: h.organization_uz,
      organization_ru: h.organization_ru,
      phone_number: h.phone_number,
      description_uz: h.description_uz || "",
      description_ru: h.description_ru || "",
      order: h.order.toString(),
      is_active: h.is_active,
    });
    setShowForm(true);
  }

  async function handleDelete(id: number) {
    if (!confirm("O'chirilsinmi?")) return;
    try {
      await deleteHelpline(id);
      load();
    } catch (err) {
      alert("Xatolik yuz berdi");
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-6">
        <h1 className="text-2xl font-bold">Ishonch Telefonlari</h1>
        <button
          onClick={() => {
            setEditId(null);
            setForm({
              category_uz: "Boshqa",
              category_ru: "Другие",
              organization_uz: "",
              organization_ru: "",
              phone_number: "",
              description_uz: "",
              description_ru: "",
              order: "0",
              is_active: true,
            });
            setShowForm(true);
          }}
          className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700"
        >
          Yangi Qo'shish
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm border mb-8 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Kategoriya (UZ)</label>
            <input required value={form.category_uz} onChange={(e) => setForm({...form, category_uz: e.target.value})} className="w-full border rounded p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Kategoriya (RU)</label>
            <input required value={form.category_ru} onChange={(e) => setForm({...form, category_ru: e.target.value})} className="w-full border rounded p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tashkilot nomi (UZ)</label>
            <input required value={form.organization_uz} onChange={(e) => setForm({...form, organization_uz: e.target.value})} className="w-full border rounded p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tashkilot nomi (RU)</label>
            <input required value={form.organization_ru} onChange={(e) => setForm({...form, organization_ru: e.target.value})} className="w-full border rounded p-2" />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Telefon raqami</label>
            <input required value={form.phone_number} onChange={(e) => setForm({...form, phone_number: e.target.value})} className="w-full border rounded p-2" placeholder="Masalan: 1007 yoki +998 71 123 45 67" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tartib (Order)</label>
            <input type="number" value={form.order} onChange={(e) => setForm({...form, order: e.target.value})} className="w-full border rounded p-2" />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Tavsif (UZ)</label>
            <textarea value={form.description_uz} onChange={(e) => setForm({...form, description_uz: e.target.value})} className="w-full border rounded p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tavsif (RU)</label>
            <textarea value={form.description_ru} onChange={(e) => setForm({...form, description_ru: e.target.value})} className="w-full border rounded p-2" />
          </div>

          <div className="col-span-1 md:col-span-2 flex items-center gap-2">
            <input type="checkbox" id="is_active" checked={form.is_active} onChange={(e) => setForm({...form, is_active: e.target.checked})} />
            <label htmlFor="is_active">Faol</label>
          </div>

          <div className="col-span-1 md:col-span-2 flex flex-col sm:flex-row gap-4 mt-4">
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">Saqlash</button>
            <button type="button" onClick={() => setShowForm(false)} className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300">Bekor qilish</button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Yuklanmoqda...</p>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="p-4 font-medium text-gray-600">ID</th>
                  <th className="p-4 font-medium text-gray-600">Kategoriya</th>
                  <th className="p-4 font-medium text-gray-600">Tashkilot</th>
                  <th className="p-4 font-medium text-gray-600">Telefon</th>
                  <th className="p-4 font-medium text-gray-600">Holat</th>
                  <th className="p-4 font-medium text-gray-600">Amallar</th>
                </tr>
              </thead>
              <tbody>
                {items.map(h => (
                  <tr key={h.id} className="border-b hover:bg-gray-50">
                    <td className="p-4">{h.id}</td>
                    <td className="p-4 text-gray-500">{h.category_uz}</td>
                    <td className="p-4 font-medium text-blue-600">{h.organization_uz}</td>
                    <td className="p-4 font-mono">{h.phone_number}</td>
                    <td className="p-4">
                      {h.is_active ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">Faol</span>
                      ) : (
                        <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">Faol emas</span>
                      )}
                    </td>
                    <td className="p-4 flex gap-2">
                      <button onClick={() => handleEdit(h)} className="text-sm bg-gray-100 px-3 py-1 rounded hover:bg-gray-200">Tahrirlash</button>
                      <button onClick={() => handleDelete(h.id)} className="text-sm bg-red-50 text-red-600 px-3 py-1 rounded hover:bg-red-100">O'chirish</button>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-gray-500">
                      Ma'lumot topilmadi
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile View */}
          <div className="md:hidden divide-y divide-gray-100">
            {items.map((h) => (
              <div key={h.id} className="p-4 space-y-3 hover:bg-gray-50">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium text-blue-600">{h.organization_uz}</div>
                    <div className="text-sm text-gray-500 mt-1">{h.category_uz}</div>
                  </div>
                  <div>
                    {h.is_active ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-[10px] uppercase font-bold rounded-full">Faol</span>
                    ) : (
                      <span className="px-2 py-1 bg-red-100 text-red-700 text-[10px] uppercase font-bold rounded-full">Faol emas</span>
                    )}
                  </div>
                </div>
                <div className="font-mono text-sm">{h.phone_number}</div>
                <div className="flex gap-2 pt-2">
                  <button onClick={() => handleEdit(h)} className="flex-1 text-sm bg-gray-100 py-1.5 rounded hover:bg-gray-200 font-medium text-gray-700">Tahrirlash</button>
                  <button onClick={() => handleDelete(h.id)} className="flex-1 text-sm bg-red-50 text-red-600 py-1.5 rounded hover:bg-red-100 font-medium">O'chirish</button>
                </div>
              </div>
            ))}
            {items.length === 0 && (
              <div className="p-8 text-center text-gray-500">
                Ma'lumot topilmadi
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
