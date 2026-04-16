import type { SearchResult } from "../types/api";

interface Props {
  results: SearchResult[];
  onSelect: (appid: string) => void;
}

export default function SearchResults({ results, onSelect }: Props) {
  return (
    <ul className="search-results">
      {results.map((result) => (
        <li key={result.appid} className="search-result-item" role="option">
          <button
            type="button"
            className="search-result-button"
            onClick={() => onSelect(result.appid)}
          >
            <span className="result-name">{result.name}</span>
            <span className="result-appid">AppID: {result.appid}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
