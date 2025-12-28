import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";
import { formatNumber } from "../../utils/formatters";

interface ComparisonCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const ComparisonCard: React.FC<ComparisonCardProps> = ({
  text,
  metrics,
}) => {
  const parseRank = (
    rankValue: string | number
  ): { rank: number; total: number | null } | null => {
    // Handle string format like "2/8"
    if (typeof rankValue === "string") {
      const match = rankValue.match(/(\d+)\s*\/\s*(\d+)/);
      if (match) {
    return { rank: parseInt(match[1]), total: parseInt(match[2]) };
      }
    }
    // Handle numeric format (just the rank number)
    if (typeof rankValue === "number" && Number.isFinite(rankValue)) {
      return { rank: rankValue, total: null };
    }
    return null;
  };

  const getPercentileColor = (percentile: number): string => {
    if (percentile >= 95) return "#2F9E44";
    if (percentile >= 85) return "#4ECDC4";
    if (percentile >= 70) return "#FFD43B";
    return "#FF6B6B";
  };

  const labelForKey = (key: string): string => {
    const base = key
      .replace(/^average_/, "")
      .replace(/^percentile_/, "")
      .replace(/_vs_average$/, "")
      .replace(/_rank$/, "")
      .replace(/_percentile$/, "");

    const pretty: Record<string, string> = {
      watch_time: "Watch Time",
      episodes: "Episodes",
      movies: "Movies",
      binge_sessions: "Binge Sessions",
      device_diversity: "Device Diversity",
      genre_diversity: "Genre Diversity",
    };
    return (
      pretty[base] ||
      base
        .replace(/_/g, " ")
        .replace(/\b\w/g, (l) => l.toUpperCase())
        .trim()
    );
  };

  const iconForLabel = (label: string): string => {
    const map: Record<string, string> = {
      "Watch Time": "⏱️",
      Episodes: "📺",
      Movies: "🎞️",
      "Binge Sessions": "🔥",
      "Device Diversity": "🧩",
      "Genre Diversity": "🎭",
    };
    return map[label] || "📊";
  };

  const toNumber = (v: any): number | null => {
    if (typeof v === "number") return v;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };

  // Collect metrics
  const percentileEntries = Object.entries(metrics)
    .filter(([k]) => k.endsWith("_percentile") || k.startsWith("percentile_"))
    .map(([k, v]) => {
      const pct = toNumber(v);
      if (pct === null) return null;
      const label = labelForKey(k);
      return { key: k, label, percentile: pct };
    })
    .filter(Boolean) as Array<{
    key: string;
    label: string;
    percentile: number;
  }>;

  const rankEntries = Object.entries(metrics)
    .filter(([k]) => k.endsWith("_rank"))
    .map(([k, v]) => {
      const parsed = parseRank(v);
      if (!parsed) return null;
      const label = labelForKey(k);
      return { key: k, label, rank: parsed.rank, total: parsed.total };
    })
    .filter((item): item is { key: string; label: string; rank: number; total: number | null } => item !== null)
    .sort((a, b) => a.rank - b.rank);

  const vsAvgPairs = Object.entries(metrics)
    .filter(([k]) => k.endsWith("_vs_average"))
    .map(([k, v]) => {
      const base = k.replace(/_vs_average$/, "");
      const avgKey = `average_${base}`;
      const you = toNumber(v);
      const avg = toNumber((metrics as any)[avgKey]);
      if (you === null || avg === null) return null;
      return { key: base, label: labelForKey(base), you, avg };
    })
    .filter(Boolean) as Array<{
    key: string;
    label: string;
    you: number;
    avg: number;
  }>;

  // Prefer a "primary" metric for a hero gauge
  const primary =
    percentileEntries.find((p) => p.key === "watch_time_percentile" || p.key === "percentile_watch_time") ||
    percentileEntries.sort((a, b) => b.percentile - a.percentile)[0] ||
    null;

  // Simplified percentile display
  const PercentileDisplay: React.FC<{ value: number; label: string }> = ({
    value,
    label,
  }) => {
    const clamped = Math.max(0, Math.min(100, value));
    const color = getPercentileColor(clamped);
    return (
      <div className="cmp-percentile">
        <div className="cmp-percentile-badge" style={{ backgroundColor: color + "20", borderColor: color }}>
          <div className="cmp-percentile-number">{clamped.toFixed(1)}</div>
          <div className="cmp-percentile-label">percentile</div>
        </div>
        <div className="cmp-percentile-metric">
          <span className="cmp-percentile-icon">{iconForLabel(label)}</span>
          <span>{label}</span>
        </div>
      </div>
    );
  };

  const medalForRank = (rank: number): string | null => {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return null;
  };

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>

      {(primary || rankEntries.length > 0 || vsAvgPairs.length > 0) && (
        <div className="cmp-dashboard">
          {/* HERO */}
          {primary && (
            <div className="cmp-hero">
              <PercentileDisplay value={primary.percentile} label={primary.label} />
              <div className="cmp-hero-right">
                <div className="cmp-hero-title">How you stack up</div>
                {rankEntries.length > 0 && (
                  <div className="cmp-rank-pill-row">
                    {rankEntries.map((r) => (
                      <div key={r.key} className="cmp-rank-pill">
                        <span className="cmp-rank-pill-icon">
                          {iconForLabel(r.label)}
                        </span>
                        <span className="cmp-rank-pill-label">{r.label}</span>
                        <span className="cmp-rank-pill-value">
                          {medalForRank(r.rank)
                            ? `${medalForRank(r.rank)} `
                            : ""}
                          #{r.rank}{r.total !== null ? `/${r.total}` : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* YOU VS AVG */}
          {vsAvgPairs.length > 0 && (
            <div className="cmp-section">
              <div className="cmp-section-title">You vs Average</div>
              <div className="cmp-vs-list">
                {vsAvgPairs.map((p) => {
                  const max = Math.max(p.you, p.avg, 1);
                  const youPct = (p.you / max) * 100;
                  const avgPct = (p.avg / max) * 100;
                  return (
                    <div key={p.key} className="cmp-vs-row">
                      <div className="cmp-vs-label">
                        <span className="cmp-vs-icon">
                          {iconForLabel(p.label)}
                        </span>
                        {p.label}
                      </div>
                      <div className="cmp-vs-bars">
                        <div className="cmp-vs-bar">
                          <div className="cmp-vs-bar-label">You</div>
                          <div className="cmp-vs-bar-track">
                            <motion.div
                              className="cmp-vs-bar-fill cmp-vs-you"
                              initial={{ width: 0 }}
                              animate={{ width: `${youPct}%` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                            />
                          </div>
                          <div className="cmp-vs-bar-value">
                            {formatNumber(p.you)}
                          </div>
                        </div>
                        <div className="cmp-vs-bar">
                          <div className="cmp-vs-bar-label">Avg</div>
                          <div className="cmp-vs-bar-track">
                            <motion.div
                              className="cmp-vs-bar-fill cmp-vs-avg"
                              initial={{ width: 0 }}
                              animate={{ width: `${avgPct}%` }}
                              transition={{ duration: 0.8, ease: "easeOut" }}
                            />
                          </div>
                          <div className="cmp-vs-bar-value">
                            {formatNumber(p.avg)}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
