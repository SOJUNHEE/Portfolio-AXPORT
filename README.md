# AXPORT

사용자가 올린 반도체 기업 Excel(또는 가상 샘플)을 서버 분석 엔진(참고 적합도 v1)으로 분석해 시장성·가격·물류·안정성 참고 점수와 규제 확인 후보를 보여 주는 Flask 앱입니다. 결과는 참고용이며, AXPORT는 수출허가 여부를 최종 판정하지 않습니다.

> 조원 배포본: API 키·개인 설정은 들어 있지 않습니다. 처음 받았다면 [TEAM_SETUP.md](TEAM_SETUP.md)부터 따라 하세요.

## 실행

PowerShell에서 프로젝트 폴더를 연 뒤 실행합니다.

```powershell
.\start.ps1
```

스크립트 실행이 제한된 환경에서는 다음 명령을 사용합니다.

```powershell
.\.venv\Scripts\python.exe app.py
```

최초 설치가 필요한 PC:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

- 홈: http://127.0.0.1:5073/
- 작업공간: http://127.0.0.1:5073/app (2026-10-05부터 로그인 없이 사용. 로그인 코드·Supabase 설정 안내는 `junhee/docs/ACCOUNTS_SETUP.md`에 남아 있음)
- 종료: 서버 터미널에서 Ctrl+C
- Python 3.14.7 / Flask 3.1.3에서 검증. 로컬 실행(`app.py`)은 127.0.0.1에 바인딩하고, 배포(Render)는 같은 Python 3.14.7에서 gunicorn으로 실행합니다(`render.yaml`).

## 확인할 수 있는 동작

- 첨부 로고·뇌/반도체 이미지를 사용한 홈, 서비스 소개, 앱 전환 로딩
- 파일 선택·드롭, 기업명·HS 코드·대상국 입력, 샘플 분석 진입
- 파일 아이콘 더블클릭, 격자 이동, Delete 키/휴지통 드롭, 복원
- 창 이동·크기 조절·최소화·최대화·배치 초기화
- 종합 참고 적합도와 5개 영역 탭(엔진 계산값·출처·결측 표시)
- 가중치 합계 100% 검증, 기본값 복원, 규제 관문 별도 표시(가중치를 바꾸면 엔진 등급이 아닌 화면 참고점수로 다시 계산)
- 보고서 화면 미리보기와 HTML 다운로드 링크. HTML을 브라우저로 열면 인쇄로 PDF 저장 가능
- 모바일 단일 창과 하단 탭, 메뉴, 키보드·움직임 줄이기 대응

## 현재 범위

분석 엔진은 업로드한 Excel 내용을 읽고 UN Comtrade·관세청·한국은행 ECOS·국가법령정보 API와 보유 원문(HSK 연계표·KOTRA 수입규제·ITA CSL·WTO 관세)을 조회합니다. API 키는 OS 환경변수 또는 루트 `.env`에서 읽으며, 키가 없으면 해당 지표만 '검색 불가'로 표시합니다. 규제는 확인 후보만 제시하는 별도 관문이며, AXPORT는 수출허가·전략물자 해당 여부를 최종 판정하지 않습니다.

업로드한 파일은 분석 서버로 전송·저장되어 분석됩니다. 로그인하지 않은 브라우저는 세션 쿠키의 방문자 id로 구분되어, 다른 브라우저의 파일·분석은 보이지 않습니다. 기본 종합 점수는 엔진 배점(시장성 40·가격 20·물류 10·안정성 10, 근거 없는 항목은 정책 기준 50점과 근거 반영률 표시)이고, 가중치를 바꾸면 화면에서 '사용자 가중치 참고점수'로 다시 계산합니다(엔진 등급 아님). 바탕화면 샘플은 모두 가상 기업입니다.

바탕화면 파일·폴더·분석 조건과 완료된 분석 결과는 로그인 없이 쓰면 서버 디스크(`instance/visitor-workspaces.sqlite3`, `company-assessments.sqlite3`)에, 로그인한 계정이면 Supabase에 저장됩니다. 업로드 원본·진행 상태·세션도 서버 디스크(`instance/`)에 있어 무료 배포 환경에서는 재시작 때 사라질 수 있습니다. 휴지통에서 영구 삭제하면 서버의 원본·분석 결과도 삭제되며 PC의 원본 파일은 변경되지 않습니다.

## 수정 위치

| 화면/기능 | 파일 |
|---|---|
| 홈 구조 | `templates/home.html` |
| 홈 디자인 | `static/css/home.css` |
| 홈 메뉴·전환 | `static/js/home.js` |
| 작업공간 구조·모달 | `templates/workspace.html` |
| 작업공간 디자인 | `static/css/workspace.css` |
| 아이콘·창·탭 | `static/js/workspace.js` |
| 종합·상세 탭·보고서 | `static/js/junhee-dashboard.js` |
| 로그인·파일 저장·분석 요청 | `static/js/junhee-auth.js`, `junhee-files.js`, `junhee-analysis.js` |
| 계정·분석 서버·엔진 | `junhee/server/` (`engine/` 은 분석 엔진) |
| 위젯·챗봇 | `minjung/AXPORT_widget/` |
| Flask 화면 경로 | `app.py` |

이미지는 `static/assets`, 로컬 폰트·아이콘·차트는 `static/vendor`에 있습니다. 실행 시 CDN 호출은 하지 않습니다. 첨부 이미지는 원본을 복사했으며 CSS로 배치했습니다.

## 개발 도구

Node는 정적 패키지 갱신과 포매팅에만 사용합니다. Flask 실행에는 Node가 필요하지 않습니다. 패키지 버전은 `package-lock.json`으로 고정합니다.

```powershell
npm ci
npm run format
npm run check
```

Chart.js(MIT), Phosphor Icons(MIT), Noto Sans KR(OFL) 라이선스는 vendor 폴더에 포함되어 있습니다. 원래 기획 문서는 유지했습니다.
