import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { FieldSpec, Integration, IntegrationPayload, IntegrationType, TestResult } from "../types";

export function initialValue(f: FieldSpec, existing?: unknown): string | boolean {
  const v = existing !== undefined && existing !== null ? existing : f.default;
  if (f.type === "bool") return Boolean(v);
  if (v === undefined || v === null) return "";
  return String(v);
}

export function FieldInput({
  field,
  value,
  secretSet,
  onChange,
}: {
  field: FieldSpec;
  value: string | boolean;
  secretSet?: boolean;
  onChange: (v: string | boolean) => void;
}) {
  const id = `f-${field.key}`;
  const helpId = field.help ? `${id}-help` : undefined;
  let control;
  switch (field.type) {
    case "bool":
      control = (
        <label className="check" htmlFor={id}>
          <input id={id} type="checkbox" checked={Boolean(value)} aria-describedby={helpId} onChange={(e) => onChange(e.target.checked)} />
          <span>{field.label}</span>
        </label>
      );
      break;
    case "select":
      control = (
        <>
          <label htmlFor={id}>{field.label}</label>
          <select id={id} value={String(value)} required={field.required} aria-describedby={helpId} onChange={(e) => onChange(e.target.value)}>
            {!field.required && <option value="">None</option>}
            {(field.options ?? []).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </>
      );
      break;
    default: {
      const secret = field.type === "secret";
      const htmlType = secret ? "password" : field.type === "url" ? "url" : field.type === "number" ? "number" : "text";
      control = (
        <>
          <label htmlFor={id}>
            {field.label}
            {field.required && <span aria-hidden="true"> *</span>}
          </label>
          <input
            id={id}
            type={htmlType}
            step={field.type === "number" ? "any" : undefined}
            value={String(value)}
            required={field.required && !(secret && secretSet)}
            placeholder={secret && secretSet ? "Saved, leave blank to keep" : (field.placeholder ?? undefined)}
            autoComplete={secret ? "new-password" : "off"}
            aria-describedby={helpId}
            onChange={(e) => onChange(e.target.value)}
          />
        </>
      );
    }
  }
  return (
    <div className="field">
      {control}
      {field.help && (
        <p id={helpId} className="help">
          {field.help}
        </p>
      )}
    </div>
  );
}

export function TestResultView({ result }: { result: TestResult & { at?: string } }) {
  return (
    <div className={`test-result ${result.ok ? "ok" : "fail"}`} role="status">
      <strong>{result.ok ? "Test passed" : "Test failed"}</strong>
      {result.at && <span className="muted"> at {new Date(result.at).toLocaleString()}</span>}
      <p>{result.message}</p>
      {result.details?.length > 0 && (
        <dl className="details">
          {result.details.map((d, i) => (
            <div key={i}>
              <dt>{d.label}</dt>
              <dd>{d.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

interface Props {
  type: IntegrationType;
  integration?: Integration;
  saveLabel?: string;
  cancelLabel?: string;
  onSave: (payload: IntegrationPayload) => Promise<void>;
  onCancel: () => void;
}

export function IntegrationForm({ type, integration, saveLabel = "Save", cancelLabel = "Cancel", onSave, onCancel }: Props) {
  const [name, setName] = useState(integration?.name ?? type.label);
  const [enabled, setEnabled] = useState(integration?.enabled ?? true);
  const [values, setValues] = useState<Record<string, string | boolean>>(() =>
    Object.fromEntries(type.fields.map((f) => [f.key, initialValue(f, integration?.config[f.key])])),
  );
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"test" | "save" | null>(null);

  const build = (): IntegrationPayload => {
    const config: Record<string, unknown> = {};
    const secrets: Record<string, string> = {};
    for (const f of type.fields) {
      const v = values[f.key];
      if (f.type === "secret") {
        if (typeof v === "string" && v !== "") secrets[f.key] = v;
      } else if (f.type === "bool") {
        config[f.key] = Boolean(v);
      } else if (f.type === "number") {
        config[f.key] = v === "" ? null : Number(v);
      } else {
        config[f.key] = v;
      }
    }
    return { name, enabled, config, secrets };
  };

  const test = async () => {
    setBusy("test");
    setResult(null);
    setError(null);
    try {
      const p = build();
      setResult(await api.testDraft(type.kind, p.config, p.secrets, integration?.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Test failed.");
    } finally {
      setBusy(null);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy("save");
    setError(null);
    try {
      await onSave(build());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <form className="form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="int-name">Name</label>
        <input id="int-name" value={name} required onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="field">
        <label className="check" htmlFor="int-enabled">
          <input id="int-enabled" type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          <span>Enabled</span>
        </label>
      </div>
      {type.fields.map((f) => (
        <FieldInput
          key={f.key}
          field={f}
          value={values[f.key]}
          secretSet={integration?.secrets_set?.[f.key]}
          onChange={(v) => setValues((s) => ({ ...s, [f.key]: v }))}
        />
      ))}
      {result && <TestResultView result={result} />}
      {error && (
        <p role="alert" className="msg-error">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button type="button" className="btn" onClick={test} disabled={busy !== null}>
          {busy === "test" ? "Testing..." : "Test"}
        </button>
        <span className="spacer" />
        <button type="button" className="btn" onClick={onCancel} disabled={busy !== null}>
          {cancelLabel}
        </button>
        <button type="submit" className="btn btn-primary" disabled={busy !== null}>
          {busy === "save" ? "Saving..." : saveLabel}
        </button>
      </div>
    </form>
  );
}
