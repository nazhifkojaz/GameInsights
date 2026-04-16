import { useState } from "react";

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

  return (
    <div className="detail-section">
      <button
        className="detail-section-header"
        onClick={() => setOpen(!open)}
        type="button"
      >
        <span>{title}</span>
        <span className="detail-section-icon">{open ? "\u25BE" : "\u25B8"}</span>
      </button>
      {open && <div className="detail-section-body">{children}</div>}
    </div>
  );
}
