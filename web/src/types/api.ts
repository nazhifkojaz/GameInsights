export interface SearchResult {
  appid: string;
  name: string;
  search_score: number;
}

export interface Game {
  steam_appid: string;
  name: string;
  is_free: boolean | null;
  price_final: number | null;
  price_currency: string | null;
  review_score_desc: string | null;
  total_reviews: number | null;
  total_positive: number | null;
  total_negative: number | null;
  ccu: number | null;
  active_player_24h: number | null;
  peak_active_player_all_time: number | null;
  metacritic_score: number | null;
  developers: string[];
  publishers: string[];
  genres: string[];
  tags: string[];
  categories: string[];
  platforms: string[];
  languages: string[];
  release_date: string | null;
  days_since_release: number | null;
  copies_sold: number | null;
  estimated_revenue: number | null;
  owners: number | null;
  followers: number | null;
  comp_main: number | null;
  comp_plus: number | null;
  comp_100: number | null;
  comp_all: number | null;
  achievements_count: number | null;
  achievements_percentage_average: number | null;
  protondb_tier: string | null;
  protondb_score: number | null;
  protondb_trending: string | null;
  protondb_confidence: string | null;
  average_playtime: number | null;
  [key: string]: unknown;
}

export interface PlayerHistory {
  steam_appid: string;
  name: string;
  peak_active_player_all_time: number | null;
  [key: string]: unknown;
}

export interface ApiError {
  error: string;
  message: string;
  identifier?: string;
  source?: string;
}

export interface HealthCheck {
  status: string;
  api_title: string;
  api_version: string;
  pool_size: number;
  pool_available: number;
}
