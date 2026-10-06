# AXPORT 조원용 설치·설정 안내

이 폴더는 **API 키와 개인 계정 정보를 뺀 배포본**입니다. 받은 그대로 실행하면 챗봇·위젯은 **예시(demo) 모드**로 동작합니다. 실제 데이터와 AI 연결은 **각자 발급받은 키**를 `.env`에 넣어야 켜집니다.

> 키 사용량과 요금은 키를 넣은 사람의 계정에 청구됩니다. 다른 사람의 키를 받아 쓰거나 내 키를 공유하지 마세요.

---

## 0. 이 배포본에 들어 있지 않은 것

| 빠진 것 | 이유 | 대신 할 일 |
|---|---|---|
| `.env` (모든 API 키·비밀값) | 개인 키 보호 | `.env.example`을 복사해 본인 값 입력 (2단계) |
| Supabase 프로젝트 주소·키 | 개인 프로젝트 | 본인 Supabase 프로젝트 생성 (3단계) |
| `instance/` 폴더 (로그인 세션, 분석 결과 DB, Contact 접수 내역) | 개인정보 포함 | 실행하면 자동으로 새로 생성됨 |
| 개인 키 파일(`*api 키*.txt`) 자동 읽기 | 개인 키 보호 | 필요하면 `AXPORT_KEY_FILE`에 본인 파일 경로를 직접 지정 |
| Render 배포 설정값 | 개인 배포 | 본인 Render 계정으로 배포 (6단계) |

---

## 1. 설치와 첫 실행 (키 없이)

Python 3.14 권장(3.14.7에서 검증). PowerShell에서 프로젝트 폴더를 열고 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

두 번째 실행부터는 `.\start.ps1`만 실행하면 됩니다.

- 홈: http://127.0.0.1:5073/ (키 없이 바로 확인 가능)
- 작업공간: http://127.0.0.1:5073/app (**로그인 필요.** 3단계를 하기 전에는 "설정 필요" 안내가 뜨는 것이 정상)

---

## 2. `.env` 채우기

`.env.example`을 복사해 만든 `.env` 파일을 엽니다. 쓰려는 기능의 값만 채우면 되고, 비워 둔 기능은 꺼지거나 예시 값으로 동작합니다.

| 기능 | 필요한 항목 | 없을 때 |
|---|---|---|
| 로그인·작업공간 | `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `FLASK_SECRET_KEY` | `/app` 접속 불가(설정 안내 화면) |
| AI 챗봇 | `AXPORT_CHAT_MODE=live`, `OPENAI_API_KEY`, `OPENAI_MODEL` | 예시 답변 |
| 분석 엔진 외부 자료 | `UN_COMTRADE_API_KEY`, `KCS_TRADE_API_KEY`, `ECOS_API_KEY`, `LAW_API_KEY` | 해당 지표만 '검색 불가', 분석은 계속됨 |
| 바탕화면 위젯 | `AXPORT_DATA_MODE=live`, `EXCHANGERATE_API_KEY`, `THENEWS_API_KEY`, `CUSTOMS_API_KEY`, `AXPORT_WEATHER_JSON` | 예시 값 |

`FLASK_SECRET_KEY`는 아래 명령으로 만든 값을 넣습니다.

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

각 키의 발급 주소는 `.env.example` 주석에 적혀 있습니다. 값을 바꾼 뒤에는 서버를 껐다가(Ctrl+C) 다시 실행해야 적용됩니다.

---

## 3. 로그인(Supabase) 설정

작업공간(`/app`)을 쓰려면 필요합니다. 자세한 화면 순서는 [junhee/docs/ACCOUNTS_SETUP.md](junhee/docs/ACCOUNTS_SETUP.md)에 있습니다. 요약:

1. https://supabase.com 에서 새 프로젝트를 만듭니다.
2. **Project Settings → API**에서 Project URL과 Publishable key(`sb_publishable_…`)를 `.env`에 넣습니다. secret/service_role 키는 넣지 않습니다.
3. **Authentication → URL Configuration → Redirect URLs**에 `http://127.0.0.1:5073/auth/confirm`을 추가합니다.
4. **Authentication → Emails → Confirm signup** 본문을 [junhee/supabase/templates/confirm_signup.html](junhee/supabase/templates/confirm_signup.html) 내용으로 바꿉니다.
5. **SQL Editor**에서 아래 두 파일을 순서대로 실행합니다.
   - [junhee/supabase/migrations/202609270001_junhee_workspace.sql](junhee/supabase/migrations/202609270001_junhee_workspace.sql)
   - [junhee/supabase/migrations/202609270002_junhee_assessments.sql](junhee/supabase/migrations/202609270002_junhee_assessments.sql)
6. Supabase 기본 메일은 프로젝트 멤버에게만, 시간당 몇 통만 발송됩니다. 다른 주소로 가입 메일을 받으려면 **SMTP Settings**에 본인 메일 계정을 설정합니다. 메일 계정 정보는 Supabase에만 넣고 이 폴더에는 두지 않습니다.

---

## 4. AI 챗봇 켜기 (선택)

```env
AXPORT_CHAT_MODE=live
OPENAI_API_KEY=sk-...        # 본인 키
OPENAI_MODEL=gpt-4.1-mini    # 사용할 모델 이름
```

- 서버가 OpenAI를 호출하고, 브라우저에는 키가 전달되지 않습니다.
- 답변 성격·말투는 [minjung/AXPORT_widget/chatbot_persona.md](minjung/AXPORT_widget/chatbot_persona.md)에서 바꿉니다.
- 호출 코드는 [minjung/AXPORT_widget/chatbot.py](minjung/AXPORT_widget/chatbot.py)의 `generate_answer()`에 있습니다. 다른 AI 서비스를 쓰려면 이 함수만 바꾸면 됩니다.

---

## 5. 위젯·공개 통계 자료 갱신 (선택)

- 위젯 실시간 조회: `.env`에 `AXPORT_DATA_MODE=live`와 위젯 키를 넣습니다. 수출기상도 JSON 만드는 법은 [minjung/AXPORT_widget/_axport_semiconductor_widgets/](minjung/AXPORT_widget/_axport_semiconductor_widgets/)의 안내 txt 파일에 있습니다.
- 공식 자료 자동 갱신(환율·뉴스·수출기상도): `.env`에 `AXPORT_WIDGET_REFRESH=1`, `ECOS_API_KEY`, `KCS_TRADE_API_KEY`를 넣습니다.
- 키를 넣고 챗봇·위젯 갱신을 한 번에 켜서 실행하려면 `python junhee/scripts/run_live.py`를 실행합니다.
- 대시보드 공개 통계를 다시 만드는 순서는 [junhee/README.md](junhee/README.md)를 참고합니다.

---

## 6. Render에 본인 계정으로 배포 (선택)

1. 이 폴더를 **본인 GitHub 저장소**에 올립니다(`.env`는 `.gitignore`에 있어 올라가지 않습니다).
2. Render → **New → Blueprint** → 저장소 선택. [render.yaml](render.yaml)을 읽어 서비스를 만듭니다. 서비스 이름(`name: axport`)과 브랜치(`branch: main`)는 필요하면 바꿉니다.
3. Render 대시보드 → **Environment**에 `.env`에서 쓰는 값을 직접 입력합니다(`sync: false` 항목). `FLASK_SECRET_KEY`는 Render가 자동으로 만들고, `SESSION_COOKIE_SECURE`는 넣지 않습니다.
4. `AXPORT_PUBLIC_URL=https://<서비스 이름>.onrender.com`을 넣고, Supabase Redirect URLs에 `https://<서비스 이름>.onrender.com/auth/confirm`을 추가합니다.
5. 챗봇 AI를 켜려면 `render.yaml`의 `AXPORT_CHAT_MODE` 값을 `live`로 바꾸거나 Render 대시보드에서 덮어씁니다(기본값은 `demo`).

---

## 7. 어디를 고치면 되나

| 바꾸고 싶은 것 | 파일 |
|---|---|
| 키 읽는 순서(스크립트용) | [junhee/scripts/api_keys.py](junhee/scripts/api_keys.py) |
| 로그인·세션 | [junhee/server/accounts.py](junhee/server/accounts.py) |
| 분석 엔진 | [junhee/server/engine/](junhee/server/engine/) |
| 챗봇 | [minjung/AXPORT_widget/chatbot.py](minjung/AXPORT_widget/chatbot.py), [static/js/chatbot.js](static/js/chatbot.js) |
| 위젯 | [minjung/AXPORT_widget/_axport_semiconductor_widgets/sx_widgets/](minjung/AXPORT_widget/_axport_semiconductor_widgets/sx_widgets/) |
| 화면 | `templates/`, `static/css/`, `static/js/` (자세한 표는 [README.md](README.md)의 "수정 위치") |

---

## 8. 키 관리 규칙

- 키는 `.env`(로컬) 또는 Render Environment(배포)에만 넣습니다. 코드·md·이미지·채팅방에 붙여 넣지 않습니다.
- 커밋 전에 `git status`로 `.env`가 목록에 없는지 확인합니다.
- 키가 노출되었다면 즉시 발급처에서 폐기하고 새로 발급합니다. 커밋 이력에 남은 키는 삭제해도 복구될 수 있으므로 반드시 폐기해야 합니다.

---

## (배포하는 사람용) 깨끗한 배포본 만들기

폴더를 통째로 압축하면 `.gitignore`에 있는 `.env`, `.env.render`, `instance/`(개인정보·DB), `.venv/`, `node_modules/`, `.git/`까지 들어가 수백 MB가 되고 키도 함께 나갑니다. **변경 사항을 커밋한 뒤 Git에 등록된 파일만 압축**하세요.

```powershell
git archive --format=zip -9 -o AXPORT_team.zip HEAD
```

- 결과 크기: 약 21MB (폴더 통째 압축 대비 대폭 감소, 2026-09-30 기준)
- 만든 압축 파일 안에 `.env`, `instance/`가 없는지 한 번 열어 확인한 뒤 전달합니다.

**압축본에서 자동으로 빠지는 파일** (`.gitattributes`의 `export-ignore`. 저장소에는 그대로 남음)

| 제외 | 이유 |
|---|---|
| `junhee/data/raw/test1_regulations/`의 별표·고시 PDF/HWP/HWPX 원문 | 분석 엔진·스크립트가 읽지 않는 참고 원문 |
| `junhee/test-results/`, `minjung/AXPORT_widget/test-results/` | 테스트 스크린샷 결과물 |
| `static/assets/earth-*` | 화면에서 쓰지 않는 이미지 |
| `static/vendor/phosphor/regular/selection.json` | 아이콘 편집기 프로젝트 파일(실행에 불필요) |

원문이 필요한 조원은 저장소(GitHub)에서 받으면 됩니다. 제외 목록을 바꾸려면 `.gitattributes`를 수정합니다.

**이미지·영상 최적화** (2026-09-30): 홈 화면 이미지는 표시 크기에 맞게 줄였습니다(가로 최대 1920px JPEG, 로고·챗봇 캐릭터는 표시 크기의 4배). 소개 영상은 소리 트랙을 빼고 다시 인코딩했습니다(무음 자동재생이라 화면 변화 없음). 새 이미지를 넣을 때도 가로 1920px 이하 JPEG(투명 배경이 필요하면 PNG)로 넣어 주세요.
