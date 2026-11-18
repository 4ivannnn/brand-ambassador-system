import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getReportsSummary } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StatusBadge from "../components/StatusBadge";

const COLORS = {
  approved: "#17835d",
  rejected: "#d34d4d",
  flagged: "#e0a900",
  pending: "#3978d4",
};

const PERIODS = [
  ["30d", "Last 30 days"],
  ["90d", "Last 90 days"],
  ["12m", "Last 12 months"],
  ["all", "All time"],
];

function DonutChart({ categories, total }) {
  const radius = 72;
  const circumference = 2 * Math.PI * radius;
  let consumed = 0;

  return (
    <div className="report-donut-wrap">
      <svg className="report-donut" viewBox="0 0 220 220" role="img" aria-label="Request outcomes as percentages">
        <circle className="report-donut-track" cx="110" cy="110" r={radius} />
        {categories.filter((item) => item.count > 0).map((item) => {
          const length = (item.count / Math.max(total, 1)) * circumference;
          const offset = consumed;
          consumed += length;
          return (
            <circle
              key={item.key}
              className="report-donut-segment"
              cx="110"
              cy="110"
              r={radius}
              stroke={COLORS[item.key]}
              strokeDasharray={`${length} ${circumference - length}`}
              strokeDashoffset={-offset}
            />
          );
        })}
        <text className="report-donut-total" x="110" y="105">{total}</text>
        <text className="report-donut-caption" x="110" y="129">requests</text>
      </svg>
    </div>
  );
}

function TrendChart({ trend }) {
  const maxTotal = Math.max(1, ...trend.map((item) => Object.values(item.counts).reduce((sum, value) => sum + value, 0)));
  const keys = ["approved", "rejected", "flagged", "pending"];

  return (
    <div className="report-trend" role="img" aria-label="Monthly request counts for the last six months">
      {trend.map((item) => {
        const total = Object.values(item.counts).reduce((sum, value) => sum + value, 0);
        return (
          <div className="report-trend-month" key={item.month}>
            <div className="report-trend-track" title={`${item.label}: ${total} requests`}>
              <div className="report-trend-stack" style={{ height: `${total ? Math.max(5, (total / maxTotal) * 100) : 0}%` }}>
                {keys.map((key) => item.counts[key] > 0 && (
                  <span key={key} style={{ height: `${(item.counts[key] / total) * 100}%`, background: COLORS[key] }} />
                ))}
              </div>
            </div>
            <span className="report-trend-label">{item.label.split(" ")[0]}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function Reports() {
  const { token, role } = useAuth();
  const [period, setPeriod] = useState("90d");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setReport(null);
    setError("");
    getReportsSummary(token, period)
      .then((data) => !cancelled && setReport(data))
      .catch((err) => !cancelled && setError(err.message || "Could not load reports."));
    return () => { cancelled = true; };
  }, [token, period]);

  const categoryMap = useMemo(
    () => Object.fromEntries((report?.categories || []).map((item) => [item.key, item])),
    [report]
  );
  const heading = role === "SUPPLIER" ? "Your performance" : role === "STORE_MANAGER" ? "Store performance" : "Activation reports";

  return (
    <div className="reports-page">
      <section className="reports-hero">
        <div className="reports-hero-copy">
          <span className="reports-eyebrow">PERFORMANCE SNAPSHOT</span>
          <h1>{heading}</h1>
          <p>Track request outcomes, spot changes over time, and quickly review recent activity.</p>
        </div>
        <div className="reports-period">
          <label htmlFor="report-period">Reporting period</label>
          <select id="report-period" value={period} onChange={(event) => setPeriod(event.target.value)}>
            {PERIODS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <span className="reports-hero-orb reports-hero-orb-one" aria-hidden="true" />
        <span className="reports-hero-orb reports-hero-orb-two" aria-hidden="true" />
      </section>

      {error && <div className="error-box" role="alert">{error}</div>}
      {!report && !error && <p className="loading" role="status">Preparing your reports…</p>}

      {report && (
        <>
          <p className="reports-denominator">
            Outcome percentages use all {report.total} requests in this period. Pending includes drafts and requests awaiting a decision.
          </p>

          <section className="report-metrics" aria-label="Request outcome totals">
            <article className="report-metric report-metric-total">
              <span className="report-metric-icon" aria-hidden="true">✦</span>
              <span className="report-metric-label">Total requests</span>
              <strong>{report.total}</strong>
              <span className="report-metric-note">in selected period</span>
            </article>
            {["approved", "rejected", "flagged"].map((key) => (
              <article className={`report-metric report-metric-${key}`} key={key}>
                <span className="report-metric-icon" aria-hidden="true">{key === "approved" ? "✓" : key === "rejected" ? "×" : "!"}</span>
                <span className="report-metric-label">{categoryMap[key]?.label}</span>
                <strong>{categoryMap[key]?.percentage ?? 0}%</strong>
                <span className="report-metric-note">{categoryMap[key]?.count ?? 0} requests</span>
              </article>
            ))}
          </section>

          <section className="report-panels">
            <article className="report-panel outcome-panel">
              <div className="report-panel-heading">
                <div><span className="report-kicker">OUTCOME MIX</span><h2>How requests are going</h2></div>
                <span className="report-panel-symbol" aria-hidden="true">◒</span>
              </div>
              {report.total === 0 ? (
                <p className="report-empty">No requests in this period yet. Once activity starts, the outcome chart will appear here.</p>
              ) : (
                <div className="report-outcome-content">
                  <DonutChart categories={report.categories} total={report.total} />
                  <ul className="report-legend">
                    {report.categories.map((item) => (
                      <li key={item.key}>
                        <span className="report-legend-dot" style={{ background: COLORS[item.key] }} />
                        <span className="report-legend-name">{item.label}</span>
                        <strong>{item.percentage}%</strong>
                        <span className="report-legend-count">{item.count}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </article>

            <article className="report-panel trend-panel">
              <div className="report-panel-heading">
                <div><span className="report-kicker">MOMENTUM</span><h2>Monthly activity</h2></div>
                <span className="report-panel-symbol" aria-hidden="true">↗</span>
              </div>
              <p className="report-panel-subtitle">Request outcomes across the last six months</p>
              <TrendChart trend={report.trend} />
              <div className="report-trend-legend">
                {report.categories.map((item) => (
                  <span key={item.key}><i style={{ background: COLORS[item.key] }} />{item.label}</span>
                ))}
              </div>
            </article>
          </section>

          <section className="report-panel recent-panel">
            <div className="report-panel-heading">
              <div><span className="report-kicker">LATEST ACTIVITY</span><h2>Recent requests</h2></div>
              <Link className="report-text-link" to="/">View all requests <span aria-hidden="true">→</span></Link>
            </div>
            {report.recent.length === 0 ? (
              <p className="report-empty">Your latest requests will show here.</p>
            ) : (
              <div className="report-recent-list">
                {report.recent.map((item) => (
                  <Link to={`/requests/${item.request_id}`} className="report-recent-row" key={item.request_id}>
                    <span className="report-recent-mark" aria-hidden="true">{item.brand_name.slice(0, 1).toUpperCase()}</span>
                    <span className="report-recent-copy">
                      <strong>{item.brand_name}</strong>
                      <span>{item.store_name} · Activation {item.activation_date}</span>
                    </span>
                    <StatusBadge status={item.status} />
                    <span className="report-recent-arrow" aria-hidden="true">→</span>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
