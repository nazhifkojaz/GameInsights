import { useState, useRef, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import { parseSearchInput } from "../utils/inputParser";
import type { SearchResult } from "../types/api";
import SearchResults from "./SearchResults";

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const blurTimer = useRef<number>(0);
  const navigate = useNavigate();

  // Abort in-flight request on unmount
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  // Clean up blur timer on unmount
  useEffect(() => {
    return () => clearTimeout(blurTimer.current);
  }, []);

  const doSearch = useCallback(
    async (value: string) => {
      const parsed = parseSearchInput(value);

      if (parsed.type === "appid") {
        navigate(`/games/${parsed.appid}`);
        return;
      }

      if (!parsed.query) {
        setResults([]);
        setShowResults(false);
        return;
      }

      // Cancel previous request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      try {
        const data = await apiClient.searchGames(
          parsed.query,
          5,
          controller.signal,
        );
        setResults(data);
        setShowResults(true);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        // Silently swallow non-abort errors for search (user can retry by typing)
      } finally {
        setLoading(false);
      }
    },
    [navigate],
  );

  // Debounce (300ms)
  useEffect(() => {
    if (!query.trim()) {
      abortRef.current?.abort();
      setResults([]);
      setShowResults(false);
      return;
    }
    const timer = setTimeout(() => doSearch(query), 300);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  return (
    <div className="search-container">
      <input
        type="text"
        className="search-input"
        placeholder="Search by game name, AppID, or Steam URL..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => {
          clearTimeout(blurTimer.current);
          if (results.length > 0) setShowResults(true);
        }}
        onBlur={() => {
          // Delay to allow click on result to register before dropdown unmounts
          blurTimer.current = window.setTimeout(
            () => setShowResults(false),
            150,
          );
        }}
      />
      {loading && <span className="search-spinner" />}
      {showResults && results.length > 0 && (
        <SearchResults
          results={results}
          onSelect={(appid) => {
            navigate(`/games/${appid}`);
            setShowResults(false);
          }}
        />
      )}
      {showResults && !loading && query.trim() && results.length === 0 && (
        <div className="search-empty">
          No games found for &quot;{query}&quot;
        </div>
      )}
    </div>
  );
}
