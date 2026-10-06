/**
 * Thin wrapper around fetch for the FastAPI back-end in app/main.py.
 * Every function here maps 1:1 to one endpoint, so this file is the
 * single place to look if an endpoint's URL or payload shape changes.
 */
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.status = status;
    this.details = details || [];
  }
}

async function request(path, { method = "GET", body, token, params } = {}) {
  const url = new URL(BASE_URL + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }

  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;

  if (!res.ok) {
    throw new ApiError(data?.detail || `Request failed (${res.status})`, res.status, data?.errors);
  }
  return data;
}

// ---- auth ------------------------------------------------------------
export const register = (body) => request("/auth/register", { method: "POST", body });
export const login = (body) => request("/auth/login", { method: "POST", body });

// ---- reference data ----------------------------------------------------
export const listStores = (token) => request("/stores", { token });
export const listSlots = (storeId, token, onlyOpen = true) =>
  request(`/stores/${storeId}/slots`, { token, params: { only_open: onlyOpen } });

export const listBrands = (token) => request("/brands", { token });
export const addBrand = (body, token) => request("/brands", { method: "POST", body, token });

// ---- requests ------------------------------------------------------------
export const createRequest = (body, token) => request("/requests", { method: "POST", body, token });
export const submitRequest = (id, token) => request(`/requests/${id}/submit`, { method: "POST", token });
export const listRequests = (token, status) => request("/requests", { token, params: { status } });
export const getRequest = (id, token) => request(`/requests/${id}`, { token });

export const decide = (id, body, token) =>
  request(`/requests/${id}/decision`, { method: "POST", body, token });
export const overrideFlag = (id, body, token) =>
  request(`/requests/${id}/override`, { method: "POST", body, token });
export const completeRequest = (id, token) =>
  request(`/requests/${id}/complete`, { method: "POST", token });

// ---- audit + notifications -----------------------------------------------
export const auditTrail = (token, requestId) =>
  request("/audit-trail", { token, params: { request_id: requestId } });

export const listNotifications = (token, unreadOnly = false) =>
  request("/notifications", { token, params: { unread_only: unreadOnly } });
export const markNotificationRead = (id, token) =>
  request(`/notifications/${id}/read`, { method: "POST", token });
