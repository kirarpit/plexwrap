/**
 * Utility functions for handling media poster images
 */

/**
 * Convert a Plex thumb path to a proxied URL via the backend API
 * The backend proxies images through Tautulli so the frontend doesn't need direct access
 */
export const getPlexImageUrl = async (thumbPath: string | null | undefined): Promise<string | null> => {
  if (!thumbPath) return null;
  
  // If it's already a full URL (external), return it
  // But if it's a Plex URL, we should still proxy it through the backend
  // For now, only skip if it's clearly not a Plex path
  if (thumbPath.startsWith('http://') || thumbPath.startsWith('https://')) {
    // Check if it's a Plex URL - if so, extract the path and proxy it
    const plexMatch = thumbPath.match(/https?:\/\/[^\/]+\/(.+)/);
    if (plexMatch) {
      // Extract the path part and proxy it
      thumbPath = plexMatch[1];
    } else {
      // External URL, return as-is
      return thumbPath;
    }
  }
  
  // Remove leading slash if present
  const cleanPath = thumbPath.startsWith('/') ? thumbPath.slice(1) : thumbPath;
  
  // Use the API endpoint to proxy the image
  // Match the same logic as api.ts for consistency
  const port = typeof window !== 'undefined' ? window.location.port : '';
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  
  let apiBaseUrl = '';
  
  // Development ports - need absolute URL to backend
  const devPorts = ['3000', '5173', '5174', '4200'];
  
  if (devPorts.includes(port)) {
    // For development, use absolute URL to backend
    apiBaseUrl = `http://${hostname}:8000`;
  } else {
    // For all other cases (Docker/nginx on any port), use relative URLs
    // nginx will proxy /api/* requests to the backend
    apiBaseUrl = '';
  }
  
  // Return the proxied endpoint URL directly
  // The backend will fetch and serve the image
  return `${apiBaseUrl}/api/plex-image/${cleanPath}`;
};

/**
 * Extract poster URLs from card metrics
 * Looks for items with 'thumb' property in various structures
 * Also matches titles to top_content to find poster URLs
 */
export const extractPosterUrls = (
  metrics: Record<string, any>,
  topContent?: Array<{ title: string; thumb?: string }>
): string[] => {
  const urls: string[] = [];
  const titleToThumb = new Map<string, string>();
  
  // Build a map of titles to thumb URLs from top_content
  if (topContent) {
    topContent.forEach(item => {
      if (item.title && item.thumb) {
        // Normalize title for matching (remove year, extra spaces, etc.)
        const normalizedTitle = item.title
          .replace(/\s*\(\d{4}\)\s*$/, '') // Remove year in parentheses
          .trim()
          .toLowerCase();
        titleToThumb.set(normalizedTitle, item.thumb);
        // Also store original title
        titleToThumb.set(item.title.toLowerCase(), item.thumb);
      }
    });
  }
  
  // Helper to find thumb by title
  const findThumbByTitle = (title: string | null | undefined): string | null => {
    if (!title) return null;
    const normalized = title.trim().toLowerCase();
    return titleToThumb.get(normalized) || null;
  };
  
  // Check numbered items (1, 2, 3, etc.)
  Object.entries(metrics).forEach(([key, value]) => {
    if (/^\d+$/.test(key) && value && typeof value === 'object') {
      if (value.thumb) {
        urls.push(value.thumb);
      } else if (value.title || value.name) {
        const thumb = findThumbByTitle(value.title || value.name);
        if (thumb) urls.push(thumb);
      }
    }
  });
  
  // Check common metric keys
  const commonKeys = [
    'most_repeats',
    'other_repeaters',
    'longest_sessions_sample',
    'sessions',
    'longest_binge_title',
    'featured_titles',
    'featured_title',
    'top_title',
    'top_titles',
  ];
  
  commonKeys.forEach(key => {
    const item = metrics[key];
    if (item) {
      if (Array.isArray(item)) {
        item.forEach((entry: any) => {
          if (entry && typeof entry === 'object') {
            if (entry.thumb) {
              urls.push(entry.thumb);
            } else if (entry.title || entry.name) {
              const thumb = findThumbByTitle(entry.title || entry.name);
              if (thumb) urls.push(thumb);
            }
            // Check nested items array (for binge sessions)
            if (entry.items && Array.isArray(entry.items)) {
              entry.items.forEach((itemTitle: string) => {
                const thumb = findThumbByTitle(itemTitle);
                if (thumb) urls.push(thumb);
              });
            }
          }
        });
      } else if (typeof item === 'object' && item.thumb) {
        urls.push(item.thumb);
      } else if (typeof item === 'string') {
        // String title - try to find thumb
        const thumb = findThumbByTitle(item);
        if (thumb) urls.push(thumb);
      }
    }
  });
  
  // Check for featured_titles array (for collages)
  if (metrics.featured_titles && Array.isArray(metrics.featured_titles)) {
    metrics.featured_titles.forEach((title: string) => {
      const thumb = findThumbByTitle(title);
      if (thumb) urls.push(thumb);
    });
  }
  
  // Check for featured_title (single)
  if (metrics.featured_title && typeof metrics.featured_title === 'string') {
    const thumb = findThumbByTitle(metrics.featured_title);
    if (thumb) urls.push(thumb);
  }
  
  // Remove duplicates and filter out falsy values
  const uniqueUrls = Array.from(new Set(urls.filter(Boolean)));
  return uniqueUrls;
};

/**
 * Convert multiple thumb paths to URLs (for collage)
 */
export const getPosterUrls = async (thumbPaths: string[]): Promise<string[]> => {
  const urlPromises = thumbPaths.map(path => getPlexImageUrl(path));
  const urls = await Promise.all(urlPromises);
  return urls.filter((url): url is string => url !== null);
};

