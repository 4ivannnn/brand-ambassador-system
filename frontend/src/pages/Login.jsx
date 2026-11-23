import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError, login } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function LoginArtwork() {
  return (
    <div className="login-art-card" aria-hidden="true">
      <div className="login-art-heading"><span>THIS WEEK</span><b>Activation progress <i>•••</i></b></div>
      <div className="login-art-chart"><div className="chart-y"><span>100%</span><span>50%</span><span>0%</span></div><div className="chart-bars"><i style={{ height: "38%" }} /><i style={{ height: "55%" }} /><i style={{ height: "49%" }} /><i style={{ height: "72%" }} /><i style={{ height: "63%" }} /><i style={{ height: "88%" }} /><i style={{ height: "78%" }} /></div></div>
      <div className="login-art-legend"><span><i />Approved</span><span><i />In review</span><span className="login-art-total"><b>18</b> requests</span></div>
      <div className="login-art-note"><span>✓</span><div><b>All teams up to date</b><small>Last activity just now</small></div><i className="note-pulse" /></div>
    </div>
  );
}

export default function Login() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await login(form);
      signIn(data);
      navigate(location.state?.from?.pathname || "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen login-screen">
      <Link className="auth-back-home" to="/">← <span>Back to home</span></Link>
      <div className="login-layout">
        <section className="login-showcase">
          <Link className="landing-brand login-brand" to="/"><span className="landing-brand-mark">A</span><span>Activation<span className="landing-brand-light">Desk</span></span></Link>
          <div className="login-showcase-copy"><span className="login-eyebrow"><i /> YOUR CAMPAIGN WORKSPACE</span><h1>Good to have you <span>back.</span></h1><p>One place to plan activations, review requests, and keep every team moving forward.</p></div>
          <LoginArtwork />
          <div className="login-showcase-foot"><span>BUILT FOR BETTER IN-STORE EXPERIENCES</span><span>01 <i /> 03</span></div>
        </section>

        <form className="auth-card login-card" onSubmit={handleSubmit}>
          <div className="login-card-mark" aria-hidden="true">↗</div>
          <span className="login-form-eyebrow">WORKSPACE ACCESS</span>
          <h2>Sign in</h2>
          <p className="tag">Enter your details to continue to your workspace.</p>

          {error && <div className="error-box" role="alert">{error}</div>}

          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="you@company.com"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />

          <div className="login-password-label"><label htmlFor="password">Password</label><span>Secure sign in</span></div>
          <div className="password-field">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
            <button type="button" className="password-toggle" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? "Hide password" : "Show password"}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <button className="login-submit" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Continue to workspace"}<span aria-hidden="true">→</span>
          </button>
          <div className="login-divider"><span>NEW TO ACTIVATION DESK?</span></div>
          <Link className="login-register-link" to="/register">Create a supplier account <span aria-hidden="true">↗</span></Link>
          <p className="login-support-note"><span aria-hidden="true">✦</span> Suppliers and managers use their assigned accounts to sign in.</p>
        </form>
      </div>
    </main>
  );
}
