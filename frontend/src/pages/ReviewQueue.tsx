import { useEffect, useState } from "react";
import { api, Application, DocumentItem } from "../api/client";
import { useToast } from "../components/Toast";

function docLabel(doc: DocumentItem): string {
  const kind = doc.doc_type === "resume" ? "Resume" : "Cover letter";
  return `${kind} v${doc.version_number}`;
}

type GeneratingTarget = { id: number; kind: "resume" | "cover_letter" };

export default function ReviewQueue() {
  const [apps, setApps] = useState<Application[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [generating, setGenerating] = useState<GeneratingTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Optional per-application tweak request, threaded into the LLM prompt for
  // the next "Generate resume" / "Generate cover letter" click on that card.
  const [instructions, setInstructions] = useState<Record<number, string>>({});
  // The one cover letter currently open for direct manual editing, if any.
  const [editingDocId, setEditingDocId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  const load = () => {
    api.listApplications("staged_for_review").then(setApps);
    api.listDocuments().then(setDocs);
  };

  useEffect(() => {
    load();
  }, []);

  const approve = async (id: number) => {
    await api.updateApplicationStatus(id, "approved_ready_to_submit");
    load();
  };

  const reject = async (id: number) => {
    await api.updateApplicationStatus(id, "withdrawn", "Rejected during review");
    load();
  };

  const generateResume = async (id: number) => {
    setError(null);
    setGenerating({ id, kind: "resume" });
    try {
      const result = await api.generateResume(id, instructions[id]);
      showGenerationResult("Resume", result.warnings);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setGenerating(null);
    }
  };

  const generateCoverLetter = async (id: number) => {
    setError(null);
    setGenerating({ id, kind: "cover_letter" });
    try {
      const result = await api.generateCoverLetter(id, instructions[id]);
      showGenerationResult("Cover letter", result.warnings);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setGenerating(null);
    }
  };

  const showGenerationResult = (label: string, warnings: string[] | undefined) => {
    if (warnings && warnings.length > 0) {
      showToast(`${label} generated, but: ${warnings.join(" ")}`, "info");
    } else {
      showToast(`${label} generated and fully AI-tailored.`, "success");
    }
  };

  const removeDoc = async (id: number) => {
    await api.deleteDocument(id);
    load();
  };

  const startEdit = (doc: DocumentItem) => {
    setEditingDocId(doc.id);
    setEditText(doc.content_text ?? "");
  };

  const cancelEdit = () => {
    setEditingDocId(null);
    setEditText("");
  };

  const saveEdit = async (id: number) => {
    setError(null);
    setSaving(true);
    try {
      await api.updateDocumentContent(id, editText);
      cancelEdit();
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Review Queue</h1>
          <div className="page-subtitle">{apps.length} staged for your review</div>
        </div>
      </div>
      <p className="intro-text">
        Every application here is staged, not submitted. Generate a tailored resume and cover
        letter, review them, then approve. Nothing goes to an employer until you submit it
        yourself on the company's own site.
      </p>
      {error && <div className="error-banner">{error}</div>}
      {apps.map((a) => {
        const appDocs = docs.filter((d) => d.application_id === a.id);
        return (
          <div key={a.id} className="review-card">
            <div className="review-card-title">
              {a.role_title ?? "Untitled role"} <span className="company">- {a.company ?? "Unknown company"}</span>
            </div>

            {appDocs.length > 0 && (
              <div className="doc-list">
                {appDocs.map((d) => (
                  <div key={d.id} className="doc-row-wrapper">
                    <div className="doc-row">
                      <span>{docLabel(d)}</span>
                      <a
                        className="btn btn-secondary btn-small"
                        href={api.documentPreviewUrl(d.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Preview
                      </a>
                      <a className="btn btn-secondary btn-small" href={api.documentDownloadUrl(d.id)}>
                        Download
                      </a>
                      {d.doc_type === "cover_letter" && editingDocId !== d.id && (
                        <button className="btn btn-secondary btn-small" onClick={() => startEdit(d)}>
                          Edit
                        </button>
                      )}
                      <button className="btn btn-danger btn-small" onClick={() => removeDoc(d.id)}>
                        Delete
                      </button>
                    </div>
                    {editingDocId === d.id && (
                      <div className="doc-edit-panel">
                        <textarea
                          className="doc-edit-textarea"
                          rows={8}
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                        />
                        <div className="review-card-actions">
                          <button className="btn btn-small" disabled={saving} onClick={() => saveEdit(d.id)}>
                            {saving ? "Saving…" : "Save edit"}
                          </button>
                          <button className="btn btn-secondary btn-small" disabled={saving} onClick={cancelEdit}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <textarea
              className="instructions-textarea"
              placeholder="Optional: tell the LLM what to change before generating (e.g. 'put SQL higher', 'make the cover letter punchier')"
              rows={2}
              value={instructions[a.id] ?? ""}
              onChange={(e) => setInstructions({ ...instructions, [a.id]: e.target.value })}
            />

            <div className="review-card-actions">
              <button className="btn" onClick={() => approve(a.id)}>
                Approve
              </button>
              <button className="btn btn-danger" onClick={() => reject(a.id)}>
                Reject
              </button>
              <button
                className="btn btn-secondary"
                disabled={generating?.id === a.id}
                onClick={() => generateResume(a.id)}
              >
                {generating?.id === a.id && generating.kind === "resume" ? "Generating…" : "Generate resume"}
              </button>
              <button
                className="btn btn-secondary"
                disabled={generating?.id === a.id}
                onClick={() => generateCoverLetter(a.id)}
              >
                {generating?.id === a.id && generating.kind === "cover_letter"
                  ? "Generating…"
                  : "Generate cover letter"}
              </button>
            </div>
          </div>
        );
      })}
      {apps.length === 0 && <div className="empty-state">Nothing staged for review right now.</div>}
    </div>
  );
}
