import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listRequests } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StatusBadge from "../components/StatusBadge";

const FILTERS = {
  SUPPLIER: [
    { value: "", label: "All", statuses: null },
    { value: "DRAFT", label: "Drafts", statuses: ["DRAFT"] },
    { value: "PENDING_APPROVAL", label: "In review", statuses: ["PENDING_APPROVAL"] },
    { value: "APPROVED", label: "Approved", statuses: ["APPROVED", "SLOT_BOOKED", "COMPLETED"] },
    { value: "FLAGGED_FOR_REVIEW", label: "Needs attention", statuses: ["FLAGGED_FOR_REVIEW"] },
    { value: "REJECTED", label: "Declined", statuses: ["REJECTED"] },
  ],
  APPROVING_MANAGER: [
    { value: "", label: "All", statuses: null },
    { value: "PENDING_APPROVAL", label: "In review", statuses: ["PENDING_APPROVAL"] },
    { value: "APPROVED", label: "Approved", statuses: ["APPROVED", "SLOT_BOOKED", "COMPLETED"] },
    { value: "FLAGGED_FOR_REVIEW", label: "Needs attention", statuses: ["FLAGGED_FOR_REVIEW"] },
    { value: "REJECTED", label: "Declined", statuses: ["REJECTED"] },
  ],
  STORE_MANAGER: [
    { value: "", label: "All decisions", statuses: null },
    { value: "SLOT_BOOKED", label: "Approved", statuses: ["SLOT_BOOKED"] },
    { value: "COMPLETED", label: "Completed", statuses: ["COMPLETED"] },
    { value: "REJECTED", label: "Denied", statuses: ["REJECTED"] },
  ],
};

const HEADS = {
  SUPPLIER: { title: "Your requests", blurb: "Track every activation from submission to final decision.", greeting: "Welcome to your activation desk" },
  APPROVING_MANAGER: { title: "Activation requests", blurb: "Review and follow the requests routed to your team.", greeting: "Your review workspace" },
  STORE_MANAGER: { title: "Activation history", blurb: "See approved, completed, and denied requests for your stores.", greeting: "Your store activity" },
};

function fmtDate(d) {
  return new Date(d).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function displayStatus(status) {
  return status === "PENDING_APPROVAL" ? "In review" : status === "FLAGGED_FOR_REVIEW" ? "Needs attention" : status.replaceAll("_", " ").toLowerCase();
}

export default function RequestsList() {
  const { token, role } = useAuth();
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [requests, setRequests] = useState(null);
  const [error, setError] = useState("");
  const filters = FILTERS[role] || FILTERS.SUPPLIER;
  const head = HEADS[role] || HEADS.SUPPLIER;

  useEffect(() => {
    let cancelled = false;
    setRequests(null);
    setError("");
    listRequests(token)
      .then((data) => !cancelled && setRequests(data))
      .catch((err) => !cancelled && setError(err.message || "Could not load requests."));
    return () => { cancelled = true; };
  }, [token]);

  const counts = useMemo(() => {
    if (!requests) return {};
    return filters.reduce((result, filter) => {
      result[filter.value] = filter.statuses ? requests.filter((r) => filter.statuses.includes(r.status)).length : requests.length;
      return result;
    }, {});
  }, [requests, filters]);

  const visibleRequests = useMemo(() => {
    if (!requests) return [];
    const selected = filters.find((filter) => filter.value === status);
    const needle = query.trim().toLocaleLowerCase();
    return requests.filter((request) => {
      const matchesStatus = !selected?.statuses || selected.statuses.includes(request.status);
      const matchesSearch = !needle || [request.store_id, request.activation_date, request.brand_id, request.status]
        .some((value) => String(value ?? "").toLocaleLowerCase().includes(needle));
      return matchesStatus && matchesSearch;
    });
  }, [requests, filters, status, query]);

  return (
    <div className="requests-home">
      <section className="home-hero">
        <div className="home-hero-copy">
          <span className="home-eyebrow">{head.greeting}</span>
          <h1>{head.title}</h1>
          <p>{head.blurb}</p>
        </div>
        {role === "SUPPLIER" && <Link className="home-primary-action" to="/requests/new"><span aria-hidden="true">＋</span> New request</Link>}
        {requests && <div className="home-total"><strong>{requests.length}</strong><span>{requests.length === 1 ? "request" : "requests"} total</span></div>}
        <span className="home-hero-orbit" aria-hidden="true" />
      </section>

      <section className="request-overview" aria-label="Request status summary">
        {filters.map((filter, index) => (
          <button
            type="button"
            key={filter.value || "all"}
            className={`overview-card overview-${index}${status === filter.value ? " is-active" : ""}`}
            onClick={() => setStatus(filter.value)}
            aria-pressed={status === filter.value}
          >
            <span>{filter.label}</span>
            <strong>{requests ? (counts[filter.value] ?? 0) : "—"}</strong>
            <i aria-hidden="true">{status === filter.value ? "Viewing" : "View requests →"}</i>
          </button>
        ))}
      </section>

      <section className="request-list-panel">
        <div className="request-list-heading">
          <div><h2>Recent activity</h2><p>Choose a status or search to find a request.</p></div>
          <label className="request-search"><span aria-hidden="true">⌕</span><input aria-label="Search requests" placeholder="Search store, brand or date" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        </div>
        <div className="request-filter-row" role="group" aria-label="Filter requests by status">
          {filters.map((filter) => <button type="button" key={filter.value || "all"} className={`filter-chip${status === filter.value ? " active" : ""}`} onClick={() => setStatus(filter.value)}>{filter.label}<span>{requests ? counts[filter.value] ?? 0 : "…"}</span></button>)}
        </div>

        {error && <div className="error-box" role="alert">{error}</div>}
        {!requests && !error && <div className="request-skeletons" aria-label="Loading requests"><span /><span /><span /></div>}
        {requests && visibleRequests.length === 0 && (
          <div className="request-empty"><span aria-hidden="true">{requests.length === 0 ? "✦" : "⌕"}</span><h3>{requests.length === 0 ? "Your activity starts here" : "No matching requests"}</h3><p>{requests.length === 0 ? (role === "SUPPLIER" ? "Create your first activation request and its progress will appear here." : "There are no requests to show yet.") : "Try another status or a different search."}</p>{requests.length === 0 && role === "SUPPLIER" && <Link to="/requests/new" className="empty-action">Create a request</Link>}</div>
        )}
        {requests && visibleRequests.length > 0 && (
          <div className="request-activity-list">
            {visibleRequests.map((request) => (
              <Link key={request.request_id} to={`/requests/${request.request_id}`} className="activity-row">
                <span className="activity-mark" aria-hidden="true">{String(request.store_id).slice(-2)}</span>
                <span className="activity-main"><strong>Store {request.store_id}</strong><span>Brand {request.brand_id} · {fmtDate(request.activation_date)} · {request.start_time?.slice(0, 5)}–{request.end_time?.slice(0, 5)}</span></span>
                <span className="activity-people">{request.ambassador_count} ambassador{request.ambassador_count === 1 ? "" : "s"}</span>
                {role === "STORE_MANAGER" ? <span className={`stamp ${request.status === "REJECTED" ? "rejected" : "approved"}`}>{request.status === "REJECTED" ? "Denied" : displayStatus(request.status)}</span> : <StatusBadge status={request.status} />}
                <span className="activity-arrow" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
