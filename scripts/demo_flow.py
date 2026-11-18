"""End-to-end demo against the RUNNING API (start uvicorn first, and run seed + train first).

    python -m scripts.demo_flow

It walks through the diagrams' scenarios and prints what happened at each step:
  A. valid request        -> AI checks pass -> manager approves -> slot booked
  B. competing brand      -> same store/time, same category, other supplier -> FLAGGED + alternatives
  C. invalid request      -> ambassador count mismatch -> 422 error list (request stays a draft)
  D. suspicious request   -> fake-looking followers, reused contact -> AI flags it
"""
import json
import random
import uuid
from datetime import date, timedelta

import httpx

from app.booking_calendar import booking_window

BASE = "http://127.0.0.1:8000"
PASSWORD = "Password123!"
c = httpx.Client(base_url=BASE, timeout=30)


def show(title, resp):
    print(f"\n--- {title}  [HTTP {resp.status_code}]")
    print(json.dumps(resp.json(), indent=2, default=str)[:1500])


def expect(resp, status_code, title):
    if resp.status_code != status_code:
        show(f"{title} (unexpected response)", resp)
        raise RuntimeError(f"{title}: expected HTTP {status_code}, got {resp.status_code}")
    return resp.json()


def login(email, password=PASSWORD):
    r = c.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ambassadors(n, prefix, **extra):
    return [{"full_name": f"{prefix} Ambassador {i}", "phone": f"07{random.randint(10000000, 99999999)}",
             "email": f"{prefix.lower()}{i}{uuid.uuid4().hex[:4]}@mail.com", "followers": 8000,
             "engagement_rate": 0.04, "account_age_days": 900, **extra} for i in range(1, n + 1)]


supplier = login("supplier@example.com")
manager = login("manager@example.com")

stores = c.get("/stores", headers=supplier).json()
brands = c.get("/brands", headers=supplier).json()
brand = next((b for b in brands if b["category"].lower() == "beverages"), brands[0])
today = date.today()
_, two_years_out = booking_window(today)
slot_window = {"start_date": (today + timedelta(days=1)).isoformat(),
               "end_date": two_years_out.isoformat()}
all_slots = []
for store in stores:
    all_slots.extend(c.get(f"/stores/{store['store_id']}/slots", headers=supplier,
                           params=slot_window).json())

active = c.get("/requests", headers=manager).json()
active = [r for r in active if r["status"] in {"PENDING_APPROVAL", "APPROVED", "SLOT_BOOKED"}]


def free_slot(exclude=()):
    excluded = set(exclude)
    for candidate in all_slots:
        if candidate["slot_id"] in excluded:
            continue
        overlaps = [r for r in active if r["store_id"] == candidate["store_id"]
                    and r["activation_date"] == candidate["slot_date"]
                    and r["start_time"] < candidate["end_time"]
                    and r["end_time"] > candidate["start_time"]]
        if not overlaps:
            return candidate
    raise RuntimeError("No unbooked future store slots are available for the demo flow.")


slot = free_slot()

# A ----------------------------------------------------------------------------------
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": slot["slot_id"],
                                                "ambassador_count": 2, "ambassadors": ambassadors(2, "Ok")})
req = expect(r, 201, "A1 create draft")
show("A1 create draft", r)
req_id = req["request_id"]
r = c.post(f"/requests/{req_id}/submit", headers=supplier)
submitted = expect(r, 200, "A2 submit")
show("A2 submit", r)
if submitted["status"] != "PENDING_APPROVAL":
    raise RuntimeError(f"A2 expected PENDING_APPROVAL, got {submitted['status']}")
r = c.post(f"/requests/{req_id}/decision", headers=manager,
           json={"decision": "APPROVE", "reason": "Looks good"})
approved = expect(r, 200, "A3 manager approves")
show("A3 manager approves", r)
if approved["status"] != "SLOT_BOOKED":
    raise RuntimeError(f"A3 expected SLOT_BOOKED, got {approved['status']}")
active.append({**req, "status": "SLOT_BOOKED"})

# B ----------------------------------------------------------------------------------
email = f"rival{uuid.uuid4().hex[:6]}@rival.com"
tok = c.post("/auth/register", json={"company": "Rival Drinks Ltd", "contact": "0722000000", "email": email,
                                     "full_name": "Rival Rep", "gender": "MALE",
                                     "password": PASSWORD}).json()
rival = {"Authorization": f"Bearer {tok['access_token']}"}
r = c.post("/brands", headers=rival, json={"brand_name": "SplashCo", "category": brand["category"]})
rb = expect(r, 201, "B0 create rival brand")
r = c.post("/requests", headers=rival, json={"brand_id": rb["brand_id"], "slot_id": slot["slot_id"],
                                             "ambassador_count": 1, "ambassadors": ambassadors(1, "Rv")})
req = expect(r, 201, "B1 create competing request")
r = c.post(f"/requests/{req['request_id']}/submit", headers=rival)
result = expect(r, 200, "B2 submit competing brand")
show("B submit competing brand (same slot)", r)
if result["status"] != "FLAGGED_FOR_REVIEW" or not any("Competing brand conflict" in p for p in result["problems"]):
    raise RuntimeError("B2 did not flag the same-category competing brand conflict.")

# C ----------------------------------------------------------------------------------
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": free_slot()["slot_id"],
                                                "ambassador_count": 3, "ambassadors": ambassadors(2, "Bad")})
req = expect(r, 201, "C1 create invalid request")
r = c.post(f"/requests/{req['request_id']}/submit", headers=supplier)
expect(r, 422, "C2 submit count mismatch")
show("C submit with count mismatch", r)

# D ----------------------------------------------------------------------------------
shady = ambassadors(3, "Fk", followers=400_000, engagement_rate=0.002, account_age_days=15)
shady[1]["phone"] = shady[0]["phone"]
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": free_slot()["slot_id"],
                                                "ambassador_count": 3, "ambassadors": shady})
req = expect(r, 201, "D1 create suspicious request")
r = c.post(f"/requests/{req['request_id']}/submit", headers=supplier)
result = expect(r, 200, "D2 submit suspicious request")
show("D submit suspicious request", r)
if result["status"] != "FLAGGED_FOR_REVIEW":
    raise RuntimeError(f"D2 expected FLAGGED_FOR_REVIEW, got {result['status']}")

# E ----------------------------------------------------------------------------------
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"],
                                                "slot_id": free_slot()["slot_id"],
                                                "ambassador_count": 1, "ambassadors": ambassadors(1, "No")})
req = expect(r, 201, "E1 create request for rejection")
r = c.post(f"/requests/{req['request_id']}/submit", headers=supplier)
submitted = expect(r, 200, "E2 submit request for rejection")
if submitted["status"] not in {"PENDING_APPROVAL", "FLAGGED_FOR_REVIEW"}:
    raise RuntimeError(f"E2 unexpected pre-decision status: {submitted['status']}")
r = c.post(f"/requests/{req['request_id']}/decision", headers=manager,
           json={"decision": "REJECT", "reason": "Demo rejection for store history."})
rejected = expect(r, 200, "E3 manager rejects request")
if rejected["status"] != "REJECTED":
    raise RuntimeError(f"E3 expected REJECTED, got {rejected['status']}")
store_manager = login("storemanager@example.com")
history = expect(c.get("/requests", headers=store_manager), 200, "E4 store manager views history")
history_by_id = {item["request_id"]: item for item in history}
if history_by_id.get(req["request_id"], {}).get("status") != "REJECTED":
    raise RuntimeError("Store manager history did not include the denied request.")
if history_by_id.get(req_id, {}).get("status") != "SLOT_BOOKED":
    raise RuntimeError("Store manager history did not include the approved activation.")
print("\nStore manager history includes approved and denied decisions.")

r = c.get("/audit-trail", headers=manager)
expect(r, 200, "Audit trail")
show("Audit trail (manager)", r)
r = c.get("/notifications", headers=manager)
expect(r, 200, "Manager notifications")
show("Manager notifications", r)
print("\nAll end-to-end demo scenarios passed.")
