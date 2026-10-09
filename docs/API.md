# API reference

Base URL: `NEXT_PUBLIC_API_BASE_URL` (local: `http://localhost:5000`). JSON in, JSON out.
Auth: `Authorization: Bearer <Supabase access token>` on everything except `/api/health` and the cron endpoint.
Errors always look like `{"error": {"code": "...", "message": "...", "details": [...]}}`.

| Method & path | Who may call | Success | Errors |
|---|---|---|---|
| `GET /api/health` | anyone | 200 `{status:"ok"}` | |
| `GET /api/me` | signed-in | 200 `{user}` (creates profile if missing) | 401 |
| `GET /api/users/assignable` | signed-in | 200 `{users:[{id,email,full_name,avatar_url}]}` | 401 |
| `GET /api/tasks?role=all\|created\|assigned&status=&page=&page_size=` | signed-in | 200 `{tasks,page,page_size,total}` | 401, 422 |
| `GET /api/tasks/summary` | signed-in | 200 `{counts:{pending,in_progress,completed}}` | 401 |
| `POST /api/tasks` `{title, description?, assigned_to?}` | signed-in | 201 `{task, notification}` | 400, 401, 422 (`assignee_not_found`) |
| `GET /api/tasks/<id>` | creator, assignee | 200 `{task}` (+ `permissions`) | 401, 404 (also for strangers), 422 bad uuid |
| `PATCH /api/tasks/<id>` `{title?, description?}` | creator | 200 `{task}` | 403 (assignee), 404, 422 |
| `PATCH /api/tasks/<id>/status` `{status}` | creator, assignee | 200 `{task, notification}` | 404, 422 |
| `PATCH /api/tasks/<id>/assignee` `{assigned_to: uuid\|null}` | creator | 200 `{task, notification}` | 403, 404, 422 |
| `DELETE /api/tasks/<id>` | creator | 204 | 403, 404 |
| `POST /api/internal/notifications/process` header `X-Cron-Secret` | scheduler | 200 `{claimed,sent,retry,failed}` | 401, 404 (disabled when `CRON_SECRET` unset) |

`notification.status`: `not_required` (nobody to email) · `sent` (Gmail accepted) · `queued` (will retry / Gmail not configured) · `failed` (permanent error).
A write that saved the task but could not email still returns 2xx **with** the honest notification status; the UI shows it.

401 = we do not know who you are (no/invalid/expired token). 403 = we know you, but you may not do this. 404 = task missing **or not yours**.
