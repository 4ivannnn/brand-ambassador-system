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

import httpx

BASE = "http://127.0.0.1:8000"
PASSWORD = "Password123!"
c = httpx.Client(base_url=BASE, timeout=30)


def show(title, resp):
    print(f"\n--- {title}  [HTTP {resp.status_code}]")
    print(json.dumps(resp.json(), indent=2, default=str)[:1500])


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
slots = c.get(f"/stores/{stores[0]['store_id']}/slots", headers=supplier).json()
slot = random.choice(slots[:30])
brand = c.get("/brands", headers=supplier).json()[0]

# A ----------------------------------------------------------------------------------
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": slot["slot_id"],
                                                "ambassador_count": 2, "ambassadors": ambassadors(2, "Ok")})
show("A1 create draft", r)
req_id = r.json()["request_id"]
show("A2 submit", c.post(f"/requests/{req_id}/submit", headers=supplier))
show("A3 manager approves", c.post(f"/requests/{req_id}/decision", headers=manager,
                                   json={"decision": "APPROVE", "reason": "Looks good"}))

# B ----------------------------------------------------------------------------------
email = f"rival{uuid.uuid4().hex[:6]}@rival.com"
tok = c.post("/auth/register", json={"company": "Rival Drinks Ltd", "contact": "0722000000", "email": email,
                                     "full_name": "Rival Rep", "password": PASSWORD}).json()
rival = {"Authorization": f"Bearer {tok['access_token']}"}
rb = c.post("/brands", headers=rival, json={"brand_name": "SplashCo", "category": "Beverages"}).json()
r = c.post("/requests", headers=rival, json={"brand_id": rb["brand_id"], "slot_id": slot["slot_id"],
                                             "ambassador_count": 1, "ambassadors": ambassadors(1, "Rv")})
show("B submit competing brand (same slot)", c.post(f"/requests/{r.json()['request_id']}/submit", headers=rival))

# C ----------------------------------------------------------------------------------
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": slots[31]["slot_id"],
                                                "ambassador_count": 3, "ambassadors": ambassadors(2, "Bad")})
show("C submit with count mismatch", c.post(f"/requests/{r.json()['request_id']}/submit", headers=supplier))

# D ----------------------------------------------------------------------------------
shady = ambassadors(3, "Fk", followers=400_000, engagement_rate=0.002, account_age_days=15)
shady[1]["phone"] = shady[0]["phone"]
r = c.post("/requests", headers=supplier, json={"brand_id": brand["brand_id"], "slot_id": slots[40]["slot_id"],
                                                "ambassador_count": 3, "ambassadors": shady})
show("D submit suspicious request", c.post(f"/requests/{r.json()['request_id']}/submit", headers=supplier))

show("Audit trail (manager)", c.get("/audit-trail", headers=manager))
show("Manager notifications", c.get("/notifications", headers=manager))
