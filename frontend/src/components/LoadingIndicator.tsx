import { useEffect, useState } from "react";
import { onLoadingChange } from "../api/client";

// Shows automatically whenever any api.* call is in flight (see client.ts's
// request-counting) -- one global indicator instead of every page tracking
// its own loading state.
export default function LoadingIndicator() {
  const [loading, setLoading] = useState(false);

  useEffect(() => onLoadingChange(setLoading), []);

  if (!loading) return null;

  return (
    <div className="loading-indicator" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      Loading…
    </div>
  );
}
