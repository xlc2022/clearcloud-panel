import { useState, type FormEvent } from "react";
import { api } from "../api";
import { CloudIcon } from "../components/Sidebar";
import { useSession } from "../session";

export function LoginForm({ onDone }: { onDone?: () => void }) {
  const { refresh } = useSession();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(password);
      await refresh();
      onDone?.();
    } catch (err) {
      const status = (err as { status?: number }).status;
      setError(status === 401 ? "Wrong password." : err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="form">
      <div className="field">
        <label htmlFor="login-pw">Password</label>
        <input id="login-pw" type="password" autoComplete="current-password" autoFocus required value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      {error && <p role="alert" className="msg-error">{error}</p>}
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Signing In..." : "Sign In"}
      </button>
    </form>
  );
}

export function Login() {
  return (
    <div className="center-screen">
      <div className="card auth-card">
        <div className="brand">
          <CloudIcon />
          <span>Clear Cloud Farm</span>
        </div>
        <h1>Sign In</h1>
        <p className="muted">Signing in as admin.</p>
        <LoginForm />
      </div>
    </div>
  );
}
