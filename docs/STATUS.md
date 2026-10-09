# Verification status (honest ledger)

Levels: **L1** implemented · **L2** locally tested · **L3** externally configured (needs your accounts) · **L4** production verified.
Last updated from real command output in the development sandbox. Nothing here has reached L3 or L4 yet.

| Feature | L1 | L2 | L3 | L4 | How it was tested |
|---|---|---|---|---|---|
| Schema, constraints, indexes, triggers | yes | yes | no | no | `scripts/test_migrations.py`: real PostgreSQL (embedded), **Supabase `auth` schema is stubbed** - 23/23 checks |
| RLS policies, function privileges | yes | yes | no | no | same script, as `authenticated` role |
| Atomic task+outbox SQL functions, idempotency, claim/skip-locked | yes | yes | no | no | same script |
| JWT verification (signature, iss, aud, exp, alg) | yes | yes | no | no | pytest with a locally generated ES256 key. **Real Supabase JWKS fetch not exercised** |
| Task API + authorization matrix (creator / assignee / stranger) | yes | yes | no | no | pytest 71 tests, in-memory fake repository |
| Real Supabase calls (`SupabaseRepository`) | yes | partly | no | no | contract tests only (RPC arg names vs SQL, filters). **Never run against a real Supabase** |
| Email building, error classification, retry/backoff, give-up | yes | yes | no | no | pytest with fake Gmail service |
| Real Gmail send | yes | no | no | no | needs sender account + refresh token |
| Google sign-in flow | yes | no | no | no | needs Supabase + Google config; callback/redirect logic unit-tested only |
| Frontend screens, forms, guards, error states | yes | yes | no | no | vitest 44 tests (mocked API), tsc, eslint, `next build`, `next start` smoke (HTTP 200s) |
| Bundle contains no private credentials | yes | yes | - | no | canary scan of `.next` after build |
| Real browser end-to-end, screenshots | no | no | no | no | no browser automation was run |
| Deployment (Vercel / Render / Supabase prod) | no | no | no | no | not done - needs your accounts |

## Known limitations
* Delivery is **at-least-once**: a crash between Gmail accepting a message and the DB marking it `sent` can cause one duplicate on retry.
* Emails are attempted inside the request (adds Gmail latency, ~1s). Retries rely on an external scheduler hitting `/api/internal/notifications/process`. This is an outbox + poller, **not** a message queue.
* "sent" = Gmail API accepted the message. It is not proof of inbox delivery (spam filters, bounces happen later).
* Re-assigning A -> B -> A does not re-email A (dedupe key `task_assigned:<task>:<assignee>`).
* Deleting a task also deletes its outbox rows (an unsent email for a deleted task is dropped).
* Any signed-in user can list all registered users' name/email (required by the "pick any registered user" feature).
* Gmail refresh tokens expire after 7 days if the Google consent screen is External + Testing (see DEPLOYMENT.md).
* Session token is held by supabase-js in browser storage (XSS would expose it); see INTERVIEW_PREPARATION.md for trade-offs.
* Dashboard counts use 3 `COUNT` queries; assignable-user list is capped at 200 with no search.
