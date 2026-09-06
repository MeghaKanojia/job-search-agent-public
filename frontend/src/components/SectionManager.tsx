import { FormEvent, useEffect, useState } from "react";

export interface FieldConfig {
  key: string;
  label: string;
  type: "text" | "date" | "textarea" | "checkbox";
  required?: boolean;
  placeholder?: string;
  fullWidth?: boolean;
}

interface ResourceApi<T> {
  list: () => Promise<T[]>;
  create: (payload: Record<string, unknown>) => Promise<T>;
  update: (id: number, payload: Record<string, unknown>) => Promise<T>;
  remove: (id: number) => Promise<unknown>;
}

interface BaseItem {
  id: number;
  is_active: boolean;
}

interface SectionManagerProps<T extends BaseItem> {
  title: string;
  description?: string;
  fields: FieldConfig[];
  api: ResourceApi<T>;
  renderTitle: (item: T) => string;
  renderSubtitle?: (item: T) => string | null;
}

export function formatMonthYear(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function emptyForm(fields: FieldConfig[]): Record<string, unknown> {
  const form: Record<string, unknown> = {};
  for (const f of fields) form[f.key] = f.type === "checkbox" ? false : "";
  return form;
}

function toPayload(fields: FieldConfig[], form: Record<string, unknown>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const f of fields) {
    const value = form[f.key];
    payload[f.key] = value === "" ? null : value;
  }
  return payload;
}

function FieldInput({
  field,
  form,
  setForm,
}: {
  field: FieldConfig;
  form: Record<string, unknown>;
  setForm: (form: Record<string, unknown>) => void;
}) {
  const value = form[field.key];
  if (field.type === "checkbox") {
    return (
      <input
        type="checkbox"
        className="w-4 h-4 accent-blue-600 cursor-pointer"
        checked={Boolean(value)}
        onChange={(e) => setForm({ ...form, [field.key]: e.target.checked })}
      />
    );
  }
  if (field.type === "textarea") {
    return (
      <textarea
        className="field-input w-full"
        rows={3}
        value={String(value ?? "")}
        placeholder={field.placeholder}
        onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
      />
    );
  }
  return (
    <input
      className="field-input w-full"
      type={field.type}
      value={String(value ?? "")}
      placeholder={field.placeholder}
      required={field.required}
      onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
    />
  );
}

export default function SectionManager<T extends BaseItem>({
  title,
  description,
  fields,
  api,
  renderTitle,
  renderSubtitle,
}: SectionManagerProps<T>) {
  const [items, setItems] = useState<T[]>([]);
  const [form, setForm] = useState<Record<string, unknown>>(emptyForm(fields));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);

  const load = () => api.list().then(setItems).catch((e) => setError(String(e)));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title]);

  const handleAdd = async (e: FormEvent) => {
    e.preventDefault();
    await api.create(toPayload(fields, form));
    setForm(emptyForm(fields));
    load();
  };

  const startEdit = (item: T) => {
    setEditingId(item.id);
    const initial: Record<string, unknown> = {};
    for (const f of fields) initial[f.key] = (item as unknown as Record<string, unknown>)[f.key] ?? (f.type === "checkbox" ? false : "");
    setEditForm(initial);
  };

  const saveEdit = async (id: number) => {
    await api.update(id, toPayload(fields, editForm));
    setEditingId(null);
    load();
  };

  const toggleActive = async (item: T) => {
    await api.update(item.id, { is_active: !item.is_active });
    load();
  };

  const remove = async (id: number) => {
    await api.remove(id);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{title}</h1>
          <div className="page-subtitle">{items.length} entries</div>
        </div>
      </div>
      {description && <p className="intro-text">{description}</p>}
      {error && <div className="error-banner">{error}</div>}

      <form className="filter-bar" onSubmit={handleAdd}>
        {fields.map((f) => (
          <div className="filter-field" key={f.key} style={f.fullWidth ? { flex: 1, minWidth: 260 } : undefined}>
            <label>{f.label}</label>
            <FieldInput field={f} form={form} setForm={setForm} />
          </div>
        ))}
        <button className="btn" type="submit">
          Add
        </button>
      </form>

      {items.map((item) =>
        editingId === item.id ? (
          <div className="review-card" key={item.id}>
            {fields.map((f) => (
              <div key={f.key} className="mb-2.5">
                <label className="text-xs text-slate-500 block mb-1">{f.label}</label>
                <FieldInput field={f} form={editForm} setForm={setEditForm} />
              </div>
            ))}
            <div className="review-card-actions">
              <button className="btn btn-small" onClick={() => saveEdit(item.id)}>
                Save
              </button>
              <button className="btn btn-secondary btn-small" onClick={() => setEditingId(null)}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="review-card" key={item.id}>
            <div className="review-card-title">
              {renderTitle(item)}
              {renderSubtitle && renderSubtitle(item) && <span className="company"> - {renderSubtitle(item)}</span>}
            </div>
            {fields
              .filter((f) => f.type === "textarea")
              .map((f) => {
                const text = (item as unknown as Record<string, unknown>)[f.key];
                return text ? (
                  <p key={f.key} className="whitespace-pre-wrap text-sm text-slate-500 mt-2">
                    {String(text)}
                  </p>
                ) : null;
              })}
            <div className="review-card-actions">
              <span className={`badge ${item.is_active ? "badge-fresh" : "badge-neutral"}`}>
                {item.is_active ? "Active" : "Inactive"}
              </span>
              <button className="btn btn-secondary btn-small" onClick={() => startEdit(item)}>
                Edit
              </button>
              <button className="btn btn-secondary btn-small" onClick={() => toggleActive(item)}>
                {item.is_active ? "Deactivate" : "Activate"}
              </button>
              <button className="btn btn-danger btn-small" onClick={() => remove(item.id)}>
                Delete
              </button>
            </div>
          </div>
        )
      )}
      {items.length === 0 && <div className="empty-state">No entries yet.</div>}
    </div>
  );
}
