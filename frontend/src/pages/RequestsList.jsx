import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRequests } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StatusBadge from "../components/StatusBadge";

const FILTERS = {
  SUPPLIER: [
    { value: "", label: "All" },
    { value: "DRAFT", label: "Drafts" },
    { value: "PENDING_APPROVAL", label: "Pending" },
    { value: "FLAGGED_FOR_REVIEW", label: "Flagged" },
    { value: "APPROVED", label: "Approved" },
    { value: "REJECTED", label: "Rejected" },
  ],
  APPROVING_MANAGER: [
    { value: "", label: "All" },
    { value: "PENDING_APPROVAL", label: "Pending" },
    { value: "FLAGGED_FOR_REVIEW", label: "Flagged" },
    { value: "APPROVED", label: "Approved" },
    { value: "REJECTED", label: "Rejected" },
  ],
  STORE_MANAGER: [
    { value: "", label: "All decisions" },
    { value: "SLOT_BOOKED", label: "Approved and booked" },
    { value: "COMPLETED", label: "Completed" },
    { value: "REJECTED", label: "Denied" },
  ],
};

const HEADS = {
  SUPPLIER: { title: "Your requests", blurb: "Everything you've submitted, from draft through to a booked slot." },
  APPROVING_MANAGER: { title: "Activation requests", blurb: "Review what the qualification engine has routed to you." },
  STORE_MANAGER: { title: "Activation history", blurb: "Review approved, completed, and denied requests for your stores." },
};

function fmtDate(d) {
  return new Date(d).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export default function RequestsList() {
  const { token, role } = useAuth();
  const [status, setStatus] = useState("");
  const [requests, setRequests] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setRequests(null);
    listRequests(token, status || undefined)
      .then((data) => !cancelled && setRequests(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [token, status]);

  const head = HEADS[role] || HEADS.SUPPLIER;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{head.title}</h1>
          <p>{head.blurb}</p>
        </div>
        {role === "SUPPLIER" && <Link to="/requests/new"><button>New request</button></Link>}
      </div>

      <div className="field-row" style={{ maxWidth: 420, marginBottom: "1.2em" }}>
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          {(FILTERS[role] || FILTERS.SUPPLIER).map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>

      {error && <div className="error-box">{error}</div>}
      {!requests && !error && <p className="loading">Loading requests…</p>}

      {requests && requests.length === 0 && (
        <p className="empty-state">Nothing here yet. {role === "SUPPLIER" && "Start a new request to see it listed."}</p>
      )}

      {requests && requests.length > 0 && (
        <div className="ledger">
          {requests.map((r) => (
            <Link key={r.request_id} to={`/requests/${r.request_id}`} className="ledger-row">
              <span className="case-no">#{String(r.request_id).padStart(3, "0")}</span>
              <span>
                <span className="title">Store {r.store_id} · {fmtDate(r.activation_date)}</span>
                <br />
                <span className="meta">{r.ambassador_count} ambassador(s) · {r.start_time?.slice(0, 5)}–{r.end_time?.slice(0, 5)}</span>
              </span>
              {role === "STORE_MANAGER" ? (
                <span className={`stamp ${r.status === "REJECTED" ? "rejected" : "approved"}`}>
                  {r.status === "REJECTED" ? "Denied" : r.status === "COMPLETED" ? "Approved · completed" : "Approved"}
                </span>
              ) : <StatusBadge status={r.status} />}
              <span className="meta">&rsaquo;</span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
