import { useEffect, useMemo, useRef, useState } from "react";
import { api, Application, DocumentItem } from "../api/client";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 15;

// This tracker is for applications that have actually been submitted and their
// post-apply lifecycle -- "new"/"staged_for_review"/"approved_ready_to_submit"
// belong to New Matches/Review Queue instead, so they're excluded here both as
// filter/edit options and from the listing itself (see load()).
const STATUSES = ["applied", "viewed", "interview", "offer", "rejected", "withdrawn"];

function latestResumeFor(docs: DocumentItem[], applicationId: number): DocumentItem | null {
  const resumes = docs.filter((d) => d.application_id === applicationId && d.doc_type === "resume");
  if (resumes.length === 0) return null;
  return resumes.reduce((latest, d) => (d.version_number > latest.version_number ? d : latest));
}

export default function ApplicationsTracker() {
  const [apps, setApps] = useState<Application[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [resumeMenuOpenId, setResumeMenuOpenId] = useState<number | null>(null);
  const fileInputs = useRef<Record<number, HTMLInputElement | null>>({});

  useEffect(() => {
    if (resumeMenuOpenId === null) return;
    const closeOnOutsideClick = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest(".icon-menu-wrapper")) {
        setResumeMenuOpenId(null);
      }
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [resumeMenuOpenId]);

  const load = () => {
    api
      .listApplications(statusFilter || undefined)
      .then((data) => setApps(data.filter((a) => STATUSES.includes(a.status))));
    api.listDocuments().then(setDocs);
  };

  const changeStatus = async (id: number, status: string) => {
    setError(null);
    try {
      await api.updateApplicationStatus(id, status);
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    load();
    setSelectedIds(new Set());
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const sortedApps = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = q
      ? apps.filter(
          (a) =>
            (a.company ?? "").toLowerCase().includes(q) || (a.role_title ?? "").toLowerCase().includes(q)
        )
      : apps;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const diff = new Date(a.last_status_change_at).getTime() - new Date(b.last_status_change_at).getTime();
      return sortDir === "asc" ? diff : -diff;
    });
    return copy;
  }, [apps, search, sortDir]);

  useEffect(() => {
    setPage(1);
  }, [search]);

  const pageCount = Math.max(1, Math.ceil(sortedApps.length / PAGE_SIZE));
  const pagedApps = sortedApps.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const allSelected = pagedApps.length > 0 && pagedApps.every((a) => selectedIds.has(a.id));

  const toggleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        pagedApps.forEach((a) => next.delete(a.id));
      } else {
        pagedApps.forEach((a) => next.add(a.id));
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
    if (!window.confirm(`Remove ${ids.length} application${ids.length === 1 ? "" : "s"} from the tracker? This can't be undone.`)) {
      return;
    }
    setError(null);
    setDeleting(true);
    try {
      await Promise.all(ids.map((id) => api.deleteApplication(id)));
      setSelectedIds(new Set());
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(false);
    }
  };

  const triggerUpload = (applicationId: number) => {
    setResumeMenuOpenId(null);
    fileInputs.current[applicationId]?.click();
  };

  const deleteResume = async (documentId: number) => {
    setResumeMenuOpenId(null);
    if (!window.confirm("Delete this resume? This can't be undone.")) return;
    setError(null);
    try {
      await api.deleteDocument(documentId);
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleUpload = async (applicationId: number, fileList: FileList | null) => {
    const file = fileList?.[0];
    if (!file) return;
    setError(null);
    setUploadingId(applicationId);
    try {
      await api.uploadResume(applicationId, file);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploadingId(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Applications</h1>
          <div className="page-subtitle">{sortedApps.length} tracked</div>
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
              {deleting ? "Removing…" : `Remove ${selectedIds.size} selected`}
            </button>
          </div>
        </div>
      )}

      <div className="filter-bar">
        <div className="filter-field">
          <label htmlFor="app-search">Search</label>
          <input
            id="app-search"
            type="text"
            placeholder="Company or role"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-field">
          <label htmlFor="status-filter">Status</label>
          <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-field">
          <label htmlFor="sort-dir">Last updated</label>
          <select
            id="sort-dir"
            value={sortDir}
            onChange={(e) => {
              setSortDir(e.target.value as "desc" | "asc");
              setPage(1);
            }}
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </select>
        </div>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Select all" />
              </th>
              <th>Company</th>
              <th>Role</th>
              <th>Portal</th>
              <th>Status</th>
              <th>Last update</th>
              <th>Resume used</th>
            </tr>
          </thead>
          <tbody>
            {pagedApps.map((a) => {
              const resume = latestResumeFor(docs, a.id);
              return (
                <tr key={a.id} className={selectedIds.has(a.id) ? "row-selected" : undefined}>
                  <td className="checkbox-col">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(a.id)}
                      onChange={() => toggleOne(a.id)}
                      aria-label={`Select ${a.role_title ?? "application"}`}
                    />
                  </td>
                  <td>{a.company ?? "-"}</td>
                  <td>{a.role_title ?? "-"}</td>
                  <td>{a.source_portal ?? "-"}</td>
                  <td>
                    <select
                      className="field-input text-xs py-1.5"
                      value={a.status}
                      onChange={(e) => changeStatus(a.id, e.target.value)}
                      aria-label={`Status for ${a.role_title ?? "application"}`}
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{new Date(a.last_status_change_at).toLocaleDateString()}</td>
                  <td>
                    <div className="flex items-center gap-1.5">
                    {resume ? (
                      <a
                        className="icon-btn"
                        href={api.documentPreviewUrl(resume.id)}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={`View resume v${resume.version_number}`}
                        title={`View resume v${resume.version_number}`}
                      >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
                          <path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5Z" />
                          <circle cx="8" cy="8" r="1.8" fill="currentColor" stroke="none" />
                        </svg>
                      </a>
                    ) : (
                      <span className="page-subtitle text-xs">None</span>
                    )}
                    <span className="icon-menu-wrapper">
                      <button
                        type="button"
                        className="icon-btn"
                        disabled={uploadingId === a.id}
                        aria-label={resume ? "Resume actions" : "Upload resume"}
                        onClick={() =>
                          setResumeMenuOpenId(resumeMenuOpenId === a.id ? null : a.id)
                        }
                      >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                          <circle cx="8" cy="3" r="1.4" />
                          <circle cx="8" cy="8" r="1.4" />
                          <circle cx="8" cy="13" r="1.4" />
                        </svg>
                      </button>
                      {resumeMenuOpenId === a.id && (
                        <div className="icon-menu">
                          <button
                            type="button"
                            className="icon-menu-item"
                            disabled={uploadingId === a.id}
                            onClick={() => triggerUpload(a.id)}
                          >
                            {uploadingId === a.id ? "Uploading…" : resume ? "Replace" : "Upload"}
                          </button>
                          {resume && (
                            <button
                              type="button"
                              className="icon-menu-item icon-menu-item-danger"
                              onClick={() => deleteResume(resume.id)}
                            >
                              Delete
                            </button>
                          )}
                        </div>
                      )}
                    </span>
                    <input
                      ref={(el) => {
                        fileInputs.current[a.id] = el;
                      }}
                      type="file"
                      accept="application/pdf"
                      hidden
                      onChange={(e) => handleUpload(a.id, e.target.files)}
                    />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {sortedApps.length === 0 && (
          <div className="empty-state">
            {apps.length === 0 ? "No applications tracked yet." : "No applications match your search."}
          </div>
        )}
        <Pagination
          page={page}
          pageCount={pageCount}
          totalItems={sortedApps.length}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      </div>
      <p className="footnote">
        "Upload" attaches a resume PDF you built some other way to this application as a new
        version -- it shows up here and in the Resume Library exactly like a generated one.
      </p>
    </div>
  );
}
