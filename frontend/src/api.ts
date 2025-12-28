import axios from 'axios';

// Dynamically determine API URL based on current hostname
// This allows the app to work when accessed from other devices on the LAN
const getApiBaseUrl = (): string => {
  // Use environment variable if set (highest priority)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // If running in browser
  if (typeof window !== 'undefined') {
    const port = window.location.port;
    const hostname = window.location.hostname;
    
    // Development ports - need absolute URL to backend
    const devPorts = ['3000', '5173', '5174', '4200']; // React, Vite, Angular dev servers
    
    if (devPorts.includes(port)) {
      // For development, try common backend port
      return `http://${hostname}:8000`;
    }
    
    // For all other cases (Docker/nginx on any port), use relative URLs
    // nginx will proxy /api/* requests to the backend
    return '';
  }
  
  // Fallback to localhost for SSR or other cases
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// Debug logging (remove in production if needed)
if (typeof window !== 'undefined') {
  console.log('API Base URL:', API_BASE_URL || '(relative - will use current origin)');
  console.log('Current location:', window.location.href);
  console.log('Port:', window.location.port);
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000, // 10 second timeout
});

// Add response interceptor for better error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
      const baseUrl = API_BASE_URL || window.location.origin;
      error.message = `Cannot connect to backend API at ${baseUrl}. Please ensure the backend server is running.`;
    }
    return Promise.reject(error);
  }
);

export interface User {
  id: string;
  username: string;
  title?: string;
  thumb?: string;
}

export interface Insight {
  title: string;
  description: string;
  value: string;
  icon?: string;
  category: string;
}

export interface GenreStat {
  genre: string;
  watch_time: number;
  count: number;
  percentage: number;
}

export interface ActorStat {
  name: string;
  watch_time: number;
  count: number;
}

export interface DeviceStat {
  device: string;
  watch_time: number;
  percentage: number;
}

export interface BingeSession {
  date: string;
  duration: number;
  content: string[];
  episodes: number;
}

export interface WrapData {
  user: User;
  period: {
    start: string;
    end: string;
  };
  total_watch_time: number;
  total_items_watched: number;
  total_episodes_watched: number;
  total_movies_watched: number;
  insights: Insight[];
  top_genres: GenreStat[];
  top_actors: ActorStat[];
  top_directors: ActorStat[];
  top_content: Array<{
    title: string;
    watch_time: number;
    thumb?: string;
    year?: string;
    media_type?: string;
  }>;
  devices: DeviceStat[];
  platforms: DeviceStat[];
  longest_binge?: BingeSession;
  binge_sessions: BingeSession[];
  total_requests: number;
  approved_requests: number;
  most_requested_genre?: string;
  fun_facts: string[];
  cards?: Array<{
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
    generated_image?: string | null;
  }>;
  raw_data?: any;
}

export const getUsers = async (): Promise<User[]> => {
  const response = await api.get<User[]>('/api/users');
  return response.data;
};

export const getWrap = async (username: string): Promise<WrapData> => {
  const response = await api.get<WrapData>(`/api/wrap/${username}`);
  return response.data;
};

export const getWrapByToken = async (token: string): Promise<WrapData> => {
  const response = await api.get<WrapData>(`/api/wrap-by-token/${token}`);
  return response.data;
};

export const getTokenForUser = async (username: string): Promise<{ username: string; token: string }> => {
  const response = await api.get<{ username: string; token: string }>(`/api/token/${username}`);
  return response.data;
};

export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get('/api/health');
  return response.data;
};

