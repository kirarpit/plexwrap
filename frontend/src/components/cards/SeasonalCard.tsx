import React from "react";
import { motion } from "framer-motion";
import { SeasonalData, CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import { extractSeasonalData } from "../../utils/metricExtractors";

interface SeasonalCardProps {
  seasonalData: SeasonalData | null;
  text: CardText;
  metrics?: Record<string, any>;
}

export const SeasonalCard: React.FC<SeasonalCardProps> = ({
  seasonalData,
  text,
  metrics,
}) => {
  const seasons = [
    { name: "Winter", emoji: "❄️", color: "#4A90E2" },
    { name: "Spring", emoji: "🌸", color: "#50C878" },
    { name: "Summer", emoji: "☀️", color: "#FFD700" },
    { name: "Fall", emoji: "🍂", color: "#FF6B35" },
  ];

  // Try to get seasonal data from metrics first, then fall back to seasonalData
  let seasonBreakdown: Record<string, number> = {};
  let mostActiveSeason: string | null = null;

  if (metrics) {
    const extracted = extractSeasonalData(metrics);
    seasonBreakdown = extracted.seasonBreakdown;
    mostActiveSeason = extracted.mostActiveSeason;
  }

  // Fall back to seasonalData if metrics don't have the data
  if (Object.keys(seasonBreakdown).length === 0 && seasonalData?.by_season) {
    Object.entries(seasonalData.by_season).forEach(([season, data]) => {
      if (data && typeof data === "object" && "time" in data) {
        seasonBreakdown[season] = data.time || 0;
      }
    });
    mostActiveSeason = seasonalData.most_active || null;
  }

  const seasonData = seasons.map((season) => {
    const minutes = seasonBreakdown[season.name] || 0;
    return {
      ...season,
      time: minutes,
      count: 0, // Count not always available in metrics
    };
  });

  const maxTime = Math.max(...seasonData.map((s) => s.time), 1);

  // If no seasonal data at all, show fallback
  if (maxTime === 0) {
    return (
      <div className="card-content">
        {text.headline && <h3 className="card-headline">{text.headline}</h3>}
        <p className="card-description">{text.description}</p>
        {text.aside && <p className="card-aside">{text.aside}</p>}
      </div>
    );
  }

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description" style={{ marginBottom: "2rem" }}>
        {text.description}
      </p>
      {text.aside && (
        <p className="card-aside" style={{ marginBottom: "2rem" }}>
          {text.aside}
        </p>
      )}
      <div className="seasonal-visualization">
        {seasonData.map((season) => {
          const percentage = maxTime > 0 ? (season.time / maxTime) * 100 : 0;
          return (
            <div key={season.name} className="season-item">
              <div className="season-header">
                <span className="season-emoji">{season.emoji}</span>
                <span className="season-name">{season.name}</span>
              </div>
              <div className="season-bar-container">
                <motion.div
                  className="season-bar"
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  style={{ backgroundColor: season.color }}
                />
              </div>
              <div className="season-stats">
                <span className="season-time">
                  {formatDuration(season.time)}
                </span>
                {season.count > 0 && (
                  <span className="season-count">{season.count} items</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
