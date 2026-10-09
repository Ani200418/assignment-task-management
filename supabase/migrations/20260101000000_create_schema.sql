-- profiles: one row per authenticated user (mirror of auth.users, public-safe fields only)
create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- tasks
create table public.tasks (
  id           uuid primary key default gen_random_uuid(),
  title        text not null check (char_length(btrim(title)) between 1 and 200),
  description  text not null default '' check (char_length(description) <= 5000),
  status       text not null default 'pending'
               check (status in ('pending', 'in_progress', 'completed')),
  created_by   uuid not null,
  assigned_to  uuid,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  completed_at timestamptz,
  constraint tasks_created_by_fkey  foreign key (created_by)  references public.profiles (id) on delete cascade,
  constraint tasks_assigned_to_fkey foreign key (assigned_to) references public.profiles (id) on delete set null,
  -- completed_at must be set exactly when status = completed
  constraint tasks_completed_at_matches_status
    check ((status = 'completed') = (completed_at is not null))
);
create index tasks_created_by_idx  on public.tasks (created_by, created_at desc);
create index tasks_assigned_to_idx on public.tasks (assigned_to, created_at desc);
create index tasks_status_idx      on public.tasks (status);

-- notification_outbox: emails waiting to be sent (transactional outbox pattern)
create table public.notification_outbox (
  id              uuid primary key default gen_random_uuid(),
  event_type      text not null check (event_type in ('task_assigned', 'task_completed')),
  task_id         uuid not null references public.tasks (id) on delete cascade,
  recipient_email text not null,
  payload         jsonb not null default '{}'::jsonb,
  dedupe_key      text not null unique,          -- idempotency: same key can only be inserted once
  status          text not null default 'pending'
                  check (status in ('pending', 'processing', 'sent', 'failed')),
  attempt_count   integer not null default 0 check (attempt_count >= 0),
  next_attempt_at timestamptz not null default now(),
  locked_at       timestamptz,
  last_error      text,
  created_at      timestamptz not null default now(),
  sent_at         timestamptz
);
create index outbox_due_idx on public.notification_outbox (status, next_attempt_at);

-- keep updated_at fresh
create function public.set_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end $$;
create trigger profiles_set_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger tasks_set_updated_at before update on public.tasks
  for each row execute function public.set_updated_at();

-- create a profile automatically when someone signs up through Supabase Auth
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', new.raw_user_meta_data ->> 'name'),
    coalesce(new.raw_user_meta_data ->> 'avatar_url', new.raw_user_meta_data ->> 'picture')
  )
  on conflict (id) do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();
