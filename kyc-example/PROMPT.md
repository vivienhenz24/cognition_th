# Build the KYC Review Queue in Power Apps

Use the `power-apps-canvas-authoring` skill (`skills/power-apps-canvas-authoring/SKILL.md`)
for everything about how to connect, write `.pa.yaml`, validate, and report. This file only
says what to build.

## Connection values

- ENVIRONMENT_ID: `26e4f594-b375-ebb4-a01d-d93c5d0f3c01`
- APP_ID: `6172e0eb-0763-4046-af22-efccb7f7a6cb`
- WORKDIR: `/Users/vivienhenz/cognition_th/kyc-example/generated`

## Files to produce in WORKDIR

`App.pa.yaml`, `Screen1.pa.yaml` (the Dashboard, reuse the existing key),
`ReviewDetail.pa.yaml`, `History.pa.yaml`.

# App spec: KYC Review Queue

Internal tool for a fintech compliance team.

## Data (collections seeded in App.OnStart; no Dataverse in this environment)

- `KYC_Requests`: id (number), customer_name, customer_email, risk_score (1–10),
  submission_date (date), status ("Pending" / "Approved" / "Rejected"), reviewer_notes,
  reviewed_by, reviewed_date
- `Audit_Log`: action_type, user, timestamp, record_id, details

Seed 8 realistic pending requests with a spread of risk scores (at least two each of
low 1–3, medium 4–7, high 8–10).

## Screens

1. **Dashboard (Screen1)** — three KPI cards: pending count, approved today, rejected
   today. Gallery of pending requests showing name, risk score (colour: 1–3 green,
   4–7 orange, 8–10 red), submission date. A dropdown filter (All / Low / Medium / High)
   and a name search box. Tapping a row sets `varSelected` and navigates to ReviewDetail.
   Empty state label when no rows match.
2. **ReviewDetail** — all fields of `varSelected`; risk badge; multi-line reviewer notes
   input. **Approve**: if risk_score > 7, show a confirm panel requiring a supervisor
   email (must contain "@") before approving. **Reject**: notes required; confirm panel.
   Both `Patch` the record (status, reviewed_by = `User().Email`, reviewed_date = `Now()`,
   reviewer_notes), `Collect` an Audit_Log row, `Notify` success, and navigate back.
   Back button.
3. **History** — gallery of non-pending requests showing name, status, reviewer, date.
   Status filter dropdown (All / Approved / Rejected). Back button.

## Quality bar

- Consistent theme (one primary colour, one accent, neutral greys).
- Loading and empty states, friendly error messages.
- Zero `compile_canvas` errors before you report done.
