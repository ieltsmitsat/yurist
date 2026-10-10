"use client";

import { useEffect, useState } from "react";
import {
  getDashboardStats,
  getLeadPipeline,
  getRiskBreakdown,
  getUsersChart,
  getInquiriesChart,
  type DashboardStats,
  type PipelineItem,
  type RiskItem,
  type ChartPoint,
} from "@/lib/api";
import { formatCurrency, getRiskColor, PIPELINE_STAGES } from "@/lib/utils";
import StatsCard from "@/components/stats-card";
import SimpleChart from "@/components/simple-chart";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pipeline, setPipeline] = useState<PipelineItem[]>([]);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [usersChart, setUsersChart] = useState<ChartPoint[]>([]);
  const [inquiriesChart, setInquiriesChart] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, p, r, uc, ic] = await Promise.all([
          getDashboardStats(),
          getLeadPipeline(),
          getRiskBreakdown(),
          getUsersChart(30),
          getInquiriesChart(30),
        ]);
        setStats(s);
        setPipeline(p);
        setRisks(r);
        setUsersChart(uc);
        setInquiriesChart(ic);
      } catch (err) {
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Yurist LegalTech umumiy ko'rsatkichlar</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <StatsCard
            title="Jami foydalanuvchilar"
            value={stats.total_users}
            subtitle={`+${stats.users_today} bugun`}
            icon="👥"
            color="indigo"
          />
          <StatsCard
            title="Jami so'rovlar"
            value={stats.total_inquiries}
            subtitle={`+${stats.inquiries_today} bugun`}
            icon="💬"
            color="blue"
          />
          <StatsCard
            title="Jami daromad"
            value={formatCurrency(stats.total_revenue)}
            subtitle={`${stats.pending_payments} kutilmoqda`}
            icon="💰"
            color="green"
          />
          <StatsCard
            title="Referrallar"
            value={stats.referred_users}
            subtitle={`${stats.subscribers} obunachi`}
            icon="🔗"
            color="purple"
          />
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">📈 Yangi foydalanuvchilar (30 kun)</h3>
          <SimpleChart data={usersChart} dataKey="count" color="#6366f1" />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow">
          <h3 className="text-sm font-semibold text-slate-700 mb-4">📊 So'rovlar (30 kun)</h3>
          <SimpleChart data={inquiriesChart} dataKey="count" color="#3b82f6" />
        </div>
      </div>

      {/* Pipeline & Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CRM Pipeline */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow">
          <h3 className="text-sm font-semibold text-slate-700 mb-5">🔄 CRM Pipeline</h3>
          <div className="space-y-4">
            {PIPELINE_STAGES.map((stage) => {
              const item = pipeline.find((p) => p.status === stage.key);
              const count = item?.count || 0;
              const total = pipeline.reduce((s, p) => s + p.count, 0) || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={stage.key} className="flex items-center gap-3">
                  <span className="text-base w-6 text-center">{stage.emoji}</span>
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1.5">
                      <span className="font-medium text-slate-700">{stage.label}</span>
                      <span className="text-slate-500 font-semibold">{count} <span className="text-slate-400 font-normal">({pct}%)</span></span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Risk Breakdown */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 hover:shadow-md transition-shadow">
          <h3 className="text-sm font-semibold text-slate-700 mb-5">⚠️ Xavf darajasi taqsimoti</h3>
          <div className="space-y-4">
            {risks.map((r) => {
              const total = risks.reduce((s, item) => s + item.count, 0) || 1;
              const pct = Math.round((r.count / total) * 100);
              const riskLabels: Record<string, string> = {
                low: "Past xavf",
                medium: "O'rta xavf",
                high: "Yuqori xavf",
                unrated: "Baholanmagan",
              };
              return (
                <div key={r.level} className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${getRiskColor(r.level)} shrink-0`} />
                  <div className="flex-1">
                    <div className="flex justify-between text-sm mb-1.5">
                      <span className="font-medium text-slate-700">{riskLabels[r.level] || r.level}</span>
                      <span className="text-slate-500 font-semibold">{r.count} <span className="text-slate-400 font-normal">({pct}%)</span></span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${getRiskColor(r.level)}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
