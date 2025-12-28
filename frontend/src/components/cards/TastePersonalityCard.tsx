import React from "react";
import { motion } from "framer-motion";
import { CardText } from "../../types/cards";

interface TastePersonalityCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const TastePersonalityCard: React.FC<TastePersonalityCardProps> = ({
  text,
  metrics,
}) => {
  const parseGenreItem = (item: string | any) => {
    // If item is an object, extract properties directly
    if (typeof item === 'object' && item !== null) {
      const genreName = item.genre || item.name || String(item);
      const watchTime = item.watch_time_minutes || item.watch_time || item.minutes || 0;
      const percentage = item.percentage_of_top_genres || item.percentage || null;
      return {
        name: String(genreName),
        minutes: Number(watchTime) || 0,
        percentage: percentage !== null && percentage !== undefined ? Number(percentage) : null,
      };
    }
    // If item is a string, parse it
    const match = String(item).match(/^(.+?)\s*\((\d+)\s*min(?:,\s*([\d.]+)%)?\)$/);
    if (match) {
      return {
        name: match[1].trim(),
        minutes: parseInt(match[2]),
        percentage: match[3] ? parseFloat(match[3]) : null,
      };
    }
    return { name: String(item), minutes: 0, percentage: null };
  };

  const parseActorItem = (item: string) => {
    const match = item.match(/^(.+?)\s*\((\d+)\s*min\)$/);
    if (match) {
      return {
        name: match[1].trim(),
        minutes: parseInt(match[2]),
      };
    }
    return { name: item, minutes: 0 };
  };

  // Handle new format: top_genres array + top_genre_percentages or top_genre_watch_times object
  const topGenresArray = metrics.top_genres || [];
  const topGenrePercentages = metrics.top_genre_percentages || {};
  const topGenreWatchTimes = metrics.top_genre_watch_times || {};
  const personalityTag = metrics.personality_tag;
  const topTitle = metrics.top_title;

  // Build genres from new format
  // Handle both string arrays and object arrays
  const genresFromNewFormat = topGenresArray.map((genre: string | any) => {
    // If genre is an object, extract the genre name and other properties
    if (typeof genre === 'object' && genre !== null) {
      const genreName = genre.genre || genre.name || String(genre);
      const watchTime = genre.watch_time_minutes || genre.watch_time || 0;
      const percentage = genre.percentage_of_top_genres || genre.percentage || topGenrePercentages[genreName] || null;
      return {
        name: genreName,
        minutes: watchTime,
        percentage: percentage,
      };
    }
    // If genre is a string, look up watch time from top_genre_watch_times or percentage from top_genre_percentages
    const genreName = String(genre);
    const watchTime = topGenreWatchTimes[genreName] || 0;
    const percentage = topGenrePercentages[genreName] || null;
    return {
      name: genreName,
      minutes: watchTime,
      percentage: percentage,
    };
  });

  // Handle old format: top_genres_by_minutes
  const genresFromOldFormat = (metrics.top_genres_by_minutes || []).map(parseGenreItem);

  // Use new format if available, otherwise fall back to old format
  const parsedGenres = genresFromNewFormat.length > 0 ? genresFromNewFormat : genresFromOldFormat;
  
  // Handle both top_actors_seen and notable_actors
  const actors = metrics.top_actors_seen || metrics.notable_actors || [];
  const director = metrics.top_director_seen;

  // Parse actors - handle both string arrays and objects
  const parsedActors = actors.map((actor: string | any) => {
    if (typeof actor === 'object' && actor !== null) {
      return {
        name: actor.name || actor.actor || String(actor),
        minutes: actor.minutes || actor.watch_time_minutes || 0
      };
    }
    return parseActorItem(String(actor));
  });
  const parsedDirector = director ? parseActorItem(director) : null;

  const maxGenrePercentage = Math.max(
    ...parsedGenres.map(
      (g: { name: string; minutes: number; percentage: number | null }) =>
        g.percentage || 0
    ),
    1
  );
  const maxActorMinutes = Math.max(
    ...parsedActors.map((a: { name: string; minutes: number }) => a.minutes),
    1
  );

  return (
    <div className="card-content taste-personality-content">
      {text.headline && (
        <motion.h3
          className="card-headline taste-headline"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200 }}
        >
          {text.headline}
        </motion.h3>
      )}
      <p className="card-description">{text.description}</p>

      {personalityTag && (
        <div className="taste-personality-tag">
          <motion.div
            className="personality-badge"
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, type: "spring" }}
          >
            {personalityTag}
          </motion.div>
        </div>
      )}

      {parsedGenres.length > 0 && (
        <div className="taste-section">
          <h4 className="taste-section-title">Top Genres</h4>
          <div className="taste-list">
            {parsedGenres.map(
              (
                genre: {
                  name: string;
                  minutes: number;
                  percentage: number | null;
                },
                index: number
              ) => {
                // Use percentage if available, otherwise use minutes
                const displayValue = genre.percentage !== null 
                  ? genre.percentage 
                  : genre.minutes;
                const maxValue = genre.percentage !== null 
                  ? maxGenrePercentage 
                  : Math.max(...parsedGenres.map((g: any) => g.minutes), 1);
                const widthPercent = genre.percentage !== null
                  ? (genre.percentage / maxGenrePercentage) * 100
                  : (genre.minutes / maxValue) * 100;

                return (
                  <motion.div
                    key={index}
                    className="taste-item"
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <div className="taste-item-bar">
                      <motion.div
                        className="taste-item-bar-fill"
                        initial={{ width: 0 }}
                        animate={{
                          width: `${widthPercent}%`,
                        }}
                        transition={{ delay: index * 0.05 + 0.2, duration: 0.5 }}
                      />
                    </div>
                    <div className="taste-item-content">
                      <span className="taste-item-name">{genre.name}</span>
                      <span className="taste-item-stats">
                        {genre.percentage !== null 
                          ? `${genre.percentage.toFixed(1)}%`
                          : `${genre.minutes.toLocaleString()} min`}
                      </span>
                    </div>
                  </motion.div>
                );
              }
            )}
          </div>
        </div>
      )}

      {parsedActors.length > 0 && (
        <div className="taste-section">
          <h4 className="taste-section-title">Top Actors</h4>
          <div className="taste-list">
            {parsedActors.map(
              (actor: { name: string; minutes: number }, index: number) => {
                const hasMinutes = actor.minutes > 0;
                const barWidth = hasMinutes && maxActorMinutes > 0 
                  ? (actor.minutes / maxActorMinutes) * 100 
                  : 0;
                
                return (
                  <motion.div
                    key={index}
                    className="taste-item"
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    {hasMinutes && (
                      <div className="taste-item-bar">
                        <motion.div
                          className="taste-item-bar-fill actor-bar"
                          initial={{ width: 0 }}
                          animate={{
                            width: `${barWidth}%`,
                          }}
                          transition={{ delay: index * 0.05 + 0.2, duration: 0.5 }}
                        />
                      </div>
                    )}
                    <div className="taste-item-content">
                      <span className="taste-item-name">{actor.name}</span>
                      {hasMinutes && (
                        <span className="taste-item-stats">
                          {actor.minutes.toLocaleString()} min
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              }
            )}
          </div>
        </div>
      )}

      {parsedDirector && (
        <div className="taste-section">
          <h4 className="taste-section-title">Top Director</h4>
          <div className="taste-item director-item">
            <div className="taste-item-bar">
              <motion.div
                className="taste-item-bar-fill director-bar"
                initial={{ width: 0 }}
                animate={{ width: "100%" }}
                transition={{ delay: 0.3, duration: 0.5 }}
              />
            </div>
            <div className="taste-item-content">
              <span className="taste-item-name">{parsedDirector.name}</span>
              <span className="taste-item-stats">
                {parsedDirector.minutes.toLocaleString()} min
              </span>
            </div>
          </div>
        </div>
      )}

      {text.aside && <p className="card-aside taste-aside">{text.aside}</p>}
    </div>
  );
};
