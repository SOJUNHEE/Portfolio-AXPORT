# AXPORT 챗봇 — 독립 추가 파일 및 통합 안내

> 2026-09-26 업데이트: 홈/작업공간 연결과 챗봇 전용 페르소나 및 선택적 LLM API 연동을 완료했습니다. 현재 설정은 [minjung/AXPORT_widget/INTEGRATION.md](minjung/AXPORT_widget/INTEGRATION.md)를 따르세요. 아래 내용은 최초 프론트엔드 인계 당시 기록입니다.
>
> 2026-09-27 현재: `AXPORT_CHAT_MODE=demo` 면 브라우저의 예시 답변(`static/js/chatbot-i18n.js`), `live` 면 서버 `/api/chat` 이 질문과 최근 대화를 OpenAI 에 보냅니다. 예시 답변 문구 일부(프로토타입·파일 미전송·재계산 안 됨 등)는 현재 기능과 달라 갱신이 필요합니다.

## 현재 상태

기존 templates/home.html, templates/workspace.html, README.md는 수정 전 Git HEAD 내용으로 복원했습니다. app.py와 기존 홈·대시보드 CSS/JS도 변경하지 않았습니다.
이 파일들은 챗봇 연결 전 상태이므로 현재 홈페이지를 실행해도 챗봇은 표시되지 않습니다. 아래 연결 작업은 main 통합 담당자가 수행합니다.

## 브랜치에 추가할 파일 7개

- templates/chatbot.html
- static/css/chatbot.css
- static/js/chatbot-i18n.js
- static/js/chatbot-demo.js
- static/js/chatbot.js
- static/assets/Axport_AI.png
- CHATBOT.md (이 안내 문서)

폴더 구조를 유지해서 추가하세요. 기존 공통 파일을 덮어쓰지 않습니다.

## main 통합 시 연결 방법

Flask/Jinja 템플릿을 전제로 합니다. 홈과 대시보드 템플릿의 기존 스타일 뒤, </head> 앞에 아래를 각각 한 번 추가합니다. 스크립트 순서를 유지하세요.

```html
<link rel="stylesheet" href="/static/css/chatbot.css" />
<script defer src="/static/js/chatbot-i18n.js"></script>
<script defer src="/static/js/chatbot-demo.js"></script>
<script defer src="/static/js/chatbot.js"></script>
```

두 템플릿의 </body> 바로 앞에 각각 한 번 추가합니다.

```jinja2
{% include "chatbot.html" %}
```

현재 main의 로컬 Noto Sans KR 폰트와 Phosphor 아이콘 스타일을 사용합니다. 기존 페이지에 아래 스타일이 이미 로딩되므로 중복으로 추가하지 않습니다.

```html
<link rel="stylesheet" href="/static/vendor/font/index.css" />
<link rel="stylesheet" href="/static/vendor/phosphor/regular/style.css" />
```

공통 마크업은 request.path가 /app이면 대시보드 질문, 그 외에는 홈 질문을 표시합니다. 통합 시 경로를 변경했다면 chatbot.html의 data-page 조건도 실제 경로에 맞추세요. 루트가 아닌 URL 경로에 배포한다면 /static/ 자산 경로도 배포 구조에 맞춰 조정해야 합니다.

## 제공 기능 및 현재 디자인

- 열기·최소화·복원·종료 초기화, 좌측 상단 크기 조절, 추천 질문 즉시 전송.
- 채팅·로딩·오류·재시도, 중복 요청 방지, 초안 유지, 이전 응답 차단, 새 답변 스크롤 안내.
- 한국어·영어·중국어 간체·일본어 UI 및 로컬 예시 답변.
- 실행 버튼 80px / 모바일 60px, 기본 팝업 400×600px. 화면 공간 우선 보정.
- 네이비·블루·반투명 화이트 유리 질감. 라벤더 없음. 실행 캐릭터 84%, 첫 화면 캐릭터 90% 불투명도. 원본 이미지 자체는 수정하지 않았습니다.
- 가운데 인사말과 아이콘, 알약형 추천 질문, 220ms 등장 효과, 움직임 줄이기 대응.
- 대화는 페이지 메모리에만 유지하며 페이지 이동·새로고침 시 초기화합니다.

## 홈페이지 언어 연동

```js
// 홈페이지 언어 변경을 챗봇이 자동으로 감지합니다.
document.documentElement.lang = 'en'; // ko / en / zh-CN / ja

// 또는 챗봇만 변경합니다.
window.AXPORTChat.setLanguage('ja');
```

기존 대화와 초안은 유지합니다. 이미 요청 중인 답변·재시도는 최초 요청 언어, 새 질문은 변경 언어를 사용합니다. 홈페이지 전체 번역은 포함하지 않습니다.

## 로컬 오류·지연 재현

연결 후 개발자 콘솔에서 설정하고 질문을 전송하세요. 설정은 다음 전송 또는 재시도 한 번에만 적용됩니다.

```js
AXPORTChatDemo.configureNext({ delayMs: 5000 });
AXPORTChatDemo.configureNext({ delayMs: 1000, fail: true });
```

실패 후 재시도는 별도 설정이 없으면 기본 정상 응답입니다. 기본 지연은 850ms입니다.

## 백엔드 인계

실제 AI, RAG, LangChain, 서버 API, 분석 데이터 조회, 외부 전송은 구현하지 않았습니다. chatbot-demo.js의 응답 provider를 향후 실제 백엔드 어댑터로 교체합니다. 대화 맥락·평가 실행·권한·출처·실패·취소 정책은 백엔드와 별도로 협의해야 합니다. 현재 내부 respond(question, locale)는 서버 API 규격을 확정한 것이 아닙니다.

## 검증 범위

분리 전 홈·대시보드 실화면, 모바일 배치, 전송·복원 및 다국어 상태 전환을 확인했습니다. 다국어 구현 시 회귀 검사 66개를 통과했으며 이후 시각 변경은 화면 중심으로 확인했습니다. 실제 휴대폰 키보드·화면 읽기 프로그램·원어민 감수는 미검증입니다.
이번 분리 작업에서는 기존 추적 파일의 Git 차이가 없는 것과 신규 파일 유지·JavaScript 문법을 확인합니다. 통합 후 두 페이지에서 챗봇 표시와 기존 기능을 다시 확인하세요.
