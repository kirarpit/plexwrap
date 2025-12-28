import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import { extractTopContent } from "../../utils/metricExtractors";

interface TopContentCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const TopContentCard: React.FC<TopContentCardProps> = ({
  text,
  metrics,
}) => {
  const contentItems = extractTopContent(metrics);

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>
      {contentItems.length > 0 && (
        <div className="top-content-list">
          {contentItems.map((item, index: number) => (
            <motion.div
              key={index}
              className="top-content-item"
              initial={{ x: -20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: index * 0.05 }}
            >
              <div className="content-rank">#{index + 1}</div>
              <div className="content-info">
                <div className="content-title">{item.title}</div>
                {(item.minutes !== undefined || item.count !== undefined) && (
                  <div className="content-stats">
                    {item.minutes !== undefined && (
                      <span>{formatDuration(item.minutes)}</span>
                    )}
                    {item.count !== undefined && (
                      <span className="content-repeats">
                        {item.minutes !== undefined ? " • " : ""}
                        {item.count}x watched
                      </span>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
