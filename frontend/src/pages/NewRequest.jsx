import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createRequest, listBrands, listSlots, listStores } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const BLANK_AMBASSADOR = { full_name: "", phone: "", email: "", social_handle: "", followers: "", engagement_rate: "", account_age_days: "" };

export default function NewRequest() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [brands, setBrands] = useState([]);
  const [stores, setStores] = useState([]);
  const [slots, setSlots] = useState([]);
  const [storeId, setStoreId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [slotId, setSlotId] = useState("");
  const [ambassadors, setAmbassadors] = useState([{ ...BLANK_AMBASSADOR }]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listBrands(token).then(setBrands).catch((e) => setError(e.message));
    listStores(token).then(setStores).catch((e) => setError(e.message));
  }, [token]);

  useEffect(() => {
    if (!storeId) return setSlots([]);
    listSlots(storeId, token).then(setSlots).catch((e) => setError(e.message));
    setSlotId("");
  }, [storeId, token]);

  function updateAmbassador(i, field, value) {
    setAmbassadors((list) => list.map((a, idx) => (idx === i ? { ...a, [field]: value } : a)));
  }

  function addAmbassador() {
    setAmbassadors((list) => [...list, { ...BLANK_AMBASSADOR }]);
  }

  function removeAmbassador(i) {
    setAmbassadors((list) => list.filter((_, idx) => idx !== i));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = {
        brand_id: Number(brandId),
        slot_id: Number(slotId),
        ambassador_count: ambassadors.length,
        ambassadors: ambassadors.map((a) => ({
          full_name: a.full_name,
          phone: a.phone,
          email: a.email || null,
          social_handle: a.social_handle || null,
          followers: a.followers === "" ? null : Number(a.followers),
          engagement_rate: a.engagement_rate === "" ? null : Number(a.engagement_rate),
          account_age_days: a.account_age_days === "" ? null : Number(a.account_age_days),
        })),
      };
      const created = await createRequest(payload, token);
      navigate(`/requests/${created.request_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the request.");
    } finally {
      setBusy(false);
    }
  }

  const noBrands = brands.length === 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>New activation request</h1>
          <p>Pick a store slot and list the ambassadors who will staff it. You can review and submit on the next screen.</p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {noBrands && (
        <div className="notice-box">Add a brand first — go to the Brands page, then come back here.</div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="panel">
          <h3>Where and when</h3>
          <div className="field-row">
            <div>
              <label htmlFor="brand">Brand</label>
              <select id="brand" required value={brandId} onChange={(e) => setBrandId(e.target.value)}>
                <option value="" disabled>Choose a brand</option>
                {brands.map((b) => (
                  <option key={b.brand_id} value={b.brand_id}>{b.brand_name} ({b.category})</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="store">Store</label>
              <select id="store" required value={storeId} onChange={(e) => setStoreId(e.target.value)}>
                <option value="" disabled>Choose a store</option>
                {stores.map((s) => (
                  <option key={s.store_id} value={s.store_id}>{s.store_name} — {s.location}</option>
                ))}
              </select>
            </div>
          </div>

          <label htmlFor="slot">Time slot</label>
          <select id="slot" required disabled={!storeId} value={slotId} onChange={(e) => setSlotId(e.target.value)}>
            <option value="" disabled>{storeId ? "Choose an open slot" : "Choose a store first"}</option>
            {slots.map((s) => (
              <option key={s.slot_id} value={s.slot_id}>
                {s.slot_date} · {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)} (capacity {s.capacity})
              </option>
            ))}
          </select>
          {storeId && slots.length === 0 && (
            <p className="meta" style={{ marginTop: "0.5em" }}>No open slots left at this store.</p>
          )}
        </div>

        <div className="panel">
          <div className="page-head" style={{ marginBottom: "0.6em" }}>
            <h3>Ambassadors ({ambassadors.length})</h3>
            <button type="button" className="secondary" onClick={addAmbassador}>+ Add ambassador</button>
          </div>

          {ambassadors.map((a, i) => (
            <div className="ambassador-card" key={i}>
              {ambassadors.length > 1 && (
                <button type="button" className="remove" onClick={() => removeAmbassador(i)}>Remove</button>
              )}
              <div className="field-row">
                <div>
                  <label>Full name</label>
                  <input required value={a.full_name} onChange={(e) => updateAmbassador(i, "full_name", e.target.value)} />
                </div>
                <div>
                  <label>Phone</label>
                  <input required placeholder="07XXXXXXXX" value={a.phone} onChange={(e) => updateAmbassador(i, "phone", e.target.value)} />
                </div>
              </div>
              <div className="field-row">
                <div>
                  <label>Email (optional)</label>
                  <input type="email" value={a.email} onChange={(e) => updateAmbassador(i, "email", e.target.value)} />
                </div>
                <div>
                  <label>Social handle (optional)</label>
                  <input value={a.social_handle} onChange={(e) => updateAmbassador(i, "social_handle", e.target.value)} />
                </div>
              </div>
              <div className="field-row">
                <div>
                  <label>Followers</label>
                  <input type="number" min="0" value={a.followers} onChange={(e) => updateAmbassador(i, "followers", e.target.value)} />
                </div>
                <div>
                  <label>Engagement rate (e.g. 0.035 = 3.5%)</label>
                  <input type="number" min="0" step="0.001" value={a.engagement_rate} onChange={(e) => updateAmbassador(i, "engagement_rate", e.target.value)} />
                </div>
                <div>
                  <label>Account age (days)</label>
                  <input type="number" min="0" value={a.account_age_days} onChange={(e) => updateAmbassador(i, "account_age_days", e.target.value)} />
                </div>
              </div>
            </div>
          ))}
        </div>

        <button type="submit" disabled={busy || noBrands}>
          {busy ? "Saving…" : "Save as draft"}
        </button>
      </form>
    </>
  );
}
