import { useEffect, useMemo, useRef, useState } from "react";
import { api, Application, DocumentItem } from "../api/client";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 15;

const STATUSES = [
  "new",
  "staged_for_review",
  "approved_ready_to_submit",
  "applied",
  "viewed",
  "interview",
  "offer",
  "rejected",
  "withdrawn",
];

const POSITIVE_STATUSES = new Set(["interview", "offer"]);
const NEGATIVE_STATUSES = new Set(["rejected", "withdrawn"]);

function statusBadgeClass(status: string): string {
  if (POSITIVE_STATUSES.has(status)) return "badge badge-fresh";
  if (NEGATIVE_STATUSES.has(status)) return "badge badge-negative";
  return "badge badge-neutral";
}

function latestResumeFor(docs: DocumentItem[], applicationId: number): DocumentItem | null {
  const resumes = docs.filter((d) => d.application_id === applicationId && d.doc_type === "resume");
  if (resumes.length === 0) return null;
  return resumes.reduce((latest, d) => (d.version_number > latest.version_number ? d : latest));
}

export default function ApplicationsTracker() {
  const [apps, setApps] = useState<Application[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const fileInputs = useRef<Record<number, HTMLInputElement | null>>({});

  const load = () => {
    api.listApplications(statusFilter || undefined).then(setApps);
    api.listDocuments().then(setDocs);
  };

  useEffect(() => {
    load();
    setSelectedIds(new Set());
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const sortedApps = useMemo(() => {
    const copy = [...apps];
    copy.sort((a, b) => {
      const diff = new Date(a.last_status_change_at).getTime() - new Date(b.last_status_change_at).getTime();
      return sortDir === "asc" ? diff : -diff;
    });
    return copy;
  }, [apps, sortDir]);

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
    fileInputs.current[applicationId]?.click();
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
          <div className="page-subtitle">{apps.length} tracked</div>
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
                    <span className={statusBadgeClass(a.status)}>{a.status}</span>
                  </td>
                  <td>{new Date(a.last_status_change_at).toLocaleDateString()}</td>
                  <td>
                    {resume ? (
                      <a
                        className="btn btn-secondary btn-small"
                        href={api.documentPreviewUrl(resume.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Resume v{resume.version_number}
                      </a>
                    ) : (
                      <span className="page-subtitle">None</span>
                    )}{" "}
                    <button
                      className="btn btn-secondary btn-small"
                      disabled={uploadingId === a.id}
                      onClick={() => triggerUpload(a.id)}
                    >
                      {uploadingId === a.id ? "Uploading…" : resume ? "Replace" : "Upload"}
                    </button>
                    <input
                      ref={(el) => {
                        fileInputs.current[a.id] = el;
                      }}
                      type="file"
                      accept="application/pdf"
                      hidden
                      onChange={(e) => handleUpload(a.id, e.target.files)}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {apps.length === 0 && <div className="empty-state">No applications tracked yet.</div>}
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
