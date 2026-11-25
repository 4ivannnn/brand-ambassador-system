import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createRequest, listBrands, listSlots, listStores } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const BLANK_AMBASSADOR = { full_name: "", phone: "", email: "", social_handle: "", followers: "", engagement_rate: "", account_age_days: "" };
const SAMPLE_AMBASSADORS = [
  { full_name: "Amina Wanjiku", phone: "0710000101", email: "amina.wanjiku@example.com", social_handle: "@amina.creates", followers: "6800", engagement_rate: "0.042", account_age_days: "920", sample: true },
  { full_name: "Brian Otieno", phone: "0710000102", email: "brian.otieno@example.com", social_handle: "@brianonthego", followers: "12400", engagement_rate: "0.036", account_age_days: "1180", sample: true },
  { full_name: "Nia Mwangi", phone: "0710000103", email: "nia.mwangi@example.com", social_handle: "@nia.lifestyle", followers: "9100", engagement_rate: "0.051", account_age_days: "760", sample: true },
  { full_name: "Kevin Kiptoo", phone: "0710000104", email: "kevin.kiptoo@example.com", social_handle: "@kevinkiptoo", followers: "5300", engagement_rate: "0.039", account_age_days: "640", sample: true },
];

function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function shiftDateByYears(value, years) {
  const [year, month, day] = value.split("-").map(Number);
  const targetYear = year + years;
  const lastDay = new Date(targetYear, month, 0).getDate();
  return `${targetYear}-${String(month).padStart(2, "0")}-${String(Math.min(day, lastDay)).padStart(2, "0")}`;
}

export default function NewRequest() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [brands, setBrands] = useState([]);
  const [stores, setStores] = useState([]);
  const [slots, setSlots] = useState([]);
  const [storeId, setStoreId] = useState("");
  const [calendarDate, setCalendarDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return toDateInputValue(tomorrow);
  });
  const [brandId, setBrandId] = useState("");
  const [slotId, setSlotId] = useState("");
  const [ambassadors, setAmbassadors] = useState([{ ...BLANK_AMBASSADOR }]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const brandGroups = useMemo(() => {
    const sorted = [...brands].sort((a, b) =>
      a.category.localeCompare(b.category, undefined, { sensitivity: "base" }) ||
      a.brand_name.localeCompare(b.brand_name, undefined, { sensitivity: "base" })
    );
    return sorted.reduce((groups, brand) => {
      (groups[brand.category] ||= []).push(brand);
      return groups;
    }, {});
  }, [brands]);

  useEffect(() => {
    listBrands(token).then(setBrands).catch((e) => setError(e.message));
    listStores(token).then(setStores).catch((e) => setError(e.message));
  }, [token]);

  useEffect(() => {
    if (!storeId) return setSlots([]);
    listSlots(storeId, token, false, calendarDate, calendarDate)
      .then(setSlots)
      .catch((e) => setError(e.message));
    setSlotId("");
  }, [storeId, token, calendarDate]);

  function updateAmbassador(i, field, value) {
    setAmbassadors((list) => list.map((a, idx) => (idx === i ? { ...a, [field]: value } : a)));
  }

  function addAmbassador() {
    setAmbassadors((list) => [...list, { ...BLANK_AMBASSADOR }]);
  }

  function addSampleAmbassadors() {
    const selectedStore = stores.find((store) => String(store.store_id) === String(storeId));
    const filledCount = ambassadors.filter((ambassador) => ambassador.full_name || ambassador.phone).length;
    const remaining = Math.max(0, (selectedStore?.ambassador_limit ?? 6) - filledCount);
    const available = SAMPLE_AMBASSADORS
      .filter((sample) => !ambassadors.some((ambassador) => ambassador.full_name === sample.full_name))
      .slice(0, remaining);
    if (!available.length) return;

    setAmbassadors((list) => {
      const next = [...list];
      for (const sample of available) {
        const emptyIndex = next.findIndex((ambassador) => !ambassador.full_name && !ambassador.phone);
        if (emptyIndex >= 0) next[emptyIndex] = { ...sample };
        else next.push({ ...sample });
      }
      return next;
    });
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
  const today = toDateInputValue(new Date());
  const earliestDate = shiftDateByYears(today, -2);
  const latestDate = shiftDateByYears(today, 2);
  const selectedStore = stores.find((store) => String(store.store_id) === String(storeId));
  const requiredFields = 4 + ambassadors.length * 2;
  const completedFields = Number(Boolean(brandId)) + Number(Boolean(storeId)) + Number(Boolean(calendarDate)) + Number(Boolean(slotId)) +
    ambassadors.reduce((sum, ambassador) => sum + Number(Boolean(ambassador.full_name)) + Number(Boolean(ambassador.phone)), 0);
  const progress = Math.round(completedFields / requiredFields * 100);
  const sampleProfilesLeft = SAMPLE_AMBASSADORS.filter((sample) => !ambassadors.some((ambassador) => ambassador.full_name === sample.full_name)).length;

  return (
    <>
      <div className="request-builder-hero">
        <div className="request-builder-copy"><span className="request-builder-kicker">NEW CAMPAIGN REQUEST</span><h1>Build your activation</h1><p>Choose where and when it happens, then add the team who will bring your brand to life.</p></div>
        <div className="request-progress-card"><div><span>FORM PROGRESS</span><strong>{progress}%</strong></div><div className="request-progress-track"><i style={{ width: `${progress}%` }} /></div><small>{completedFields} of {requiredFields} required details complete</small></div>
        <span className="request-builder-decoration" aria-hidden="true">✦</span>
      </div>

      <div className="request-stepper" aria-label="Request steps">
        <div className="request-step active"><span>1</span><div><b>Activation details</b><small>Brand, store and time</small></div></div>
        <i aria-hidden="true" />
        <div className="request-step"><span>2</span><div><b>Ambassador team</b><small>People and profile details</small></div></div>
        <i aria-hidden="true" />
        <div className="request-step"><span>3</span><div><b>Review</b><small>Save and check your request</small></div></div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {noBrands && (
        <div className="notice-box">Add a brand first — go to the Brands page, then come back here.</div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="panel request-form-panel">
          <div className="request-section-heading"><span className="request-section-icon">⌖</span><div><h2>Where and when</h2><p>Pick a brand, store and available activation slot.</p></div><span className="request-section-step">STEP 01</span></div>
          <div className="field-row">
            <div>
              <label htmlFor="brand">Brand</label>
              <select id="brand" required value={brandId} onChange={(e) => setBrandId(e.target.value)}>
                <option value="" disabled>Choose a brand</option>
                {Object.entries(brandGroups).map(([category, categoryBrands]) => (
                  <optgroup key={category} label={category}>
                    {categoryBrands.map((brand) => (
                      <option key={brand.brand_id} value={brand.brand_id}>{brand.brand_name}</option>
                    ))}
                  </optgroup>
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

          <label htmlFor="activation-date">Calendar date</label>
          <input
            id="activation-date"
            type="date"
            required
            min={earliestDate}
            max={latestDate}
            value={calendarDate}
            onChange={(event) => {
              if (event.target.value) setCalendarDate(event.target.value);
            }}
          />
          <p className="calendar-helper" style={{ marginTop: "0.4em" }}>
            Calendar range: {earliestDate} to {latestDate}. Past dates and today are shown for reference and cannot be booked.
          </p>

          <label htmlFor="slot">Time slot</label>
          <select id="slot" required disabled={!storeId} value={slotId} onChange={(e) => setSlotId(e.target.value)}>
            <option value="" disabled>{storeId ? "Choose a time slot" : "Choose a store first"}</option>
            {slots.map((s) => (
              <option key={s.slot_id} value={s.slot_id} disabled={s.slot_date <= today || s.status !== "OPEN"}>
                {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)} · {s.status !== "OPEN" ? s.status : s.slot_date <= today ? "Not bookable" : `Capacity ${s.capacity}`}
              </option>
            ))}
          </select>
          {storeId && slots.length === 0 && (
            <p className="slot-empty-hint"><span>ⓘ</span> No time slots are listed for this date. Try another date or store.</p>
          )}
        </div>

        <div className="panel request-form-panel">
          <div className="request-section-heading"><span className="request-section-icon ambassador-section-icon">♧</span><div><h2>Your ambassador team <span className="team-count">{ambassadors.filter((ambassador) => ambassador.full_name || ambassador.phone).length}</span></h2><p>Add the people who will represent your brand at the activation.</p></div><span className="request-section-step">STEP 02</span></div>
          <div className="ambassador-tools">
            <div className="sample-ambassador-prompt"><span className="sample-sparkle">✦</span><span><b>Building a demo?</b><small>Add realistic sample profiles in one click. They’re clearly marked as examples.</small></span></div>
            <div className="ambassador-tool-buttons"><button type="button" className="secondary sample-add-button" disabled={sampleProfilesLeft === 0 || (selectedStore && ambassadors.filter((a) => a.full_name || a.phone).length >= selectedStore.ambassador_limit)} onClick={addSampleAmbassadors}>✦ Add sample team</button><button type="button" className="add-person-button" onClick={addAmbassador}><span>＋</span> Add person</button></div>
          </div>

          {ambassadors.map((a, i) => (
            <div className={`ambassador-card enhanced-ambassador-card${a.sample ? " sample-profile" : ""}`} key={i}>
              <div className="ambassador-card-head"><span className="ambassador-avatar">{a.full_name ? a.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase() : String(i + 1).padStart(2, "0")}</span><div><b>{a.full_name || `Ambassador ${String(i + 1).padStart(2, "0")}`}</b><small>{a.sample ? "Sample profile · edit before using" : "Team member details"}</small></div>{a.sample && <span className="sample-profile-tag">DEMO</span>}</div>
              {ambassadors.length > 1 && (
                <button type="button" className="remove" aria-label={`Remove ambassador ${a.full_name || i + 1}`} onClick={() => removeAmbassador(i)}>Remove</button>
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
