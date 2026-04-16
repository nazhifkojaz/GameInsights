import type { Game } from "../types/api";
import { formatNumber, formatCurrency } from "../utils/formatting";

interface Props {
  game: Game;
}

export default function StatsBar({ game }: Props) {
  const price = game.is_free ? "Free" : formatCurrency(game.price_final);
  const reviews = game.review_score_desc || "N/A";
  const totalReviews = formatNumber(game.total_reviews);
  const players = formatNumber(game.ccu ?? game.active_player_24h);
  const peak = formatNumber(game.peak_active_player_all_time);
  const metacritic =
    game.metacritic_score != null ? String(game.metacritic_score) : "N/A";

  return (
    <div className="stats-bar">
      <div className="stat">
        <span className="stat-value stat-price">{price}</span>
        <span className="stat-label">Price</span>
      </div>
      <div className="stat">
        <span className="stat-value stat-reviews">{reviews}</span>
        <span className="stat-label">Reviews ({totalReviews})</span>
      </div>
      <div className="stat">
        <span className="stat-value">{players}</span>
        <span className="stat-label">Players (24h)</span>
      </div>
      <div className="stat">
        <span className="stat-value">{peak}</span>
        <span className="stat-label">All-Time Peak</span>
      </div>
      <div className="stat">
        <span className="stat-value stat-metacritic">{metacritic}</span>
        <span className="stat-label">Metacritic</span>
      </div>
    </div>
  );
}
