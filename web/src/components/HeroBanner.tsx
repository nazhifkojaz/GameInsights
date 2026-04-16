import type { Game } from "../types/api";
import { formatCurrency } from "../utils/formatting";

interface Props {
  game: Game;
}

export default function HeroBanner({ game }: Props) {
  const imageUrl = `https://cdn.akamai.steamstatic.com/steam/apps/${game.steam_appid}/header.jpg`;
  const price = game.is_free ? "Free to Play" : formatCurrency(game.price_final);
  const devs = game.developers?.join(", ") || "Unknown";

  return (
    <div className="hero-banner">
      <img
        src={imageUrl}
        alt={game.name}
        className="hero-image"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
        }}
      />
      <h1 className="hero-title">{game.name}</h1>
      <p className="hero-meta">
        {devs} &bull; {price} &bull;{" "}
        {game.release_date
          ? new Date(game.release_date).toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
            })
          : "Unknown release date"}
      </p>
      <div className="hero-tags">
        {game.genres?.map((genre) => (
          <span key={genre} className="tag">
            {genre}
          </span>
        ))}
      </div>
    </div>
  );
}
