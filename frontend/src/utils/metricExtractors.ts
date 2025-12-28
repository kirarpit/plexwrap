/**
 * Utility functions to extract metrics with flexible key matching
 * Handles variations in metric keys produced by the LLM
 */

/**
 * Find a metric value by trying multiple possible key names
 */
export const findMetric = (
  metrics: Record<string, any>,
  possibleKeys: string[]
): any => {
  for (const key of possibleKeys) {
    if (key in metrics && metrics[key] !== null && metrics[key] !== undefined) {
      return metrics[key];
    }
  }
  return null;
};

/**
 * Extract duration in minutes from various metric key formats
 */
export const extractDurationMinutes = (metrics: Record<string, any>): number | null => {
  const possibleKeys = [
    'longest_binge_duration_minutes',
    'longest_binge_minutes',
    'longest_session_duration_minutes',
    'longest_session_minutes',
    'day_with_most_minutes',
    'duration_minutes',
    'watch_time_minutes',
    'minutes',
    'longest_binge_duration',
    'longest_session_duration',
    'duration'
  ];
  
  const value = findMetric(metrics, possibleKeys);
  if (typeof value === 'number') return value;
  return null;
};

/**
 * Extract count from various metric key formats
 */
export const extractCount = (metrics: Record<string, any>): number | null => {
  const possibleKeys = [
    'longest_binge_episodes',
    'longest_binge_items',
    'longest_session_items',
    'day_with_most_items',
    'binge_sessions_count',
    'sessions_count',
    'count',
    'episodes',
    'items',
    'total_items',
    'total_episodes'
  ];
  
  const value = findMetric(metrics, possibleKeys);
  if (typeof value === 'number') return value;
  return null;
};

/**
 * Extract date from various metric key formats
 */
export const extractDate = (metrics: Record<string, any>): string | null => {
  const possibleKeys = [
    'longest_binge_date',
    'binge_date',
    'date',
    'session_date'
  ];
  
  const value = findMetric(metrics, possibleKeys);
  if (typeof value === 'string') return value;
  return null;
};

/**
 * Extract featured title(s) from various formats
 */
export const extractFeaturedTitles = (metrics: Record<string, any>): string[] => {
  // Try array first
  const featuredTitlesArray = findMetric(metrics, ['featured_titles', 'longest_binge_titles']);
  if (Array.isArray(featuredTitlesArray)) {
    return featuredTitlesArray.map(t => typeof t === 'string' ? t : (t?.title || t?.name || String(t)));
  }
  
  // Try single title
  const featuredTitle = findMetric(metrics, ['featured_title', 'top_title', 'most_watched_title', 'longest_binge_title']);
  if (typeof featuredTitle === 'string') {
    return [featuredTitle];
  }
  
  return [];
};

/**
 * Extract top device information
 */
export const extractTopDevice = (metrics: Record<string, any>): {
  name: string | null;
  minutes: number | null;
  percentage: number | null;
} => {
  const deviceName = findMetric(metrics, [
    'top_device',
    'featured_device',
    'most_used_device',
    'primary_device'
  ]);
  
  if (!deviceName) {
    return { name: null, minutes: null, percentage: null };
  }
  
  // Try to find minutes/percentage for this device
  const deviceKey = String(deviceName).toLowerCase().replace(/\s+/g, '_');
  const minutes = findMetric(metrics, [
    `${deviceKey}_watch_time_minutes`,
    `${deviceKey}_watch_minutes`,
    `${deviceKey}_minutes`,
    'top_device_watch_time_minutes',
    'top_device_minutes'
  ]);
  
  const percentage = findMetric(metrics, [
    `${deviceKey}_percentage`,
    'top_device_percentage',
    'tv_dominance_percent'
  ]);
  
  return {
    name: String(deviceName),
    minutes: typeof minutes === 'number' ? minutes : null,
    percentage: typeof percentage === 'number' ? percentage : null
  };
};

/**
 * Extract other devices information
 */
export const extractOtherDevices = (metrics: Record<string, any>): Array<{
  name: string;
  minutes: number;
  percentage: number;
}> => {
  // Try devices object
  const devicesObj = findMetric(metrics, ['devices', 'other_devices']);
  if (devicesObj && typeof devicesObj === 'object' && !Array.isArray(devicesObj)) {
    return Object.entries(devicesObj).map(([name, data]: [string, any]) => {
      if (typeof data === 'object' && data !== null) {
        return {
          name,
          minutes: data.watch_time_minutes || data.minutes || data.watch_time || 0,
          percentage: data.percentage || 0
        };
      }
      return { name, minutes: 0, percentage: 0 };
    });
  }
  
  // Try devices_simplified object
  const devicesSimplified = findMetric(metrics, ['devices_simplified']);
  if (devicesSimplified && typeof devicesSimplified === 'object' && !Array.isArray(devicesSimplified)) {
    return Object.entries(devicesSimplified).map(([name, percentage]: [string, any]) => ({
      name,
      minutes: 0, // Not available in simplified format
      percentage: typeof percentage === 'number' ? percentage : 0
    }));
  }
  
  // Try array format
  const devicesArray = Array.isArray(devicesObj) ? devicesObj : [];
  return devicesArray.map((device: any) => {
    if (typeof device === 'string') {
      return { name: device, minutes: 0, percentage: 0 };
    }
    return {
      name: device.device || device.name || String(device),
      minutes: device.minutes || device.watch_time_minutes || 0,
      percentage: device.percentage || 0
    };
  });
};

/**
 * Extract repeat watch information
 */
export const extractRepeatWatches = (metrics: Record<string, any>): {
  topTitle: string | null;
  topCount: number | null;
  others: Array<{ title: string; count: number }>;
} => {
  // Try various formats for top repeat
  const topTitle = findMetric(metrics, [
    'featured_title',
    'most_repeated_title',
    'top_repeat_title',
    'top_title'
  ]);
  
  const topCount = findMetric(metrics, [
    'top_repeat_count',
    'repeat_count_top',
    'most_repeats',
    'top_repeats',
    'repeat_count'
  ]);
  
  // Try various formats for other repeats
  const others: Array<{ title: string; count: number }> = [];
  
  // Try object format like other_repeat_favorites or top_repeat_titles
  const repeatObj = findMetric(metrics, [
    'other_repeat_favorites',
    'top_repeat_titles',
    'repeat_watches_top',
    'other_repeaters'
  ]);
  
  if (repeatObj && typeof repeatObj === 'object' && !Array.isArray(repeatObj)) {
    Object.entries(repeatObj).forEach(([title, count]: [string, any]) => {
      if (typeof count === 'number') {
        others.push({ title, count });
      }
    });
  }
  
  // Try array format
  const repeatArray = findMetric(metrics, ['other_repeaters']);
  if (Array.isArray(repeatArray)) {
    repeatArray.forEach((item: any) => {
      if (typeof item === 'object' && item !== null) {
        others.push({
          title: item.title || item.name || String(item),
          count: item.count || item.repeat_count || 0
        });
      }
    });
  }
  
  // Try second_repeat_title format
  const secondTitle = findMetric(metrics, ['second_repeat_title']);
  const secondCount = findMetric(metrics, ['second_repeat_count']);
  if (secondTitle && secondCount) {
    others.push({
      title: String(secondTitle),
      count: typeof secondCount === 'number' ? secondCount : 0
    });
  }
  
  return {
    topTitle: topTitle ? String(topTitle) : null,
    topCount: typeof topCount === 'number' ? topCount : null,
    others: others.sort((a, b) => b.count - a.count)
  };
};

/**
 * Extract top content titles with watch times
 */
export const extractTopContent = (metrics: Record<string, any>): Array<{
  title: string;
  minutes?: number;
  count?: number;
}> => {
  const items: Array<{ title: string; minutes?: number; count?: number }> = [];
  const seenTitles = new Set<string>();
  
  // Try featured_titles array first - match with corresponding watch times
  const featuredTitles = extractFeaturedTitles(metrics);
  if (featuredTitles.length > 0) {
    featuredTitles.forEach((title, index) => {
      if (seenTitles.has(title)) return;
      seenTitles.add(title);
      
      // Try to match watch time by position
      const minutes = findMetric(metrics, [
        index === 0 ? 'top_title_watch_time_minutes' : '',
        index === 0 ? 'top_watch_time_minutes' : '',
        index === 1 ? 'second_watch_time_minutes' : '',
        index === 1 ? 'second_title_watch_time_minutes' : '',
        index === 2 ? 'third_watch_time_minutes' : '',
        index === 2 ? 'third_title_watch_time_minutes' : '',
        `first_watch_time_minutes`,
        `second_watch_time_minutes`,
        `third_watch_time_minutes`
      ].filter(Boolean));
      
      items.push({
        title,
        minutes: typeof minutes === 'number' ? minutes : undefined
      });
    });
  }
  
  // Try explicit top/second/third format (only if not already added from featured_titles)
  const topTitle = findMetric(metrics, ['top_title', 'first_title']);
  if (topTitle && !seenTitles.has(String(topTitle))) {
    seenTitles.add(String(topTitle));
    const topMinutes = findMetric(metrics, [
      'top_title_watch_time_minutes',
      'top_watch_time_minutes',
      'first_watch_time_minutes'
    ]);
    items.push({
      title: String(topTitle),
      minutes: typeof topMinutes === 'number' ? topMinutes : undefined
    });
  }
  
  const secondTitle = findMetric(metrics, ['second_title']);
  if (secondTitle && !seenTitles.has(String(secondTitle))) {
    seenTitles.add(String(secondTitle));
    const secondMinutes = findMetric(metrics, [
      'second_watch_time_minutes',
      'second_title_watch_time_minutes'
    ]);
    items.push({
      title: String(secondTitle),
      minutes: typeof secondMinutes === 'number' ? secondMinutes : undefined
    });
  }
  
  const thirdTitle = findMetric(metrics, ['third_title']);
  if (thirdTitle && !seenTitles.has(String(thirdTitle))) {
    seenTitles.add(String(thirdTitle));
    const thirdMinutes = findMetric(metrics, [
      'third_watch_time_minutes',
      'third_title_watch_time_minutes'
    ]);
    items.push({
      title: String(thirdTitle),
      minutes: typeof thirdMinutes === 'number' ? thirdMinutes : undefined
    });
  }
  
  // Try numbered format (1, 2, 3, etc.) - only if not already added
  Object.entries(metrics)
    .filter(([key]) => /^\d+$/.test(key))
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .forEach(([key, value]) => {
      let title: string | null = null;
      let minutes: number | undefined = undefined;
      let count: number | undefined = undefined;
      
      if (typeof value === 'object' && value !== null) {
        title = value.title || value.name || String(value);
        minutes = value.minutes || value.watch_time_minutes;
        count = value.count || value.repeat_count;
      } else if (typeof value === 'string') {
        title = value;
      }
      
      if (title && !seenTitles.has(title)) {
        seenTitles.add(title);
        items.push({ title, minutes, count });
      }
    });
  
  return items;
};

/**
 * Extract seasonal data from metrics
 */
export const extractSeasonalData = (metrics: Record<string, any>): {
  mostActiveSeason: string | null;
  seasonBreakdown: Record<string, number>;
} => {
  const mostActiveSeason = findMetric(metrics, [
    'most_active_season',
    'peak_season'
  ]);
  
  const breakdown = findMetric(metrics, [
    'season_breakdown',
    'seasonal_breakdown',
    'seasonal_data'
  ]);
  
  const seasonBreakdown: Record<string, number> = {};
  
  if (breakdown && typeof breakdown === 'object' && !Array.isArray(breakdown)) {
    Object.entries(breakdown).forEach(([key, value]: [string, any]) => {
      // Handle keys like "Winter_minutes", "Spring_minutes", etc.
      const seasonMatch = key.match(/^(Winter|Spring|Summer|Fall)_minutes?$/i);
      if (seasonMatch) {
        seasonBreakdown[seasonMatch[1]] = typeof value === 'number' ? value : 0;
      } else if (['Winter', 'Spring', 'Summer', 'Fall'].includes(key)) {
        seasonBreakdown[key] = typeof value === 'number' ? value : 0;
      }
    });
  }
  
  return {
    mostActiveSeason: mostActiveSeason ? String(mostActiveSeason) : null,
    seasonBreakdown
  };
};

/**
 * Extract watch age estimate
 */
export const extractWatchAge = (metrics: Record<string, any>): {
  age: number | null;
  confidence: string | number | null;
  range?: string | null;
} => {
  const age = findMetric(metrics, [
    'watch_age_years',
    'watch_age_estimate',
    'estimated_watch_age',
    'estimated_watch_age_years',
    'watch_age'
  ]);
  
  const confidence = findMetric(metrics, [
    'confidence',
    'confidence_level',
    'confidence_score'
  ]);
  
  const range = findMetric(metrics, [
    'estimated_age_range',
    'age_range'
  ]);
  
  return {
    age: typeof age === 'number' ? age : null,
    confidence: confidence !== null && confidence !== undefined ? confidence : null,
    range: range ? String(range) : undefined
  };
};

