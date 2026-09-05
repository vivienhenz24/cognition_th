# Two ways to build internal tools with Devin

This repository keeps two implementations of the same KYC review-queue idea so they can be compared directly. The `powerapps/` arm tests Devin as an author inside Microsoft Power Apps, while the `django/` arm tests Devin building and owning the internal tool as a separate application.

## Approach 1: build with Devin on Power Apps

[`powerapps/`](powerapps/) uses Microsoft's Canvas Authoring MCP server so Devin can sync, edit, validate, and compile a live Canvas app. This approach keeps Power Apps as the runtime and low-code platform while using Devin to accelerate authoring. See the [Power Apps setup guide](powerapps/README.md) for the Studio and authentication workflow.

## Approach 2: build the internal tool separately

[`django/`](django/) is an independent Django 5 application with server-rendered templates, HTMX, MongoDB 7, authentication, business rules, and an audit trail. It does not depend on Power Apps and runs locally through Docker Compose. [Watch the browser-tested Django workflow](django/kyc-review-queue-demo.mp4).

## Run the standalone Django tool

```bash
cd django
just dev
```

Open `http://localhost:8000` and sign in with `reviewer` / `reviewer` or `supervisor` / `supervisor`. Run `just test` for the test suite and `just down` to stop the containers.

## What the comparison shows

| | Devin on Power Apps | Separate Django tool |
|---|---|---|
| Platform | Power Apps Canvas and its coauthoring services | Python, Django, HTMX, and MongoDB |
| Devin's role | Edits and compiles the live Canvas app | Builds and maintains the complete application |
| Runtime | Microsoft Power Apps | Team-operated Docker services |
| Main tradeoff | Faster low-code platform integration with platform constraints | More implementation and operational ownership with full code-level control |
