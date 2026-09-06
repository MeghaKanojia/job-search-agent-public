import { useEffect, useState } from "react";
import { api, KeywordFilterItem, LLMStatus, PipelineSourceItem } from "../api/client";
import { useToast } from "../components/Toast";

const ALL_PROVIDERS = ["groq", "gemini"];

export default function Settings() {
  const [sources, setSources] = useState<PipelineSourceItem[]>([]);
  const [keywords, setKeywords] = useState<KeywordFilterItem[]>([]);
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [newKeyword, setNewKeyword] = useState("");
  const [newCategory, setNewCategory] = useState<"role" | "skill">("role");
  const { showToast } = useToast();

  const load = () => {
    api.listPipelineSources().then(setSources);
    api.listKeywords().then(setKeywords);
    api.llmStatus().then(setLlmStatus);
  };

  useEffect(() => {
    load();
  }, []);

  const toggleSource = async (source: PipelineSourceItem) => {
    try {
      const updated = await api.setPipelineSource(source.key, !source.enabled);
      setSources((prev) => prev.map((s) => (s.key === source.key ? updated : s)));
      showToast(`${updated.label} ${updated.enabled ? "enabled" : "disabled"}.`, "success");
    } catch (e) {
      showToast(`Failed to update ${source.label}: ${e}`, "error");
    }
  };

  const addKeyword = async () => {
    const keyword = newKeyword.trim();
    if (!keyword) return;
    try {
      await api.createKeyword({ keyword, category: newCategory });
      setNewKeyword("");
      load();
    } catch (e) {
      showToast(`Failed to add keyword: ${e}`, "error");
    }
  };

  const toggleKeywordActive = async (kw: KeywordFilterItem) => {
    await api.updateKeyword(kw.id, { is_active: !kw.is_active });
    load();
  };

  const removeKeyword = async (id: number) => {
    await api.deleteKeyword(id);
    load();
  };

  const roleKeywords = keywords.filter((k) => k.category === "role");
  const skillKeywords = keywords.filter((k) => k.category === "skill");

  return (
    <div>
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      <div className="card settings-section">
        <h2 className="settings-section-title">Pipeline sources</h2>
        <p className="intro-text">
          Turn a source off to stop the ingestion pipeline from calling it at all on its next
          scheduled run -- an instant kill switch, not just a filter on what you see.
        </p>
        <div className="source-toggle-list">
          {sources.map((s) => (
            <label key={s.key} className="source-toggle-row">
              <input type="checkbox" checked={s.enabled} onChange={() => toggleSource(s)} />
              <span>{s.label}</span>
              <span className={`badge ${s.enabled ? "badge-fresh" : "badge-neutral"}`}>
                {s.enabled ? "Enabled" : "Disabled"}
              </span>
            </label>
          ))}
          {sources.length === 0 && <div className="empty-state">No pipeline sources configured.</div>}
        </div>
      </div>

      <div className="card settings-section">
        <h2 className="settings-section-title">LLM provider status</h2>
        <p className="intro-text">
          Cover-letter drafting and resume tailoring use Groq first, falling back to Gemini --
          both free-tier. Everything degrades gracefully to static/rule-based logic if neither is
          configured.
        </p>
        <div className="source-toggle-list">
          {ALL_PROVIDERS.map((p) => {
            const configured = llmStatus?.configured_providers.includes(p) ?? false;
            return (
              <div key={p} className="source-toggle-row">
                <span style={{ textTransform: "capitalize" }}>{p}</span>
                <span className={`badge ${configured ? "badge-fresh" : "badge-neutral"}`}>
                  {configured ? "Configured" : "Not configured"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card settings-section">
        <h2 className="settings-section-title">Keyword filters</h2>
        <p className="intro-text">
          Controls what the pipeline lands at all. A posting must match a role keyword (or a role
          noun + domain qualifier, e.g. "Analytics Consultant") to be ingested in the first place.
        </p>

        <div className="filter-bar">
          <div className="filter-field">
            <label htmlFor="new-keyword">New keyword</label>
            <input
              id="new-keyword"
              type="text"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder="e.g. Data Engineer"
            />
          </div>
          <div className="filter-field">
            <label htmlFor="new-category">Category</label>
            <select
              id="new-category"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value as "role" | "skill")}
            >
              <option value="role">Role</option>
              <option value="skill">Skill</option>
            </select>
          </div>
          <button className="btn" onClick={addKeyword}>
            Add
          </button>
        </div>

        <div className="keyword-columns">
          <div>
            <h3 className="keyword-column-title">Role keywords ({roleKeywords.length})</h3>
            <div className="keyword-chip-list">
              {roleKeywords.map((k) => (
                <span key={k.id} className={`keyword-chip${k.is_active ? "" : " keyword-chip-inactive"}`}>
                  <span onClick={() => toggleKeywordActive(k)}>{k.keyword}</span>
                  <button onClick={() => removeKeyword(k.id)} aria-label={`Remove ${k.keyword}`}>
                    &times;
                  </button>
                </span>
              ))}
              {roleKeywords.length === 0 && <span className="page-subtitle">None yet.</span>}
            </div>
          </div>
          <div>
            <h3 className="keyword-column-title">Skill keywords ({skillKeywords.length})</h3>
            <div className="keyword-chip-list">
              {skillKeywords.map((k) => (
                <span key={k.id} className={`keyword-chip${k.is_active ? "" : " keyword-chip-inactive"}`}>
                  <span onClick={() => toggleKeywordActive(k)}>{k.keyword}</span>
                  <button onClick={() => removeKeyword(k.id)} aria-label={`Remove ${k.keyword}`}>
                    &times;
                  </button>
                </span>
              ))}
              {skillKeywords.length === 0 && <span className="page-subtitle">None yet.</span>}
            </div>
          </div>
        </div>
        <p className="footnote">Click a keyword to toggle it active/inactive; click &times; to delete it.</p>
      </div>
    </div>
  );
}
