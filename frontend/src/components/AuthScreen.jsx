import { useState } from "react";
import { loginUser, signupUser } from "../api";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [accountType, setAccountType] = useState("user");
  const [form, setForm] = useState({ username: "", password: "", display_name: "", employee_id: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = mode === "login"
        ? await loginUser({ username: form.username, password: form.password, account_type: accountType })
        : await signupUser(form);
      if (mode === "signup") {
        setMode("login");
        setNotice(response.message);
        setForm({ username: form.username, password: "", display_name: "", employee_id: "" });
      } else {
        onAuthenticated(response);
      }
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
        {mode === "login" && <div className="account-switcher" aria-label="Login type"><button type="button" className={accountType === "user" ? "selected" : ""} onClick={() => { setAccountType("user"); setError(null); }}>User login</button><button type="button" className={accountType === "admin" ? "selected" : ""} onClick={() => { setAccountType("admin"); setError(null); }}>Admin login</button></div>}
        <div className="eyebrow">Your forecast workspace</div>
        <h2 id="auth-title">{mode === "login" ? (accountType === "admin" ? "Administrator access" : "Welcome back") : "Request access"}</h2>
        <p className="auth-note">{mode === "login" ? (accountType === "admin" ? "Review and approve employee access requests." : "Sign in after an administrator approves your account.") : "Submit your details for administrator approval before using the forecast workspace."}</p>
        <form className="auth-form" onSubmit={submit}>
          {mode === "signup" && <label>Display name<input autoComplete="name" value={form.display_name} onChange={(event) => update("display_name", event.target.value)} placeholder="Your name" required /></label>}
          {mode === "signup" && <label>Employee ID<input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={form.employee_id} onChange={(event) => update("employee_id", event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6 digits" required /></label>}
          <label>Username<input autoComplete="username" value={form.username} onChange={(event) => update("username", event.target.value)} placeholder="e.g. operator01" required minLength={3} /></label>
          <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={form.password} onChange={(event) => update("password", event.target.value)} placeholder={mode === "signup" ? "At least 8 characters" : "Your password"} required minLength={mode === "signup" ? 8 : 1} /></label>
          {notice && <div className="auth-notice" role="status">{notice}</div>}
          {error && <div className="auth-error" role="alert">{error}</div>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? (accountType === "admin" ? "Open admin console" : "Open dashboard") : "Submit access request"}</button>
        </form>
        {mode === "signup" && <p className="auth-footnote">Use a unique username and a password of at least 8 characters. Your password is stored as a one-way hash.</p>}
      </section>
    </main>
  );
}
