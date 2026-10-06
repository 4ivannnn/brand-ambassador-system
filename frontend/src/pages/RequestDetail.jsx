import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ApiError, completeRequest, decide, getRequest, overrideFlag, submitRequest,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StatusBadge from "../components/StatusBadge";

function pct(x) {
  return `${Math.round(x * 100)}%`;
}

export default function RequestDetail() {
  const { id } = useParams();
  const { token, role } = useAuth();
  const navigate = useNavigate();

  const [req, setReq] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [problems, setProblems] = useState([]);
  const [alternatives, setAlternatives] = useState([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  function refresh() {
    getRequest(id, token).then(setReq).catch((e) => setError(e.message));
  }

  useEffect(refresh, [id, token]);

  async function run(action) {
    setError("");
    setNotice("");
    setProblems([]);
    setBusy(true);
    try {
      await action();
      refresh();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        setProblems(err.details || []);
      } else {
        setError("Something went wrong talking to the server.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit() {
    await run(async () => {
      const result = await submitRequest(id, token);
      setProblems(result.problems || []);
      setAlternatives(result.alternative_slots || []);
      setNotice(
        result.status === "FLAGGED_FOR_REVIEW"
          ? "This request was flagged for manual review."
          : "Submitted — awaiting manager approval."
      );
    });
  }

  if (error && !req) return <div className="error-box">{error}</div>;
  if (!req) return <p className="loading">Loading request…</p>;

  const a = req.latest_assessment;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Request #{String(req.request_id).padStart(3, "0")}</h1>
          <p>
            Store {req.store_id} · {req.activation_date} · {req.start_time.slice(0, 5)}–{req.end_time.slice(0, 5)}
          </p>
        </div>
        <StatusBadge status={req.status} />
      </div>

      {notice && <div className="notice-box">{notice}</div>}
      {error && (
        <div className="error-box">
          {error}
          {problems.length > 0 && (
            <ul>
              {problems.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          )}
        </div>
      )}
      {alternatives.length > 0 && (
        <div className="panel">
          <h3>Open alternative slots at this store</h3>
          <ul className="reasons">
            {alternatives.map((s) => (
              <li key={s.slot_id}>{s.slot_date} · {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)}</li>
            ))}
          </ul>
        </div>
      )}

      {req.flag_reason && req.status === "FLAGGED_FOR_REVIEW" && (
        <div className="panel">
          <h3>Why this was flagged</h3>
          <p className="meta">{req.flag_reason}</p>
        </div>
      )}

      {a && (
        <div className="panel">
          <h3>Qualification engine assessment</h3>
          <div className="score-grid">
            <div className="score"><div className="value">{pct(a.authenticity_score)}</div><div className="label">Authenticity</div></div>
            <div className="score"><div className="value">{pct(a.fit_score)}</div><div className="label">Approval fit</div></div>
            <div className="score"><div className="value">{pct(a.confidence)}</div><div className="label">Confidence</div></div>
          </div>
          {a.feedback?.length > 0 && (
            <ul className="reasons">
              {a.feedback.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          )}
        </div>
      )}

      <div className="panel">
        <h3>Ambassadors ({req.ambassadors.length})</h3>
        <div className="ledger">
          {req.ambassadors.map((amb) => (
            <div key={amb.ambassador_id} className="ledger-row" style={{ gridTemplateColumns: "1fr auto" }}>
              <span>
                <span className="title">{amb.full_name}</span><br />
                <span className="meta">{amb.phone}{amb.email ? ` · ${amb.email}` : ""}</span>
              </span>
              <span className="meta mono">
                {amb.followers != null ? `${amb.followers} followers` : "—"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ---- actions, by role and status ------------------------------ */}
      {role === "SUPPLIER" && req.status === "DRAFT" && (
        <button onClick={handleSubmit} disabled={busy}>{busy ? "Submitting…" : "Submit for review"}</button>
      )}

      {role === "APPROVING_MANAGER" && req.status === "PENDING_APPROVAL" && (
        <div className="panel">
          <h3>Decision</h3>
          <label htmlFor="reason">Reason (required to reject)</label>
          <textarea id="reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          <div className="field-row" style={{ marginTop: "0.9em" }}>
            <button
              disabled={busy}
              onClick={() => run(() => decide(id, { decision: "APPROVE", reason: reason || null }, token))}
            >
              Approve
            </button>
            <button
              className="danger"
              disabled={busy || !reason.trim()}
              onClick={() => run(() => decide(id, { decision: "REJECT", reason }, token))}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {role === "APPROVING_MANAGER" && req.status === "FLAGGED_FOR_REVIEW" && (
        <div className="panel">
          <h3>Manual review</h3>
          <label htmlFor="reason">Reason</label>
          <textarea id="reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          <div className="field-row" style={{ marginTop: "0.9em" }}>
            <button disabled={busy || !reason.trim()} onClick={() => run(() => overrideFlag(id, { reason }, token))}>
              Override &amp; send to approval
            </button>
            <button
              className="danger"
              disabled={busy || !reason.trim()}
              onClick={() => run(() => decide(id, { decision: "REJECT", reason }, token))}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {["APPROVING_MANAGER", "STORE_MANAGER"].includes(role) && req.status === "SLOT_BOOKED" && (
        <button disabled={busy} onClick={() => run(() => completeRequest(id, token))}>
          Mark as completed
        </button>
      )}

      {role === "APPROVING_MANAGER" && (
        <p className="switch-line" style={{ textAlign: "left", marginTop: "1.5em" }}>
          <a href="#" onClick={(e) => { e.preventDefault(); navigate(`/audit-trail?request_id=${id}`); }}>
            View this request's audit trail
          </a>
        </p>
      )}
    </>
  );
}
