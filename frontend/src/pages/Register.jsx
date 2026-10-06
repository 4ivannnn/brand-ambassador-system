import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, register } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const EMPTY = { company: "", contact: "", email: "", full_name: "", password: "" };

export default function Register() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await register(form);
      signIn(data);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="brand">Activation Desk</div>
        <p className="tag">Register your company to start submitting activation requests.</p>

        {error && <div className="error-box">{error}</div>}

        <label htmlFor="company">Company name</label>
        <input id="company" required value={form.company} onChange={set("company")} />

        <label htmlFor="contact">Contact phone</label>
        <input id="contact" required placeholder="07XXXXXXXX" value={form.contact} onChange={set("contact")} />

        <label htmlFor="email">Work email</label>
        <input id="email" type="email" required value={form.email} onChange={set("email")} />

        <label htmlFor="full_name">Your name</label>
        <input id="full_name" required value={form.full_name} onChange={set("full_name")} />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          required
          minLength={8}
          value={form.password}
          onChange={set("password")}
        />

        <button type="submit" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
        <p className="switch-line">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
