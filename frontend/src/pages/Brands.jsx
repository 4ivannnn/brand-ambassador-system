import { useEffect, useState } from "react";
import { addBrand, listBrands } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function Brands() {
  const { token } = useAuth();
  const [brands, setBrands] = useState(null);
  const [form, setForm] = useState({ brand_name: "", category: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function refresh() {
    listBrands(token).then(setBrands).catch((e) => setError(e.message));
  }

  useEffect(refresh, [token]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await addBrand(form, token);
      setForm({ brand_name: "", category: "" });
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Brands</h1>
          <p>The brands/products you run activations for. Add one before creating a request.</p>
        </div>
      </div>

      <div className="panel">
        <h3>Add a brand</h3>
        {error && <div className="error-box">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field-row">
            <div>
              <label htmlFor="brand_name">Brand name</label>
              <input
                id="brand_name"
                required
                value={form.brand_name}
                onChange={(e) => setForm({ ...form, brand_name: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="category">Category</label>
              <input
                id="category"
                required
                placeholder="e.g. Beverages"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            </div>
          </div>
          <button type="submit" disabled={busy} style={{ marginTop: "1em" }}>
            {busy ? "Adding…" : "Add brand"}
          </button>
        </form>
      </div>

      {!brands && <p className="loading">Loading brands…</p>}
      {brands && brands.length === 0 && <p className="empty-state">No brands yet.</p>}
      {brands && brands.length > 0 && (
        <div className="ledger">
          {brands.map((b) => (
            <div key={b.brand_id} className="ledger-row" style={{ gridTemplateColumns: "4.5em 1fr" }}>
              <span className="case-no">#{b.brand_id}</span>
              <span>
                <span className="title">{b.brand_name}</span>
                <br />
                <span className="meta">{b.category}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
