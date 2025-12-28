import React from "react";
import { WrapData } from "../../api";
import { CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import { findMetric } from "../../utils/metricExtractors";

interface SummaryCardProps {
  wrapData: WrapData;
  text: CardText;
  metrics: Record<string, any>;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({
  wrapData,
  text,
  metrics,
}) => {
  // Extract values from metrics with fallback to wrapData
  const totalWatchTimeHours = findMetric(metrics, [
    'total_watch_time_hours',
    'total_watch_time'
  ]) || (wrapData.total_watch_time ? wrapData.total_watch_time / 60 : null);
  
  const totalItems = findMetric(metrics, [
    'total_items',
    'total_items_watched'
  ]) || wrapData.total_items_watched;
  
  const totalEpisodes = findMetric(metrics, [
    'total_episodes',
    'total_episodes_watched'
  ]) || wrapData.total_episodes_watched;
  
  const totalMovies = findMetric(metrics, [
    'total_movies',
    'total_movies_watched'
  ]) || wrapData.total_movies_watched;
  
  const mostWatchedTitle = findMetric(metrics, [
    'most_watched_title',
    'top_title',
    'favorite_movie'
  ]);
  
  const mostRepeated = findMetric(metrics, [
    'most_repeated',
    'top_repeat_title'
  ]);
  
  const mostUsedDevice = findMetric(metrics, [
    'most_used_device',
    'top_device'
  ]);
  
  const mostActiveSeason = findMetric(metrics, [
    'most_active_season'
  ]);
  
  const watchAge = findMetric(metrics, [
    'watch_age_estimate',
    'estimated_watch_age',
    'estimated_watch_age_years'
  ]);
  
  const bingeSessions = findMetric(metrics, [
    'binge_sessions',
    'binge_sessions_count'
  ]) || (wrapData.binge_sessions ? wrapData.binge_sessions.length : null);

  const stats = [];
  
  if (totalWatchTimeHours !== null) {
    stats.push({
      value: typeof totalWatchTimeHours === 'number' 
        ? formatDuration(totalWatchTimeHours * 60) 
        : String(totalWatchTimeHours),
      label: "Total Watch Time"
    });
  }
  
  if (totalItems) {
    stats.push({
      value: String(totalItems),
      label: "Shows & Movies"
    });
  }
  
  if (totalEpisodes) {
    stats.push({
      value: String(totalEpisodes),
      label: "Episodes Watched"
    });
  }
  
  if (totalMovies) {
    stats.push({
      value: String(totalMovies),
      label: "Movies Watched"
    });
  }
  
  if (mostWatchedTitle) {
    stats.push({
      value: String(mostWatchedTitle),
      label: "Most Watched"
    });
  }
  
  if (mostRepeated) {
    stats.push({
      value: String(mostRepeated),
      label: "Most Repeated"
    });
  }
  
  if (mostUsedDevice) {
    stats.push({
      value: String(mostUsedDevice),
      label: "Top Device"
    });
  }
  
  if (mostActiveSeason) {
    stats.push({
      value: String(mostActiveSeason),
      label: "Most Active Season"
    });
  }
  
  if (watchAge !== null) {
    stats.push({
      value: typeof watchAge === 'number' ? `${watchAge} years` : String(watchAge),
      label: "Watch Age"
    });
  }
  
  if (bingeSessions !== null) {
    stats.push({
      value: String(bingeSessions),
      label: "Binge Sessions"
    });
  }

  // Fallback to wrapData if no metrics stats found
  if (stats.length === 0) {
    if (wrapData.total_watch_time) {
      stats.push({
        value: formatDuration(wrapData.total_watch_time),
        label: "Total Watch Time"
      });
    }
    if (wrapData.total_items_watched) {
      stats.push({
        value: String(wrapData.total_items_watched),
        label: "Shows & Movies"
      });
    }
    if (wrapData.total_episodes_watched) {
      stats.push({
        value: String(wrapData.total_episodes_watched),
        label: "Episodes Watched"
      });
    }
    if (wrapData.total_movies_watched) {
      stats.push({
        value: String(wrapData.total_movies_watched),
        label: "Movies Watched"
      });
    }
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
      {stats.length > 0 && (
        <div className="summary-stats-grid">
          {stats.map((stat, index) => (
            <div key={index} className="summary-stat">
              <div className="summary-stat-value">{stat.value}</div>
              <div className="summary-stat-label">{stat.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
