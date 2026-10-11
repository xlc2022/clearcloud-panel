import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { IntegrationForm, TestResultView } from "../components/IntegrationForm";
import type { Integration, IntegrationPayload, IntegrationType, TestResult } from "../types";

type Mode = { kind: "list" } | { kind: "pick" } | { kind: "add"; type: IntegrationType } | { kind: "edit"; item: Integration; type: IntegrationType };

export function Integrations() {
  const [types, setTypes] = useState<IntegrationType[] | null>(null);
  const [items, setItems] = useState<Integration[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>({ kind: "list" });
  const [fresh, setFresh] = useState<Record<number, TestResult & { at?: string }>>({});
  const [testing, setTesting] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const [t, l] = await Promise.all([api.types(), api.list()]);
      setTypes(t);
      setItems(l);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load integrations.");
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);

  const typeOf = (kind: string) => types?.find((t) => t.kind === kind);

  const save = async (payload: IntegrationPayload) => {
    if (mode.kind === "add") await api.create(mode.type.kind, payload);
    else if (mode.kind === "edit") await api.update(mode.item.id, payload);
    setMode({ kind: "list" });
    await load();
  };

  const runTest = async (it: Integration) => {
    setTesting(it.id);
    try {
      const r = await api.testStored(it.id);
      setFresh((f) => ({ ...f, [it.id]: { ...r, at: new Date().toISOString() } }));
      await load();
    } catch (e) {
      setFresh((f) => ({ ...f, [it.id]: { ok: false, message: e instanceof Error ? e.message : "Test failed.", details: [], at: new Date().toISOString() } }));
    } finally {
      setTesting(null);
    }
  };

  const remove = async (it: Integration) => {
    if (!window.confirm(`Delete ${it.name}? This cannot be undone.`)) return;
    try {
      await api.remove(it.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  };

  if (mode.kind === "add" || mode.kind === "edit") {
    const t = mode.type;
    return (
      <>
        <div className="page-head">
          <h1>{mode.kind === "add" ? `Add ${t.label}` : `Edit ${mode.item.name}`}</h1>
        </div>
        <div className="card form-card">
          {t.description && <p className="muted">{t.description}</p>}
          <IntegrationForm
            type={t}
            integration={mode.kind === "edit" ? mode.item : undefined}
            onSave={save}
            onCancel={() => setMode({ kind: "list" })}
          />
        </div>
      </>
    );
  }

  const available = (types ?? []).filter((t) => t.multiple || !(items ?? []).some((i) => i.kind === t.kind));

  return (
    <>
      <div className="page-head">
        <h1>Integrations</h1>
        <div className="page-actions">
          <button type="button" className="btn btn-primary" disabled={!types} onClick={() => setMode({ kind: "pick" })}>
            Add Integration
          </button>
        </div>
      </div>
      {error && (
        <p role="alert" className="msg-error">
          {error}
        </p>
      )}
      {mode.kind === "pick" && (
        <section className="card" aria-label="Choose an integration type">
          <h2 className="card-title">Choose a Type</h2>
          {available.length === 0 ? (
            <p className="muted">Every available integration type has already been added.</p>
          ) : (
            <ul className="type-list">
              {available.map((t) => (
                <li key={t.kind}>
                  <button type="button" className="type-btn" onClick={() => setMode({ kind: "add", type: t })}>
                    <strong>{t.label}</strong>
                    <span className="muted">{t.description}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="form-actions">
            <button type="button" className="btn" onClick={() => setMode({ kind: "list" })}>
              Cancel
            </button>
          </div>
        </section>
      )}
      {items === null && !error && <p className="muted">Loading...</p>}
      {items?.length === 0 && mode.kind !== "pick" && (
        <div className="card empty">
          <p>No integrations yet. Add Home Assistant first, then Grafana.</p>
        </div>
      )}
      <div className="int-list">
        {items?.map((it) => {
          const t = typeOf(it.kind);
          const last = fresh[it.id] ?? it.last_test;
          return (
            <article key={it.id} className="card int-card">
              <header className="int-head">
                <div>
                  <h2 className="card-title">{it.name}</h2>
                  <span className="muted">{t?.label ?? it.kind}</span>
                </div>
                <span className={`pill ${it.enabled ? "pill-ok" : ""}`}>{it.enabled ? "Enabled" : "Disabled"}</span>
              </header>
              {last ? <TestResultView result={last} /> : <p className="muted">Not tested yet.</p>}
              <div className="form-actions">
                <button type="button" className="btn" disabled={testing === it.id} onClick={() => runTest(it)}>
                  {testing === it.id ? "Testing..." : "Test"}
                </button>
                <button type="button" className="btn" disabled={!t} onClick={() => t && setMode({ kind: "edit", item: it, type: t })}>
                  Edit
                </button>
                <button type="button" className="btn btn-danger" onClick={() => remove(it)}>
                  Delete
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
