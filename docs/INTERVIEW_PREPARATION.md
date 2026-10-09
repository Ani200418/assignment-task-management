# Interview preparation guide

Rule: do not memorise. For each section, close this file and explain it aloud using the real code. Everything below names real files/functions.
Be honest about status: this project is **built and tested locally; not yet deployed** (see STATUS.md). If you deploy it, update your story.

---
## A. 60-90 second introduction (edit into your own words)
"I built TaskFlow, a task-management web app where users sign in with Google, create tasks, assign them to other registered users, and get emails when a task is
assigned or completed. The frontend is Next.js with TypeScript. It signs users in through Supabase Auth with Google and then calls a Flask REST API with the access token.
Flask verifies that token against Supabase's public keys, applies the permission rules - creators manage tasks, assignees can change status, everyone else gets a 404 -
and talks to a Supabase PostgreSQL database. For email I used a transactional outbox: the task change and the 'email to send' row are saved in one database transaction,
then Flask sends through the Gmail API and records sent, retry or failed. Three things were challenging: keeping authorization correct when the backend uses a privileged key that bypasses
row-level security, making notifications reliable and non-duplicated, and learning that Google refresh tokens can expire after 7 days in testing mode. I tested the SQL on a real PostgreSQL,
the API with 71 pytest tests and the UI with 44 Vitest tests. What I learned is how authentication differs from authorization and why side effects like email need a design, not just a function call."
(Do **not** add numbers of users, performance claims or team size - none exist.)

---
## B. Architecture in plain English
* **Why Next.js?** React with routing, TypeScript, build tooling and easy Vercel hosting. Here it is a client-rendered app: pages call the API from the browser.
* **Why Flask?** Small, explicit Python web framework. It is the single place for business rules and the only holder of secrets (service-role key, Gmail credentials).
* **Why Supabase PostgreSQL?** Relational data (users 1-many tasks) with foreign keys/constraints; Supabase also supplies Google login and JWT issuing.
* **Authentication vs authorization:** authentication = "who are you?" (verify the JWT). Authorization = "are you allowed to do this to *that* task?" (`TaskService`).
* **Why the backend verifies the token:** the browser is untrusted. Anyone can send any user id in a request body; only a signature-verified token proves identity.
* **Why no privileged key in the frontend:** the service-role key bypasses row-level security. Anything in `NEXT_PUBLIC_*` or the JS bundle is public; with that key anyone could read/write the whole database.
* **Frontend <-> backend:** `frontend/src/services/api.ts` -> `fetch` with `Authorization: Bearer` -> Flask routes -> services -> repository -> Supabase.
* **Why foreign keys:** the database itself refuses a task pointing to a non-existent user - correctness does not depend on every code path remembering to check.
* **Transactions:** a group of statements that all succeed or all roll back. `create_task()` inserts the task and the outbox row in one function = one transaction.
* **Why idempotency:** networks and workers retry. A unique `dedupe_key` means "the same event" can only be recorded once, so retries do not create duplicate emails.
* **Local vs deployed:** locally everything is on localhost with fake or dev keys; deployed, secrets live in host dashboards, URLs must be allow-listed (CORS, OAuth redirects), and processes sleep/restart.

---
## C. Code walkthrough: the 20 files to study
1. `supabase/migrations/20260101000000_create_schema.sql` - tables `profiles`, `tasks`, `notification_outbox`; CHECKs (status, `completed_at` iff completed), FKs, indexes; trigger `handle_new_user` creates a profile when a user signs up. Break it: no profiles => FK failures on every task.
2. `supabase/migrations/20260101000100_rls_policies.sql` - RLS on; users read only own profile / own tasks; no write policies; outbox has none. Removing => direct client access could leak data.
3. `supabase/migrations/20260101000200_task_functions.sql` - `create_task`, `reassign_task`, `set_task_status`, `claim_notifications`. Each locks (`FOR UPDATE`), changes the task and inserts the outbox row atomically; `claim_notifications` uses `FOR UPDATE SKIP LOCKED`. Granted to `service_role` only.
4. `backend/app/__init__.py` - `create_app()` wires config, repository, sender, notifier, services, CORS, blueprints, logging, error handlers. Dependencies are injectable - that is why tests need no Supabase.
5. `backend/app/config.py` - `Config.from_env()`, `validate()` (fails fast naming missing variables, never printing values), `gmail_configured`.
6. `backend/app/middleware/auth.py` - `TokenVerifier.verify()` (PyJWT + JWKS; algorithms ES256/RS256 only; checks `iss`, `aud`, `exp`, `role`) and `require_auth` decorator that puts `CurrentUser` into `flask.g`. Break it: unauthenticated access or wrong identity.
7. `backend/app/services/task_service.py` - **authorization core**: `permissions_for()`, `_visible_task()` (404 for strangers), `create/update_details/set_status/reassign/delete`, `_deliver()`.
8. `backend/app/repositories/supabase_repository.py` - the only DB code: `list_tasks` (role filters, pagination), RPC wrappers, outbox updates. Validates UUID before building the `or_` filter string (injection guard).
9. `backend/app/services/notification_service.py` - `deliver_one()` (never raises), `process_due()`, `_process()` (success / retry with exponential backoff / give up after 5).
10. `backend/app/services/email_service.py` - `build_message()` (escapes HTML, strips newlines = header-injection safe), `classify_error()` (retryable vs permanent, safe messages), `GmailSender.send_row()` (scope `gmail.send`, 10s timeout).
11. `backend/app/routes/tasks.py` - thin HTTP layer: `_body()`/`_validate()` convert Pydantic errors to 422; each route calls `TaskService`.
12. `backend/app/schemas/tasks.py` - Pydantic models; `extra="forbid"` rejects unknown fields (so a client cannot send `created_by`).
13. `backend/app/routes/internal.py` - cron endpoint protected by `X-Cron-Secret` via `hmac.compare_digest` (constant-time); disabled if no secret.
14. `backend/tests/fakes.py` + `conftest.py` - in-memory repository/sender and real ES256 test tokens; shows how to test without external services.
15. `frontend/src/lib/supabase.ts` - `getSupabase()`: lazy singleton using only the publishable key, PKCE flow.
16. `frontend/src/hooks/useAuth.tsx` - `AuthProvider`: tracks session, loads `/api/me`, `signInWithGoogle`, `signOut`, registers the 401 handler.
17. `frontend/src/services/api.ts` - `request()` attaches the token, maps errors to `ApiRequestError`, calls the unauthorized handler on 401; `api.*` functions are the only place that knows URLs.
18. `frontend/src/app/auth/callback/page.tsx` - finishes login, maps `access_denied` to "cancelled", then redirects to a validated path.
19. `frontend/src/components/RequireAuth.tsx` + `src/lib/safeRedirect.ts` - UX route guard (not the real security) and open-redirect protection.
20. `frontend/src/hooks/useApi.ts` - small data-fetching hook: loading/error/reload, cancels stale responses.

---
## D. Authentication walkthrough
1. Click "Continue with Google" -> `useAuth.signInWithGoogle()` -> `supabase.auth.signInWithOAuth({provider:"google", redirectTo: <origin>/auth/callback})`.
2. Browser goes to Supabase, which redirects to Google's consent/account chooser. If the user presses Cancel, Google returns `error=access_denied` -> callback shows "cancelled".
3. Google calls Supabase's callback with a one-time code; Supabase redirects the browser to `/auth/callback?code=...` (PKCE flow).
4. supabase-js exchanges the code for a session (access token = JWT, refresh token) and stores it in browser storage; `getSession()` returns it.
5. `api.ts` sends `Authorization: Bearer <access token>` on each call; supabase-js refreshes it before expiry.
6. Flask `require_auth` -> `TokenVerifier.verify()`: fetch signing key by `kid` from the cached JWKS, verify signature, check `iss`, `aud`, `exp`, role; `sub` becomes `g.user.id`.
7. Services use `g.user.id`, never an id from the request. 8. Logout: `supabase.auth.signOut()` clears the session; RequireAuth sends the user to `/login`. 401 from Flask triggers a local sign-out and `?error=session_expired`.

## E. Task lifecycle walkthrough
1. `POST /api/tasks` -> route validates body (Pydantic) -> `TaskService.create`. 2. Check assignee exists (`profile_exists`) else 422.
3. `repo.rpc_create_task` -> SQL `create_task()` inserts the task; if assignee is someone else it inserts an outbox row with `dedupe_key = task_assigned:<task>:<assignee>` - same transaction.
4. `NotificationService.deliver_one(outbox_id)` -> `claim_notifications` marks it `processing`, `attempt_count+1`. 5. `GmailSender.send_row` builds the message and calls Gmail.
6. Success -> `sent`; temporary error -> `pending` + `next_attempt_at`; permanent -> `failed`. Response reports `notification.status` honestly.
7. Assignee calls `PATCH /status {completed}` -> `set_task_status()` locks the row; if already completed it returns without an outbox row; else sets `completed_at` and (if actor != creator) inserts `task_completed:<task>:<completed_at epoch>`.
8. Same delivery path emails the creator.

---
## F. Interview questions (with answers)
### React / Next.js / TypeScript
1. **What is a Client Component?** A component that runs in the browser (marked `"use client"`) and can use state, effects and browser APIs. All my pages are client components because they depend on the browser-held session.
2. **Why Suspense around the app layout?** The shell reads the current URL (`usePathname`), which is only known at request time; Next prerenders pages, so runtime data must stream in behind Suspense. The build failed until I added it.
3. **useEffect vs event handler?** Effects synchronise with the outside world after render (fetching on mount); handlers react to user actions. `useApi` fetches in an effect; buttons call API in handlers.
4. **How do you avoid a slow old response overwriting a new one?** A `cancelled` flag in the effect cleanup (`useApi`), so only the latest request's result is stored.
5. **Why React Hook Form + Zod?** RHF handles form state/submission cheaply; Zod gives one typed schema for validation messages. The server validates again - client validation is convenience only.
6. **How do you stop double submits?** RHF's `isSubmitting` stays true until the async submit settles and disables the button; a test verifies one call.
7. **Why TypeScript?** Compile-time checking of shapes like `Task`, so renaming a field breaks the build instead of production. `any` is avoided.
8. **What is the App Router?** Folder-based routing under `src/app`; `(app)` is a route group that shares a layout without changing the URL; `[id]` is a dynamic segment.
### Flask / REST / HTTP
9. **Blueprint?** A group of routes registered on the app (`routes/tasks.py`). Gotcha I hit: `register_blueprint(url_prefix=...)` replaces the blueprint's own prefix.
10. **PUT vs PATCH?** PUT replaces a whole resource; PATCH changes some fields. I use PATCH for partial updates.
11. **401 vs 403?** 401: not authenticated (missing/invalid/expired token). 403: authenticated but not permitted (assignee trying to edit).
12. **Why 404 for another user's task, not 403?** 403 confirms the task exists. 404 reveals nothing.
13. **422 vs 400?** 400 = malformed request (not JSON); 422 = well-formed JSON failing validation.
14. **201 vs 200 vs 204?** 201 created; 200 OK with body; 204 success without body (delete).
15. **What is idempotent in HTTP?** Repeating gives the same server state: PUT, DELETE, and my status PATCH (setting "completed" twice changes nothing).
16. **App factory benefit?** `create_app()` builds an app from injected parts; tests inject fakes, production injects real clients.
17. **Why Gunicorn?** Flask's dev server is not for production; Gunicorn is a production WSGI server with workers and timeouts.
18. **How is error handling structured?** One `ApiError` type and handlers so every error has `{error:{code,message}}`; unexpected exceptions return a generic 500 and log details server-side only.
19. **Pagination?** `page`/`page_size` (max 100) -> `range()` on the query and a `total` count. For huge tables use keyset (cursor) pagination because large OFFSETs get slow.
### PostgreSQL / Supabase
20. **Why normalise?** Store each fact once: user info in `profiles`, tasks reference it by id. Renaming a user changes one row.
21. **What is a foreign key / ON DELETE?** A constraint linking rows. Deleting a creator cascades to their tasks; deleting an assignee sets `assigned_to` to null.
22. **What do indexes do and what is their cost?** Speed lookups (tasks by creator/assignee/status) but slow writes and use space.
23. **What is a CHECK constraint?** A rule the DB enforces, e.g. status in 3 values and `completed_at` set iff completed.
24. **What is RLS?** Row-Level Security: per-row policies evaluated by Postgres per role, e.g. users see only tasks they participate in.
25. **If Flask uses the service-role key, why keep RLS?** Service role bypasses RLS, so RLS does not protect those queries - Flask enforces rules itself. RLS is the second wall for any query made with a normal user key.
26. **What is `SECURITY DEFINER`?** The function runs with its owner's rights. I set `search_path = ''` to prevent search-path hijacking and revoked execute from normal roles.
27. **What does `FOR UPDATE` do?** Locks the row until commit, so two concurrent status changes cannot interleave and both enqueue emails.
28. **What is `SKIP LOCKED`?** Lets a second worker skip rows another worker already claimed, so two workers never process the same email.
29. **How would you handle concurrent edits?** Add optimistic concurrency: client sends `updated_at`; update with `WHERE updated_at = ...`; zero rows updated => 409 Conflict. (Listed as future work.)
30. **How did you test the SQL?** Ran migrations on a real embedded PostgreSQL with a stubbed Supabase `auth` schema and asserted constraints, RLS and idempotency (23 checks). Caveat: not the real Supabase.
### Auth / OAuth / JWT / CORS / Secrets
31. **What is OAuth 2.0?** A way to let an app act for/identify a user via a provider (Google) without handling their password; the app gets tokens.
32. **Why PKCE?** Binds the code exchange to a secret only this browser has, so an intercepted code is useless - the recommended flow for browser apps.
33. **What is a JWT?** Header.payload.signature, base64url encoded. The signature proves Supabase issued it and it was not altered; the payload carries claims like `sub`, `exp`.
34. **How do you validate one safely?** Use a library, fetch the right public key by `kid` from JWKS, verify signature, `iss`, `aud`, `exp`, and restrict allowed algorithms.
35. **What is algorithm confusion?** Attacker changes `alg` to HS256 and signs with the public key as if it were a secret. I only allow ES256/RS256 (a test covers it).
36. **Why not hand-roll verification?** Subtle mistakes (alg, timing, claim checks) become vulnerabilities; vetted libraries cover them.
37. **Where should a browser keep tokens?** Trade-off: localStorage (simple; readable by XSS), httpOnly cookies (JS cannot read; need CSRF care and server involvement), server-side sessions (most control; more infrastructure). I chose supabase-js storage for simplicity and mitigate XSS with escaping/no raw HTML.
38. **What is CORS?** A browser rule: a page from origin A may only read responses from origin B if B allows A. It is not server security - curl ignores it. I allow only `CORS_ORIGINS`.
39. **How would you debug a CORS error?** DevTools Network: look at the preflight `OPTIONS` response and `Access-Control-Allow-Origin`; compare the exact Origin with `CORS_ORIGINS` (scheme, host, port, no trailing slash); check allowed headers (`Authorization`).
40. **How would you debug a Google redirect error?** Read the error text: `redirect_uri_mismatch` -> Google client redirect URI must be Supabase's `/auth/v1/callback`; bounce to login -> app URL missing from Supabase redirect allow-list; check Site URL.
41. **What is an open redirect and how do you prevent it?** Redirecting to an attacker-chosen URL after login. `safeRedirectPath` accepts only same-site relative paths and rejects `//evil.com`.
42. **Why is a service-role key dangerous in frontend code?** Bundles are public; with that key anyone bypasses RLS and can read/delete everything.
43. **Env vars & secrets?** Config outside code; `.env` git-ignored, `.env.example` has placeholders; production secrets live in host settings; `NEXT_PUBLIC_` means public.
### Gmail / async / retries / idempotency
44. **Why a dedicated sender account?** Google sign-in gives the *user's* identity, not permission to send mail. A server-owned account authorises once via OAuth and keeps a refresh token.
45. **Why only `gmail.send`?** Least privilege: the server can send but cannot read mail.
46. **What if Gmail fails after the task is created?** The task and outbox row were committed together. The row stays `pending`/`failed` with `last_error`; the user sees an honest "queued/failed" message; a cron sweep retries with backoff.
47. **How do you prevent duplicate emails?** Unique `dedupe_key`; status transition guard (completing twice is a no-op); claim step with locking. Limitation: at-least-once if the process dies between send and marking sent.
48. **Accepted vs delivered?** Gmail API success means accepted for sending; inbox placement/bounces are later, separate events.
49. **Why exponential backoff and a cap?** Gives a struggling provider time to recover and avoids hammering it; bounded attempts stop endless retries.
50. **Why an outbox instead of "save then send"?** If the process crashes between the two, the email is lost. Writing the intent in the same transaction makes it durable.
51. **Retryable vs permanent errors?** 429/5xx/timeouts are retryable; 400 (bad recipient) and auth failures are not, so retrying is pointless.
52. **What does an expired refresh token look like?** `invalid_grant` -> `RefreshError` -> rows marked failed with a safe message; fix credentials and re-queue.
### Testing / Git / Deployment / Debugging / Security
53. **How did you test email without sending?** Injected a `FakeSender`/fake Gmail service and asserted on recorded messages and outbox state.
54. **What did mutation checks show?** I deliberately broke the double-submit guard, the redirect check and the route guard; the matching tests failed - evidence tests are meaningful.
55. **Unit vs integration?** Unit tests one piece in isolation; integration tests pieces together. My API tests are integration-style over Flask with fakes at the edges; real Supabase/Gmail integration is still manual.
56. **What happens if a user completes someone else's task?** A stranger gets 404. An assignee may complete; creator may complete; neither triggers an email to themselves.
57. **What is a good commit message?** `type: what changed` (e.g. `feat: add outbox processing`) - small, reviewable steps.
58. **How would you investigate a production 500?** Find the request in logs (method/path/time/user id), reproduce, read the stack trace server-side (never returned to clients), add a regression test.
59. **SQL injection?** Parameterised/builder queries; the one place with a filter string (`or_`) uses a validated UUID.
60. **XSS?** React escapes by default; emails escape HTML (`html.escape`); no `dangerouslySetInnerHTML`.

---
## G. Self-quiz (answer aloud)
1. Trace what Flask does with a token whose `exp` has passed. Which status code, which error code, what does the frontend do?
2. A stranger sends `PATCH /api/tasks/<id>/status`. Which function decides, what is returned and why not 403?
3. Gmail returns 503 on attempt 2. Which columns change? When is it tried again? What if it is attempt 5?
4. Why does `set_task_status` return early when the status is unchanged?
5. What would break if you removed `extra="forbid"`?
