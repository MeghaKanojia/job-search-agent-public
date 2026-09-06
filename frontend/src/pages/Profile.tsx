import { FormEvent, useEffect, useState } from "react";
import {
  api,
  CertificationItem,
  EducationItem,
  ProjectItem,
  SkillProfileItem,
  SkillProfileItemInput,
  WorkExperienceItem,
} from "../api/client";
import SectionManager, { formatMonthYear } from "../components/SectionManager";

const TABS = ["Skills", "Education", "Experience", "Projects", "Certifications"] as const;
type Tab = (typeof TABS)[number];

const CATEGORY_OPTIONS = ["Skill", "Tool", "Language", "Certification"];

const EMPTY_SKILL_FORM: SkillProfileItemInput = {
  skill_name: "",
  category: "Skill",
  proficiency_level: "",
  years_experience: undefined,
  evidence_bullet: "",
};

function SkillsSection() {
  const [items, setItems] = useState<SkillProfileItem[]>([]);
  const [form, setForm] = useState<SkillProfileItemInput>(EMPTY_SKILL_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<SkillProfileItemInput>(EMPTY_SKILL_FORM);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.listSkills().then(setItems).catch((e) => setError(String(e)));

  useEffect(() => {
    load();
  }, []);

  const addItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.skill_name.trim()) return;
    await api.createSkill(form);
    setForm(EMPTY_SKILL_FORM);
    load();
  };

  const startEdit = (item: SkillProfileItem) => {
    setEditingId(item.id);
    setEditForm({
      skill_name: item.skill_name,
      category: item.category ?? "",
      proficiency_level: item.proficiency_level ?? "",
      years_experience: item.years_experience ?? undefined,
      evidence_bullet: item.evidence_bullet ?? "",
    });
  };

  const saveEdit = async (id: number) => {
    await api.updateSkill(id, editForm);
    setEditingId(null);
    load();
  };

  const toggleActive = async (item: SkillProfileItem) => {
    await api.updateSkill(item.id, { is_active: !item.is_active });
    load();
  };

  const remove = async (id: number) => {
    await api.deleteSkill(id);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Skills</h1>
          <div className="page-subtitle">{items.length} entries</div>
        </div>
      </div>
      <p className="intro-text">
        This is the only material CV tailoring and cover-letter drafting are allowed to draw
        from for skills. It never invents anything not listed here.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <form className="filter-bar" onSubmit={addItem}>
        <div className="filter-field">
          <label htmlFor="new-name">Name</label>
          <input
            id="new-name"
            value={form.skill_name}
            onChange={(e) => setForm({ ...form, skill_name: e.target.value })}
            placeholder="e.g. Apache Airflow"
            required
          />
        </div>
        <div className="filter-field">
          <label htmlFor="new-category">Category</label>
          <input
            id="new-category"
            list="category-options"
            value={form.category ?? ""}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          />
          <datalist id="category-options">
            {CATEGORY_OPTIONS.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </div>
        <div className="filter-field">
          <label htmlFor="new-years">Years</label>
          <input
            id="new-years"
            type="number"
            step={0.5}
            min={0}
            value={form.years_experience ?? ""}
            onChange={(e) => setForm({ ...form, years_experience: e.target.value ? Number(e.target.value) : undefined })}
          />
        </div>
        <div className="filter-field" style={{ flex: 1, minWidth: 240 }}>
          <label htmlFor="new-evidence">Evidence / description</label>
          <input
            id="new-evidence"
            value={form.evidence_bullet ?? ""}
            onChange={(e) => setForm({ ...form, evidence_bullet: e.target.value })}
            placeholder="What you actually did with it"
          />
        </div>
        <button className="btn" type="submit">
          Add
        </button>
      </form>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Years</th>
              <th>Evidence</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) =>
              editingId === item.id ? (
                <tr key={item.id}>
                  <td>
                    <input
                      className="field-input w-full"
                      value={editForm.skill_name}
                      onChange={(e) => setEditForm({ ...editForm, skill_name: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="field-input w-full"
                      value={editForm.category ?? ""}
                      onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="field-input w-full"
                      type="number"
                      step={0.5}
                      min={0}
                      value={editForm.years_experience ?? ""}
                      onChange={(e) =>
                        setEditForm({
                          ...editForm,
                          years_experience: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                    />
                  </td>
                  <td>
                    <input
                      className="field-input w-full"
                      value={editForm.evidence_bullet ?? ""}
                      onChange={(e) => setEditForm({ ...editForm, evidence_bullet: e.target.value })}
                    />
                  </td>
                  <td>{item.is_active ? "Active" : "Inactive"}</td>
                  <td>
                    <button className="btn btn-small" onClick={() => saveEdit(item.id)}>
                      Save
                    </button>{" "}
                    <button className="btn btn-secondary btn-small" onClick={() => setEditingId(null)}>
                      Cancel
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={item.id}>
                  <td>{item.skill_name}</td>
                  <td>{item.category ?? "-"}</td>
                  <td>{item.years_experience ?? "-"}</td>
                  <td>{item.evidence_bullet ?? "-"}</td>
                  <td>
                    <span className={`badge ${item.is_active ? "badge-fresh" : "badge-neutral"}`}>
                      {item.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td>
                    <button className="btn btn-secondary btn-small" onClick={() => startEdit(item)}>
                      Edit
                    </button>{" "}
                    <button className="btn btn-secondary btn-small" onClick={() => toggleActive(item)}>
                      {item.is_active ? "Deactivate" : "Activate"}
                    </button>{" "}
                    <button className="btn btn-danger btn-small" onClick={() => remove(item.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
        {items.length === 0 && <div className="empty-state">No skills added yet.</div>}
      </div>
    </div>
  );
}

function dateRange(start: string | null, end: string | null, current?: boolean): string {
  const s = formatMonthYear(start);
  const e = current ? "Present" : formatMonthYear(end);
  if (!s && !e) return "";
  return `${s || "?"} - ${e || "?"}`;
}

export default function Profile() {
  const [tab, setTab] = useState<Tab>("Skills");

  return (
    <div>
      <div className="flex gap-2 mb-6 border-b border-slate-100">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`bg-transparent border-0 rounded-none px-3.5 py-2.5 cursor-pointer border-b-2 ${
              tab === t ? "border-blue-600 text-blue-600 font-bold" : "border-transparent text-slate-500 font-medium"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Skills" && <SkillsSection />}

      {tab === "Education" && (
        <SectionManager<EducationItem>
          title="Education"
          description="Your academic history, most relevant/recent first."
          api={api.education}
          fields={[
            { key: "institution", label: "Institution", type: "text", required: true },
            { key: "degree", label: "Degree", type: "text", required: true },
            { key: "field_of_study", label: "Field of study", type: "text" },
            { key: "location", label: "Location", type: "text" },
            { key: "start_date", label: "Start date", type: "date" },
            { key: "end_date", label: "End date", type: "date" },
            { key: "grade", label: "Grade / result", type: "text" },
            { key: "description", label: "Description", type: "textarea", fullWidth: true },
          ]}
          renderTitle={(item) => `${item.degree}${item.field_of_study ? ` in ${item.field_of_study}` : ""}`}
          renderSubtitle={(item) =>
            [item.institution, item.location, dateRange(item.start_date, item.end_date)].filter(Boolean).join(", ")
          }
        />
      )}

      {tab === "Experience" && (
        <SectionManager<WorkExperienceItem>
          title="Work Experience"
          description="Your real work history: this is what tailored resumes and cover letters draw their experience from."
          api={api.experience}
          fields={[
            { key: "role_title", label: "Role title", type: "text", required: true },
            { key: "company", label: "Company", type: "text", required: true },
            { key: "location", label: "Location", type: "text" },
            { key: "start_date", label: "Start date", type: "date" },
            { key: "end_date", label: "End date", type: "date" },
            { key: "is_current", label: "Current role", type: "checkbox" },
            { key: "description", label: "Description / achievements", type: "textarea", fullWidth: true },
          ]}
          renderTitle={(item) => item.role_title}
          renderSubtitle={(item) =>
            [item.company, item.location, dateRange(item.start_date, item.end_date, item.is_current)]
              .filter(Boolean)
              .join(", ")
          }
        />
      )}

      {tab === "Projects" && (
        <SectionManager<ProjectItem>
          title="Projects"
          description="Personal and academic projects with real links, grounding both resume tailoring and cover letters."
          api={api.projects}
          fields={[
            { key: "title", label: "Title", type: "text", required: true },
            { key: "tech_stack", label: "Tech stack", type: "text", placeholder: "Python, PySpark, ..." },
            { key: "project_url", label: "Project URL", type: "text", placeholder: "https://github.com/..." },
            { key: "start_date", label: "Start date", type: "date" },
            { key: "end_date", label: "End date", type: "date" },
            { key: "description", label: "Description", type: "textarea", fullWidth: true },
          ]}
          renderTitle={(item) => item.title}
          renderSubtitle={(item) => item.tech_stack}
        />
      )}

      {tab === "Certifications" && (
        <SectionManager<CertificationItem>
          title="Certifications & Awards"
          description="Certifications, courses, and notable awards."
          api={api.certifications}
          fields={[
            { key: "name", label: "Name", type: "text", required: true },
            { key: "issuing_organization", label: "Issuing organization", type: "text" },
            { key: "issue_date", label: "Issue date", type: "date" },
            { key: "credential_url", label: "Credential URL", type: "text" },
            { key: "description", label: "Description", type: "textarea", fullWidth: true },
          ]}
          renderTitle={(item) => item.name}
          renderSubtitle={(item) =>
            [item.issuing_organization, formatMonthYear(item.issue_date)].filter(Boolean).join(", ")
          }
        />
      )}
    </div>
  );
}
