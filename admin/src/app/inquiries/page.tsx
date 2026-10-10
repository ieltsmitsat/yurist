"use client";

import { useEffect, useState } from "react";
import { getInquiries, approveInquiry, type Inquiry } from "@/lib/api";
import { formatDate, getStatusColor } from "@/lib/utils";

export default function InquiriesPage() {
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  async function load() {
    setLoading(true);
    try {
      const data = await getInquiries(filter || undefined, 100);
      setInquiries(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  async function handleApprove(id: number) {
    try {
      await approveInquiry(id, editText);
      setInquiries((prev) =>
        prev.map((i) =>
          i.id === id ? { ...i, status: "approved", final_response: editText } : i
        )
      );
      setEditingId(null);
      setEditText("");
    } catch (err) {
      console.error(err);
    }
  }

  function getRiskBadge(level: string | null) {
    if (!level) return <span className="text-xs text-slate-400">—</span>;
    const colors: Record<string, string> = {
      low: "bg-emerald-100 text-emerald-800 border border-emerald-200",
      medium: "bg-amber-100 text-amber-800 border border-amber-200",
      high: "bg-red-100 text-red-800 border border-red-200",
    };
    const emojis: Record<string, string> = { low: "🟢", medium: "🟡", high: "🔴" };
    return (
      <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wide ${colors[level] || "bg-slate-100 text-slate-600 border border-slate-200"}`}>
        {emojis[level] || ""} {level}
      </span>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">So&apos;rovlar</h1>
          <p className="text-sm text-slate-500 mt-1">Yuridik savollar, AI javoblar va tasdiq</p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">Barcha xavf darajasi</option>
          <option value="low">🟢 Past</option>
          <option value="medium">🟡 O&apos;rta</option>
          <option value="high">🔴 Yuqori</option>
        </select>
      </div>

      <div className="space-y-5">
        {loading ? (
          <div className="text-center py-16 text-slate-400">
            <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
            Yuklanmoqda...
          </div>
        ) : inquiries.length === 0 ? (
          <div className="text-center py-16 text-slate-400">So&apos;rov topilmadi</div>
        ) : (
          inquiries.map((inq) => (
            <div key={inq.id} className="bg-white rounded-xl border border-slate-200 p-4 md:p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex flex-wrap items-center gap-2 justify-between mb-4 pb-4 border-b border-slate-100">
                <div className="flex flex-wrap items-center gap-2 md:gap-3">
                  <span className="text-sm font-mono text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md">#{inq.id}</span>
                  {getRiskBadge(inq.risk_level)}
                  <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(inq.status)}`}>
                    {inq.status}
                  </span>
                  {inq.risk_score !== null && (
                    <span className="text-xs font-semibold text-slate-500 bg-slate-50 px-2 py-0.5 rounded-md">Score: {inq.risk_score}/100</span>
                  )}
                </div>
                <span className="text-xs font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-md">{formatDate(inq.created_at)}</span>
              </div>

              {/* Question */}
              <div className="mb-4">
                <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <span className="text-sm">❓</span> Savol
                </h4>
                <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100">{inq.question_text || inq.stt_transcript || "—"}</p>
              </div>

              {/* AI Draft */}
              {inq.ai_draft_response && (
                <div className="mb-4">
                  <h4 className="text-[11px] font-bold text-indigo-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <span className="text-sm">🤖</span> AI Javob (Qoralama)
                  </h4>
                  <p className="text-sm text-indigo-900 leading-relaxed bg-indigo-50 p-4 rounded-lg border border-indigo-100 whitespace-pre-wrap">{inq.ai_draft_response}</p>
                </div>
              )}

              {/* Upsell offer */}
              {inq.ai_upsell_offer && (
                <div className="mb-4">
                  <h4 className="text-[11px] font-bold text-amber-600 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <span className="text-sm">💡</span> Upsell taklif
                  </h4>
                  <p className="text-sm text-amber-900 leading-relaxed bg-amber-50 p-4 rounded-lg border border-amber-100">{inq.ai_upsell_offer}</p>
                </div>
              )}

              {/* Final Response / Approve */}
              {inq.final_response ? (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <h4 className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <span className="text-sm">✅</span> Tasdiqlangan javob
                  </h4>
                  <p className="text-sm text-emerald-900 leading-relaxed bg-emerald-50 p-4 rounded-lg border border-emerald-100 whitespace-pre-wrap">{inq.final_response}</p>
                </div>
              ) : editingId === inq.id ? (
                <div className="space-y-3 mt-4 pt-4 border-t border-slate-100">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    placeholder="Yakuniy javobni tahrirlang..."
                    className="w-full border border-slate-300 rounded-xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                    rows={4}
                  />
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={() => handleApprove(inq.id)}
                      className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
                    >
                      Tasdiqlash va Yuborish
                    </button>
                    <button
                      onClick={() => { setEditingId(null); setEditText(""); }}
                      className="px-5 py-2.5 bg-white border border-slate-300 text-slate-700 text-sm font-semibold rounded-xl hover:bg-slate-50 transition-colors"
                    >
                      Bekor qilish
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <button
                    onClick={() => { setEditingId(inq.id); setEditText(inq.ai_draft_response || ""); }}
                    className="w-full sm:w-auto px-5 py-2.5 bg-white border border-indigo-200 text-indigo-700 text-sm font-semibold rounded-xl hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2"
                  >
                    ✏️ Tahrirlash va tasdiqlash
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
