import { useEffect, useState } from "react";
import { listNotifications, markNotificationRead } from "../api/client";
import { useAuth } from "../auth/AuthContext";

function fmt(ts) {
  return new Date(ts).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function Notifications() {
  const { token } = useAuth();
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");

  function refresh() {
    listNotifications(token).then(setItems).catch((e) => setError(e.message));
  }

  useEffect(refresh, [token]);

  async function handleRead(id) {
    try {
      await markNotificationRead(id, token);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Notifications</h1>
          <p>Updates about requests you're involved in.</p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {!items && !error && <p className="loading">Loading…</p>}
      {items && items.length === 0 && <p className="empty-state">You're all caught up.</p>}

      {items && items.length > 0 && (
        <div>
          {items.map((n) => (
            <div key={n.notification_id} className={`notif-row ${n.is_read ? "" : "unread"}`}>
              <div>
                <div className="msg">{n.message}</div>
                <div className="meta ts">{fmt(n.created_at)}</div>
              </div>
              {!n.is_read && (
                <button className="secondary" onClick={() => handleRead(n.notification_id)}>Mark read</button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
