import { useEffect, useState } from "react";
import { getStats } from "../services/api";
import { useAuth } from "../hooks/useAuth";

export default function UsageBar() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (user) getStats().then(setStats).catch(() => {});
  }, [user]);

  if (!stats) return null;

  const pct = Math.round((stats.daily_used / stats.daily_limit) * 100);
  const col  = pct >= 100 ? "#FF3B5C" : pct >= 66 ? "#FFB830" : "#00FF87";
  const planColor = stats.plan === "FREE" ? "#3A6070" : stats.plan === "PRO" ? "#00D4FF" : "#00FF87";

  return (
    <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg"
      style={{ background: "#0A1520", border: "1px solid #132435" }}>
      <span className="font-mono text-[9px] tracking-widest px-2 py-0.5 rounded"
        style={{ background: planColor + "22", color: planColor, border: `1px solid ${planColor}44` }}>
        {stats.plan}
      </span>
      <div className="flex items-center gap-1.5">
        <div className="w-20 h-1.5 rounded-full overflow-hidden" style={{ background: "#132435" }}>
          <div className="h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, pct)}%`, background: col }} />
        </div>
        <span className="font-mono text-[10px]" style={{ color: col }}>
          {stats.daily_used}/{stats.daily_limit}
        </span>
      </div>
    </div>
  );
}
