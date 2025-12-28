import React from "react";
import { Card, CardDeckItem } from "../../types/cards";
import { WrapData } from "../../api";
import { SeasonalCard } from "./SeasonalCard";
import { StatCard } from "./StatCard";
import { SummaryCard } from "./SummaryCard";
import { ComparisonCard } from "./ComparisonCard";
import { RecordCard } from "./RecordCard";
import { BingeSessionsCard } from "./BingeSessionsCard";
import { TastePersonalityCard } from "./TastePersonalityCard";
import { RepeatWatchesCard } from "./RepeatWatchesCard";
import { FunCard } from "./FunCard";
import { TopContentCard } from "./TopContentCard";
import { DeviceCard } from "./DeviceCard";
import { WatchAgeCard } from "./WatchAgeCard";
import { extractPosterUrls } from "../../utils/imageUtils";
import { extractWatchAge } from "../../utils/metricExtractors";

export const buildCardDeck = (wrapData: WrapData): CardDeckItem[] => {
  if (!wrapData.cards || wrapData.cards.length === 0) {
    return [];
  }

  return wrapData.cards.map((card: Card, index: number) => {
    let content: React.ReactNode;

    if (card.kind === "pattern") {
      const seasonalData = wrapData.raw_data?.seasonal_analysis || null;
      content = (
        <SeasonalCard 
          seasonalData={seasonalData} 
          text={card.content.text}
          metrics={card.content.metrics}
        />
      );
    } else if (card.kind === "summary") {
      content = (
        <SummaryCard
          wrapData={wrapData}
          text={card.content.text}
          metrics={card.content.metrics}
        />
      );
    } else if (card.kind === "stat") {
      const hasNumberedItems = Object.keys(card.content.metrics).some((key) =>
        /^\d+$/.test(key)
      );
      if (hasNumberedItems && card.id.includes("top-content")) {
        content = (
          <TopContentCard
            text={card.content.text}
            metrics={card.content.metrics}
          />
        );
      } else if (
        card.id.includes("device") ||
        card.content.metrics.other_devices
      ) {
        content = (
          <DeviceCard text={card.content.text} metrics={card.content.metrics} />
        );
      } else {
        content = (
          <StatCard text={card.content.text} metrics={card.content.metrics} />
        );
      }
    } else if (card.kind === "comparison") {
      content = (
        <ComparisonCard
          text={card.content.text}
          metrics={card.content.metrics}
        />
      );
    } else if (card.kind === "record") {
      if (
        card.id.includes("binge") ||
        card.content.metrics.longest_sessions_sample
      ) {
        content = (
          <BingeSessionsCard
            text={card.content.text}
            metrics={card.content.metrics}
          />
        );
      } else {
        content = (
          <RecordCard text={card.content.text} metrics={card.content.metrics} />
        );
      }
    } else if (card.kind === "fun") {
      // Check for watch age card first
      const watchAge = extractWatchAge(card.content.metrics);
      if (
        card.id.includes("watch_age") ||
        watchAge.age !== null
      ) {
        content = (
          <WatchAgeCard
            text={card.content.text}
            metrics={card.content.metrics}
          />
        );
      } else if (
        card.id.includes("taste") ||
        card.id.includes("personality") ||
        card.content.metrics.top_genres_by_minutes ||
        card.content.metrics.top_actors_seen
      ) {
        content = (
          <TastePersonalityCard
            text={card.content.text}
            metrics={card.content.metrics}
          />
        );
      } else if (
        card.id.includes("repeat") ||
        card.content.metrics.most_repeats
      ) {
        content = (
          <RepeatWatchesCard
            text={card.content.text}
            metrics={card.content.metrics}
          />
        );
      } else {
        content = (
          <FunCard text={card.content.text} metrics={card.content.metrics} />
        );
      }
    } else {
      content = (
        <StatCard text={card.content.text} metrics={card.content.metrics} />
      );
    }

    // Extract poster URLs from metrics, matching titles to top_content
    let posterUrls = extractPosterUrls(card.content.metrics, wrapData.top_content);
    
    // For summary cards and first card (welcome/overall stats), create a collage from top_content
    const isFirstCard = index === 0;
    const isWelcomeCard = isFirstCard || card.id.includes("overall") || card.id.includes("welcome");
    
    if (card.kind === "summary" || isWelcomeCard) {
      // Use top 4-6 items from top_content for a nice collage
      const topContentThumbs = wrapData.top_content
        ?.slice(0, 6)
        .map(item => item.thumb)
        .filter((thumb): thumb is string => Boolean(thumb)) || [];
      // Remove duplicates
      const uniqueThumbs = Array.from(new Set(topContentThumbs));
      if (uniqueThumbs.length > 0) {
        posterUrls = uniqueThumbs;
      }
    }

    return {
      id: card.id,
      kind: card.kind,
      title: card.content.title,
      subtitle: card.content.subtitle,
      content,
      icon: card.visual_hint.icon,
      color: card.visual_hint.color,
      posterUrls,
      generatedImage: card.generated_image || null,
    };
  });
};
