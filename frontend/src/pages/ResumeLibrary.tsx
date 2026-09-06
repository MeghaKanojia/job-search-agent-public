import { useEffect, useState } from "react";
import { api, DocumentItem } from "../api/client";
import Pagination from "../components/Pagination";

const CLEANUP_OPTIONS = [
  { value: "30", label: "Older than 30 days" },
  { value: "90", label: "Older than 90 days" },
  { value: "180", label: "Older than 180 days" },
];

const PAGE_SIZE = 20;

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function ResumeLibrary() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [cleanupDays, setCleanupDays] = useState("90");
  const [status, setStatus] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [page, setPage] = useState(1);

  const load = () => api.listDocuments().then(setDocs);

  useEffect(() => {
    load();
  }, []);

  const cleanupOld = async () => {
    const result = await api.deleteOldDocuments(Number(cleanupDays));
    setStatus(`Deleted ${result.deleted_count} document${result.deleted_count === 1 ? "" : "s"}.`);
    setSelectedIds(new Set());
    load();
  };

  const pageCount = Math.max(1, Math.ceil(docs.length / PAGE_SIZE));
  const pagedDocs = docs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const allSelected = pagedDocs.length > 0 && pagedDocs.every((d) => selectedIds.has(d.id));

  const toggleAll = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        pagedDocs.forEach((d) => next.delete(d.id));
      } else {
        pagedDocs.forEach((d) => next.add(d.id));
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
    if (!window.confirm(`Delete ${ids.length} document${ids.length === 1 ? "" : "s"}? This can't be undone.`)) {
      return;
    }
    setDeleting(true);
    try {
      await Promise.all(ids.map((id) => api.deleteDocument(id)));
      setSelectedIds(new Set());
      setStatus(null);
      load();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Resume Library</h1>
          <div className="page-subtitle">{docs.length} document{docs.length === 1 ? "" : "s"}</div>
        </div>
      </div>
      <p className="intro-text">
        Every tailored resume and cover letter ever generated, stored in Postgres, not on this
        machine. Nothing here uses your own disk space.
      </p>

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
          <label htmlFor="cleanup-days">Clean up</label>
          <select id="cleanup-days" value={cleanupDays} onChange={(e) => setCleanupDays(e.target.value)}>
            {CLEANUP_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <button className="btn btn-danger" onClick={cleanupOld}>
          Delete old documents
        </button>
        {status && <span className="page-subtitle">{status}</span>}
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
              <th>Type</th>
              <th>Version</th>
              <th>Generated</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {pagedDocs.map((d) => (
              <tr key={d.id} className={selectedIds.has(d.id) ? "row-selected" : undefined}>
                <td className="checkbox-col">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(d.id)}
                    onChange={() => toggleOne(d.id)}
                    aria-label={`Select document ${d.id}`}
                  />
                </td>
                <td>{d.company ?? "-"}</td>
                <td>{d.role_title ?? "-"}</td>
                <td>{d.doc_type === "resume" ? "Resume" : "Cover letter"}</td>
                <td>v{d.version_number}</td>
                <td>{formatDate(d.generated_at)}</td>
                <td>
                  <a
                    className="btn btn-secondary btn-small"
                    href={api.documentPreviewUrl(d.id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Preview
                  </a>{" "}
                  <a className="btn btn-secondary btn-small" href={api.documentDownloadUrl(d.id)}>
                    Download
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {docs.length === 0 && (
          <div className="empty-state">
            No documents yet. Generate one from the Review Queue.
          </div>
        )}
        <Pagination
          page={page}
          pageCount={pageCount}
          totalItems={docs.length}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      </div>
    </div>
  );
}
