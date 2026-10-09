# Requirements & Acceptance Criteria

## Permission model (approved)
| Actor | Can do |
|---|---|
| Creator | view, edit title/description, reassign, change status, delete own tasks |
| Assignee | view assigned tasks, change status (incl. complete / reopen) |
| Anyone else | **404 Not Found** for any task they are not part of (we do not reveal that it exists) |

Authentication = *who are you?* (Google login, verified JWT). Authorization = *what may you do?* (the rules above, checked in Flask on every request).

## Functional criteria
| ID | Criterion |
|---|---|
| A1 | Sign in with Google via Supabase Auth; first login creates a `profiles` row |
| A2 | Logout clears the session; protected pages redirect to `/login` |
| A3 | Flask verifies the Supabase JWT (signature, issuer, audience, expiry) on every protected route |
| T1 | Create task (title, description, optional assignee) |
| T2 | List tasks filtered by role (all/created/assigned) and status, paginated |
| T3 | Task detail, edit, status change, reassign, delete (per permission table) |
| T4 | Assignee picker shows only id, name, email, avatar of registered users |
| N1 | Task assigned to someone else -> email to assignee |
| N2 | Task completed by someone other than creator -> email to creator |
| N3 | Self-assigned tasks and self-completed tasks send no email |
| N4 | Outbox row written in the same DB transaction as the task change |
| N5 | Idempotency key prevents duplicate emails; retries are bounded; failures recorded |

## Verification levels used in this project
1. **Implemented** - code exists
2. **Locally tested** - automated tests / commands were run in the dev sandbox
3. **Externally configured** - needs your Supabase / Google / hosting accounts
4. **Production verified** - checked on the real deployed URL

See `docs/STATUS.md` for the current level of every feature.
