import { useState } from "react";
import { loginUser, signupUser } from "../api";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", password: "", display_name: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = mode === "login"
        ? await loginUser({ username: form.username, password: form.password })
        : await signupUser(form);
      onAuthenticated(response);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-story">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">GC</div>
          <div><div className="eyebrow">Renewable energy intelligence</div><h1>GreenCast</h1></div>
        </div>
        <div className="auth-story-copy">
          <div className="eyebrow">Forecast with context</div>
          <h2>Make the next 72 hours easier to act on.</h2>
          <p>GreenCast turns weather signals into clear solar generation forecasts, uncertainty ranges, and practical grid recommendations.</p>
          <div className="auth-highlights"><span>72-hour planning</span><span>Explainable actions</span><span>What-if sites</span></div>
        </div>
      </section>
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button className={mode === "login" ? "auth-tab active" : "auth-tab"} onClick={() => { setMode("login"); setError(null); }} type="button">Log in</button>
          <button className={mode === "signup" ? "auth-tab active" : "auth-tab"} onClick={() => { setMode("signup"); setError(null); }} type="button">Create account</button>
        </div>
        <div className="eyebrow">Your forecast workspace</div>
        <h2 id="auth-title">{mode === "login" ? "Welcome back" : "Start forecasting"}</h2>
        <p className="auth-note">{mode === "login" ? "Sign in to access your saved forecasts and site views." : "Create a personal workspace to save forecast runs and comparisons."}</p>
        <form className="auth-form" onSubmit={submit}>
          {mode === "signup" && <label>Display name<input autoComplete="name" value={form.display_name} onChange={(event) => update("display_name", event.target.value)} placeholder="Your name" required /></label>}
          <label>Username<input autoComplete="username" value={form.username} onChange={(event) => update("username", event.target.value)} placeholder="e.g. operator01" required minLength={3} /></label>
          <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={form.password} onChange={(event) => update("password", event.target.value)} placeholder={mode === "signup" ? "At least 8 characters" : "Your password"} required minLength={mode === "signup" ? 8 : 1} /></label>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Open dashboard" : "Create my workspace"}</button>
        </form>
        {mode === "signup" && <p className="auth-footnote">Use a unique username and a password of at least 8 characters. Your password is stored as a one-way hash.</p>}
      </section>
    </main>
  );
}
