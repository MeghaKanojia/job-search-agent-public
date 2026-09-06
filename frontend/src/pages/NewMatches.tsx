import { useEffect, useState } from "react";
import { api, JobPosting } from "../api/client";
import { useToast } from "../components/Toast";

type SortOption = "posted_at" | "score";

const POSTED_WITHIN_OPTIONS = [
  { value: "", label: "Any time" },
  { value: "1", label: "Past 24 hours" },
  { value: "3", label: "Past 3 days" },
  { value: "7", label: "Past week" },
  { value: "30", label: "Past month" },
];

function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function hoursSince(value: string | null): number | null {
  if (!value) return null;
  return (Date.now() - new Date(value).getTime()) / (1000 * 60 * 60);
}

function FreshnessBadge({ postedAt }: { postedAt: string | null }) {
  const hours = hoursSince(postedAt);
  if (hours === null) return <span>-</span>;
  if (hours <= 24) return <span className="badge badge-fresh">New today</span>;
  if (hours <= 72) return <span className="badge badge-recent">{Math.round(hours / 24)}d ago</span>;
  return <span>{formatDate(postedAt)}</span>;
}

export default function NewMatches() {
  const [postings, setPostings] = useState<JobPosting[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortOption>("posted_at");
  const [postedWithinDays, setPostedWithinDays] = useState<string>("");
  const [minScore, setMinScore] = useState<number>(0);
  const { showToast } = useToast();

  useEffect(() => {
    api
      .listMatches({
        minScore,
        sort,
        postedWithinDays: postedWithinDays ? Number(postedWithinDays) : undefined,
      })
      .then(setPostings)
      .catch((e) => setError(String(e)));
  }, [sort, postedWithinDays, minScore]);

  const stage = async (id: number) => {
    try {
      await api.stageApplication(id);
      showToast("Staged for review, check the Review Queue tab.", "success");
    } catch (e) {
      showToast(`Failed to stage this posting: ${e}`, "error");
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>New Matches</h1>
          <div className="page-subtitle">{postings.length} posting{postings.length === 1 ? "" : "s"}</div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="filter-bar">
        <div className="filter-field">
          <label htmlFor="sort">Sort by</label>
          <select id="sort" value={sort} onChange={(e) => setSort(e.target.value as SortOption)}>
            <option value="posted_at">Date posted (newest first)</option>
            <option value="score">Match score (highest first)</option>
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="posted-within">Posted within</label>
          <select id="posted-within" value={postedWithinDays} onChange={(e) => setPostedWithinDays(e.target.value)}>
            {POSTED_WITHIN_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="min-score">Min. match score</label>
          <input
            id="min-score"
            type="number"
            step={0.1}
            min={0}
            max={1}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value) || 0)}
          />
        </div>
      </div>

      <div className="card">
        {postings.map((p) => (
          <div className="job-row" key={p.id}>
            <div className="job-row-icon">{(p.company ?? p.source).charAt(0).toUpperCase()}</div>
            <div className="job-row-main">
              <a
                className="job-title-link"
                href={p.url}
                target="_blank"
                rel="noreferrer"
                title={p.relevance_reasoning ?? undefined}
              >
                {p.title}
              </a>
              <div className="job-row-meta">
                {p.company ?? "Unknown company"} · {p.source} · <FreshnessBadge postedAt={p.posted_at} /> · found{" "}
                {formatDate(p.ingested_at)}
              </div>
            </div>
            <div className="job-row-value">
              {p.salary_text && <div>{p.salary_text}</div>}
              {p.keyword_match_score !== null && (
                <span className="badge badge-score">{p.keyword_match_score.toFixed(2)}</span>
              )}
            </div>
            <button className="btn btn-small" onClick={() => stage(p.id)}>
              Stage for review
            </button>
          </div>
        ))}
        {postings.length === 0 && !error && (
          <div className="empty-state">No matches yet for these filters. Try widening the date range.</div>
        )}
      </div>
    </div>
  );
}
