const LABELS = {
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  UNDER_VALIDATION: "Validating",
  FLAGGED_FOR_REVIEW: "Flagged",
  PENDING_APPROVAL: "Pending approval",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  SLOT_BOOKED: "Slot booked",
  COMPLETED: "Completed",
};

export default function StatusBadge({ status }) {
  const cls = status?.toLowerCase().replace("_for_review", "").replace("_approval", "").replace("slot_", "");
  return <span className={`stamp ${cls}`}>{LABELS[status] || status}</span>;
}
