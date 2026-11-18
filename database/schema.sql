-- =====================================================================
--  Automated Brand Ambassador Activation Request & Approval System
--  PostgreSQL schema  (implements the "DATABASE ERD" in Diagrams.docx)
--
--  Run once, against an empty database called brand_ambassador:
--      psql -U postgres -d brand_ambassador -f database/schema.sql
--
--  Changes made to the ERD (deliberate corrections, see README):
--    * users.password FLOAT      -> password_hash VARCHAR (never store passwords as numbers/plain text)
--    * stores.ambassador_limit STRING -> INTEGER (it is used in arithmetic comparisons)
--    * ambassadors.phone INT     -> VARCHAR (phone numbers start with 0 / +254)
--    * all primary/foreign keys  -> INTEGER identity (the ERD mixed STRING and INT)
--    * activation_requests       -> + activation_date, slot_id, status, date_submitted, flag_reason
--                                   (needed by the Class + State diagrams)
--    * ambassadors               -> + optional social-media metrics used by the ML model
--    * approvals                 -> + approver (user_id), reason, decided_at
--    * notifications             -> + created_at, is_read, channel
--    * NEW ai_assessments        -> stores the Qualification Engine output + feature snapshot
--    * NEW audit_logs            -> supports the "View audit trail" use case
-- =====================================================================

DROP TABLE IF EXISTS audit_logs, ai_assessments, notifications, approvals, ambassadors,
                     activation_requests, store_slots, stores, brands, users, suppliers CASCADE;

-- ---------------------------------------------------------------- suppliers
CREATE TABLE suppliers (
    supplier_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company      VARCHAR(150) NOT NULL,
    contact      VARCHAR(20)  NOT NULL,
    email        VARCHAR(255) NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- -------------------------------------------------------------------- users
-- One table for every login: suppliers' staff, the approving manager, store managers.
CREATE TABLE users (
    user_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id    INTEGER REFERENCES suppliers(supplier_id) ON DELETE CASCADE,  -- only for SUPPLIER users
    role           VARCHAR(20)  NOT NULL
                   CHECK (role IN ('SUPPLIER', 'APPROVING_MANAGER', 'STORE_MANAGER')),
    full_name      VARCHAR(150) NOT NULL,
    email          VARCHAR(255) NOT NULL UNIQUE,      -- also the login name
    phone          VARCHAR(20),
    gender         VARCHAR(10) CHECK (gender IS NULL OR gender IN ('MALE', 'FEMALE')),
    password_hash  VARCHAR(255) NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CHECK ((role = 'SUPPLIER') = (supplier_id IS NOT NULL))
);

-- ------------------------------------------------------------------- brands
CREATE TABLE brands (
    brand_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id  INTEGER      NOT NULL REFERENCES suppliers(supplier_id) ON DELETE CASCADE,
    brand_name   VARCHAR(150) NOT NULL,
    category     VARCHAR(80)  NOT NULL,
    UNIQUE (supplier_id, brand_name)
);

-- ------------------------------------------------------------------- stores
CREATE TABLE stores (
    store_id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_name        VARCHAR(150) NOT NULL,
    location          VARCHAR(200) NOT NULL,
    ambassador_limit  INTEGER      NOT NULL CHECK (ambassador_limit > 0),
    manager_user_id   INTEGER REFERENCES users(user_id) ON DELETE SET NULL  -- store manager to notify
);

-- -------------------------------------------------------------- store_slots
CREATE TABLE store_slots (
    slot_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id    INTEGER     NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    slot_date   DATE        NOT NULL,
    start_time  TIME        NOT NULL,
    end_time    TIME        NOT NULL,
    capacity    INTEGER     NOT NULL CHECK (capacity > 0),
    status      VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'FULL', 'BLOCKED')),
    CHECK (end_time > start_time),
    UNIQUE (store_id, slot_date, start_time, end_time)
);

-- ------------------------------------------------------- activation_requests
CREATE TABLE activation_requests (
    request_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id       INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    brand_id          INTEGER NOT NULL REFERENCES brands(brand_id),
    store_id          INTEGER NOT NULL REFERENCES stores(store_id),
    slot_id           INTEGER NOT NULL REFERENCES store_slots(slot_id),
    activation_date   DATE    NOT NULL,
    start_time        TIME    NOT NULL,
    end_time          TIME    NOT NULL,
    ambassador_count  INTEGER NOT NULL CHECK (ambassador_count > 0),
    status            VARCHAR(20) NOT NULL DEFAULT 'DRAFT'
                      CHECK (status IN ('DRAFT', 'SUBMITTED', 'UNDER_VALIDATION', 'FLAGGED_FOR_REVIEW',
                                        'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SLOT_BOOKED', 'COMPLETED')),
    flag_reason       TEXT,
    date_submitted    TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (end_time > start_time)
);
CREATE INDEX ix_requests_store_date ON activation_requests (store_id, activation_date, status);
CREATE INDEX ix_requests_supplier   ON activation_requests (supplier_id, status);

-- --------------------------------------------------------------- ambassadors
CREATE TABLE ambassadors (
    ambassador_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id        INTEGER      NOT NULL REFERENCES activation_requests(request_id) ON DELETE CASCADE,
    full_name         VARCHAR(150) NOT NULL,
    phone             VARCHAR(20)  NOT NULL,
    email             VARCHAR(255),
    social_handle     VARCHAR(100),            -- optional, used by the ML model
    followers         INTEGER CHECK (followers >= 0),
    engagement_rate   NUMERIC(6,4) CHECK (engagement_rate >= 0),   -- fraction: 0.0350 = 3.5 %
    account_age_days  INTEGER CHECK (account_age_days >= 0)
);
CREATE INDEX ix_amb_phone ON ambassadors (phone);
CREATE INDEX ix_amb_email ON ambassadors (email);

-- ----------------------------------------------------------------- approvals
CREATE TABLE approvals (
    approval_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id   INTEGER     NOT NULL REFERENCES activation_requests(request_id) ON DELETE CASCADE,
    user_id      INTEGER     NOT NULL REFERENCES users(user_id),      -- the approving manager
    decision     VARCHAR(10) NOT NULL CHECK (decision IN ('APPROVED', 'REJECTED', 'OVERRIDE')),
    reason       TEXT,
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (decision <> 'REJECTED' OR reason IS NOT NULL)              -- a rejection must be explained
);

-- ------------------------------------------------------------ notifications
CREATE TABLE notifications (
    notification_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id       INTEGER REFERENCES activation_requests(request_id) ON DELETE CASCADE,
    user_id          INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,   -- recipient
    message          TEXT    NOT NULL,
    channel          VARCHAR(10) NOT NULL DEFAULT 'DASHBOARD' CHECK (channel IN ('DASHBOARD', 'EMAIL')),
    is_read          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_notif_user ON notifications (user_id, is_read);

-- ---------------------------------------------------------- ai_assessments
CREATE TABLE ai_assessments (
    assessment_id       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id          INTEGER      NOT NULL REFERENCES activation_requests(request_id) ON DELETE CASCADE,
    model_version       VARCHAR(50)  NOT NULL,
    authenticity_score  NUMERIC(5,4) NOT NULL,
    fraud_probability   NUMERIC(5,4) NOT NULL,
    fit_score           NUMERIC(5,4) NOT NULL,
    confidence          NUMERIC(5,4) NOT NULL,
    recommendation      VARCHAR(20)  NOT NULL,
    feedback            JSONB        NOT NULL DEFAULT '[]',   -- list of plain-language reasons
    features            JSONB,                                -- snapshot used later for retraining
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- --------------------------------------------------------------- audit_logs
CREATE TABLE audit_logs (
    audit_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id   INTEGER REFERENCES activation_requests(request_id) ON DELETE SET NULL,
    user_id      INTEGER REFERENCES users(user_id) ON DELETE SET NULL,   -- NULL = done by the system
    action       VARCHAR(50) NOT NULL,
    from_status  VARCHAR(20),
    to_status    VARCHAR(20),
    detail       TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_request ON audit_logs (request_id, created_at);

-- Keep updated_at fresh automatically
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_requests_updated BEFORE UPDATE ON activation_requests
FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

-- Handy reporting view for the manager dashboard ("pending requests", "performance dashboards")
CREATE OR REPLACE VIEW v_request_overview AS
SELECT r.request_id, r.status, r.date_submitted, r.activation_date, r.start_time, r.end_time,
       r.ambassador_count, s.company, b.brand_name, b.category, st.store_name,
       a.fit_score, a.fraud_probability, a.recommendation
FROM activation_requests r
JOIN suppliers s  ON s.supplier_id = r.supplier_id
JOIN brands b     ON b.brand_id    = r.brand_id
JOIN stores st    ON st.store_id   = r.store_id
LEFT JOIN LATERAL (SELECT * FROM ai_assessments x WHERE x.request_id = r.request_id
                   ORDER BY x.created_at DESC LIMIT 1) a ON TRUE;
