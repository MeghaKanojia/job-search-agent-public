import { FormEvent, useState } from "react";
import { setAuthHeader } from "../api/client";

// Not imported from client.ts's BASE_URL to keep this component fully
// self-contained for the one request it makes before the rest of the app
// (and its auth state) exists.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setChecking(true);
    const header = `Basic ${btoa(`${username}:${password}`)}`;
    try {
      // Any cheap authenticated route works here -- this just confirms the
      // credentials are actually valid before storing them.
      const res = await fetch(`${BASE_URL}/settings/llm_status`, {
        headers: { Authorization: header },
      });
      if (!res.ok) {
        setError("Invalid username or password.");
        return;
      }
      setAuthHeader(header);
      onSuccess();
    } catch (e) {
      setError(`Couldn't reach the server: ${e}`);
    } finally {
      setChecking(false);
    }
  };

  const fillDemoCredentials = () => {
    setUsername("public");
    setPassword("12345");
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>Job Search Agent</h1>
        <p className="page-subtitle">Public portfolio demo, no real personal data behind this login</p>
        <div className="demo-banner">
          This is a public demo. Sign in with username <strong>public</strong> and password{" "}
          <strong>12345</strong>, or{" "}
          <button type="button" className="demo-banner-link" onClick={fillDemoCredentials}>
            click to fill them in
          </button>
          .
        </div>
        {error && <div className="error-banner">{error}</div>}
        <label htmlFor="login-username">Username</label>
        <input
          id="login-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
          autoComplete="username"
        />
        <label htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        <button className="btn" type="submit" disabled={checking}>
          {checking ? "Checking…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
