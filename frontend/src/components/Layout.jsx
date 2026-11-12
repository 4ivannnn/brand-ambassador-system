import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { ROLE_LABEL, useAuth } from "../auth/AuthContext";

const NAV = {
  SUPPLIER: [
    { to: "/", label: "Requests", end: true },
    { to: "/requests/new", label: "New request" },
    { to: "/brands", label: "Brands" },
    { to: "/notifications", label: "Notifications" },
  ],
  APPROVING_MANAGER: [
    { to: "/", label: "Requests", end: true },
    { to: "/audit-trail", label: "Audit trail" },
    { to: "/notifications", label: "Notifications" },
  ],
  STORE_MANAGER: [
    { to: "/", label: "Activation history", end: true },
    { to: "/notifications", label: "Notifications" },
  ],
};

export default function Layout() {
  const { role, signOut } = useAuth();
  const navigate = useNavigate();
  const items = NAV[role] || [];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          Activation Desk
          <span>BRAND AMBASSADOR APPROVALS</span>
        </div>
        <nav>
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="role-chip">
          Signed in as
          <strong>{ROLE_LABEL[role] || role}</strong>
          <button
            onClick={() => {
              signOut();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
