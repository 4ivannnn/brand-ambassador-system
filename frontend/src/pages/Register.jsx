import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, register } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import GenderSelector from "../components/GenderSelector";

const EMPTY = { company: "", contact: "", email: "", full_name: "", gender: "", password: "", supplier_invite_code: "" };

export default function Register() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [accountMode, setAccountMode] = useState("create");

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  const passwordStrength = [
    form.password.length >= 8,
    /[a-z]/.test(form.password) && /[A-Z]/.test(form.password),
    /\d/.test(form.password),
    /[^A-Za-z0-9]/.test(form.password),
  ].filter(Boolean).length;
  const strengthLabel = ["", "Needs more strength", "Getting there", "Good password", "Strong password"][passwordStrength];

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = { ...form, supplier_invite_code: accountMode === "join" ? form.supplier_invite_code.trim() : undefined };
      const data = await register(payload);
      signIn(data);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen register-screen">
      <form className="auth-card register-card" onSubmit={handleSubmit}>
        <div className="brand">Activation Desk</div>
        <p className="tag">Create a supplier workspace or join your team to work on requests together.</p>

        <div className="supplier-account-modes" role="group" aria-label="Supplier account type">
          <button type="button" className={accountMode === "create" ? "active" : ""} onClick={() => setAccountMode("create")} aria-pressed={accountMode === "create"}>Create workspace</button>
          <button type="button" className={accountMode === "join" ? "active" : ""} onClick={() => setAccountMode("join")} aria-pressed={accountMode === "join"}>Join a team</button>
        </div>
        {accountMode === "join" ? (
          <div className="supplier-join-note">
            <strong>Joining a supplier team?</strong>
            <span>Ask a teammate for the invite code from their supplier dashboard. Your team will share brands and requests.</span>
            <label htmlFor="supplier-invite-code">Supplier invite code</label>
            <input id="supplier-invite-code" required minLength={12} autoComplete="off" value={form.supplier_invite_code} onChange={set("supplier_invite_code")} placeholder="Paste your team code" />
          </div>
        ) : (
          <div className="supplier-join-note"><strong>Starting a new supplier team?</strong><span>You’ll get an invite code to share with colleagues after creating your account.</span></div>
        )}

        {error && <div className="error-box" role="alert">{error}</div>}

        {accountMode === "create" && <>
          <label htmlFor="company">Company name</label>
          <input id="company" required value={form.company} onChange={set("company")} />

          <label htmlFor="contact">Contact phone</label>
          <input id="contact" required placeholder="07XXXXXXXX" value={form.contact} onChange={set("contact")} />
        </>}

        <label htmlFor="email">Work email</label>
        <input id="email" type="email" required value={form.email} onChange={set("email")} />

        <label htmlFor="full_name">Your name</label>
        <input id="full_name" autoComplete="name" required value={form.full_name} onChange={set("full_name")} />

        <GenderSelector value={form.gender} onChange={(gender) => setForm({ ...form, gender })} />

        <label htmlFor="password">Password</label>
        <div className="password-field">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            required
            minLength={8}
            value={form.password}
            onChange={set("password")}
          />
          <button type="button" className="password-toggle" onClick={() => setShowPassword((shown) => !shown)}>
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        <div className="password-strength" aria-live="polite">
          <div className="password-strength-bars" aria-hidden="true">
            {[1, 2, 3, 4].map((step) => (
              <span key={step} className={step <= passwordStrength ? `filled strength-${passwordStrength}` : ""} />
            ))}
          </div>
          <span>{form.password ? strengthLabel : "Use at least 8 characters."}</span>
        </div>

        <button type="submit" disabled={busy}>
          {busy ? "Creating account…" : accountMode === "join" ? "Join supplier team" : "Create supplier account"}
        </button>
        <p className="switch-line">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
