# Database

| Table | Purpose | Key relationships |
|---|---|---|
| `profiles` | Public-safe copy of each user (email, name, avatar). Auto-created by a trigger on `auth.users`. | `id` -> `auth.users.id` (cascade) |
| `tasks` | The tasks. | `created_by` -> `profiles` (cascade), `assigned_to` -> `profiles` (set null) |
| `notification_outbox` | Emails waiting to be sent / already sent. | `task_id` -> `tasks` (cascade) |

Constraints worth knowing: status CHECK; `completed_at` is set **iff** status is `completed`; `dedupe_key` is UNIQUE (idempotency).
Indexes: tasks by creator, assignee, status; outbox by (status, next_attempt_at).

SQL functions (service role only): `create_task`, `reassign_task`, `set_task_status` (task change + outbox row in one transaction),
`claim_notifications` (`FOR UPDATE SKIP LOCKED` so two workers never take the same email).

Security: RLS is on for all tables. Users may read only their own profile and tasks they participate in; there are no write policies;
the outbox has no policies. Flask uses the service role (bypasses RLS) and enforces the same rules in Python.

Tested: `python scripts/test_migrations.py` runs every migration on a real embedded PostgreSQL with a stubbed Supabase `auth` schema
(23 checks). It does NOT test real Supabase, so migrations must still be applied to your project (see DEPLOYMENT.md).
