-- (junhee) 2026-09-27 계정별 바탕화면 상태(파일·폴더 이름과 위치, 파일별 분석 조건, 마지막 분석). 원본 파일·비밀번호·토큰은 저장하지 않음.
-- Supabase SQL Editor 에서 한 번 실행한다. 다시 실행해도 안전하다.
-- sanghyeob 의 workspace_manifests 와 이름이 겹치지 않도록 axport_workspaces 를 쓴다(같은 Supabase 프로젝트를 써도 섞이지 않음).
begin;

create table if not exists public.axport_workspaces (
    user_id uuid primary key references auth.users(id) on delete cascade,
    revision bigint not null default 1 check (revision >= 1),
    state jsonb not null,
    updated_at timestamptz not null default now(),
    constraint axport_workspace_state_object check (jsonb_typeof(state) = 'object'),
    constraint axport_workspace_state_size check (octet_length(state::text) <= 524288)
);

alter table public.axport_workspaces enable row level security;
alter table public.axport_workspaces force row level security;
revoke all on table public.axport_workspaces from public, anon, authenticated;
grant select on table public.axport_workspaces to authenticated;

drop policy if exists axport_workspace_owner_select on public.axport_workspaces;
create policy axport_workspace_owner_select on public.axport_workspaces
    for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists axport_workspace_owner_insert on public.axport_workspaces;
create policy axport_workspace_owner_insert on public.axport_workspaces
    for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists axport_workspace_owner_update on public.axport_workspaces;
create policy axport_workspace_owner_update on public.axport_workspaces
    for update to authenticated using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

-- 클라이언트는 직접 쓰지 못한다. 이 함수만 쓰기 가능: 소유자 인자를 받지 않고 모든 쓰기를 auth.uid() 에 묶는다.
-- revision 이 기대값과 같을 때만 저장해, 오래된 탭이 최신 저장을 덮어쓰지 못하게 한다.
create or replace function public.save_axport_workspace(
    p_expected_revision bigint, p_state jsonb
) returns setof public.axport_workspaces
language plpgsql
security definer
set search_path = ''
as $$
declare
    owner_id uuid := auth.uid();
begin
    if owner_id is null then
        raise sqlstate 'PT401' using message = 'authentication_required';
    end if;
    if p_expected_revision is null or p_expected_revision < 0
       or p_state is null or jsonb_typeof(p_state) <> 'object' then
        raise sqlstate 'PT400' using message = 'invalid';
    end if;
    if p_expected_revision = 0 then
        return query
            insert into public.axport_workspaces as ws (user_id, revision, state)
            values (owner_id, 1, p_state)
            on conflict (user_id) do nothing
            returning ws.*;
    else
        return query
            update public.axport_workspaces as ws
            set state = p_state, revision = ws.revision + 1, updated_at = now()
            where ws.user_id = owner_id and ws.revision = p_expected_revision
            returning ws.*;
    end if;
    if not found then
        raise sqlstate 'PT409' using message = 'conflict';
    end if;
end;
$$;

revoke all on function public.save_axport_workspace(bigint, jsonb) from public, anon;
grant execute on function public.save_axport_workspace(bigint, jsonb) to authenticated;

notify pgrst, 'reload schema';
commit;
