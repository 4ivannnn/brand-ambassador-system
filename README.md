# Automated Brand Ambassador Activation Request & Approval System
Database + back-end + machine-learning code for Malachi Ivan's proposal (133207), built from the
class, use-case, sequence, state, activity and database-ERD diagrams.

## Run the complete demo with Docker

With Docker Desktop running, open a terminal in this project and run:

```sh
docker compose up --build
```

On its first run this starts PostgreSQL, creates the schema and reporting view, adds demo stores,
slots, accounts and a sample brand, trains the qualification model, then starts the API and React
app. Open **http://localhost:5173**; the interactive API documentation is at
**http://localhost:8000/docs**. Sign in using any of these demo accounts (password
`Password123!`): `supplier@example.com`, `manager@example.com`, `storemanager@example.com`.

Stop the demo with `Ctrl+C`. Keep the database between runs with `docker compose down`; to erase
the database and initialize a clean demo from scratch, use `docker compose down -v`.

To walk through the API flow from another terminal after startup, run
`python -m scripts.demo_flow` in an environment with the project dependencies installed.

The Compose credentials and secret are for local demonstration only. Change them before deploying
anywhere accessible to other people. Docker is optional; the manual setup below remains available.

**Stack (from proposal §3.4):** PostgreSQL · SQLAlchemy · Python/FastAPI back-end · scikit-learn ML.
The React front-end lives in `frontend/` and calls the REST API below.

---------------------------------------------------------------------------------------------------
## 1. Where each diagram lives in the code

| Diagram | Implemented in |
|---|---|
| Database ERD | `database/schema.sql` (PostgreSQL) and `app/models.py` (SQLAlchemy) |
| Class diagram | `app/models.py` (Supplier, Product→Brand, Store, ActivationRequest, Ambassador, Notification, Approving Manager→User) and `app/ml/qualification_engine.py` (Qualification Engine) |
| State diagram | `app/state_machine.py` |
| Sequence + Activity diagrams | `app/services/workflow.py` (`submit_request`, `decide`, `override_flag`, `complete`) |
| Use-case diagram | `app/main.py` endpoints (Register, Submit Request, Register Ambassadors, Select Time Slot, Approve Request, View audit trail, Prevent store conflict, Notify) |
| Validation & conflict rules (proposal §1.3.2) | `app/rules.py` |
| AI/ML (proposal §2.5, §3.5) | `app/ml/features.py`, `app/ml/train.py`, `app/ml/qualification_engine.py` |

---------------------------------------------------------------------------------------------------
## 2. Set it up in Visual Studio Code

### Prerequisites (install once)
1. **VS Code** – https://code.visualstudio.com
2. **Python 3.10+** – https://www.python.org/downloads (Windows: tick *"Add Python to PATH"*)
3. **PostgreSQL 14+** – https://www.postgresql.org/download (remember the `postgres` password you set)
   *— or, if you use Docker Desktop, skip this and run `docker compose up -d db` in step 6.*

### Step by step
1. **Open the project:** VS Code → *File ▸ Open Folder…* → choose `brand-ambassador-system`.
   Accept the popup *"Do you want to install the recommended extensions?"* (Python, Pylance, SQLTools + PostgreSQL driver).
2. **Open a terminal:** *Terminal ▸ New Terminal* (`Ctrl+\``).
3. **Create a virtual environment and install packages**

   Windows (PowerShell):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   pip install -r requirements.txt
   ```
   macOS / Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Select the interpreter:** `Ctrl+Shift+P` → *Python: Select Interpreter* → pick the one inside `.venv`.
5. **Create your settings file:** copy `.env.example` to `.env` and put your real PostgreSQL password in
   `DATABASE_URL` (`postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/brand_ambassador`).
6. **Create the database**
   * Docker: `docker compose up -d db` (database `brand_ambassador` is created for you), **or**
   * Installed PostgreSQL: `psql -U postgres -c "CREATE DATABASE brand_ambassador;"`
     (if `psql` is not found, add PostgreSQL's `bin` folder to PATH, or create the database in pgAdmin.)
7. **Create the tables** if you use an installed PostgreSQL server:
   `psql -U postgres -d brand_ambassador -f database/schema.sql`. Docker creates the schema
   automatically when it initializes a new database volume.
8. **Prepare the demo** (starter data and trained model):
   `python -m scripts.bootstrap`. You can run this again safely.
   The request calendar maintains daily slots from two years ago through two years ahead. Historical dates remain visible for reference but cannot be booked.
   Supplier registration requires a Male/Female gender selection. Existing supplier accounts without a saved selection are prompted to complete their profile after signing in.
9. **Start the API:** press **F5** and choose *"API: run FastAPI (debug)"*
    (or run `uvicorn app.main:app --reload`). Open http://127.0.0.1:8000/docs
10. **Try the whole workflow** in a second terminal: `python -m scripts.demo_flow`
    — or use the `/docs` page: `POST /auth/login` → copy `access_token` → click **Authorize** → try endpoints.
11. **Run the tests:** `pytest` (rules, state machine and ML need no database).

To start the local API after PostgreSQL is listening on `localhost:5432`, run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-backend.ps1` in PowerShell.
It checks the database connection, prepares demo data and the qualification model, then starts the
API at `http://127.0.0.1:8000`. Edit `.env` if your
PostgreSQL credentials differ. For a locally installed server, initialize its schema once using
`database/schema.sql`.

Seed logins (password `Password123!`): `supplier@example.com`, `manager@example.com`, `storemanager@example.com`.

### Inspect the data in VS Code
SQLTools sidebar → *brand_ambassador (local)* → Tables. Useful queries:
```sql
SELECT * FROM v_request_overview ORDER BY request_id DESC;   -- manager dashboard view
SELECT * FROM audit_logs ORDER BY created_at DESC;           -- audit trail
SELECT request_id, fraud_probability, fit_score, recommendation, feedback FROM ai_assessments;
```

---------------------------------------------------------------------------------------------------
## 3. How a request flows (matches the diagrams)
1. Supplier registers, adds a brand, picks a slot and lists ambassadors → `POST /requests` (status **DRAFT**).
2. `POST /requests/{id}/submit`
   * missing/invalid data (required fields, phone/e-mail format, ambassador count ≠ names listed, today or past date) → **422** with the list of errors; request stays a draft;
   * otherwise **SUBMITTED → UNDER_VALIDATION**; the Qualification Engine scores authenticity, fraud risk and fit;
   * store-limit and competing-brand checks run; a conflict or a confident fraud signal → **FLAGGED_FOR_REVIEW** (with reasons and, for conflicts, alternative slots); otherwise **PENDING_APPROVAL**.
3. Approving manager: `POST /requests/{id}/decision` (`APPROVE` / `REJECT` + mandatory reason), or `/override` for a flagged request.
   Approval re-checks conflicts under a row lock, then **APPROVED → SLOT_BOOKED** and notifies the supplier and the store manager.
4. After the activation date: `POST /requests/{id}/complete` → **COMPLETED**.
Every step is written to `audit_logs`; every message to `notifications` (plus e-mail if SMTP is configured).

Store managers can view approved, completed, and rejected requests for stores assigned to them from the **Activation history** page. Requests at draft or pending-review stages are not shown there.

## 4. The machine-learning part
* **Fraud / authenticity model** (RandomForest) → `detect_fraud()` / `check_authenticity()`: duplicate or reused contacts, repeated submissions, fake-looking follower/engagement figures, very new accounts, supplier history.
* **Approval-fit model** (GradientBoosting) → `score_fit()`: how likely the manager is to approve (load vs store limit, completeness, category history at that store, lead time, supplier record).
* `generate_feedback()` turns the signals into plain-language reasons, so suppliers are told why (a gap the proposal identifies).
* Routing uses `CONFIDENCE_THRESHOLD` / `FRAUD_FLAG_THRESHOLD` (in `.env`); anything the AI is unsure about goes to a human.
* **Important:** with no real history yet, training uses *synthetic* data (`generate_synthetic_data`). The printed metrics prove the pipeline works, **not** real-world accuracy. Once managers have decided at least ~200 real requests, run `python -m app.ml.train --from-db` to retrain the approval-fit model from real decisions (the exact features of each request are stored in `ai_assessments.features`). Do the accuracy test from proposal §3.2.5 (compare with human-reviewed requests) on real data.

## 5. Deliberate corrections to the ERD
| ERD | Change | Why |
|---|---|---|
| `users.password : FLOAT` | `password_hash VARCHAR` | passwords must be stored as salted hashes |
| `stores.ambassador_limit : STRING` | `INTEGER` | compared numerically |
| `ambassadors.phone : INT` | `VARCHAR(20)` | leading 0 / `+254` would be lost |
| mixed STRING / INT keys | all `INTEGER` identity keys | consistent joins |
| `activation_requests` had no date/status | added `activation_date`, `slot_id`, `status`, `date_submitted`, `flag_reason` | needed by the class and state diagrams |
| — | new `ai_assessments`, `audit_logs`; extra columns on `ambassadors`, `approvals`, `notifications`, `stores.manager_user_id` | ML output, audit-trail use case, social-media metrics, who approved, who to notify |

Note: the proposal §3.4 lists JavaScript as the language but also SQLAlchemy, which is a Python library.
This code uses Python for the back-end (and ML); the React front-end can stay in JavaScript.

## 6. Troubleshooting
* `ModuleNotFoundError: app` → run commands from the project root folder, with `python -m …` as shown.
* `password authentication failed` → the password in `.env` differs from your PostgreSQL password.
* `database "brand_ambassador" does not exist` → repeat step 6.
* `503 … model is not trained yet` → run step 9, then restart the API.
* `relation "users" does not exist` → repeat step 7.
