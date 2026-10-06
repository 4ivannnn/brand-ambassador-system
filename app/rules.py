"""Pure business rules (no database access) so they are easy to unit-test.

They implement the validation and conflict-prevention requirements from the
proposal (sections 1.3.2 and 1.4):
  * all required fields present, phone / e-mail in a valid format
  * declared ambassador_count == number of ambassadors actually listed
  * ambassadors for a store must not exceed the store's limit
  * two competing brands (same category, different supplier) must not
    run activations at the same store during overlapping times
"""
import re
from datetime import time

KENYA_PHONE = re.compile(r"^(?:\+254|0)[17]\d{8}$")   # 07xx / 01xx / +2547xx / +2541xx
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_phone(phone: str | None) -> str:
    return re.sub(r"[\s\-()]", "", phone or "")


def is_valid_phone(phone: str | None) -> bool:
    return bool(KENYA_PHONE.match(normalise_phone(phone)))


def is_valid_email(email: str | None) -> bool:
    return bool(email and EMAIL.match(email))


def times_overlap(s1: time, e1: time, s2: time, e2: time) -> bool:
    return s1 < e2 and s2 < e1


def required_field_checks(*, company, contact, email, brand_name, category,
                          store_id, slot_id, ambassador_count) -> dict[str, bool]:
    """One True/False per required field (used for errors AND the ML completeness feature)."""
    return {
        "supplier company name": bool(company),
        "supplier contact number": bool(contact),
        "supplier email": bool(email),
        "product/brand name": bool(brand_name),
        "product category": bool(category),
        "store": store_id is not None,
        "time slot": slot_id is not None,
        "ambassador count": bool(ambassador_count and ambassador_count > 0),
    }


def validate_submission(*, checks: dict[str, bool], contact, email,
                        ambassador_count: int, ambassadors: list[dict]) -> list[str]:
    """Return a list of human-readable errors. Empty list == valid."""
    errors = [f"Missing required field: {name}." for name, ok in checks.items() if not ok]

    if contact and not is_valid_phone(contact):
        errors.append("Supplier contact number is not a valid Kenyan phone number.")
    if email and not is_valid_email(email):
        errors.append("Supplier email address is not valid.")

    if not ambassadors:
        errors.append("At least one brand ambassador must be listed.")
    elif ambassador_count and ambassador_count != len(ambassadors):
        errors.append(
            f"Declared ambassador count ({ambassador_count}) does not match the "
            f"{len(ambassadors)} ambassador(s) listed."
        )

    for i, amb in enumerate(ambassadors, start=1):
        if not amb.get("full_name"):
            errors.append(f"Ambassador #{i}: name is required.")
        if not is_valid_phone(amb.get("phone")):
            errors.append(f"Ambassador #{i}: phone number is missing or invalid.")
        if amb.get("email") and not is_valid_email(amb["email"]):
            errors.append(f"Ambassador #{i}: email address is not valid.")
    return errors


def find_conflicts(*, requested_count: int, effective_limit: int, category: str,
                   supplier_id: int, overlaps: list[dict]) -> list[str]:
    """Store-limit and competing-brand checks.

    `overlaps` = other ACTIVE requests at the same store & overlapping time, each
    as {"supplier_id", "company", "category", "ambassador_count"}.
    """
    problems = []
    already = sum(o["ambassador_count"] for o in overlaps)
    if already + requested_count > effective_limit:
        problems.append(
            f"Store limit exceeded: {already} ambassador(s) already booked + "
            f"{requested_count} requested > limit of {effective_limit}."
        )
    for o in overlaps:
        if o["supplier_id"] != supplier_id and (o["category"] or "").lower() == (category or "").lower():
            problems.append(
                f"Competing brand conflict: {o['company']} already has a '{o['category']}' "
                f"activation at this store in the same period."
            )
    return problems
