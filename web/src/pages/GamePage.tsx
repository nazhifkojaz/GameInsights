import { useParams, Link } from "react-router-dom";
import { useGameData } from "../hooks/useGameData";
import HeroBanner from "../components/HeroBanner";
import StatsBar from "../components/StatsBar";
import PlayerChart from "../components/PlayerChart";
import DetailSection from "../components/DetailSection";
import LoadingSkeleton from "../components/LoadingSkeleton";
import ErrorDisplay from "../components/ErrorDisplay";
import { formatNumber, formatCurrency, formatHours } from "../utils/formatting";

export default function GamePage() {
  const { appid } = useParams<{ appid: string }>();

  if (!appid) {
    return (
      <div style={{ padding: "2rem", textAlign: "center" }}>
        <h1>Invalid Game</h1>
        <p>No AppID provided.</p>
        <Link to="/">&larr; Back to Search</Link>
      </div>
    );
  }

  const { game, playerHistory, loading, longWait, error } = useGameData(appid);

  if (loading) return <LoadingSkeleton longWait={longWait} />;
  if (error || !game) return <ErrorDisplay error={error} />;

  return (
    <main className="game-page">
      <nav className="game-nav">
        <Link to="/">&larr; Search</Link>
      </nav>

      <HeroBanner game={game} />
      <StatsBar game={game} />

      {playerHistory && <PlayerChart data={playerHistory} />}

      <div className="detail-sections">
        <DetailSection title="Sales & Revenue">
          <div className="detail-grid">
            <div>
              <span className="detail-label">Copies Sold</span>
              <span>{formatNumber(game.copies_sold)}</span>
            </div>
            <div>
              <span className="detail-label">Est. Revenue</span>
              <span>{formatCurrency(game.estimated_revenue)}</span>
            </div>
            <div>
              <span className="detail-label">Owners</span>
              <span>{formatNumber(game.owners)}</span>
            </div>
            <div>
              <span className="detail-label">Followers</span>
              <span>{formatNumber(game.followers)}</span>
            </div>
          </div>
        </DetailSection>

        <DetailSection title="Completion Times">
          <div className="detail-grid">
            <div>
              <span className="detail-label">Main Story</span>
              <span>{formatHours(game.comp_main)}</span>
            </div>
            <div>
              <span className="detail-label">Main + Extras</span>
              <span>{formatHours(game.comp_plus)}</span>
            </div>
            <div>
              <span className="detail-label">Completionist</span>
              <span>{formatHours(game.comp_100)}</span>
            </div>
            <div>
              <span className="detail-label">All Styles</span>
              <span>{formatHours(game.comp_all)}</span>
            </div>
          </div>
        </DetailSection>

        <DetailSection title="Linux / Steam Deck">
          <div className="detail-grid">
            <div>
              <span className="detail-label">ProtonDB Tier</span>
              <span>{game.protondb_tier || "N/A"}</span>
            </div>
            <div>
              <span className="detail-label">ProtonDB Score</span>
              <span>
                {game.protondb_score != null
                  ? `${game.protondb_score}%`
                  : "N/A"}
              </span>
            </div>
            <div>
              <span className="detail-label">Trending</span>
              <span>{game.protondb_trending || "N/A"}</span>
            </div>
            <div>
              <span className="detail-label">Confidence</span>
              <span>{game.protondb_confidence || "N/A"}</span>
            </div>
          </div>
        </DetailSection>

        <DetailSection title="Technical Info">
          <div className="detail-grid">
            <div>
              <span className="detail-label">Platforms</span>
              <span>{game.platforms?.join(", ") || "N/A"}</span>
            </div>
            <div>
              <span className="detail-label">Categories</span>
              <span>{game.categories?.join(", ") || "N/A"}</span>
            </div>
            <div>
              <span className="detail-label">Achievements</span>
              <span>{formatNumber(game.achievements_count)}</span>
            </div>
            <div>
              <span className="detail-label">Avg. Completion</span>
              <span>
                {game.achievements_percentage_average != null
                  ? `${game.achievements_percentage_average.toFixed(1)}%`
                  : "N/A"}
              </span>
            </div>
          </div>
        </DetailSection>
      </div>

      <footer className="game-footer">
        <span>AppID: {game.steam_appid}</span>
        <a
          href={`https://store.steampowered.com/app/${game.steam_appid}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          View on Steam Store &nearr;
        </a>
        <span>Data from GameInsights API</span>
      </footer>
    </main>
  );
}
