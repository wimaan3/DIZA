-- Draft Supabase/Postgres MVP schema. Local app currently uses SQLite, not this schema.
-- No browser access granted. Add verified role-specific policies before enabling clients.
create table if not exists public.responders (
 id uuid primary key default gen_random_uuid(), name text not null,
 skills text[] not null default '{}', status text not null default 'available'
);
create table if not exists public.reports (
 id uuid primary key default gen_random_uuid(), dedupe text unique not null,
 cluster_id uuid not null, location text not null, category text not null,
 summary text not null, evidence text, unknowns jsonb default '[]',
 severity text check (severity in ('P0','P1','P2','P3')), reason text,
 language text, source text, created timestamptz default now()
);
create table if not exists public.requests (
 id uuid primary key default gen_random_uuid(), report_id uuid unique references public.reports(id),
 status text not null default 'new', assignee uuid references public.responders(id),
 created timestamptz default now(), updated timestamptz default now()
);
create table if not exists public.assignment_attempts (
 id uuid primary key default gen_random_uuid(), request_id uuid references public.requests(id),
 responder_id uuid references public.responders(id), status text not null, expires timestamptz
);
create table if not exists public.events (
 id uuid primary key default gen_random_uuid(), request_id uuid references public.requests(id),
 ts timestamptz default now(), message text not null
);
alter table public.responders enable row level security;
alter table public.reports enable row level security;
alter table public.requests enable row level security;
alter table public.assignment_attempts enable row level security;
alter table public.events enable row level security;
-- Default deny for anon/authenticated; backend service role only until roles are implemented.
