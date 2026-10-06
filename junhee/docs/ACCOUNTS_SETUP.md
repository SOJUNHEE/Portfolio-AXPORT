# 회원가입·로그인·계정별 저장 설정 (junhee, 2026-09-27)

sanghyeob 작업본의 Supabase 로그인을 junhee 구조로 옮겼다. 코드: `junhee/server/`, 화면: `templates/junhee_login.html`·`junhee_account.html`, `static/js/junhee-auth.js`.

## 1. Supabase 프로젝트
1. Supabase 프로젝트를 만든다(또는 팀 프로젝트 사용). **Project Settings → API** 에서
   - Project URL → `SUPABASE_URL`
   - Publishable key(`sb_publishable_…`) → `SUPABASE_PUBLISHABLE_KEY`
   - secret / service_role 키는 쓰지 않는다(코드가 거부한다).
2. **Authentication → Sign In / Providers → Email**: Enable email provider, **Confirm email 켜기**.
3. **Authentication → URL Configuration** — **Site URL** 을 배포 주소(`https://<서비스 이름>.onrender.com`)로 바꾸고(기본값 localhost:3000 이면 링크가 엉뚱한 곳으로 감),
   **Redirect URLs** 에 인증 링크 주소를 등록한다(빠지면 인증 링크가 Site URL 로 가서 인증이 조용히 실패한다).
   - 로컬: `http://127.0.0.1:5073/auth/confirm`, `http://localhost:5073/auth/confirm`
   - Render: `https://<서비스 이름>.onrender.com/auth/confirm`
4. **Authentication → Emails → Confirm signup** 본문을 `junhee/supabase/templates/confirm_signup.html` 로 바꾼다.
   링크가 `{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=email` 형식이어야 한다.
5. 인증 메일 발송: Supabase 기본 메일은 **프로젝트 팀원 주소로만, 시간당 몇 통**만 보낸다. 다른 주소로 받으려면
   **Authentication → Emails → SMTP Settings** 에 SMTP(예: Gmail 앱 비밀번호, Mailtrap, Resend)를 넣는다.
   메일 계정 정보는 Supabase 에만 넣고 이 저장소·.env 에는 두지 않는다.
6. **SQL Editor** 에서 아래 두 파일을 순서대로 한 번씩 실행한다(다시 실행해도 안전).
   - `junhee/supabase/migrations/202609270001_junhee_workspace.sql` — 계정별 바탕화면(파일·폴더·위치·분석 조건)
   - `junhee/supabase/migrations/202609270002_junhee_assessments.sql` — 계정별 분석 결과(대시보드 문서)

## 2. .env (커밋 금지)
`.env.example` 의 항목을 루트 `.env` 에 채운다.
```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
FLASK_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))" 결과>
SESSION_COOKIE_SECURE=false        # 로컬 http. Render 에서는 지우거나 true
```
값이 없으면 서버는 뜨지만 `/app` 에 '로그인 설정이 필요합니다' 안내가 나온다(홈·챗봇은 그대로).

## 3. 수출적합성 계산 (sanghyeob 분석 엔진으로 통일, 2026-09-27)
- **모든 파일을 엔진으로 계산**한다: 바탕화면 샘플도 업로드 파일도 같은 엔진(참고 적합도 v1). 기존 junhee 등록 샘플 점수표 경로는 쓰지 않는다(`workspace.js` 의 `ENGINE_ONLY`).
- 바탕화면 샘플 = 가온반도체 · 누리하이테크 · 미리내전자(결측 예시), 모두 간편입력 v2 가상 기업 (`junhee/data/engine_samples.json`, 파일은 `static/samples/`).
  목록에는 한빛·대성(상세양식)·한울·다온도 있다. 샘플(또는 같은 파일을 다시 올린 경우)의 결과는 '샘플 기업 (가상)'으로 표시된다.
- 양식 다운로드: `static/templates/company-data-template.xlsx` (sanghyeob 과 같은 파일·경로). 업로드 창·업로드 가이드·위젯 모두 이 한 파일.
- 원본 자료: `junhee/data/raw/test1_*` (sanghyeob/sanghyeop/test1_* 과 같은 파일, git 에 포함 → Render 에서도 읽힘).
- 외부 자료 API 키: `UN_COMTRADE_API_KEY` · `KCS_TRADE_API_KEY`(공공데이터포털 서비스키) · `ECOS_API_KEY` · `LAW_API_KEY`.
  로컬은 루트 `.env`, Render 는 아래 4번. 첫 분석은 공개 통계 조회로 2~3분, 같은 품목은 24시간 캐시.
- 판단 기준: 시장성 40·가격 20·물류 10·안정성 10(100점 환산), 규제는 별도 관문, 근거 없는 항목은 정책 기준 50점 + 근거 반영률.
  원가·희망가·공급계획 평가는 간편입력 양식에만 적용(상세양식 샘플은 가격·물류가 '자료 부족').

## 4. Render
루트의 `.env.render`(git 제외, 로컬에서만 생성)를 Render 대시보드 → 서비스 → **Environment → Add from .env** 에 붙여 넣는다
(Supabase 2개 + 엔진 API 키 4개). `FLASK_SECRET_KEY` 는 render.yaml 의 generateValue 로 Render 가 만든다.
SESSION_COOKIE_SECURE 는 넣지 않는다(Render 에서 자동 true). Supabase Redirect URLs 에 `https://<서비스>.onrender.com/auth/confirm` 을 추가한다. Render 는 `RENDER` 변수를 자동으로 주므로
프록시(https) 처리가 켜진다. 세션 DB(`instance/auth-sessions.sqlite3`)는 무료 서버 재배포 때 지워져 **재배포 후에는 다시 로그인**해야 한다.
계정별 작업(파일·폴더 정리, 분석 조건)은 Supabase 에 있으므로 사라지지 않는다.

### Render 배포 체크리스트 (2026-09-27 배포 QA)
- `AXPORT_PUBLIC_URL=https://<서비스>.onrender.com` 을 꼭 넣는다(인증 메일 링크 기준 주소, 챗봇 live 허용 주소).
- Supabase: Site URL · Redirect URL · Confirm email · 메일 템플릿 · SMTP · 마이그레이션 2개(위 1번) 확인.
- 무료 플랜(512MB)이라 `render.yaml` 은 gunicorn 워커 1개·스레드 8개, Python 3.14.7 로 고정했다.
- 서버 디스크(`instance/`)의 업로드 원본·진행 중 분석·로그인 세션·24시간 캐시·Contact Us 접수는 재배포·재시작·유휴 절전 때 지워진다.
  완료된 분석 결과와 바탕화면은 Supabase 에 남는다. 원본이 없으면 화면이 '파일을 다시 올려 주세요'로 안내한다.
- 챗봇은 `AXPORT_CHAT_MODE=demo` 가 기본(예시 답변). live 로 바꾸면 `OPENAI_API_KEY`·`OPENAI_MODEL` 이 필요하고, `/api/chat` 은 로그인 없이 호출되므로 OpenAI 쪽 사용량 한도를 먼저 정한다.
- 배포 직후 스모크: 가입 → 인증 메일 → 로그인 → 샘플 분석 → 업로드 분석 → 가중치 → 보고서 → 로그아웃·재로그인.

## 5. 흐름
- `/app` → 로그인 화면(로그인 필수). '회원가입' → 이메일·비밀번호 → 인증 메일 발송 → 60초 뒤 재발송 가능.
- 메일의 '이메일 인증하기' → `/auth/confirm` → '인증 완료' 안내(자동 로그인은 하지 않음) → 로그인 → 워크스페이스.
- 오른쪽 위 원형 버튼(이메일 앞 두 글자) → 내 계정 창 → 로그아웃.

## 6. 테스트
```
python -m unittest discover -s junhee/tests -t . -v
python junhee/scripts/check_accounts_browser.py   # 브라우저 점검(가짜 Supabase, 앱을 따로 띄우지 않음)
```
Supabase·외부 API 는 가짜 응답·키 없음으로 대신한다. 실제 메일 수신은 위 설정 후 직접 가입해 확인한다.
