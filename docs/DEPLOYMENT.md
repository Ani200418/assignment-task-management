# Setup & deployment guide (needs YOUR accounts)

Never paste secret values into chat or Git. Put them only in the provider dashboards named below or in local, git-ignored `.env` files.
Dashboard labels change over time; if a menu name differs, search the provider docs for the term in *italics*.

## 1. Supabase project
1. Create a project at supabase.com. Note the **Project URL** and, under *API keys*, the **publishable** key (browser-safe) and the **secret / service-role** key (server only).
2. *JWT signing keys*: make sure the project uses an **asymmetric** signing key (ES256/RS256). Check: open `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` - it must list at least one key.
   If `keys` is empty the project still uses the legacy shared secret and Flask will reject every token (`invalid_token`).
3. Apply the migrations in order (`supabase/migrations/*.sql`). Either `npx supabase login && npx supabase link --project-ref <ref> && npx supabase db push`,
   or paste the three files into the SQL editor one by one. Do **not** run `supabase/seed.sql` on production (fake local users).
4. Verify in the table editor that `profiles`, `tasks`, `notification_outbox` exist with RLS enabled.

## 2. Google sign-in (Supabase Auth)
1. Google Cloud Console -> new project -> *OAuth consent screen* (External). Scopes: only `openid`, `email`, `profile`.
2. *Credentials -> Create OAuth client ID -> Web application*. Authorized redirect URI: `https://<ref>.supabase.co/auth/v1/callback`.
3. Supabase -> *Authentication -> Sign In / Providers -> Google*: enable, paste the client ID + secret.
4. Supabase -> *Authentication -> URL Configuration*: Site URL = your production frontend URL. *Redirect URLs* allow-list:
   `http://localhost:3000/auth/callback` and `https://<your-frontend-domain>/auth/callback`.

## 3. Gmail sender account (separate OAuth purpose)
Google sign-in does NOT let the server send mail. A dedicated sender account authorises the server once.
1. Create a dedicated Gmail account for notifications.
2. Same Google Cloud project: enable the **Gmail API**; consent screen -> add scope `https://www.googleapis.com/auth/gmail.send` (only this scope); add the sender as a *test user*.
3. Create a second OAuth client (Web application) with redirect URI `https://developers.google.com/oauthplayground`.
4. Open Google OAuth Playground -> gear icon -> *Use your own OAuth credentials* -> enter that client ID/secret.
   Step 1: select Gmail API v1 `gmail.send`, authorise **signed in as the sender account**. Step 2: *Exchange authorization code for tokens*; copy the **refresh token**.
5. Store as env vars on the backend host: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER_EMAIL`.
6. **7-day expiry warning:** with consent screen = External + *Testing*, Google expires refresh tokens after 7 days (symptom: failed notifications with
   "refresh token invalid, revoked or expired"). Fix: move the consent screen to *In production* (Google may show an "unverified app" screen for sensitive scopes -
   acceptable for one sender account; check Google's current policy) or use a Workspace *Internal* app. Then re-generate the refresh token.
7. After a token problem is fixed, re-queue failed rows: `update notification_outbox set status='pending', next_attempt_at=now(), attempt_count=0 where status='failed';`

## 4. Flask API on Render (or Railway)
* New Web Service from the GitHub repo. Root directory `backend`. Build: `pip install -r requirements.txt`. Start: `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 30`.
* Health check path: `/api/health`.
* Env vars (see `backend/.env.example`): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FRONTEND_URL`, `CORS_ORIGINS` (exact frontend origin, no trailing slash), `FLASK_ENV=production`, `CRON_SECRET`, the four `GMAIL_*`.
* Retries: schedule `POST https://<api>/api/internal/notifications/process` with header `X-Cron-Secret: <value>` every ~5 minutes (Render Cron Job, or any external scheduler).
* Pricing/free-tier behaviour (e.g. sleeping instances causing slow first requests) changes - check the provider's current plans before relying on it.

## 5. Next.js on Vercel
* Import the repo, Root Directory `frontend`. Env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_BASE_URL` (the Render URL).
* After the first deploy, put the Vercel URL into Render's `FRONTEND_URL` + `CORS_ORIGINS`, and into Supabase's redirect allow-list (step 2.4). Redeploy.

## 6. Production verification checklist (do each, tick honestly)
1 Google sign-in works · 2 dashboard loads · 3 create task · 4 assign to a 2nd real account · 5 assignee gets email · 6 assignee completes it · 7 creator gets email ·
8 a 3rd account gets 404 on that task URL · 9 logout works · 10 refresh keeps the session · 11 browser console shows no CORS/redirect errors · 12 DevTools -> Sources/Network show no service-role key.
