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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    if (menuOpenId === null) return;
    const closeOnOutsideClick = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest(".icon-menu-wrapper")) {
        setMenuOpenId(null);
      }
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [menuOpenId]);

  const load = () => {
    api
      .listMatches({
        minScore,
        sort,
        postedWithinDays: postedWithinDays ? Number(postedWithinDays) : undefined,
      })
      .then(setPostings)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    load();
    setSelectedIds(new Set());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort, postedWithinDays, minScore]);

  const stage = async (id: number) => {
    try {
      await api.stageApplication(id);
      showToast("Staged for review, check the Review Queue tab.", "success");
      load();
    } catch (e) {
      showToast(`Failed to stage this posting: ${e}`, "error");
    }
  };

  const deleteOne = async (id: number) => {
    setMenuOpenId(null);
    if (!window.confirm("Permanently delete this posting? This can't be undone.")) return;
    setError(null);
    try {
      await api.deleteMatch(id);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const allSelected = postings.length > 0 && postings.every((p) => selectedIds.has(p.id));

  const toggleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        postings.forEach((p) => next.delete(p.id));
      } else {
        postings.forEach((p) => next.add(p.id));
      }
      return next;
    });
  };

  const toggleOne = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const deleteSelected = async () => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    if (
      !window.confirm(
        `Permanently delete ${ids.length} posting${ids.length === 1 ? "" : "s"}? This can't be undone.`
      )
    ) {
      return;
    }
    setError(null);
    setDeleting(true);
    try {
      await Promise.all(ids.map((id) => api.deleteMatch(id)));
      setSelectedIds(new Set());
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(false);
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

      {selectedIds.size > 0 && (
        <div className="bulk-toolbar">
          <span className="bulk-toolbar-count">{selectedIds.size} selected</span>
          <div className="bulk-toolbar-actions">
            <button className="btn btn-secondary btn-small" onClick={() => setSelectedIds(new Set())}>
              Clear selection
            </button>
            <button className="btn btn-danger btn-small" disabled={deleting} onClick={deleteSelected}>
              {deleting ? "Deleting…" : `Delete ${selectedIds.size} selected`}
            </button>
          </div>
        </div>
      )}

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
        {postings.length > 0 && (
          <div className="job-row job-row-select-all">
            <div className="checkbox-col">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Select all" />
            </div>
            <div className="job-row-main page-subtitle">Select all</div>
          </div>
        )}
        {postings.map((p) => (
          <div className={`job-row${selectedIds.has(p.id) ? " row-selected" : ""}`} key={p.id}>
            <div className="checkbox-col">
              <input
                type="checkbox"
                checked={selectedIds.has(p.id)}
                onChange={() => toggleOne(p.id)}
                aria-label={`Select ${p.title}`}
              />
            </div>
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
            <span className="icon-menu-wrapper">
              <button
                type="button"
                className="icon-btn"
                aria-label="Posting actions"
                onClick={() => setMenuOpenId(menuOpenId === p.id ? null : p.id)}
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <circle cx="8" cy="3" r="1.4" />
                  <circle cx="8" cy="8" r="1.4" />
                  <circle cx="8" cy="13" r="1.4" />
                </svg>
              </button>
              {menuOpenId === p.id && (
                <div className="icon-menu">
                  <button
                    type="button"
                    className="icon-menu-item icon-menu-item-danger"
                    onClick={() => deleteOne(p.id)}
                  >
                    Delete
                  </button>
                </div>
              )}
            </span>
          </div>
        ))}
        {postings.length === 0 && !error && (
          <div className="empty-state">No matches yet for these filters. Try widening the date range.</div>
        )}
      </div>
    </div>
  );
}
