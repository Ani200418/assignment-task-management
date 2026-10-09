"""Applies the SQL migrations to a throw-away real PostgreSQL and checks the important behaviour.
Supabase-specific pieces (auth schema, roles, auth.uid()) are stubbed below.
Run:  python scripts/test_migrations.py      (needs: pip install pgserver psycopg[binary])
"""
import pathlib, sys, tempfile
import pgserver, psycopg

ROOT = pathlib.Path(__file__).resolve().parents[1] / "supabase"
STUB = """
create schema auth;
create table auth.users (id uuid primary key, email text, raw_user_meta_data jsonb default '{}');
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.sub', true), '')::uuid $$;
create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
grant usage on schema public, auth to anon, authenticated, service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant all on all tables in schema public to service_role;
"""
A, B, C = ("00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000b2",
           "00000000-0000-0000-0000-0000000000c3")
results = []
def check(name, cond):
    results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)

def main():
    srv = pgserver.get_server(tempfile.mkdtemp(), cleanup_mode="stop")
    with psycopg.connect(srv.get_uri(), autocommit=True) as db:
        db.execute(STUB)
        for f in sorted((ROOT / "migrations").glob("*.sql")):
            db.execute(f.read_text())
        # grants for tables must come after tables exist (stub ran before): re-grant
        db.execute("grant select, insert, update, delete on all tables in schema public to authenticated;"
                   "grant all on all tables in schema public to service_role;")
        db.execute((ROOT / "seed.sql").read_text())
        db.execute(f"insert into auth.users (id,email,raw_user_meta_data) values ('{C}','carol@example.test','{{\"full_name\":\"Carol\"}}')")

        n = db.execute("select count(*) from public.profiles").fetchone()[0]
        check("trigger created a profile for every auth user", n == 3)

        def one(sql, *a): return db.execute(sql, a).fetchone()[0]

        # create_task: assigned to someone else -> exactly one outbox row
        r = one("select public.create_task(%s,'T1','d',%s)", A, B)
        check("create_task returns task_id and outbox_id", r["task_id"] and r["outbox_id"])
        check("assignment outbox row targets assignee",
              one("select recipient_email from notification_outbox where id=%s", r["outbox_id"]) == "bob@example.test")
        # self-assigned -> no outbox
        r2 = one("select public.create_task(%s,'Self','d',%s)", A, A)
        check("self-assigned task creates NO outbox row", r2["outbox_id"] is None)
        # unknown assignee -> FK violation
        try:
            db.execute("select public.create_task(%s,'X','',%s)", (A, "00000000-0000-0000-0000-00000000ffff")); ok = False
        except psycopg.errors.ForeignKeyViolation: ok = True
        check("assigning to a nonexistent user is rejected by the foreign key", ok)

        # completion by assignee -> one email to creator; repeat -> none
        s1 = one("select public.set_task_status(%s,'completed',%s)", r["task_id"], B)
        check("completion by assignee creates outbox row", s1["outbox_id"] is not None)
        check("completion email goes to creator",
              one("select recipient_email from notification_outbox where id=%s", s1["outbox_id"]) == "alice@example.test")
        s2 = one("select public.set_task_status(%s,'completed',%s)", r["task_id"], B)
        check("completing an already-completed task creates NO second email", s2["outbox_id"] is None)
        check("exactly 2 outbox rows for the task", one("select count(*) from notification_outbox where task_id=%s", r["task_id"]) == 2)
        # completed_at constraint
        try:
            db.execute("update tasks set status='completed', completed_at=null where id=%s", (r["task_id"],)); ok = False
        except psycopg.errors.CheckViolation: ok = True
        check("CHECK forbids completed task without completed_at", ok)
        # creator completes own task -> no email
        r3 = one("select public.create_task(%s,'Mine','',%s)", A, B)
        one("select public.set_task_status(%s,'in_progress',%s)", r3["task_id"], B)
        s3 = one("select public.set_task_status(%s,'completed',%s)", r3["task_id"], A)
        check("creator completing own assigned task sends no email", s3["outbox_id"] is None)
        # reopen then complete again -> new email allowed
        one("select public.set_task_status(%s,'pending',%s)", r["task_id"], A)
        s4 = one("select public.set_task_status(%s,'completed',%s)", r["task_id"], B)
        check("reopen + complete again sends a fresh completion email", s4["outbox_id"] is not None)
        # reassign A->C emails C; reassign to same person does not duplicate
        r5 = one("select public.create_task(%s,'Re','',null)", A)
        q1 = one("select public.reassign_task(%s,%s)", r5["task_id"], C)
        q2 = one("select public.reassign_task(%s,%s)", r5["task_id"], C)
        check("reassign emails new assignee once", q1["outbox_id"] and q2["outbox_id"] is None)
        # duplicate dedupe_key blocked
        try:
            db.execute("insert into notification_outbox(event_type,task_id,recipient_email,dedupe_key) "
                       "select event_type,task_id,recipient_email,dedupe_key from notification_outbox limit 1"); ok = False
        except psycopg.errors.UniqueViolation: ok = True
        check("UNIQUE(dedupe_key) blocks duplicate outbox rows", ok)

        # claim: returns due rows once, increments attempts
        c1 = db.execute("select count(*) from public.claim_notifications(null, 100)").fetchone()[0]
        c2 = db.execute("select count(*) from public.claim_notifications(null, 100)").fetchone()[0]
        check("claim_notifications claims due rows, second call claims none", c1 > 0 and c2 == 0)
        check("attempt_count incremented on claim", one("select min(attempt_count) from notification_outbox where status='processing'") == 1)
        db.execute("update notification_outbox set locked_at = now() - interval '11 minutes' where status='processing'")
        c3 = db.execute("select count(*) from public.claim_notifications(null, 100)").fetchone()[0]
        check("stale 'processing' rows are reclaimed", c3 == c1)

        # RLS: as authenticated user B
        def as_user(uid, sql):
            with db.transaction():
                db.execute("set local role authenticated")
                db.execute(f"select set_config('request.jwt.sub','{uid}',true)")
                return db.execute(sql).fetchall()
        seen = as_user(C, "select id from tasks")
        check("RLS: user C sees only their own/assigned tasks", len(seen) == 1)
        check("RLS: user sees only own profile", len(as_user(B, "select id from profiles")) == 1)
        check("RLS: outbox invisible to normal users", as_user(B, "select * from notification_outbox") == [])
        # these must fail with a PERMISSION error specifically (not a typo / other error)
        def denied(uid, sql):
            try: as_user(uid, sql)
            except psycopg.errors.InsufficientPrivilege: return True
            return False
        check("RLS: normal users cannot insert tasks directly (permission error)",
              denied(B, f"insert into tasks(title,created_by) values ('hack','{B}')"))
        check("RLS: normal users cannot update others' tasks directly (no row visible/permission)",
              as_user(C, f"with u as (update tasks set title='pwn' where created_by='{A}' returning 1) select * from u") == [])
        check("RPC functions are not callable by normal users (permission error)",
              denied(B, f"select public.create_task('{B}','x','',null)"))
    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results)-len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)

main()
