import React from "react";
import { CardText } from "../../types/cards";
import { formatNumber, formatMetricLabel } from "../../utils/formatters";

interface StatCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const StatCard: React.FC<StatCardProps> = ({ text, metrics }) => {
  // Filter out featured_titles and featured_title - these are only for background images
  // Also filter out arrays
  const displayMetrics = Object.fromEntries(
    Object.entries(metrics).filter(([key, value]) => {
      if (key === "featured_titles" || key === "featured_title") return false;
      if (Array.isArray(value)) return false;
      if (value === null || value === undefined || value === "—") return false;
      if (typeof value === "object") return false;
      return true;
    })
  );

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>
      {Object.keys(displayMetrics).length > 0 && (
        <div className="stat-card-grid">
          {Object.entries(displayMetrics).map(([key, value]) => {
            return (
              <div key={key} className="stat-card-item">
                <div className="stat-card-value">{formatNumber(value)}</div>
                <div className="stat-card-label">{formatMetricLabel(key)}</div>
              </div>
            );
          })}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};

