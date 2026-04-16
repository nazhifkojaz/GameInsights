import { useState, useId } from "react";

interface Props {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export default function DetailSection({
  title,
  children,
  defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const regionId = useId();
  const headerId = `${regionId}-header`;

  return (
    <div className="detail-section">
      <button
        id={headerId}
        className="detail-section-header"
        onClick={() => setOpen(!open)}
        type="button"
        aria-expanded={open}
        aria-controls={regionId}
      >
        <span>{title}</span>
        <span className="detail-section-icon">{open ? "\u25BE" : "\u25B8"}</span>
      </button>
      {open && (
        <div
          className="detail-section-body"
          id={regionId}
          role="region"
          aria-labelledby={headerId}
        >
          {children}
        </div>
      )}
    </div>
  );
}
