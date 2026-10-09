-- Row Level Security: the database itself refuses access that the rules do not allow.
-- NOTE: Flask uses the service-role key, which BYPASSES RLS. Flask therefore enforces
-- the same rules in Python. RLS protects against any query made with a normal user key.
alter table public.profiles            enable row level security;
alter table public.tasks               enable row level security;
alter table public.notification_outbox enable row level security;

-- a user may read only their own profile (the assignee list is served by Flask, not by direct reads)
create policy profiles_select_own on public.profiles
  for select to authenticated using (id = (select auth.uid()));

-- a user may read only tasks they created or are assigned to. No insert/update/delete policies
-- exist, so direct writes by normal users are denied; all writes go through Flask.
create policy tasks_select_participants on public.tasks
  for select to authenticated
  using (created_by = (select auth.uid()) or assigned_to = (select auth.uid()));

-- notification_outbox: RLS enabled with NO policies = nobody but the service role can touch it.
