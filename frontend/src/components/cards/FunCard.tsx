import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";
import { extractWatchAge } from "../../utils/metricExtractors";

interface FunCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const FunCard: React.FC<FunCardProps> = ({ text, metrics }) => {
  // Filter out featured_titles and featured_title - these are only for background images
  const displayMetrics = Object.fromEntries(
    Object.entries(metrics).filter(
      ([key]) => key !== "featured_titles" && key !== "featured_title"
    )
  );

  // Extract watch age if present
  const watchAge = extractWatchAge(metrics);

  return (
    <div className="card-content fun-card-content">
      {text.headline && (
        <motion.h3
          className="card-headline fun-headline"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200 }}
        >
          {text.headline}
        </motion.h3>
      )}
      <p className="card-description">{text.description}</p>
      
      {/* Special handling for watch age */}
      {watchAge.age !== null && (
        <div className="fun-metrics">
          <motion.div
            className="fun-metric-badge fun-metric-badge-large"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.1, type: "spring" }}
          >
            <span className="fun-metric-value">{watchAge.age}</span>
            <span className="fun-metric-label">years</span>
            {watchAge.confidence && (
              <span className="fun-metric-subtext">
                {typeof watchAge.confidence === 'number' 
                  ? `${(watchAge.confidence * 100).toFixed(0)}% confidence`
                  : String(watchAge.confidence)}
              </span>
            )}
            {watchAge.range && (
              <span className="fun-metric-subtext">{watchAge.range}</span>
            )}
          </motion.div>
        </div>
      )}
      
      {Object.keys(displayMetrics).length > 0 && (
        <div className="fun-metrics">
          {Object.entries(displayMetrics).map(([key, value], index) => {
            // Skip watch age fields as they're handled above
            if (key.includes('watch_age') || key.includes('estimated_age') || key.includes('confidence')) {
              return null;
            }
            
            if (Array.isArray(value)) {
              return (
                <div key={key} className="fun-list">
                  <div className="fun-list-label">
                    {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </div>
                  {value.map((item: any, i: number) => (
                    <motion.div
                      key={i}
                      className="fun-list-item"
                      initial={{ x: -20, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: i * 0.1 }}
                    >
                      {typeof item === "object" && item !== null
                        ? (item.genre || item.name || item.title || JSON.stringify(item))
                        : String(item)}
                    </motion.div>
                  ))}
                </div>
              );
            }
            if (typeof value === "object" && value !== null) {
              // Skip nested objects that are better displayed as key-value pairs
              if (key.includes('repeat') || key.includes('favorite') || key.includes('other')) {
                return (
                  <div key={key} className="fun-object">
                    <div className="fun-object-label">
                      {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                    </div>
                    <div className="fun-object-value">
                      {Object.entries(value).map(([k, v]: [string, any]) => (
                        <div key={k} className="fun-object-item">
                          <span>{k}:</span> <span>{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              }
              return (
                <div key={key} className="fun-object">
                  <div className="fun-object-label">
                    {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </div>
                  <div className="fun-object-value">
                    {JSON.stringify(value)}
                  </div>
                </div>
              );
            }
            return (
              <motion.div
                key={key}
                className="fun-metric-badge"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: index * 0.1, type: "spring" }}
              >
                <span className="fun-metric-value">{String(value)}</span>
                <span className="fun-metric-label">
                  {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                </span>
              </motion.div>
            );
          })}
        </div>
      )}
      {text.aside && <p className="card-aside fun-aside">{text.aside}</p>}
    </div>
  );
};
