interface Props {
  longWait: boolean;
}

export default function LoadingSkeleton({ longWait }: Props) {
  return (
    <div className="skeleton" role="status" aria-busy="true" aria-live="polite">
      <div className="skeleton-hero">
        <div className="skeleton-image shimmer" />
        <div className="skeleton-title shimmer" />
        <div className="skeleton-meta shimmer" />
      </div>
      <div className="skeleton-stats">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton-stat shimmer" />
        ))}
      </div>
      <div className="skeleton-chart shimmer" />
      {longWait && (
        <p className="long-wait-message">
          Fetching fresh data, this may take a moment...
        </p>
      )}
    </div>
  );
}
