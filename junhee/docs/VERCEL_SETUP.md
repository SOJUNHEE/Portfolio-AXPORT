# Vercel 배포 (공개 데모, 2026-10-12)

Render 무료 서버는 디스크(`instance/`)에 방문자 작업을 저장하고 서버 안의 스레드로 정리·위젯 갱신을 했다.
Vercel 은 요청마다 다른 인스턴스가 응답하고 배포 디렉터리가 읽기 전용이라, 같은 코드를 다음처럼 바꿔 돌린다.

| 기능 | Render (기존) | Vercel |
|---|---|---|
| 방문자 바탕화면·업로드 원본·분석 결과·문의 | `instance/*.sqlite3`, `contact_messages.jsonl` | 외부 Postgres (`DATABASE_URL`) |
| 기업 분석 실행 | 백그라운드 스레드, 화면이 진행 상태를 폴링 | 요청 안에서 끝까지 실행 (`AXPORT_ANALYSIS_INLINE=1` 자동) |
| 방문자 7일 정리 | 1시간마다 스레드 | 하루 1회 Vercel Cron `GET /api/cron/daily` |
| 위젯 공식 자료(환율·뉴스·수출기상도) | 1시간마다 `static/data/widgets/widgets.json` 덮어쓰기 | 하루 1회 크론이 DB(`widget_snapshots`)에 저장, 그 파일 주소를 DB 최신본으로 응답 |
| 방문자 업로드 상한 | 5 MB | 4 MB (Vercel 요청 본문 한도 4.5 MB) |

코드는 두 환경에서 같다. `DATABASE_URL` 이 없으면 지금처럼 SQLite 파일을 쓴다(로컬·Render·테스트).
SQL 은 그대로 두고 `junhee/server/dbcompat.py` 가 연결만 Postgres 로 바꾼다.

## 1. Postgres 만들기

Vercel 프로젝트 > **Storage** > **Neon (Postgres)** 를 만들어 이 프로젝트에 연결한다.
`DATABASE_URL` 이 환경변수로 자동 등록된다. 지역은 함수 지역(`vercel.json` 의 `sin1`, 싱가포르)과 가까운
**Singapore (ap-southeast-1)** 를 고른다(요청 하나에 쿼리가 여러 번 오가므로 거리가 멀면 느려진다).

다른 Postgres(Supabase 등)를 쓰면 접속 문자열을 `DATABASE_URL` 에 직접 넣는다. 표는 처음 쓸 때 자동으로 만든다.

## 2. 환경변수 (Vercel > Settings > Environment Variables)

| 이름 | 값 |
|---|---|
| `DATABASE_URL` | 1번에서 자동 등록 (직접 넣을 때는 `postgresql://...`) |
| `FLASK_SECRET_KEY` | 32자 이상 무작위 문자열: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CRON_SECRET` | 16자 이상 무작위 문자열(위 명령으로 하나 더). Vercel 이 크론 호출에 붙여 보낸다 |
| `AXPORT_DATA_MODE` | `demo` |
| `AXPORT_CHAT_MODE` | `demo` |

외부 API 키(`OPENAI_API_KEY`, `ECOS_API_KEY` 등)는 Render 공개 데모와 같이 비워 둔다(화면에 안내가 나온다).
`FLASK_SECRET_KEY` 를 빠뜨리면 DB 접속 문자열에서 만든 키로 동작하지만, 접속 정보가 바뀌면 방문자 세션이 끊기므로 넣어 둔다.

## 3. 배포

Vercel > Add New > Project 에서 `SOJUNHEE/Portfolio-AXPORT` 를 Import 한다. 설정은 `vercel.json` 에 있다
(Flask, 싱가포르, 최대 300초, 하루 1회 크론 03:00 KST 전후). Python 버전은 `.python-version`(3.14).

## 4. 확인

- `/`, `/app` 이 열리고 공개 데모 안내에 "업로드는 4 MB 이하"가 보인다
- 샘플 파일 분석이 끝나고 대시보드가 열린다. 새로고침해도 바탕화면·분석 결과가 남아 있다
- Vercel > Settings > Cron Jobs 에서 `/api/cron/daily` 를 Run 하면 200 과 `{"purge": ..., "widgets": ...}` 가 온다
  (키가 없으면 `widgets` 는 `partial`: 뉴스만 갱신, 환율·수출기상도는 배포본 값 유지)

## 한계 (공개 데모 기준)

- IP 별 요청 제한·엑셀 동시 해석 수는 인스턴스 메모리에 둔다. 인스턴스가 여러 개면 인스턴스마다 따로 센다
  (전체 저장 용량 상한 300 MB 는 DB 기준이라 그대로 지켜진다)
- Hobby 요금제 크론은 하루 1회라 위젯 자료도 하루 1회 갱신된다
- 분석이 300초를 넘기면 Vercel 이 요청을 끊는다(키 없는 공개 데모의 샘플 분석은 로컬 측정 약 2초)
- 문의 내용은 DB `contact_messages` 표에 있다(`junhee/scripts/export_contact.py` 는 로컬 jsonl 용)
