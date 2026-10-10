"use client";

import { useEffect, useState } from "react";
import {
  getTransactions,
  updateTransactionStatus,
  type Transaction,
} from "@/lib/api";
import { formatCurrency, formatDate, getStatusColor } from "@/lib/utils";

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await getTransactions(filter || undefined, 100);
      setTransactions(data);
    } catch (err) {
      console.error("Error loading transactions:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [filter]);

  async function handleStatusChange(txId: number, newStatus: string) {
    try {
      await updateTransactionStatus(txId, newStatus);
      setTransactions((prev) =>
        prev.map((t) => (t.id === txId ? { ...t, payment_status: newStatus } : t))
      );
    } catch (err) {
      console.error("Error updating transaction status:", err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">To&apos;lovlar va Tranzaksiyalar</h1>
          <p className="text-sm text-slate-500 mt-1">
            Barcha to&apos;lovlar, kvitansiyalar va holatlar
          </p>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
        >
          <option value="">Barcha to&apos;lovlar</option>
          <option value="pending">⏳ Kutilmoqda</option>
          <option value="completed">✅ Tasdiqlangan</option>
          <option value="failed">❌ Bekor qilingan</option>
          <option value="refunded">↩️ Qaytarilgan</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">ID</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Mijoz</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Summa</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Usul</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Holat</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Tranzaksiya Ref</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Sana</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Amal</th>
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
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-slate-400 font-medium">
                    Tranzaksiyalar topilmadi
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-5 py-4 font-mono text-slate-400 text-xs">#{tx.id}</td>
                    <td className="px-5 py-4">
                      <div className="font-semibold text-slate-900">{tx.user_name}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5 font-mono">TG: {tx.telegram_id}</div>
                    </td>
                    <td className="px-5 py-4 font-bold text-slate-900">
                      {formatCurrency(tx.amount)}
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-[11px] font-semibold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md uppercase tracking-wide border border-slate-200">
                        {tx.payment_method}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`text-[11px] px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(
                          tx.payment_status
                        )}`}
                      >
                        {tx.payment_status}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono text-[11px] text-slate-500">
                      {tx.transaction_ref || "—"}
                    </td>
                    <td className="px-5 py-4 text-slate-500 text-xs font-medium">
                      {formatDate(tx.created_at)}
                    </td>
                    <td className="px-5 py-4">
                      <select
                        value={tx.payment_status}
                        onChange={(e) => handleStatusChange(tx.id, e.target.value)}
                        className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 hover:border-slate-400 focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="pending">Kutilmoqda</option>
                        <option value="completed">Tasdiqlash</option>
                        <option value="failed">Bekor qilish</option>
                        <option value="refunded">Qaytarish</option>
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
          ) : transactions.length === 0 ? (
            <div className="text-center py-16 text-slate-400 font-medium">
              Tranzaksiyalar topilmadi
            </div>
          ) : (
            transactions.map((tx) => (
              <div key={tx.id} className="p-4 space-y-3 hover:bg-slate-50 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-slate-400 text-xs">#{tx.id}</span>
                  <span className={`text-[11px] px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(tx.payment_status)}`}>
                    {tx.payment_status}
                  </span>
                </div>
                <div>
                  <div className="font-semibold text-slate-900">{tx.user_name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-bold text-slate-900">{formatCurrency(tx.amount)}</span>
                    <span className="text-[10px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase border border-slate-200">
                      {tx.payment_method}
                    </span>
                  </div>
                </div>
                <div>
                  <select
                    value={tx.payment_status}
                    onChange={(e) => handleStatusChange(tx.id, e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 hover:border-slate-400 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="pending">Kutilmoqda</option>
                    <option value="completed">Tasdiqlash</option>
                    <option value="failed">Bekor qilish</option>
                    <option value="refunded">Qaytarish</option>
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
