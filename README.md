# KYC Review Queue, two ways

The same internal tool (a queue where compliance reviewers approve or reject customer identity checks) built two ways, so they can be compared side by side.

## Approach 1: Devin on Power Apps

Devin edits a live Power Apps canvas app through Microsoft's Canvas Authoring MCP server. Power Apps stays the runtime. Setup and usage are in [`powerapps/README.md`](powerapps/README.md).

https://github.com/user-attachments/assets/6fcde944-62c8-4954-8730-af42a3042691

## Approach 2: a standalone Django app

Devin builds and owns the whole tool as a Django 5 app with HTMX, MongoDB, login, business rules, and an audit trail. Details are in [`django/README.md`](django/README.md). To run it:

```bash
cd django
just dev
```

Open http://localhost:8000 and sign in with `reviewer` / `reviewer` or `supervisor` / `supervisor`.

https://github.com/user-attachments/assets/fac891fa-c6c9-4a31-9ba0-58ef2fe1bca7
