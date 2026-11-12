"""Insert starter data and maintain a four-year booking calendar.

    python -m scripts.seed
"""
from datetime import date, time, timedelta

from sqlalchemy import select

from app.booking_calendar import booking_window
from app.database import SessionLocal
from app.models import ActivationRequest, Brand, Store, StoreSlot, Supplier, User
from app.security import hash_password

PASSWORD = "Password123!"          # demo only - change for anything real

SLOT_TIMES = [(time(9), time(12)), (time(12), time(15)), (time(15), time(18))]


def ensure_calendar_slots(db, stores, today: date | None = None) -> int:
    today = today or date.today()
    first_day, last_day = booking_window(today)
    existing = db.scalars(select(StoreSlot).where(
        StoreSlot.slot_date >= first_day,
        StoreSlot.slot_date <= last_day,
    )).all()
    existing_keys = {(slot.store_id, slot.slot_date, slot.start_time, slot.end_time) for slot in existing}
    new_slots = []
    for store in stores:
        for day_offset in range((last_day - first_day).days + 1):
            slot_date = first_day + timedelta(days=day_offset)
            for start, end in SLOT_TIMES:
                key = (store.store_id, slot_date, start, end)
                if key not in existing_keys:
                    new_slots.append(StoreSlot(store_id=store.store_id, slot_date=slot_date,
                                               start_time=start, end_time=end,
                                               capacity=store.ambassador_limit))
    db.add_all(new_slots)
    return len(new_slots)


def main():
    with SessionLocal() as db:
        existing_manager = db.scalar(select(User).where(User.email == "manager@example.com"))
        if existing_manager:
            # Maintain the rolling calendar when bootstrap runs again.
            stores = db.scalars(select(Store)).all()
            changed = ensure_calendar_slots(db, stores) > 0

            # Keep demo catalog additions available on existing databases.
            supplier = db.scalar(select(Supplier).where(Supplier.email == "supplier@example.com"))
            if supplier:
                old_brand = db.scalar(select(Brand).where(
                    Brand.supplier_id == supplier.supplier_id,
                    Brand.brand_name == "Brand 2",
                ))
                renamed_brand = db.scalar(select(Brand).where(
                    Brand.supplier_id == supplier.supplier_id,
                    Brand.brand_name == "Ukulima Beverages",
                ))
                if old_brand:
                    if renamed_brand:
                        for request in db.scalars(select(ActivationRequest).where(
                            ActivationRequest.brand_id == old_brand.brand_id,
                        )):
                            request.brand_id = renamed_brand.brand_id
                        db.delete(old_brand)
                    else:
                        old_brand.brand_name = "Ukulima Beverages"
                    changed = True
                elif not renamed_brand:
                    db.add(Brand(supplier_id=supplier.supplier_id, brand_name="Ukulima Beverages",
                                 category="Beverages"))
                    changed = True
                fizzup = db.scalar(select(Brand).where(
                    Brand.supplier_id == supplier.supplier_id,
                    Brand.brand_name == "FizzUp",
                ))
                if not fizzup:
                    db.add(Brand(supplier_id=supplier.supplier_id, brand_name="FizzUp", category="Beverages"))
                    changed = True
            if changed:
                db.commit()
                print("Demo catalog and future slots are ready.")
            else:
                print("Seed data already present and current.")
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

        ensure_calendar_slots(db, stores)

        supplier = Supplier(company="Demo Beverages Ltd", contact="0712345678", email="supplier@example.com")
        db.add(supplier)
        db.flush()
        db.add(User(supplier_id=supplier.supplier_id, role="SUPPLIER", full_name="Demo Supplier",
                    email="supplier@example.com", phone="0712345678", password_hash=hash_password(PASSWORD)))
        db.add_all([
            Brand(supplier_id=supplier.supplier_id, brand_name="FizzUp", category="Beverages"),
            Brand(supplier_id=supplier.supplier_id, brand_name="Ukulima Beverages", category="Beverages"),
        ])
        db.commit()

        print("Seed complete. Logins (password for all: %s):" % PASSWORD)
        print("  supplier@example.com       (SUPPLIER)")
        print("  manager@example.com        (APPROVING_MANAGER)")
        print("  storemanager@example.com   (STORE_MANAGER)")


if __name__ == "__main__":
    main()
