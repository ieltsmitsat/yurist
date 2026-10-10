import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("uz-UZ", {
    style: "decimal",
    maximumFractionDigits: 0,
  }).format(amount) + " so'm";
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("uz-UZ", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    new: "bg-blue-50 text-blue-700 border border-blue-200",
    verified_lead: "bg-cyan-50 text-cyan-700 border border-cyan-200",
    express_audit: "bg-amber-50 text-amber-700 border border-amber-200",
    proposal_sent: "bg-purple-50 text-purple-700 border border-purple-200",
    appointment_booked: "bg-indigo-50 text-indigo-700 border border-indigo-200",
    closed_won: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    rewarded_referral: "bg-teal-50 text-teal-700 border border-teal-200",
    lawyer: "bg-amber-50 text-amber-700 border border-amber-200",
    pending: "bg-orange-50 text-orange-700 border border-orange-200",
    completed: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    failed: "bg-red-50 text-red-700 border border-red-200",
    refunded: "bg-slate-50 text-slate-700 border border-slate-200",
    answered: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    pending_review: "bg-amber-50 text-amber-700 border border-amber-200",
    approved: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  };
  return colors[status] || "bg-slate-50 text-slate-700 border border-slate-200";
}

export function getRiskColor(level: string): string {
  const colors: Record<string, string> = {
    low: "bg-emerald-500",
    medium: "bg-amber-500",
    high: "bg-red-500",
    unrated: "bg-slate-400",
  };
  return colors[level] || "bg-slate-400";
}

export const PIPELINE_STAGES = [
  { key: "new", label: "Yangi Lead", emoji: "🆕" },
  { key: "verified_lead", label: "Tasdiqlangan", emoji: "✅" },
  { key: "express_audit", label: "Express Audit", emoji: "🔍" },
  { key: "proposal_sent", label: "Taklif yuborildi", emoji: "📨" },
  { key: "appointment_booked", label: "Uchrashuv belgilandi", emoji: "📅" },
  { key: "closed_won", label: "Muvaffaqiyatli", emoji: "🏆" },
];
