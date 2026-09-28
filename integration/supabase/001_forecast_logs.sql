-- FarmNex: table that keeps a copy of every forecast answer shown to a farmer.
-- How to run: Supabase dashboard -> SQL Editor -> New query -> paste this whole file -> Run.
-- Safe to run twice (it only creates things that don't exist yet).

create table if not exists public.forecast_logs (
    id          bigint generated always as identity primary key,
    created_at  timestamptz not null default now(),
    user_id     uuid references auth.users (id) on delete set null,  -- who asked (null = not logged in)
    kind        text not null check (kind in ('price', 'demand', 'sell_options', 'crops')),
    request     jsonb not null,   -- what was asked, e.g. {"market": "Pune", "crop": "Onion", "days": 3}
    response    jsonb not null,   -- the full answer the app showed
    data_as_of  date              -- last date of real mandi data behind the answer
);

create index if not exists forecast_logs_user_idx on public.forecast_logs (user_id, created_at desc);
create index if not exists forecast_logs_kind_idx on public.forecast_logs (kind, created_at desc);

-- Security: farmers can read ONLY their own rows from the app; nobody can write from the app.
-- Your backend writes with the service_role key, which bypasses these rules.
alter table public.forecast_logs enable row level security;

drop policy if exists "read own forecast logs" on public.forecast_logs;
create policy "read own forecast logs" on public.forecast_logs
    for select to authenticated
    using (auth.uid() = user_id);
