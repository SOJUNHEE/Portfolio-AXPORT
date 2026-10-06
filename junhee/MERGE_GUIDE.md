# MERGE_GUIDE — main 을 junhee 브랜치로 가져오는 순서 (v2)

"가이드대로 main 가져와줘" 라고 하면 아래를 그대로 따른다.

기준
- **main 에서 들어오는 내용 = 조원들이 수정 중인 최신 기준이다. 그대로 받는다.**
- **내 작업 = 그 위에 '추가'로 얹는다. main 의 내용을 덮어쓰지 않는다.**

## 0. 지켜야 할 것

- `git push` 는 하지 않는다. 결과를 보여주고 멈춘다.
- `git add .` / `git add -A` 금지. 파일을 지정해서 추가한다.
- `.env`, `*api 키*.txt`, `credentials/` 는 절대 커밋하지 않는다.
- 무엇이든 지우거나 되돌리기 전에 1번 백업을 먼저 끝낸다.

## 1. 백업

1. `git status` 를 보여준다 (브랜치 `junhee` 확인).
2. `git fetch origin`
3. 저장소 밖 `../_merge_backup/<날짜_시각>/` 에 저장한다.
   - `내꺼/` 커밋 안 된 변경 파일 전부 + 기준점 이후 내가 바꾼 파일의 현재 버전 (폴더 구조 그대로)
   - `main/` 같은 파일들의 origin/main 버전 (`git show origin/main:<경로>` 바이트 그대로 → UTF-8 유지)
   - 비밀정보 패턴(`.env`, `api 키`, `credentials/`)은 복사·커밋 대상에서 뺀다.

## 2. 누가 무엇을 바꿨는지 구분

1. 기준점: `git merge-base HEAD origin/main`
2. 파일마다 두 변경을 따로 뽑는다.
   - 내 변경 = 기준점 → 내 현재 파일
   - main 변경 = 기준점 → origin/main
3. 각 변경 줄을 다섯 가지로 분류한다.

| 분류 | 뜻 | 처리 |
|---|---|---|
| ① | main 만 바꾼 줄 | main 그대로 받는다 |
| ② | 내가 새로 추가한 줄 | main 위에 추가한다 |
| ③ | 같은 줄을 양쪽이 다르게 바꿈 | main 을 남기고, 내 변경은 3번 규칙으로 처리 |
| ④ | main 이 지운 곳을 내가 고침 | main 의 삭제를 따른다. 내 변경은 보고만 |
| ⑤ | 양쪽이 똑같이 바꿈 | 하나만 남긴다 |

4. `../_merge_backup/<날짜_시각>/비교결과.md` 에 표로 적는다: `파일 | 줄 | 분류 | 무슨 기능인지 한 줄 | 처리 방법`

## 3. 합치는 규칙

파일 소유 기준
- **내 전용 파일** → 항상 내 버전: `junhee/**`, `static/css/junhee-*`, `static/js/junhee-*`, `static/data/companies/**`, `static/samples/**`
- **건드리면 안 되는 파일** → main 버전 그대로: `app.py`, `templates/home.html`, `static/css/workspace.css`, `static/css/home.css`, `static/js/home.js`, `static/vendor/**`, `package*.json`, `requirements.txt`, 루트 `*.md`(명세·디자인 문서).
  이 파일들에 내 변경이 있었다면 버리되(백업은 남아 있음) 무엇을 버렸는지 목록으로 보고한다.
- **함께 쓰는 파일** (`templates/workspace.html`, `static/js/workspace.js`, `static/data/dashboard_summary.json` 등) → main 을 바탕으로 내 추가분만 얹는다.

충돌이 났을 때
- 한쪽을 통째로 고르지 않는다. main 줄은 그대로 두고 내 ② 줄을 끼워 넣는다.
- `<link>`, `<script>` 추가 줄 → 양쪽 모두 남기고 중복만 제거.
- `workspace.js?v=숫자` 처럼 버전 번호가 다르면 → 둘보다 큰 번호.
- `junhee-dashboard.js` 줄은 `workspace.js` 줄 바로 위에 둔다 (defer 순서: 모듈이 먼저 정의돼야 함).
- `{% include "chatbot.html" %}` 가 있으면 `templates/chatbot.html` 도 반드시 존재해야 한다. 없으면 멈추고 알린다.
- 해결한 충돌마다 '어떻게 합쳤는지' 한 줄씩 적는다.

## 4. 커밋

1. 커밋 안 된 내 작업이 있으면 파일을 지정해서 먼저 커밋한다.
   ```
   git add junhee static/css/junhee-dashboard.css static/js/junhee-dashboard.js static/data static/samples templates/workspace.html static/js/workspace.js
   git commit -m "<내 작업 메시지>"
   ```
2. 커밋 전 `git diff --cached --name-only` 로 비밀정보 파일이 없는지 확인한다.

## 5. 합치기

1. 먼저 `git merge --no-commit --no-ff origin/main` 으로 시험 병합해 충돌 파일을 본다.
2. 충돌이 없으면 `git commit --no-edit`. 충돌이 있으면 3번 규칙으로 해결 → `git add <파일>` → `git commit --no-edit`.
3. 되돌리기: 병합 중이면 `git merge --abort`. 병합 커밋 뒤라면 `git reset --hard ORIG_HEAD`(내 커밋은 남는다). 파일 단위는 백업 폴더에서 복사.

## 6. 확인

1. `python app.py` 로 서버를 띄운다 (127.0.0.1:5073).
2. 아래가 모두 200 인지 표로 보여준다: `/`, `/app`, `/static/css/junhee-dashboard.css`, `/static/js/junhee-dashboard.js`, `/static/js/workspace.js`, (챗봇이 있으면) `/static/js/chatbot.js`, `/static/css/chatbot.css`
3. `/app` 에서 더미 기업 파일(한빛·대성)을 열었을 때 대시보드 숫자가 바뀌는지 확인한다. 브라우저가 없으면 jsdom 점검으로 대신하고, 캔버스 그리기처럼 확인 못 한 항목은 '미확인'으로 적는다.
4. `node --check` 로 `workspace.js`, `junhee-dashboard.js` 문법을 확인한다.

## 7. 마무리

- 이 가이드가 바뀌었으면 `junhee/MERGE_GUIDE.md` 만 지정해서 커밋한다.
- `git status` 와 `git log --oneline -5` 를 보여주고 멈춘다. push 는 사용자가 한다.
