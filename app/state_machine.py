"""Request life-cycle, taken directly from the State Diagram.

Draft -> Submitted -> Under Validation -> (Flagged for Review | Pending Approval)
Flagged -> (Pending Approval via manual override | Rejected)
Pending Approval -> (Approved | Rejected)
Approved -> Slot Booked -> Completed
"""

DRAFT = "DRAFT"
SUBMITTED = "SUBMITTED"
UNDER_VALIDATION = "UNDER_VALIDATION"
FLAGGED = "FLAGGED_FOR_REVIEW"
PENDING_APPROVAL = "PENDING_APPROVAL"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
SLOT_BOOKED = "SLOT_BOOKED"
COMPLETED = "COMPLETED"

ALL_STATUSES = [DRAFT, SUBMITTED, UNDER_VALIDATION, FLAGGED, PENDING_APPROVAL,
                APPROVED, REJECTED, SLOT_BOOKED, COMPLETED]

ALLOWED_TRANSITIONS = {
    DRAFT: {SUBMITTED},
    SUBMITTED: {UNDER_VALIDATION},
    UNDER_VALIDATION: {FLAGGED, PENDING_APPROVAL},
    FLAGGED: {PENDING_APPROVAL, REJECTED},
    PENDING_APPROVAL: {APPROVED, REJECTED},
    APPROVED: {SLOT_BOOKED},
    SLOT_BOOKED: {COMPLETED},
    REJECTED: set(),
    COMPLETED: set(),
}

# Requests in these states hold capacity at a store (used by conflict checks).
ACTIVE_STATUSES = (PENDING_APPROVAL, APPROVED, SLOT_BOOKED)
# Requests a manager has approved / ruled on (used for approval-history statistics).
APPROVED_SET = (APPROVED, SLOT_BOOKED, COMPLETED)
DECIDED_STATUSES = APPROVED_SET + (REJECTED,)


class InvalidTransition(Exception):
    pass


def can_transition(current: str, new: str) -> bool:
    return new in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: str, new: str) -> None:
    if not can_transition(current, new):
        raise InvalidTransition(f"Cannot move a request from {current} to {new}.")
