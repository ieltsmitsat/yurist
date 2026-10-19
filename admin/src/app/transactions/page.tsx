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
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);

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
    setUpdatingId(txId);
    try {
      await updateTransactionStatus(txId, newStatus);
      setTransactions((prev) =>
        prev.map((t) => (t.id === txId ? { ...t, payment_status: newStatus } : t))
      );
      if (selectedTx && selectedTx.id === txId) {
        setSelectedTx((prev) => prev ? { ...prev, payment_status: newStatus } : null);
      }
    } catch (err) {
      console.error("Error updating transaction status:", err);
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">To&apos;lovlar va Tranzaksiyalar</h1>
          <p className="text-sm text-slate-500 mt-1">
            Mijozlar to&apos;lovlari, sotib olingan xizmatlar va muammolar tavsifi
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
          >
            <option value="">Barcha to&apos;lovlar</option>
            <option value="pending">⏳ Kutilmoqda</option>
            <option value="completed">✅ Tasdiqlangan</option>
            <option value="fulfilled">🏁 Bajarildi</option>
            <option value="failed">❌ Bekor qilingan</option>
            <option value="refunded">↩️ Qaytarilgan</option>
          </select>
          <button
            onClick={() => load()}
            className="px-3 py-2 text-sm bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700 font-medium transition-colors shadow-sm"
          >
            🔄 Yangilash
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="hidden lg:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">ID</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Mijoz va Kontakt</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Sotib olingan xizmat</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Mijoz muammosi haqida</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Summa / Usul</th>
                <th className="text-left px-5 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">Holat</th>
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
                    <td className="px-5 py-4 font-mono text-slate-400 text-xs align-top">#{tx.id}</td>
                    
                    {/* Mijoz va Kontakt */}
                    <td className="px-5 py-4 align-top">
                      <div className="font-semibold text-slate-900">{tx.user_name}</div>
                      <div className="text-xs text-indigo-600 font-medium mt-0.5">
                        {tx.phone_number ? (
                          <a href={`tel:${tx.phone_number}`} className="hover:underline">
                            📞 {tx.phone_number}
                          </a>
                        ) : (
                          <span className="text-slate-400">Telefon yo&apos;q</span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5 font-mono">TG: {tx.telegram_id}</div>
                    </td>

                    {/* Sotib olingan xizmat */}
                    <td className="px-5 py-4 align-top">
                      <div className="font-medium text-slate-900">
                        {tx.service_title || tx.transaction_ref || "Yuridik xizmat"}
                      </div>
                      {tx.transaction_ref && tx.transaction_ref !== tx.service_title && (
                        <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                          Ref: {tx.transaction_ref}
                        </div>
                      )}
                    </td>

                    {/* Mijoz muammosi haqida */}
                    <td className="px-5 py-4 align-top max-w-xs">
                      {tx.problem_summary ? (
                        <div className="group">
                          <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                            {tx.problem_summary}
                          </p>
                          <button
                            onClick={() => setSelectedTx(tx)}
                            className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium mt-1 underline"
                          >
                            Batafsil o&apos;qish
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400 italic">Muammo ko&apos;rsatilmagan</span>
                      )}
                    </td>

                    {/* Summa / Usul */}
                    <td className="px-5 py-4 align-top whitespace-nowrap">
                      <div className="font-bold text-slate-900">{formatCurrency(tx.amount)}</div>
                      <div className="mt-1">
                        <span className="text-[10px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md uppercase tracking-wide border border-slate-200">
                          {tx.payment_method}
                        </span>
                      </div>
                    </td>

                    {/* Holat */}
                    <td className="px-5 py-4 align-top whitespace-nowrap">
                      <span
                        className={`text-[11px] px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(
                          tx.payment_status
                        )}`}
                      >
                        {tx.payment_status}
                      </span>
                    </td>

                    {/* Sana */}
                    <td className="px-5 py-4 align-top text-slate-500 text-xs font-medium whitespace-nowrap">
                      {formatDate(tx.created_at)}
                    </td>

                    {/* Amal */}
                    <td className="px-5 py-4 align-top whitespace-nowrap">
                      <div className="flex flex-col gap-1.5">
                        {tx.payment_status === "pending" && (
                          <div className="flex items-center gap-1">
                            <button
                              disabled={updatingId === tx.id}
                              onClick={() => handleStatusChange(tx.id, "completed")}
                              title="To'lovni tasdiqlash"
                              className="px-2 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium shadow-sm transition-colors"
                            >
                              ✅ Tasdiqlash
                            </button>
                            <button
                              disabled={updatingId === tx.id}
                              onClick={() => handleStatusChange(tx.id, "failed")}
                              title="To'lovni bekor qilish"
                              className="px-2 py-1 text-xs bg-rose-600 hover:bg-rose-700 text-white rounded font-medium shadow-sm transition-colors"
                            >
                              ❌ Bekor
                            </button>
                          </div>
                        )}
                        {tx.payment_status === "completed" && (
                          <button
                            disabled={updatingId === tx.id}
                            onClick={() => handleStatusChange(tx.id, "fulfilled")}
                            title="Xizmat bajarildi deb belgilash"
                            className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded font-medium shadow-sm transition-colors text-center"
                          >
                            🏁 Ish bajarildi
                          </button>
                        )}
                        <select
                          value={tx.payment_status}
                          disabled={updatingId === tx.id}
                          onChange={(e) => handleStatusChange(tx.id, e.target.value)}
                          className="text-xs border border-slate-300 rounded-lg px-2 py-1 bg-white text-slate-700 hover:border-slate-400 focus:ring-2 focus:ring-indigo-500"
                        >
                          <option value="pending">⏳ Kutilmoqda</option>
                          <option value="completed">✅ Tasdiqlangan</option>
                          <option value="fulfilled">🏁 Bajarildi</option>
                          <option value="failed">❌ Bekor qilingan</option>
                          <option value="refunded">↩️ Qaytarilgan</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile / Tablet Cards View */}
        <div className="lg:hidden divide-y divide-slate-100">
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
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500">
                    {tx.phone_number && (
                      <span className="text-indigo-600 font-medium">
                        📞 {tx.phone_number}
                      </span>
                    )}
                    <span className="font-mono text-[11px]">TG: {tx.telegram_id}</span>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-1">
                  <div>
                    <span className="text-slate-500">Xizmat:</span>{" "}
                    <span className="font-semibold text-slate-800">
                      {tx.service_title || tx.transaction_ref || "Yuridik xizmat"}
                    </span>
                  </div>
                  {tx.problem_summary && (
                    <div>
                      <span className="text-slate-500">Muammo:</span>{" "}
                      <span className="text-slate-700 italic">
                        {tx.problem_summary.length > 100
                          ? `${tx.problem_summary.slice(0, 97)}...`
                          : tx.problem_summary}
                      </span>
                      {tx.problem_summary.length > 100 && (
                        <button
                          onClick={() => setSelectedTx(tx)}
                          className="ml-1 text-indigo-600 font-medium underline"
                        >
                          batafsil
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-900">{formatCurrency(tx.amount)}</span>
                    <span className="ml-2 text-[10px] font-semibold bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase border border-slate-200">
                      {tx.payment_method}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 font-medium">
                    {formatDate(tx.created_at)}
                  </span>
                </div>

                <div className="pt-1 flex flex-col gap-2">
                  {tx.payment_status === "pending" && (
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        disabled={updatingId === tx.id}
                        onClick={() => handleStatusChange(tx.id, "completed")}
                        className="py-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium shadow-sm transition-colors text-center"
                      >
                        ✅ Tasdiqlash
                      </button>
                      <button
                        disabled={updatingId === tx.id}
                        onClick={() => handleStatusChange(tx.id, "failed")}
                        className="py-1.5 text-xs bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-medium shadow-sm transition-colors text-center"
                      >
                        ❌ Bekor qilish
                      </button>
                    </div>
                  )}
                  {tx.payment_status === "completed" && (
                    <button
                      disabled={updatingId === tx.id}
                      onClick={() => handleStatusChange(tx.id, "fulfilled")}
                      className="w-full py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-sm transition-colors text-center"
                    >
                      🏁 Ish bajarildi (Mijozga baholash yuborish)
                    </button>
                  )}
                  <select
                    value={tx.payment_status}
                    disabled={updatingId === tx.id}
                    onChange={(e) => handleStatusChange(tx.id, e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700 hover:border-slate-400 focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="pending">⏳ Kutilmoqda</option>
                    <option value="completed">✅ Tasdiqlangan</option>
                    <option value="fulfilled">🏁 Bajarildi</option>
                    <option value="failed">❌ Bekor qilingan</option>
                    <option value="refunded">↩️ Qaytarilgan</option>
                  </select>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal: Full Transaction & Problem Detail */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="font-bold text-slate-900 text-lg">
                  To&apos;lov #{selectedTx.id} - To&apos;liq ma&apos;lumot
                </h3>
                <p className="text-xs text-slate-500">{formatDate(selectedTx.created_at)}</p>
              </div>
              <button
                onClick={() => setSelectedTx(null)}
                className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 space-y-1.5">
                <div>
                  <span className="text-slate-500 text-xs">Mijoz:</span>{" "}
                  <span className="font-semibold text-slate-900">{selectedTx.user_name}</span>
                </div>
                <div>
                  <span className="text-slate-500 text-xs">Telefon:</span>{" "}
                  {selectedTx.phone_number ? (
                    <a href={`tel:${selectedTx.phone_number}`} className="font-semibold text-indigo-600 hover:underline">
                      📞 {selectedTx.phone_number}
                    </a>
                  ) : (
                    <span className="text-slate-400 italic">Kiritilmagan</span>
                  )}
                </div>
                <div>
                  <span className="text-slate-500 text-xs">Telegram ID:</span>{" "}
                  <code className="text-xs bg-slate-200/70 px-1.5 py-0.5 rounded text-slate-800">
                    {selectedTx.telegram_id}
                  </code>
                </div>
              </div>

              <div className="bg-indigo-50/60 p-3 rounded-xl border border-indigo-100/60 space-y-1">
                <div className="text-xs text-indigo-700 font-semibold uppercase tracking-wider">
                  Sotib olingan xizmat
                </div>
                <div className="font-bold text-slate-900 text-base">
                  {selectedTx.service_title || selectedTx.transaction_ref || "Yuridik xizmat"}
                </div>
                <div className="text-xs text-slate-600 pt-1 flex items-center justify-between">
                  <span>To&apos;lov summasi:</span>
                  <span className="font-bold text-slate-900">{formatCurrency(selectedTx.amount)}</span>
                </div>
                <div className="text-xs text-slate-600 flex items-center justify-between">
                  <span>To&apos;lov usuli:</span>
                  <span className="font-medium text-slate-800 uppercase">{selectedTx.payment_method}</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Mijoz muammosi haqida
                </div>
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 text-xs leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {selectedTx.problem_summary || "Ushbu to'lov uchun murojaat matni topilmadi."}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${getStatusColor(
                  selectedTx.payment_status
                )}`}
              >
                {selectedTx.payment_status}
              </span>
              <div className="flex items-center gap-2">
                {selectedTx.payment_status === "pending" && (
                  <>
                    <button
                      disabled={updatingId === selectedTx.id}
                      onClick={() => handleStatusChange(selectedTx.id, "completed")}
                      className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium shadow-sm transition-colors"
                    >
                      ✅ Tasdiqlash
                    </button>
                    <button
                      disabled={updatingId === selectedTx.id}
                      onClick={() => handleStatusChange(selectedTx.id, "failed")}
                      className="px-3 py-1.5 text-xs bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-medium shadow-sm transition-colors"
                    >
                      ❌ Bekor qilish
                    </button>
                  </>
                )}
                {selectedTx.payment_status === "completed" && (
                  <button
                    disabled={updatingId === selectedTx.id}
                    onClick={() => handleStatusChange(selectedTx.id, "fulfilled")}
                    className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-sm transition-colors"
                  >
                    🏁 Ish bajarildi
                  </button>
                )}
                <button
                  onClick={() => setSelectedTx(null)}
                  className="px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors"
                >
                  Yopish
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
