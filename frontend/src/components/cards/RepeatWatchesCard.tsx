import React from "react";
import { CardText } from "../../types/cards";
import { extractRepeatWatches } from "../../utils/metricExtractors";

interface RepeatWatchesCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const RepeatWatchesCard: React.FC<RepeatWatchesCardProps> = ({
  text,
  metrics,
}) => {
  const { topTitle, topCount, others } = extractRepeatWatches(metrics);

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>
      {topTitle && topCount !== null && (
        <div className="repeat-champion">
          <div className="repeat-champion-title">🏆 Champion</div>
          <div className="repeat-champion-name">{topTitle}</div>
          <div className="repeat-champion-count">{topCount}x watched</div>
        </div>
      )}
      {others.length > 0 && (
        <div className="repeat-others">
          <div className="repeat-others-label">Other favorites:</div>
          {others.map((item, index: number) => (
            <div key={index} className="repeat-other-item">
              <span className="repeat-other-name">{item.title}</span>
              <span className="repeat-other-count">{item.count}x</span>
            </div>
          ))}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
