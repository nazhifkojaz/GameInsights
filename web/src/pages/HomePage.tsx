import SearchBar from "../components/SearchBar";

export default function HomePage() {
  return (
    <main className="home-page">
      <div className="home-content">
        <h1 className="home-title">GameInsights</h1>
        <p className="home-subtitle">Explore Steam game data</p>
        <SearchBar />
      </div>
    </main>
  );
}
