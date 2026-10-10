"use client";

import { useEffect, useState } from "react";
import {
  getReferralAnalytics,
  type ReferralAnalytics,
} from "@/lib/api";
import StatsCard from "@/components/stats-card";

export default function ReferralsPage() {
  const [analytics, setAnalytics] = useState<ReferralAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getReferralAnalytics();
        setAnalytics(data);
      } catch (err) {
        console.error("Error loading referral stats:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-3 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Referral & Retargeting Analytics
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Virusli taklif tizimi, konversiya va eng faol refererlar
        </p>
      </div>

      {analytics && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <StatsCard
            title="Jami taklif qilinganlar"
            value={analytics.total_referred}
            subtitle="Referral havolasi orqali kirganlar"
            icon="👥"
            color="indigo"
          />
          <StatsCard
            title="Tasdiqlangan leadlar"
            value={analytics.verified_referred}
            subtitle="Telefon raqamini ulashganlar"
            icon="📱"
            color="green"
          />
          <StatsCard
            title="Konversiya darajasi"
            value={`${analytics.conversion_rate}%`}
            subtitle="Taklif -> Telefon ulashish"
            icon="📈"
            color="purple"
          />
        </div>
      )}

      {/* Top referrers leaderboard */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center text-xl">
            🏆
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Eng faol do&apos;st taklif qiluvchilar
            </h2>
            <p className="text-[13px] text-slate-500">
              Eng ko'p foydalanuvchi taklif qilgan top 10 lik
            </p>
          </div>
        </div>
        
        {analytics && analytics.top_referrers.length === 0 ? (
          <p className="text-sm text-slate-400 py-16 text-center font-medium">
            Hozircha referral orqali foydalanuvchi taklif qilinmagan
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-6 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    O&apos;rin
                  </th>
                  <th className="text-left px-6 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Foydalanuvchi
                  </th>
                  <th className="text-left px-6 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                    Telegram ID
                  </th>
                  <th className="text-left px-6 py-3.5 font-semibold text-slate-600 text-xs uppercase tracking-wider text-right">
                    Taklif qilinganlar
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {analytics?.top_referrers.map((ref, idx) => (
                  <tr
                    key={ref.telegram_id}
                    className="hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-6 py-4 font-bold text-slate-700">
                      {idx === 0 ? (
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-100 text-amber-700">1</span>
                      ) : idx === 1 ? (
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-slate-200 text-slate-700">2</span>
                      ) : idx === 2 ? (
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-orange-100 text-orange-800">3</span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full text-slate-400">{idx + 1}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {ref.full_name}
                    </td>
                    <td className="px-6 py-4 font-mono text-[13px] text-slate-500">
                      {ref.telegram_id}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="bg-indigo-50 border border-indigo-100 text-indigo-700 font-bold px-3 py-1.5 rounded-lg text-xs tracking-wide">
                        {ref.referral_count} ta do&apos;st
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
