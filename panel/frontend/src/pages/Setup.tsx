import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { CloudIcon } from "../components/Sidebar";
import { IntegrationForm } from "../components/IntegrationForm";
import { useSession } from "../session";
import type { Integration, IntegrationPayload, IntegrationType } from "../types";
import { LoginForm } from "./Login";

const STEPS = ["Admin Password", "Home Assistant", "Grafana", "Done"];

function AdminStep({ onDone }: { onDone: () => void }) {
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (pw.length < 10) return setError("Use at least 10 characters.");
    if (pw !== pw2) return setError("The passwords do not match.");
    setBusy(true);
    try {
      await api.createAdmin(pw);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the admin password.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="form" onSubmit={submit}>
      <p className="muted">Choose the password for the admin account. You will use it to sign in to this panel.</p>
      <div className="field">
        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" autoComplete="new-password" minLength={10} required value={pw} onChange={(e) => setPw(e.target.value)} />
        <p className="help">At least 10 characters.</p>
      </div>
      <div className="field">
        <label htmlFor="pw2">Confirm Password</label>
        <input id="pw2" type="password" autoComplete="new-password" required value={pw2} onChange={(e) => setPw2(e.target.value)} />
      </div>
      {error && <p role="alert" className="msg-error">{error}</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Saving..." : "Continue"}
      </button>
    </form>
  );
}

function IntegrationStep({ kind, types, existing, onDone }: { kind: string; types: IntegrationType[]; existing?: Integration; onDone: () => void }) {
  const type = types.find((t) => t.kind === kind);
  if (!type) {
    return (
      <div>
        <p className="msg-error" role="alert">The backend does not offer an integration type called {kind}.</p>
        <button type="button" className="btn" onClick={onDone}>Skip for now</button>
      </div>
    );
  }
  const save = async (p: IntegrationPayload) => {
    if (existing) await api.update(existing.id, p);
    else await api.create(kind, p);
    onDone();
  };
  return (
    <>
      {type.description && <p className="muted">{type.description}</p>}
      <IntegrationForm type={type} integration={existing} saveLabel="Save and Continue" cancelLabel="Skip for now" onSave={save} onCancel={onDone} />
    </>
  );
}

export function Setup() {
  const { state, refresh } = useSession();
  const navigate = useNavigate();
  const [step, setStep] = useState<number | null>(null);
  const [types, setTypes] = useState<IntegrationType[]>([]);
  const [items, setItems] = useState<Integration[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const signedIn = !!state?.authenticated;
  const adminReady = !!state?.admin_created;

  // Resume: with an admin and a session, start at the first integration step.
  useEffect(() => {
    if (step === null && state && adminReady && signedIn) setStep(1);
  }, [step, state, adminReady, signedIn]);

  useEffect(() => {
    if (!signedIn) return;
    Promise.all([api.types(), api.list()])
      .then(([t, l]) => {
        setTypes(t);
        setItems(l);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load integration types."));
  }, [signedIn, step]);

  const current = useMemo(() => (!adminReady ? 0 : !signedIn ? -1 : (step ?? 1)), [adminReady, signedIn, step]);

  const finish = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.completeSetup();
      await refresh();
      navigate("/overview", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not finish setup.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <div className="card auth-card wide">
        <div className="brand">
          <CloudIcon />
          <span>Clear Cloud Farm</span>
        </div>
        <h1>Welcome</h1>
        <ol className="steps" aria-label="Setup steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i === current ? "current" : i < current ? "done" : ""} aria-current={i === current ? "step" : undefined}>
              <span className="step-num">{i + 1}</span> {s}
            </li>
          ))}
        </ol>
        {error && <p role="alert" className="msg-error">{error}</p>}
        {current === -1 && (
          <>
            <h2 className="card-title">Sign In to Continue</h2>
            <p className="muted">Setup was started earlier. Sign in as admin to resume.</p>
            <LoginForm />
          </>
        )}
        {current === 0 && (
          <>
            <h2 className="card-title">Admin Password</h2>
            <AdminStep onDone={async () => { await refresh(); setStep(1); }} />
          </>
        )}
        {current === 1 && (
          <>
            <h2 className="card-title">Home Assistant</h2>
            <IntegrationStep key="ha" kind="home_assistant" types={types} existing={items.find((i) => i.kind === "home_assistant")} onDone={() => setStep(2)} />
          </>
        )}
        {current === 2 && (
          <>
            <h2 className="card-title">Grafana</h2>
            <IntegrationStep key="gf" kind="grafana" types={types} existing={items.find((i) => i.kind === "grafana")} onDone={() => setStep(3)} />
          </>
        )}
        {current === 3 && (
          <>
            <h2 className="card-title">Done</h2>
            <p>
              The panel is ready. You can add more integrations and test them any time from the Integrations page.
            </p>
            <div className="form-actions">
              <button type="button" className="btn" onClick={() => setStep(2)}>Back</button>
              <span className="spacer" />
              <button type="button" className="btn btn-primary" disabled={busy} onClick={finish}>
                {busy ? "Finishing..." : "Open the Panel"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
