# Activation Desk — front-end

React (Vite) front-end for the Automated Brand Ambassador Activation Request &
Approval System. Talks to the FastAPI back-end over its REST API — nothing
here touches the database directly.

Three screens adapt to whoever is logged in:
* **Supplier** — register, add brands, submit a request (pick a store slot,
  list ambassadors), track status, see why something was flagged.
* **Approving manager** — review pending/flagged requests, see the
  qualification engine's scores and feedback, approve/reject/override, read
  the audit trail.
* **Store manager** — see upcoming activations booked into their store.

## Complete demo

From the project root, `docker compose up --build` starts the database, API, sample data, trained
model, and this app together. Open http://localhost:5173 and sign in with a seeded demo account
(password `Password123!`).

For local frontend development, first start the API from the project root. Run
`python -m scripts.bootstrap` once to create the tables, seed the accounts and train the model;
then start `uvicorn app.main:app --reload`. In this folder, run `npm install` and `npm run dev`.
The default `VITE_API_URL` connects the browser to `http://localhost:8000`.

## Set up in Visual Studio Code

1. Install **Node.js 18+** (https://nodejs.org) if you don't have it —
   `node --version` in a terminal should print 18 or higher.
2. Make sure the back-end from the other project is already running (see its
   own README) at `http://localhost:8000`, with `python -m scripts.bootstrap` run
   at least once.
3. Open this `frontend` folder in VS Code (*File ▸ Open Folder…*).
4. Open a terminal (`` Ctrl+` ``) and install packages:
   ```bash
   npm install
   ```
5. Copy `.env.example` to `.env`. The default `VITE_API_URL` already points
   at `http://localhost:8000`, so you only need to change it if your API
   runs somewhere else.
6. Start the dev server:
   ```bash
   npm run dev
   ```
   Open the printed address (usually http://127.0.0.1:5173).
7. Log in with one of the seeded accounts (password `Password123!`):
   `supplier@example.com`, `manager@example.com`, `storemanager@example.com`
   — or register a new supplier from the login screen.

### Recommended VS Code extensions
*ES7+ React/Redux/React-Native snippets* and *Prettier* (not required, just
convenient). No extensions are needed to run the app.

## Project layout
```
src/
  api/client.js          one function per back-end endpoint
  auth/AuthContext.jsx   stores the login token + role in localStorage
  components/            Layout (sidebar/nav), StatusBadge, RequireAuth (route guard)
  pages/                 one file per screen
  styles.css             design tokens + all styling (plain CSS, no framework)
```

## Notes
* There's no build step beyond Vite's defaults. `npm run build` produces a
  static `dist/` folder you can deploy anywhere that serves static files.
* The API client throws `ApiError` with the back-end's error message and
  (for validation/conflict errors) a `details` array — see how
  `RequestDetail.jsx` displays that list.
* If you change a response shape in the FastAPI app, `src/api/client.js` is
  the only file you should need to touch to match it.
