-- LOCAL DEVELOPMENT ONLY. Clearly fake users. Never run against production.
insert into auth.users (id, email, raw_user_meta_data) values
  ('00000000-0000-0000-0000-0000000000a1', 'alice@example.test', '{"full_name":"Alice Example"}'),
  ('00000000-0000-0000-0000-0000000000b2', 'bob@example.test',   '{"full_name":"Bob Example"}')
on conflict do nothing;
