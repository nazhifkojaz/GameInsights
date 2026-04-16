import { ApiRequestError } from "../api/client";

interface Props {
  error: ApiRequestError | null;
}

export default function ErrorDisplay({ error }: Props) {
  if (!error) {
    return (
      <div className="error-display">
        <h2>Something went wrong</h2>
        <p>An unexpected error occurred. Please try again later.</p>
      </div>
    );
  }

  if (error.status === 404) {
    return (
      <div className="error-display">
        <h2>Game not found</h2>
        <p>
          No game found with this AppID. Please check the ID and try again.
        </p>
      </div>
    );
  }

  return (
    <div className="error-display">
      <h2>Service temporarily unavailable</h2>
      <p>{error.body.message || "Please try again later."}</p>
    </div>
  );
}
