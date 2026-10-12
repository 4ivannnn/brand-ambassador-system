import { useEffect, useMemo, useState } from "react";
import { addBrand, listBrands } from "../api/client";
import { useAuth } from "../auth/AuthContext";

const OTHER_CATEGORY = "__other__";
const CATEGORIES = [
  "Beverages",
  "Food & Groceries",
  "Haircare",
  "Makeup & Cosmetics",
  "Personal Care",
  "Skincare",
  "Snacks & Confectionery",
];

export default function Brands() {
  const { token } = useAuth();
  const [brands, setBrands] = useState(null);
  const [form, setForm] = useState({ brand_name: "", category: "" });
  const [customCategory, setCustomCategory] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setBrands(await listBrands(token));
    } catch (err) {
      setError(err.message);
      setBrands([]);
    }
  }

  useEffect(() => {
    refresh();
  }, [token]);

  const groups = useMemo(() => {
    const term = search.trim().toLocaleLowerCase();
    const filtered = (brands || [])
      .filter((brand) => `${brand.brand_name} ${brand.category}`.toLocaleLowerCase().includes(term))
      .sort((a, b) =>
        a.category.localeCompare(b.category, undefined, { sensitivity: "base" }) ||
        a.brand_name.localeCompare(b.brand_name, undefined, { sensitivity: "base" })
      );

    return filtered.reduce((result, brand) => {
      (result[brand.category] ||= []).push(brand);
      return result;
    }, {});
  }, [brands, search]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const category = form.category === OTHER_CATEGORY ? customCategory.trim() : form.category;
    if (!category) {
      setError("Enter a category for this brand.");
      return;
    }
    if (brands?.some((brand) => brand.brand_name.trim().toLocaleLowerCase() === form.brand_name.trim().toLocaleLowerCase())) {
      setError("A brand with that name is already in your catalog.");
      return;
    }

    setBusy(true);
    try {
      await addBrand({ brand_name: form.brand_name.trim(), category }, token);
      setForm({ brand_name: "", category: "" });
      setCustomCategory("");
      setSuccess(`${form.brand_name.trim()} was added to your catalog.`);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const brandCount = brands?.length ?? 0;
  const visibleCount = Object.values(groups).reduce((sum, group) => sum + group.length, 0);

  return (
    <div className="brands-page">
      <div className="page-head">
        <div>
          <h1>Brand catalog</h1>
          <p>Keep your brands organized by category. Choose one from this catalog when creating an activation request.</p>
        </div>
        {brands && <span className="brand-count" aria-label={`${brandCount} brands`}>{brandCount} brands</span>}
      </div>

      <section className="panel" aria-labelledby="add-brand-heading">
        <h2 id="add-brand-heading">Add a brand</h2>
        <p className="helper-text">Add the brand name and the category it belongs to.</p>
        {error && <div className="error-box" role="alert">{error}</div>}
        {success && <div className="notice-box" role="status">{success}</div>}

        <form className="brand-form" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="brand_name">Brand name</label>
            <input
              id="brand_name"
              required
              maxLength={150}
              placeholder="e.g. GlowNest Studio"
              value={form.brand_name}
              onChange={(event) => setForm({ ...form, brand_name: event.target.value })}
            />
          </div>
          <div>
            <label htmlFor="category">Category</label>
            <select
              id="category"
              required
              value={form.category}
              onChange={(event) => setForm({ ...form, category: event.target.value })}
            >
              <option value="" disabled>Choose a category</option>
              {CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
              <option value={OTHER_CATEGORY}>Other / custom category</option>
            </select>
            {form.category === OTHER_CATEGORY && (
              <input
                aria-label="Custom category"
                required
                maxLength={80}
                placeholder="Type a category"
                value={customCategory}
                onChange={(event) => setCustomCategory(event.target.value)}
                style={{ marginTop: "0.55em" }}
              />
            )}
          </div>
          <button type="submit" disabled={busy}>
            {busy ? "Adding…" : "Add brand"}
          </button>
        </form>
      </section>

      {brands === null ? (
        <p className="loading" role="status">Loading your catalog…</p>
      ) : (
        <>
          <div className="brand-search">
            <label htmlFor="brand-search">Find a brand</label>
            <input
              id="brand-search"
              type="search"
              placeholder="Search brand names or categories"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <p className="helper-text">Showing {visibleCount} of {brandCount} brands, grouped by category.</p>
          </div>

          {brandCount === 0 ? (
            <div className="brand-empty">Your catalog is empty. Add your first brand above.</div>
          ) : visibleCount === 0 ? (
            <div className="brand-empty">No brands match “{search}”. Try another search.</div>
          ) : (
            <div className="brand-groups">
              {Object.entries(groups).map(([category, categoryBrands]) => (
                <section className="brand-group" key={category} aria-labelledby={`category-${category}`}>
                  <div className="brand-group-head">
                    <h2 id={`category-${category}`}>{category}</h2>
                    <span className="brand-count">{categoryBrands.length}</span>
                  </div>
                  <div className="brand-grid">
                    {categoryBrands.map((brand) => (
                      <article className="brand-card" key={brand.brand_id}>
                        <span className="brand-mark" aria-hidden="true">
                          {brand.brand_name.trim().charAt(0).toLocaleUpperCase()}
                        </span>
                        <div className="brand-card-copy">
                          <span className="title">{brand.brand_name}</span>
                          <span className="meta">Brand #{brand.brand_id}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
