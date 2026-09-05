# KYC Review Queue

## What the tool does

The KYC Review Queue gives signed-in compliance reviewers a focused dashboard for pending customer identity checks. Reviewers can filter by risk, search by customer name, and approve or reject requests through risk-aware confirmation flows. Every seeded request and reviewer decision is stored in MongoDB with exactly one corresponding audit record.

## How to run it

Install Docker Compose and `just`, then copy `.env.example` to `.env` only if you want to override the development defaults. Run `just dev` from this directory and open http://localhost:8000 after the containers finish migrating and seeding. Sign in with `reviewer` / `reviewer` or `supervisor` / `supervisor`, run `just test` for the suite, and use `just down` when finished.

## How to add the next tool

Create a new Django app beside `kyc` and keep reusable models, templates, and audit behavior in `core`. Put every domain write and business rule in the new app's services module, and make each write call `core.audit.log` within the same MongoDB transaction. Add the app's URLs, templates, plain admin registration, idempotent seed command, and service tests without importing that app back into `core`.
