import React from "react";
import { CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import { extractDurationMinutes, extractCount, extractDate } from "../../utils/metricExtractors";

interface RecordCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const RecordCard: React.FC<RecordCardProps> = ({ text, metrics }) => {
  // Filter out featured_titles and featured_title - these are only for background images
  const displayMetrics = Object.fromEntries(
    Object.entries(metrics).filter(
      ([key]) => key !== "featured_titles" && key !== "featured_title"
    )
  );

  // Extract main record values with flexible key matching
  const durationMinutes = extractDurationMinutes(metrics);
  const count = extractCount(metrics);
  const date = extractDate(metrics);

  // Determine the main record to highlight
  let mainRecord: { value: string; label: string } | null = null;
  
  if (durationMinutes !== null) {
    mainRecord = {
      value: formatDuration(durationMinutes),
      label: "Duration"
    };
  } else if (count !== null) {
    mainRecord = {
      value: String(count),
      label: "Count"
    };
  } else {
    // Fallback to finding any numeric metric
    const numericEntry = Object.entries(displayMetrics).find(
      ([, value]) => typeof value === 'number' && value > 0
    );
    if (numericEntry) {
      mainRecord = {
        value: String(numericEntry[1]),
        label: numericEntry[0]
          .replace(/_/g, " ")
          .replace(/\b\w/g, (l) => l.toUpperCase())
      };
    }
  }

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      {mainRecord && (
        <div className="record-highlight">
          <div className="record-value">{mainRecord.value}</div>
          <div className="record-label">{mainRecord.label}</div>
        </div>
      )}
      <p className="card-description">{text.description}</p>
      {Object.keys(displayMetrics).length > 1 && (
        <div className="record-details">
          {Object.entries(displayMetrics)
            .filter(([key]) => {
              // Don't show the main record again, or featured titles, or arrays/objects
              if (key === "featured_titles" || key === "featured_title") return false;
              if (durationMinutes !== null && (
                key.includes("duration") || key.includes("minutes")
              )) return false;
              if (count !== null && (
                key.includes("count") || key.includes("episodes") || key.includes("items")
              )) return false;
              if (date && key.includes("date")) return false;
              return true;
            })
            .map(([key, value]) => {
              if (Array.isArray(value)) return null;
              if (typeof value === "object") return null;
              if (value === null || value === undefined) return null;
              return (
                <div key={key} className="record-detail-item">
                  <span className="record-detail-label">
                    {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}:
                  </span>
                  <span className="record-detail-value">{String(value)}</span>
                </div>
              );
            })}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
