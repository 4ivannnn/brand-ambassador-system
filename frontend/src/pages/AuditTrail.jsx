import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { auditTrail } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function fmt(ts) {
  return new Date(ts).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function AuditTrail() {
  const { token } = useAuth();
  const [params, setParams] = useSearchParams();
  const requestId = params.get("request_id") || "";
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setEntries(null);
    auditTrail(token, requestId || undefined).then(setEntries).catch((e) => setError(e.message));
  }, [token, requestId]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Audit trail</h1>
          <p>Every status change recorded by the system, newest first.</p>
        </div>
      </div>

      <div className="field-row" style={{ maxWidth: 320, marginBottom: "1.2em" }}>
        <input
          placeholder="Filter by request id"
          value={requestId}
          onChange={(e) => setParams(e.target.value ? { request_id: e.target.value } : {})}
        />
      </div>

      {error && <div className="error-box">{error}</div>}
      {!entries && !error && <p className="loading">Loading…</p>}
      {entries && entries.length === 0 && <p className="empty-state">No audit entries match that filter.</p>}

      {entries && entries.length > 0 && (
        <div className="ledger">
          {entries.map((e) => (
            <div key={e.audit_id} className="ledger-row" style={{ gridTemplateColumns: "4.5em 1fr auto" }}>
              <span className="case-no">#{e.request_id ?? "—"}</span>
              <span>
                <span className="title">{e.action.replaceAll("_", " ")}</span>
                {e.from_status && e.to_status && (
                  <>
                    <br />
                    <span className="meta">{e.from_status} → {e.to_status}</span>
                  </>
                )}
                {e.detail && <><br /><span className="meta">{e.detail}</span></>}
              </span>
              <span className="meta mono">{fmt(e.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
