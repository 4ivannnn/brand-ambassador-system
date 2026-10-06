"""Insert starter data: 1 approving manager, 1 store manager, 3 stores, 14 days of slots, 1 demo supplier.

    python -m scripts.seed
"""
from datetime import date, time, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Brand, Store, StoreSlot, Supplier, User
from app.security import hash_password

PASSWORD = "Password123!"          # demo only - change for anything real

SLOT_TIMES = [(time(9), time(12)), (time(12), time(15)), (time(15), time(18))]


def main():
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "manager@example.com")):
            print("Seed data already present - nothing to do.")
            return

        manager = User(role="APPROVING_MANAGER", full_name="Grace Approver", email="manager@example.com",
                       phone="0700000001", password_hash=hash_password(PASSWORD))
        store_mgr = User(role="STORE_MANAGER", full_name="Sam Storekeeper", email="storemanager@example.com",
                         phone="0700000002", password_hash=hash_password(PASSWORD))
        db.add_all([manager, store_mgr])
        db.flush()

        stores = [
            Store(store_name="Westlands Branch", location="Westlands, Nairobi", ambassador_limit=6,
                  manager_user_id=store_mgr.user_id),
            Store(store_name="Thika Road Branch", location="Thika Road, Nairobi", ambassador_limit=4,
                  manager_user_id=store_mgr.user_id),
            Store(store_name="Mombasa Road Branch", location="Mombasa Road, Nairobi", ambassador_limit=5,
                  manager_user_id=store_mgr.user_id),
        ]
        db.add_all(stores)
        db.flush()

        for store in stores:
            for offset in range(1, 15):
                for start, end in SLOT_TIMES:
                    db.add(StoreSlot(store_id=store.store_id, slot_date=date.today() + timedelta(days=offset),
                                     start_time=start, end_time=end, capacity=store.ambassador_limit))

        supplier = Supplier(company="Demo Beverages Ltd", contact="0712345678", email="supplier@example.com")
        db.add(supplier)
        db.flush()
        db.add(User(supplier_id=supplier.supplier_id, role="SUPPLIER", full_name="Demo Supplier",
                    email="supplier@example.com", phone="0712345678", password_hash=hash_password(PASSWORD)))
        db.add(Brand(supplier_id=supplier.supplier_id, brand_name="FizzUp", category="Beverages"))
        db.commit()

        print("Seed complete. Logins (password for all: %s):" % PASSWORD)
        print("  supplier@example.com       (SUPPLIER)")
        print("  manager@example.com        (APPROVING_MANAGER)")
        print("  storemanager@example.com   (STORE_MANAGER)")


if __name__ == "__main__":
    main()
