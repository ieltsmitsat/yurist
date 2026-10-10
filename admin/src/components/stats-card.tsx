interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: string;
  color: "indigo" | "blue" | "green" | "purple" | "red" | "orange";
}

const colorMap = {
  indigo: { bg: "bg-indigo-50", text: "text-indigo-600", border: "border-indigo-100" },
  blue: { bg: "bg-blue-50", text: "text-blue-600", border: "border-blue-100" },
  green: { bg: "bg-emerald-50", text: "text-emerald-600", border: "border-emerald-100" },
  purple: { bg: "bg-purple-50", text: "text-purple-600", border: "border-purple-100" },
  red: { bg: "bg-red-50", text: "text-red-600", border: "border-red-100" },
  orange: { bg: "bg-amber-50", text: "text-amber-600", border: "border-amber-100" },
};

export default function StatsCard({ title, value, subtitle, icon, color }: StatsCardProps) {
  const c = colorMap[color];
  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{title}</p>
          <p className="text-2xl font-bold mt-1.5 text-slate-900">{value}</p>
          <p className="text-xs text-slate-400 mt-1.5">{subtitle}</p>
        </div>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center text-lg ${c.bg} ${c.text} border ${c.border}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
