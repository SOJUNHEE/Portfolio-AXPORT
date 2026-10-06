-- (junhee) 2026-09-27 계정별 분석 결과(대시보드 문서 handoff-v1). 원본 엑셀·API 키·토큰은 저장하지 않음.
-- Supabase SQL Editor 에서 한 번 실행한다(202609270001 다음). 다시 실행해도 안전하다.
begin;

create table if not exists public.axport_assessments (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    doc jsonb not null,
    created_at timestamptz not null default now(),
    constraint axport_assessment_doc_object check (jsonb_typeof(doc) = 'object'),
    constraint axport_assessment_doc_size check (octet_length(doc::text) <= 2097152)
);
create index if not exists axport_assessments_user_idx on public.axport_assessments (user_id, created_at desc);

alter table public.axport_assessments enable row level security;
alter table public.axport_assessments force row level security;
revoke all on table public.axport_assessments from public, anon, authenticated;
grant select, insert, delete on table public.axport_assessments to authenticated;

drop policy if exists axport_assessment_owner_select on public.axport_assessments;
create policy axport_assessment_owner_select on public.axport_assessments
    for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists axport_assessment_owner_insert on public.axport_assessments;
create policy axport_assessment_owner_insert on public.axport_assessments
    for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists axport_assessment_owner_delete on public.axport_assessments;
create policy axport_assessment_owner_delete on public.axport_assessments
    for delete to authenticated using ((select auth.uid()) = user_id);

notify pgrst, 'reload schema';
commit;
