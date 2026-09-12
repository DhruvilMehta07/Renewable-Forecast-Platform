import { useEffect, useState } from "react";
import { approveAccount, getAccountRequests, rejectAccount } from "../api";

export default function AdminPanel({ session, onLogout }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function loadRequests() {
    setLoading(true);
    setError(null);
    try {
      const response = await getAccountRequests(session.access_token);
      setRequests(response.requests || []);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRequests(); }, []);

  async function decide(userId, action) {
    try {
      if (action === "approve") await approveAccount(userId, session.access_token);
      else await rejectAccount(userId, session.access_token);
      await loadRequests();
    } catch (actionError) {
      setError(actionError.message);
    }
  }

  return (
    <main className="admin-layout">
      <header className="admin-header">
        <div className="brand-lockup"><div className="brand-mark" aria-hidden="true">GC</div><div><div className="eyebrow">Administrator console</div><h1>GreenCast access requests</h1><p className="subtitle">Review employee access before anyone can open forecast data.</p></div></div>
        <button className="signout-button" onClick={onLogout}>Sign out</button>
      </header>
      <section className="panel admin-panel">
        <div className="section-heading"><div><div className="eyebrow">Pending review</div><h2>Account requests</h2></div><button className="refresh-btn" onClick={loadRequests} disabled={loading}>{loading ? "Loading..." : "Refresh requests"}</button></div>
        <p className="panel-note">Approve only employees whose identity and access requirements have been verified. Approved users can then sign in through User login.</p>
        {error && <div className="auth-error" role="alert">{error}</div>}
        {loading ? <p className="empty-state">Loading requests...</p> : requests.length === 0 ? <p className="empty-state">No pending account requests.</p> : <div className="request-list">{requests.map((request) => <div className="request-row" key={request.id}><div><strong>{request.display_name}</strong><span>{request.username} · Employee ID {request.employee_id}</span><small>Requested {new Date(request.created_at).toLocaleString()}</small></div><div className="request-actions"><button className="approve-button" onClick={() => decide(request.id, "approve")}>Approve</button><button className="reject-button" onClick={() => decide(request.id, "reject")}>Reject</button></div></div>)}</div>}
      </section>
    </main>
  );
}
