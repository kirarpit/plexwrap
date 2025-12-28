import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";
import { extractWatchAge } from "../../utils/metricExtractors";

interface WatchAgeCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const WatchAgeCard: React.FC<WatchAgeCardProps> = ({
  text,
  metrics,
}) => {
  let watchAge = extractWatchAge(metrics);

  // Strip markdown formatting from headline (remove ** for bold)
  const cleanHeadline = text.headline?.replace(/\*\*/g, "") || "";

  // Fallback: try to extract age from headline if not found in metrics
  if (watchAge.age === null && cleanHeadline) {
    const ageMatch = cleanHeadline.match(/(\d+)\s*years?\s*old/i);
    if (ageMatch) {
      watchAge = {
        ...watchAge,
        age: parseInt(ageMatch[1], 10),
      };
    }
  }

  if (watchAge.age === null) {
    // Fallback to regular fun card if no age found
    return (
      <div className="card-content fun-card-content">
        {cleanHeadline && <h3 className="card-headline">{cleanHeadline}</h3>}
        <p className="card-description">{text.description}</p>
        {text.aside && <p className="card-aside">{text.aside}</p>}
      </div>
    );
  }

  return (
    <div className="card-content watch-age-content">
      {/* Don't show headline here - age is the main focus */}

      {/* Age Display - Front and Center */}
      <motion.div
        className="watch-age-display"
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{
          delay: 0.2,
          type: "spring",
          stiffness: 200,
          damping: 15,
        }}
      >
        <div className="watch-age-number">{watchAge.age}</div>
        <div className="watch-age-unit">years old</div>
        {watchAge.confidence && (
          <motion.div
            className="watch-age-confidence"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            {typeof watchAge.confidence === "number"
              ? `${(watchAge.confidence * 100).toFixed(0)}% confidence`
              : String(watchAge.confidence)}
          </motion.div>
        )}
        {watchAge.range && (
          <motion.div
            className="watch-age-range"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
          >
            {watchAge.range}
          </motion.div>
        )}
      </motion.div>

      {/* Description */}
      <motion.p
        className="card-description watch-age-description"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        {text.description}
      </motion.p>

      {/* Aside */}
      {text.aside && (
        <motion.p
          className="card-aside watch-age-aside"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
        >
          {text.aside}
        </motion.p>
      )}
    </div>
  );
};
