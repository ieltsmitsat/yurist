"use client";

import { useEffect, useState } from "react";
import { getLeads, updateLeadStatus, type Lead } from "@/lib/api";
import { formatDate, getStatusColor, PIPELINE_STAGES } from "@/lib/utils";

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await getLeads(filter || undefined, 100);
      setLeads(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  async function handleStatusChange(userId: number, newStatus: string) {
    try {
      await updateLeadStatus(userId, newStatus);
      setLeads((prev) =>
        prev.map((l) => (l.id === userId ? { ...l, lead_status: newStatus } : l))
      );
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Leadlar (CRM)</h1>
          <p className="text-sm text-slate-500 mt-1">Mijozlar va lead pipeline boshqaruvi</p>
        </div>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Barchasi</option>
            {PIPELINE_STAGES.map((s) => (
              <option key={s.key} value={s.key}>
                {s.emoji} {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">ID</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Ism</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Telefon</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Til</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Savollar</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Sana</th>
                <th className="text-left px-4 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Amallar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full" />
                      Yuklanmoqda...
                    </div>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-slate-400">
                    Lead topilmadi
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-slate-400 text-xs">#{lead.id}</td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-900">{lead.full_name || "—"}</div>
                      <div className="text-xs text-slate-400 mt-0.5">TG: {lead.telegram_id}</div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-700">{lead.phone_number || "—"}</td>
                    <td className="px-4 py-3.5">
                      <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-medium uppercase">
                        {lead.language}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${getStatusColor(lead.lead_status)}`}>
                        {lead.lead_status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-slate-700 font-medium">{lead.free_questions_left}</td>
                    <td className="px-4 py-3.5 text-slate-500 text-xs">{formatDate(lead.created_at)}</td>
                    <td className="px-4 py-3.5">
                      <select
                        value={lead.lead_status}
                        onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                        className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 hover:border-slate-300"
                      >
                        {PIPELINE_STAGES.map((s) => (
                          <option key={s.key} value={s.key}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Mobile View */}
        <div className="md:hidden divide-y divide-slate-100">
          {loading ? (
            <div className="text-center py-16 text-slate-400">
              <div className="flex flex-col items-center gap-2">
                <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full" />
                Yuklanmoqda...
              </div>
            </div>
          ) : leads.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              Lead topilmadi
            </div>
          ) : (
            leads.map((lead) => (
              <div key={lead.id} className="p-4 space-y-3 hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-slate-400 text-xs">#{lead.id}</span>
                  <span className={`text-[11px] px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(lead.lead_status)}`}>
                    {lead.lead_status}
                  </span>
                </div>
                <div>
                  <div className="font-medium text-slate-900">{lead.full_name || "—"}</div>
                  <div className="text-sm text-slate-600 mt-1">{lead.phone_number || "—"}</div>
                </div>
                <div>
                  <select
                    value={lead.lead_status}
                    onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                    className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white text-slate-700 hover:border-slate-300"
                  >
                    {PIPELINE_STAGES.map((s) => (
                      <option key={s.key} value={s.key}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
