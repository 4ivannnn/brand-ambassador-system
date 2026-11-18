import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "aba.session"; // { token, role }
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else localStorage.removeItem(STORAGE_KEY);
  }, [session]);

  const value = useMemo(
    () => ({
      token: session?.token || null,
      role: session?.role || null,
      gender: session?.gender || null,
      supplierInviteCode: session?.supplierInviteCode || null,
      isAuthenticated: Boolean(session?.token),
      signIn: ({ access_token, role, gender, supplier_invite_code }) => setSession({ token: access_token, role, gender: gender || null, supplierInviteCode: supplier_invite_code || null }),
      updateGender: (gender) => setSession((current) => current ? { ...current, gender } : current),
      clearSupplierInviteCode: () => setSession((current) => current ? { ...current, supplierInviteCode: null } : current),
      signOut: () => setSession(null),
    }),
    [session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export const ROLE_LABEL = {
  SUPPLIER: "Supplier",
  APPROVING_MANAGER: "Approving manager",
  STORE_MANAGER: "Store manager",
};
