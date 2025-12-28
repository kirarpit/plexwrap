export interface Card {
  id: string;
  kind: "summary" | "stat" | "record" | "pattern" | "comparison" | "fun";
  visual_hint: {
    icon: string | null;
    color: string | null;
  };
  content: {
    title: string;
    subtitle: string | null;
    metrics: Record<string, any>;
    text: {
      headline: string;
      description: string;
      aside: string | null;
    };
  };
  image_description?: string; // Description of what the image should look like
  generated_image?: string | null; // Path to generated image if available
}

export interface SeasonalData {
  by_season?: {
    Winter?: { time: number; count: number };
    Spring?: { time: number; count: number };
    Summer?: { time: number; count: number };
    Fall?: { time: number; count: number };
  };
  most_active?: string;
  most_active_time?: number;
}

export interface CardText {
  headline: string;
  description: string;
  aside: string | null;
}

export interface CardDeckItem {
  id: string;
  kind: string;
  title: string;
  subtitle: string | null;
  content: React.ReactNode;
  icon: string | null;
  color: string | null;
  posterUrls?: string[];
  generatedImage?: string | null; // Path to generated image if available
}

