# Migrations

This project uses **one** migration system: the Supabase CLI convention.
The SQL files live in [`../supabase/migrations/`](../supabase/migrations/), ordered by their timestamp prefix.
This folder exists only so the migrations are easy to find; it contains no SQL of its own.

Apply them with `supabase db push` (see `docs/DEPLOYMENT.md`).
Never edit a migration that has already been applied to a real database; add a new file instead.
