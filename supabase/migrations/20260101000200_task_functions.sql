-- Each function below changes a task AND writes its outbox row inside ONE transaction
-- (a function body is atomic). They are callable only by the service role (Flask).

create function public.create_task(
  p_creator uuid, p_title text, p_description text, p_assignee uuid
) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  t public.tasks;
  a public.profiles;
  c public.profiles;
  v_outbox uuid;
begin
  insert into public.tasks (title, description, created_by, assigned_to)
  values (btrim(p_title), coalesce(p_description, ''), p_creator, p_assignee)
  returning * into t;

  if p_assignee is not null and p_assignee <> p_creator then
    select * into a from public.profiles where id = p_assignee;
    select * into c from public.profiles where id = p_creator;
    insert into public.notification_outbox (event_type, task_id, recipient_email, payload, dedupe_key)
    values ('task_assigned', t.id, a.email,
            jsonb_build_object('task_title', t.title, 'task_description', t.description,
                               'actor_name', coalesce(c.full_name, c.email), 'recipient_name', coalesce(a.full_name, a.email)),
            'task_assigned:' || t.id || ':' || p_assignee)
    on conflict (dedupe_key) do nothing
    returning id into v_outbox;
  end if;
  return jsonb_build_object('task_id', t.id, 'outbox_id', v_outbox);
end $$;

create function public.reassign_task(p_task uuid, p_assignee uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  t public.tasks;
  old_assignee uuid;
  a public.profiles;
  c public.profiles;
  v_outbox uuid;
begin
  select * into t from public.tasks where id = p_task for update;   -- lock row: no concurrent edits
  if not found then raise exception 'task_not_found'; end if;
  old_assignee := t.assigned_to;
  update public.tasks set assigned_to = p_assignee where id = p_task returning * into t;

  if p_assignee is not null and p_assignee <> t.created_by and p_assignee is distinct from old_assignee then
    select * into a from public.profiles where id = p_assignee;
    select * into c from public.profiles where id = t.created_by;
    insert into public.notification_outbox (event_type, task_id, recipient_email, payload, dedupe_key)
    values ('task_assigned', t.id, a.email,
            jsonb_build_object('task_title', t.title, 'task_description', t.description,
                               'actor_name', coalesce(c.full_name, c.email), 'recipient_name', coalesce(a.full_name, a.email)),
            'task_assigned:' || t.id || ':' || p_assignee)
    on conflict (dedupe_key) do nothing
    returning id into v_outbox;
  end if;
  return jsonb_build_object('task_id', t.id, 'outbox_id', v_outbox);
end $$;

create function public.set_task_status(p_task uuid, p_status text, p_actor uuid) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  t public.tasks;
  actor public.profiles;
  creator public.profiles;
  v_outbox uuid;
begin
  select * into t from public.tasks where id = p_task for update;
  if not found then raise exception 'task_not_found'; end if;

  -- already in that status: do nothing, so repeated requests can never send a second email
  if t.status = p_status then
    return jsonb_build_object('task_id', t.id, 'outbox_id', null);
  end if;

  update public.tasks
     set status = p_status,
         completed_at = case when p_status = 'completed' then now() else null end
   where id = p_task returning * into t;

  if p_status = 'completed' and p_actor <> t.created_by then
    select * into actor   from public.profiles where id = p_actor;
    select * into creator from public.profiles where id = t.created_by;
    insert into public.notification_outbox (event_type, task_id, recipient_email, payload, dedupe_key)
    values ('task_completed', t.id, creator.email,
            jsonb_build_object('task_title', t.title, 'actor_name', coalesce(actor.full_name, actor.email),
                               'recipient_name', coalesce(creator.full_name, creator.email),
                               'completed_at', t.completed_at),
            'task_completed:' || t.id || ':' || extract(epoch from t.completed_at)::text)
    on conflict (dedupe_key) do nothing
    returning id into v_outbox;
  end if;
  return jsonb_build_object('task_id', t.id, 'outbox_id', v_outbox);
end $$;

-- Claim emails for sending. FOR UPDATE SKIP LOCKED lets two workers run at once without
-- grabbing the same row. 'processing' rows stuck for >10 minutes (crashed worker) are reclaimed.
create function public.claim_notifications(p_ids uuid[] default null, p_limit integer default 10)
returns setof public.notification_outbox
language plpgsql security definer set search_path = '' as $$
begin
  return query
  with due as (
    select id from public.notification_outbox
     where ((status = 'pending' and next_attempt_at <= now())
         or (status = 'processing' and locked_at < now() - interval '10 minutes'))
       and (p_ids is null or id = any (p_ids))
     order by next_attempt_at
     limit p_limit
     for update skip locked
  )
  update public.notification_outbox o
     set status = 'processing', locked_at = now(), attempt_count = o.attempt_count + 1
    from due where o.id = due.id
  returning o.*;
end $$;

-- Only the service role may call these. Normal users (anon/authenticated) may not.
revoke all on function public.create_task(uuid, text, text, uuid)      from public, anon, authenticated;
revoke all on function public.reassign_task(uuid, uuid)                from public, anon, authenticated;
revoke all on function public.set_task_status(uuid, text, uuid)        from public, anon, authenticated;
revoke all on function public.claim_notifications(uuid[], integer)     from public, anon, authenticated;
grant execute on function public.create_task(uuid, text, text, uuid)   to service_role;
grant execute on function public.reassign_task(uuid, uuid)             to service_role;
grant execute on function public.set_task_status(uuid, text, uuid)     to service_role;
grant execute on function public.claim_notifications(uuid[], integer)  to service_role;
