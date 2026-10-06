# AXPORT 위젯 및 챗봇 통합 (2026-09-26)

이 문서가 현재 폴더 배치와 실행 방법의 기준입니다. 전달받은 `_axport_semiconductor_widgets` 내부 TXT/README는 최초 전달본이며, 최상위에 패키지가 있다는 경로 설명은 현재와 다릅니다.

## 실행

프로젝트 최상위에서 `python app.py`, 화면은 http://127.0.0.1:5073/app 입니다. WSGI에서 `app:app`을 가져와도 동일하게 연결됩니다. 기존 Contact Us 라우트와 기업 분석 로직은 유지합니다.

별도 미리보기:

```powershell
python -B minjung/AXPORT_widget/_axport_semiconductor_widgets/run_preview.py
```

http://127.0.0.1:5075/app 에서 표시됩니다. 실제 폴더 깊이와 중복 등록을 수정했습니다. 비교용 기존 화면은 `/_axp_semiconductor/original`입니다.

## 환경 설정

최상위 `.env`만 사용합니다. 없다면 최상위 `.env.example`을 `.env`로 복사하세요. 기존 파일은 덮어쓰지 말고 필요한 항목만 추가합니다. OS 환경변수가 우선하며 변경 후 서버를 재시작합니다. 실제 키는 Git에 올리지 않습니다.

위젯은 기본 `AXPORT_DATA_MODE=demo`이며 예시 표시를 유지합니다. `live`로 바꾸면 환율은 `EXCHANGERATE_API_KEY`, 뉴스는 `THENEWS_API_KEY`, 수출기상도는 검증된 JSON의 경로 `AXPORT_WEATHER_JSON`을 사용합니다. 미설정·실패 항목은 실제 데이터로 위장하지 않습니다.

수출통계 생성은 TXT의 수집·검증 모듈을 그대로 사용하며 실행 파일을 최상위에 추가했습니다.

```powershell
python -B make_weather_json.py --year 2026 --month 8
```

최상위 `.env`에 `CUSTOMS_API_KEY`가 필요합니다. 완료된 월만 조회하며 새 파일로 저장합니다. 출력된 `AXPORT_WEATHER_JSON=...`을 `.env`에 반영하세요. API 호출은 이 명령을 직접 실행할 때만 수행합니다.

## 챗봇 전용 LLM

사용자 지침은 `chatbot_persona.md`에 저장하며 `chatbot.py`의 `/api/chat` 요청에만 주입합니다. 위젯, 기업 점수, 분석 로직에는 주입하지 않습니다. 브라우저에는 지침과 키를 보내지 않습니다.

```dotenv
AXPORT_CHAT_MODE=live
OPENAI_API_KEY=발급받은_키
OPENAI_MODEL=계정에서_사용_가능한_모델_ID
```

`AXPORT_CHAT_MODE`는 위젯의 demo/live와 독립적입니다. 기본 `demo`는 기존 예시 답변을 사용하며 LLM에 연결하지 않습니다. `live`에서 설정이 누락되거나 API가 실패하면 오류 및 재시도 안내가 나오고 예시 답변으로 몰래 대체하지 않습니다.

OpenAI [Responses API 공식 안내](https://developers.openai.com/api/docs/guides/migrate-to-responses)에 따라 서버에서 instructions/input을 분리해 전달합니다. 모델은 환경변수로 지정하며 특정 모델을 자동 선택하지 않습니다. 외부 패키지 추가 없이 Python 표준 라이브러리를 사용합니다.

질문과 최근 대화(최대 12개 메시지, 총 24,000자)를 외부 AI에 전송합니다. 앱은 대화를 파일에 저장하지 않으며 `store=false`를 요청합니다. 대화 종료 시 브라우저 기록과 진행 중인 브라우저 요청을 초기화합니다. 이미 공급자가 처리 중인 요청의 비용까지 취소되는 것은 아닙니다.

답변은 HTML로 실행하지 않고 텍스트로 표시합니다. 입력 길이, 요청 크기, 동시 요청 수, 분당 요청 수를 제한합니다. 분당 20회 및 동시 2회 제한은 서버 프로세스 단위입니다(Render 는 워커 1개). `/api/chat` 은 로그인 없이 호출되므로 배포에서 live 를 켜기 전에 OpenAI 쪽 사용량 한도를 정합니다.

(2026-09-27) 지침 뒤에는 분석 엔진의 정책 값(`analysis_suitability.policy_snapshot()`)만 붙입니다. 사용자 분석 결과·파일·화면 값은 넣지 않으며, 불러오지 못하면 구체적 수치를 말하지 않도록 안내 문구로 대신합니다.

웹 검색, RAG, 업로드 파일/현재 화면 자동 조회는 포함하지 않습니다. 최신 규제와 데이터는 확인 필요성을 구분하도록 지침을 추가했습니다. API 응답이 실제로 지침을 항상 준수한다고 보장할 수는 없습니다.

## 충돌 수정 및 검사

- `/_axp_semiconductor/`와 `axsx_widgets` 이름을 사용하고 기존 라우트를 보존합니다. 중복 네임스페이스는 등록 전에 검사합니다.
- `connect_dashboard()`는 이미 통합된 앱에서 중복 실행해도 위젯을 중복 삽입하지 않습니다.
- 기존 HS 입력이 select로 바뀐 상황을 지원하고 기존 분석기의 검증/결측 확인 절차를 그대로 사용합니다.
- 비동기 분석 검증 오류를 중앙 카드에도 표시합니다.
- 예시 데이터의 배지/출처가 숨겨지던 부분을 수정했습니다.
- 기존 수정 중인 팀 파일, 샘플 데이터, Contact Us 코드를 덮어쓰지 않습니다.

검증 명령:

```powershell
python -B -m unittest minjung.AXPORT_widget.test_integration -v
python -B minjung/AXPORT_widget/_axport_semiconductor_widgets/verify_extension.py
python -B minjung/AXPORT_widget/check_browser.py
```

단위·브라우저 자동 검증은 외부 호출을 모의 응답으로 대체합니다. 2026-09-26 실행 서버에서 `gpt-5.4-mini` 실제 답변 1회와 위젯 응답, 키 비노출, 환경파일 접근 차단을 확인했습니다. 향후 키·모델·과금 상태가 바뀌면 실제 연결을 다시 확인해야 합니다.

## 로컬 API 키 보호

- 실제 키는 최상위 `.env`에만 저장합니다. `.env.*` 및 환경파일 백업도 Git에서 제외하고 `.env.example`만 공유합니다.
- 브라우저는 같은 주소의 `/api/chat`만 호출하며 API 키를 전달받지 않습니다. 키는 서버에서 OpenAI 인증 헤더로만 보냅니다.
- 챗봇은 localhost/127.0.0.1/::1 과 `AXPORT_PUBLIC_URL` 의 호스트(배포 주소)만 허용하고, 그 주소와 동일 출처인 JSON 요청만 받습니다. 다른 사이트의 요청 및 DNS 재바인딩 호스트는 403으로 차단합니다. 브라우저 외 로컬 클라이언트는 Origin 없이 사용할 수 있습니다.
- 로컬 실행(`python app.py`)은 `127.0.0.1`에만 바인딩합니다. Render 배포는 gunicorn 으로 `0.0.0.0` 에서 동작하며 `/app` 은 로그인이 필요합니다(junhee accounts).
- Windows의 `.env` 권한은 현재 사용자·SYSTEM·Administrators로 제한합니다. 같은 사용자 권한의 프로그램과 관리자의 접근까지 막는 암호화 저장소는 아닙니다.
- 채팅에 한 번 노출된 키는 이 설정으로 회수되지 않습니다. 새 키를 발급받아 채팅에 붙이지 말고 로컬 `.env`에 직접 교체한 뒤 서버를 재시작하세요.

실제 실행 서버 검증(짧은 AI 질문 1회로 API 사용량이 발생): `python -B minjung/AXPORT_widget/verify_live.py`. 키는 출력하지 않으며 위젯/AI 모드, 비공개 경로, Git 제외, 소스·정적파일·로그의 키 노출을 확인합니다.
