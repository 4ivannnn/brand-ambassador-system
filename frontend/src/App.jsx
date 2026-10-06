import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import RequireAuth from "./components/RequireAuth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import RequestsList from "./pages/RequestsList";
import NewRequest from "./pages/NewRequest";
import RequestDetail from "./pages/RequestDetail";
import Brands from "./pages/Brands";
import AuditTrail from "./pages/AuditTrail";
import Notifications from "./pages/Notifications";

function RedirectIfAuthed({ children }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/" replace /> : children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
          <Route path="/register" element={<RedirectIfAuthed><Register /></RedirectIfAuthed>} />

          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/" element={<RequestsList />} />
            <Route
              path="/requests/new"
              element={
                <RequireAuth roles={["SUPPLIER"]}>
                  <NewRequest />
                </RequireAuth>
              }
            />
            <Route path="/requests/:id" element={<RequestDetail />} />
            <Route
              path="/brands"
              element={
                <RequireAuth roles={["SUPPLIER"]}>
                  <Brands />
                </RequireAuth>
              }
            />
            <Route
              path="/audit-trail"
              element={
                <RequireAuth roles={["APPROVING_MANAGER"]}>
                  <AuditTrail />
                </RequireAuth>
              }
            />
            <Route path="/notifications" element={<Notifications />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
