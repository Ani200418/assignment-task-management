# Implementation Plan
1. Scaffold + docs  2. DB migrations + RLS  3. Flask auth  4. Task API + authorization
5. Outbox + Gmail service  6. Next.js frontend  7. Lint/type/build/tests  8. Docs  9. Manual setup + deployment (needs your accounts)

## Risks
| Risk | Mitigation |
|---|---|
| Supabase project still on legacy HS256 keys (JWKS empty) | Enable asymmetric signing keys; documented in DEPLOYMENT.md |
| Gmail refresh token expires in 7 days (consent screen in Testing) | Publish consent screen or use Workspace Internal; documented |
| Gmail send succeeds but process crashes before marking sent | At-least-once delivery; documented limitation |
| Sync email in request adds latency | Bounded timeout; cron sweep for retries |
