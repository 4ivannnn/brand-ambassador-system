import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError, updateSupplierGender } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import GenderSelector from "../components/GenderSelector";

export default function SupplierProfileCompletion() {
  const { token, gender, updateGender } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [selectedGender, setSelectedGender] = useState(gender || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (gender) navigate(location.state?.from?.pathname || "/dashboard", { replace: true });
  }, [gender, location.state, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await updateSupplierGender({ gender: selectedGender }, token);
      updateGender(result.gender);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save your profile.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="profile-completion-panel">
      <span className="profile-completion-mark" aria-hidden="true">✦</span>
      <span className="report-kicker">PROFILE SETUP · 1 OF 1</span>
      <h1>Complete your supplier profile</h1>
      <p className="profile-completion-intro">Choose your gender to finish setting up your account and continue to your dashboard.</p>
      {error && <div className="error-box" role="alert">{error}</div>}
      <form onSubmit={handleSubmit}>
        <GenderSelector value={selectedGender} onChange={setSelectedGender} />
        <button type="submit" disabled={busy || !selectedGender}>
          {busy ? "Saving profile…" : "Save and continue"}
        </button>
      </form>
    </section>
  );
}
