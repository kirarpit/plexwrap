import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import {
  findMetric,
  extractDurationMinutes,
  extractCount,
  extractDate,
} from "../../utils/metricExtractors";

interface BingeSessionsCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const BingeSessionsCard: React.FC<BingeSessionsCardProps> = ({
  text,
  metrics,
}) => {
  // Try to find sessions array
  const sessions =
    findMetric(metrics, [
      "longest_sessions_sample",
      "sessions",
      "binge_sessions",
      "top_sessions",
    ]) || [];

  // If no sessions array, try to build from individual metrics
  let displaySessions: Array<{
    date?: string;
    minutes?: number;
    episodes?: number;
    items?: number;
    titles?: string[];
  }> = [];

  if (Array.isArray(sessions) && sessions.length > 0) {
    displaySessions = sessions;
  } else {
    // Try to extract single binge session from metrics
    const duration = extractDurationMinutes(metrics);
    const date = extractDate(metrics);
    const episodes = extractCount(metrics);
    const featuredTitles = findMetric(metrics, [
      "featured_titles",
      "longest_binge_titles",
    ]);

    if (duration !== null || date || episodes !== null) {
      displaySessions = [
        {
          date: date || undefined,
          minutes: duration || undefined,
          episodes: episodes || undefined,
          titles: Array.isArray(featuredTitles) ? featuredTitles : undefined,
        },
      ];
    }
  }

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>
      {displaySessions.length > 0 && (
        <div className="binge-sessions-list">
          {displaySessions.map((session: any, index: number) => (
            <motion.div
              key={index}
              className="binge-session-item"
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              {session.date && (
                <div className="binge-session-date">{session.date}</div>
              )}
              {(session.minutes !== undefined ||
                session.duration_minutes !== undefined) && (
                <div className="binge-session-duration">
                  {formatDuration(
                    session.minutes || session.duration_minutes || 0
                  )}
                </div>
              )}
              {(session.episodes !== undefined ||
                session.items !== undefined) && (
                <div className="binge-session-episodes">
                  {session.episodes || session.items}{" "}
                  {session.episodes ? "episodes" : "items"}
                </div>
              )}
              {(session.items && Array.isArray(session.items)) ||
              (session.titles && Array.isArray(session.titles)) ? (
                <div className="binge-session-content">
                  {(session.items || session.titles)
                    .slice(0, 3)
                    .map((item: string, i: number) => (
                      <span key={i} className="binge-content-tag">
                        {item}
                      </span>
                    ))}
                  {(session.items || session.titles).length > 3 && (
                    <span className="binge-content-tag">
                      +{(session.items || session.titles).length - 3} more
                    </span>
                  )}
                </div>
              ) : null}
            </motion.div>
          ))}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
