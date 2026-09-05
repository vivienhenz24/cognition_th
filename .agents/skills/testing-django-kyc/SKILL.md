---
name: testing-django-kyc
description: Run and browser-test the local Django KYC review queue with MongoDB, seeded accounts, HTMX filters, and decision workflows.
---

# Local Django KYC testing

## Devin Secrets Needed

None for the local seeded demo. Accounts are `reviewer/reviewer` and
`supervisor/supervisor`; do not use these demo passwords for a deployment.

## Runtime

- Work in the repository's `django` directory.
- Docker Compose and `just` must be available; Docker daemon must be running.
- Run `just dev`. It builds web, starts MongoDB 7, migrates, seeds idempotently,
  and serves http://localhost:8000.
- Use `docker compose ps` and `docker compose logs web` to resolve readiness.
- A bind mount exposes checkout changes to Django; reload the browser after
  template updates.
- Seeding preserves existing decisions. Never assume restart restores Pending.
  Inspect baseline first. Reset only local seed decision fields when explicitly
  authorized; do not wipe an unknown database or reset unrelated records.

## UI coverage

- `/login/` is public; dashboard `/`, `/history/`, and request detail pages
  require authentication.
- Initial seed has eight cases: low 1001/1002/1007, medium 1003/1004/1008,
  high 1005/1006.
- Filters require clicking **Apply filters** / **Apply filter**.
- Filter requests use HTMX and replace the current URL. Establish a preceding
  page before checking browser Back; it should return to that page, not an old
  filter state. Check Forward also restores consistent controls and results.
- Low-risk approval is direct. High-risk approval shows confirmation and needs
  supervisor email. Rejection needs notes and a separate confirmation.
- Decision actions mutate local records; choose cases up front and calculate
  expected KPIs after each decision.
- Use temporary browser network latency to visibly capture loading indicators,
  then restore zero latency. This is instrumentation, not a mocked response.
- At narrow viewports, tables intentionally scroll inside their cards; verify
  their scrollability and ensure the document itself does not overflow.
- Chrome may warn about the intentionally weak seeded passwords; dismiss the
  browser warning, not an app error.

## Evidence

Record real browser actions and add consolidated assertions. If native input
tools hold a stale X connection after a display restart, `xdotool` can provide
real keyboard/mouse input while screenshots verify each outcome. Check the
edited video's duration: shell-driven GUI actions may be over-compressed by
automatic editing. If necessary, create a readable-speed edit from only the
current valid raw recording segments and preserve the annotation timestamps.
