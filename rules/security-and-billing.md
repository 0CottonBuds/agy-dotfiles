---
trigger: model_decision
description: "Apply whenever touching authentication, JWT/sessions/cookies, authorization, Stripe/payments, trials/paywalls, webhooks, AWS/IAM/Bedrock, or secrets."
---

# Security, Auth & Billing Boundaries

- **Server-Authoritative Enforcement**: Enforce authentication, authorization/RBAC, trial windows, rate/quota limits, and subscription/paywall checks strictly on the server. Never trust client-supplied user IDs, roles, prices, plan IDs, or entitlement flags.
- **Fail Closed**: Deny access by default on missing, expired, or unverifiable credentials/permissions.
- **Webhook & Payment Integrity**: Always verify webhook signatures (e.g., Stripe) against the raw request payload before parsing JSON, and handle duplicate deliveries idempotently.
- **Boundary Validation**: Validate and sanitize all external inputs (HTTP bodies, query params, cookies, third-party API feeds) at system boundaries.
- **Secrets & Config Hygiene**: Never hardcode, log, print, or commit API keys, JWT secrets, IAM credentials, or `.env` files. Read secrets from environment config and keep `.env.example` placeholder-only.
- **Ask Before Auth/Billing Shifts**: Confirm with the user before changing token lifetimes, cookie `Domain`/`SameSite` flags, CORS origins, pricing constants, or IAM/permission scopes.
