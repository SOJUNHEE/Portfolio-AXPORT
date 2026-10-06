# junhee — 대시보드 요약 실제 데이터 연결

> **현재 상태 (2026-09-27 배포 QA)** — 아래 기록 중 일부는 이전 단계 설명이다. 지금은 다음이 기준이다.
> - 모든 파일(바탕화면 가상 샘플·업로드)은 서버 분석 엔진(`junhee/server/engine`, 참고 적합도 v1)으로 계산한다(`workspace.js` 의 `ENGINE_ONLY`). 브라우저 v0.3 산식(`rules/demo_scoring.md`, 35·30·20·15)은 쓰지 않는 옛 경로다.
> - 종합 점수 = 엔진 배점 시장성 40·가격 20·물류 10·안정성 10(80→100 환산), 근거 없는 항목은 정책 기준 50점 + 근거 반영률. 35·30·20·15 는 가중치 설정 창의 화면용 기본값이며, 바꾸면 '사용자 가중치 참고점수'(엔진 등급 아님)가 표시된다.
> - 점수의 안정성 = UN Comtrade 36개월 월간 수입 변동계수·급감 빈도(배점 10). `config/stability_method.json`(환율 변동성 v1.0)은 엔진 점수에 쓰이지 않고, 환율은 참고 표시만 한다(팀 확정 문서와 실행 코드가 다름 — 정리 필요).
> - `data/samples/uploads/` 에는 사용자가 올린 실제 기업 파일이 저장된다(git 제외, 공개 static 아님).
> - 챗봇은 `AXPORT_CHAT_MODE=demo` 면 예시 답변, `live` 면 서버 LLM. AXPORT 는 수출허가 여부를 최종 판정하지 않는다.

다른 조원과 겹치지 않도록 새 파일은 모두 이 폴더에 둔다.
프로젝트 파일 중에는 `templates/workspace.html`(연결 태그·기준일 span), `static/js/workspace.js`(연결부), `.gitignore`, 새 폴더 `static/data/`·`static/samples/`·`static/css|js/junhee-*` 를 손댔다. main 병합 절차는 `junhee/MERGE_GUIDE.md`.

## 구성

```
junhee/
  data/raw/         test1_data 원본 복사본 (수정 금지, API 키 파일 제외)
  data/raw/external/  fetch_fx.py 가 내려받은 환율 시계열 (FRED H.10 일별 9종 + 월평균 1종) + 수집 기록
  config/           stability_method.json — 안정성 산식 설정 v1.0 (2026-09-23 팀 확정)
  data/processed/   항목별 JSON + dashboard_summary.json
  data/samples/     업로드 시연용 가상 기업 엑셀 2개
  scripts/          추출·검증·복사 스크립트
  MANIFEST.csv      원본 출처·기준일·SHA256/MD5·이용조건
```

## 실행 순서

```
python junhee/scripts/fetch_fx.py               # 환율 시계열 10종 수집 → data/raw/external/ (API 키 불필요)
$env:ECOS_API_KEY = "<키>"; python junhee/scripts/fetch_fx_ecos.py   # COP·KHR·VND·ZiG (한국은행 ECOS, 키는 환경변수로만)
python junhee/scripts/extract_summary.py        # 원본 → processed/*.json, dashboard_summary.json
python junhee/scripts/publish_static.py         # → static/data/dashboard_summary.json (app.py 수정 없이 /static 로 서빙)
python junhee/scripts/build_manifest.py         # → junhee/MANIFEST.csv
python junhee/scripts/make_sample_companies.py  # → junhee/data/samples/*.xlsx
```

필요 패키지: `openpyxl` (requirements.txt 는 수정 금지라 추가하지 않음).

## dashboard_summary.json 항목 스키마

```
{ "key": "regulation", "headline": "핵심 결과 1개", "note": "짧은 설명 1줄",
  "state": "ok" | "insufficient", "source": "파일명", "as_of": "YYYY-MM-DD" | null,
  "data_class": "실제자료" | "가상데이터" | "가정값", "detail": { ... } }
```

- `state = insufficient` 면 headline 은 "자료 부족" 이고 숫자를 넣지 않는다. note 에 필요한 자료를 적는다.
- `as_of` 가 없는 항목은 `checked_on`(확인일)을 둔다.
- `publish_static.py` 가 복사 전에 위 규칙을 검증한다.

HS 는 `HS_LIST = ["854231", "854232"]` 두 개를 본다 (샘플 회사가 메모리 회사라 854232 가 필요). 규제·가격은 HS 별로 detail 에 나눠 담고 headline 은 합쳐서 표시한다.

## 항목별 추출 근거와 한계

| 항목 | 값 | 출처 | 한계 |
|---|---|---|---|
| 규제 | 미국의 대한국 수입규제 55건, HS 854231·854232 모두 미포함, CSL 26,146건 | KOTRA 수입규제 현황(2026-06-03), ITA CSL, HSK연계표(2026-09-01) | 별표1~4 는 파싱하지 않음(원문 확보, 판정 미적용). HSK 연계표상 8542.31 하위 4개·8542.32 하위 7개 코드가 통제번호(3A001 등)에 연계돼 있으나 해당 여부는 원문 대조 후 판정 |
| 시장성 | 2026-07 세계 출하액 1,425억 달러, 전년동월비 +129.4% | WSTS Historical Billings (Monthly Data, Worldwide) | 파일 값 그대로. 전년동월비가 매우 큰 값이므로 원자료 재확인 권장 |
| 가격 | 미국 적용관세 0.0%(두 HS 동일), 대한국 수입액 854231 11.1억 + 854232 4.3억 달러 / 수출물가 컴퓨터·전자·광학 222.17 (2026-08p, 전월비 -3.1%) | C840_C410.csv(조치일 2026-09-03), 한국은행 수출입물가지수 | 물가지수 파일에 '반도체' 세부 행이 없어 상위 분류를 표시하고 그 사실을 note 에 적음 |
| 물류 | 한국→미국 서부 해상수출 8,589천원/2TEU (전월비 +0.5%), 동부 9,973천원 | 관세청 보도자료 hwpx (2026-08 자료, 2026-09-15 배포) | hwpx 의 section0.xml 문단 텍스트를 정규식으로 추출. 표 구조가 바뀌면 `insufficient` 로 떨어지도록 방어 |
| 안정성 | 목적국 결제통화의 원/외화 월평균 최근 12개월 평균 월간 변동폭(%) + 과거 10년 롤링 분포 대비 3분위 등급. 보조로 한국→미국서부 해상운임 변동폭(등급 없음) | FRED H.10 일별 환율(DEXKOUS 등 9종)로 교차환율 계산, 관세청 hwpx 월별 운임 표 | 산식 v1.0 팀 확정(2026-09-23). USD·CNY·JPY·GBP·EUR·CAD·MXN·INR·CHF 가능, COP·KHR·ZiG·VND 는 H.10 미수록으로 자료 부족. 운임은 20개월뿐이라 등급 없음. ECOS 교체는 API 키 필요 |

## 가상 기업 샘플 (junhee/data/samples/)

- `한빛반도체_수출데이터_v0.1.xlsx` — 규모 큼, DRAM·HBM 중심 + NAND, 거래처 6곳
- `대성일렉트로닉스_수출데이터_v0.1.xlsx` — 규모 작음, NAND 중심, 거래처 4곳
- 시트: 제품정보 / 수출예정거래 / 수출실적 / 원가·비용 / 재고·생산 / 물류 / 거래처 / 증빙목록 + 검증케이스
- 첫 시트 상단에 "시연용 가상 데이터. 실제 기업 자료가 아님", `template_version 0.1` 명시. 매크로·수식 없음.
- 수출실적은 2025-09~2026-09 13개월을 고정 시드(random.Random)로 생성한다. 한빛 35행, 대성 23행. 시드·기준 수량·단가는 스크립트의 `actuals_spec` 참조.
- 검증 케이스(값 0 / 빈칸 / 거래처 연결 오류 / 날짜 형식 오류 / 중복 행)의 위치는 `검증케이스` 시트 참조. 실적 오류 행은 항상 시트 끝 3~4행.
- 목적국은 관세 CSV 가 있는 12개국 범위(미국·중국·영국·인도·멕시코·캐나다·스위스)만 사용. 대만은 12개국에 없어 제외.

## 안정성 산식 v1.0 (2026-09-23 팀 확정)

- 지표: 목적국 결제통화 환율. 원/달러(DEXKOUS) 일별 값에 다른 통화의 대달러 환율을 곱하거나 나눠 원/외화 일별 교차환율을 만든 뒤 월평균(거래일 10일 미만·진행 중인 달 제외).
- 기간: 최근 12개월 (13개 월평균 → 12개 전월비).
- headline: 전월비 등락률 절대값 평균 (%) = "한 달에 평균 ±n%". note: 최근 12개월 최고·최저. detail: 변동계수.
- 등급: 과거 10년(120개) 롤링 12개월 구간 분포에서 최근 값의 위치. 하위 1/3 안정, 중간 보통, 상위 1/3 불안정. 과거 구간 36개 미만이면 등급 없음.
- 보조 지표: 한국→목적국 해상수출 운임(관세청 월별 표). note 에 변동폭만 표시, 등급·점수에 미반영(물류와 중복 방지).
- 화면: `detail.per_country` 에 나라별 결과가 있고 workspace.js 가 현재 목적국 것을 카드에 보여준다. 통화 자료가 없는 나라는 자료 부족.
- H.10 에 없는 COP·KHR·VND·ZiG 는 `fetch_fx_ecos.py` 가 한국은행 ECOS 731Y001 에서 받는다. 키는 환경변수 `ECOS_API_KEY` 로만 넘기고 파일·로그·메타에 남기지 않는다. 파일이 없으면 해당 나라는 자료 부족으로 표시된다.
- 남은 일: fetch_fx_ecos.py 를 키와 함께 1회 실행 → extract → publish. ECOS 에 항목이 없는 통화가 있으면 대체 출처.

## (구) 종합 탭 디자인 이식 A안 — 점수형 화면으로 대체됨 (아래 참조)

- JH/templates(종합페이지)/index.html 시안의 구조·색을 현재 앱 틀(창·사이드바·책갈피 탭) 안의 종합 탭에 옮겼다. Tailwind CDN·Google Fonts 는 쓰지 않고 workspace.css 끝에 `.overview-layout`, `.suitability-card`, `.score-grid.jh-theme` 블록으로 구현했다.
- 왼쪽 '종합 수출적합도' 카드: 점수 산식이 확정 전이라 **종합 점수는 계산하지 않고**, 명세 §6 의 '근거 충족 상태'(실제 자료 확보 n/5)를 도넛 게이지로 보여준다. 요인별 목록은 확보/자료 부족/조회 실패 문구와 비중을 표시한다.
- 오른쪽 5개 카드: 아이콘 타일 + 영문 eyebrow + 제목, 상태 칩(실제자료/자료 부족/조회 실패/불러오는 중), headline, 스파크라인, note, 출처·기준일, '더보기 →'(해당 책갈피 탭으로 이동).
- 스파크라인은 요약 JSON 의 실제 시계열만 그린다: 시장성(WSTS 최근 13개월), 가격(관세 조치일별 38건), 물류(미국서부 운임 13개월), 안정성(원/통화 월평균 13개월). 규제는 시계열이 없어 '추이 자료 없음'. 가짜 곡선을 넣지 않는다.
- 팔레트는 시안 그대로: rose #f43f5e / violet #8b5cf6 / sky #0284c7 / amber #f59e0b / emerald #10b981. `colors` 맵이 바뀌어 상세 탭 강조색도 같은 팔레트를 쓴다.
- 초기화 순서: 로딩 오버레이를 숨긴 뒤 요약 fetch 를 시작한다. 요약 연결이 실패해도 대시보드는 열린다.

## 종합 탭 점수형 화면 + 더미 기업 업로드 연동 (2026-09-23, 레퍼런스 junhee/docs/reference/dashboard_reference.png)

- 새 파일: `static/css/junhee-dashboard.css`, `static/js/junhee-dashboard.js`, `static/data/companies/`, `static/samples/`, `junhee/rules/demo_scoring.md`, `junhee/scripts/augment_samples.py`, `junhee/scripts/score_companies.py`.
- workspace.html 은 새 CSS/JS 연결 태그, 기준일 span(`#asof-context`), 챗봇 연결만 추가. workspace.js 는 연결부만(초기 파일 2개, 업로드·파일 선택 시 모듈 호출, 종합 탭 렌더 위임, 파일 목록 '분석 완료'). workspace.css 는 손대지 않음.
- 실행 순서: `make_sample_companies.py` → `augment_samples.py`(12개월 보강, 기존 행 뒤에 추가) → `score_companies.py` → `publish_static.py`(companies/·samples/ 복사).
- 산식은 `junhee/rules/demo_scoring.md`. 종합 = 시장성 35·가격 30·물류 20·안정성 15 (workspace.js defaults), 규제는 관문으로 제외하고 감점 요인이 있으면 '규제 검토 필요' 배지.
- 화면: 처음엔 빈 상태(— / 100, 안내 문구). 바탕화면 아이콘(한빛·대성)을 열거나 '엑셀 파일 추가'로 실제 파일을 올리면 브라우저에서 SHA-256 을 계산해 index.json 과 대조한다. 일치하면 그 회사 JSON 을 불러오고, 아니면 '시연 환경에서는 등록된 샘플 파일만 분석됩니다' 안내만 한다.
- 게이지·추세선은 vendor 의 Chart.js 로 그린다. 숫자는 count-up, prefers-reduced-motion 이면 즉시 전환.
- 안정성 카드 설명: 기업 내부 거래 안정성(HHI·변동계수)이며 국가위험등급이 아님을 화면에 적음.

## JH2 최종 디자인 반영 (2026-09-23 저녁, main 의 JH2/index2.html 기준)

- 종합 탭: 왼쪽 패널 350px 고정, 큰 도넛(176px, 파랑→하늘→남보라 그라데이션), 요인별 점수는 mono 숫자 + 파란 전월 대비, 핵심 포인트 상자(컴퍼스 아이콘)에 '상세 리포트 보기 →'. 오른쪽 카드는 테두리 없는 파스텔 배경(#FFF5F5 · #FAF5FF · #F0F9FF · #FFFDF0 · #F0FDF4), 큰 검정 점수, '↑ +n (지난달 대비)', 끝점 있는 추세선. 색은 workspace.js `colors` 를 유지.
- 상세 탭 5개를 모듈이 그린다(`detailMeta`/`detailHTML`, workspace.js setTab 연결부 1곳). JH2 배치(상단 배너 → KPI/표 → 시사점·공개자료 → 6개월 점수 추이 차트)를 따르되 **JH2 의 하드코딩 문구·수치(OECD 등급, $48.2B 등)는 쓰지 않고** 회사 JSON 의 `inputs` 와 `static/data/dashboard_summary.json` 공개자료만 표시한다. 안정성 탭에는 '기업 내부 거래 안정성이며 국가위험등급이 아님' 안내를 둔다.
- 가중치 설정: workspace.js 의 사용자 가중치를 `getWeights`/`isCustom` 로 읽어 종합 점수를 요인 점수의 가중평균으로 다시 계산한다(기본 가중치면 점수표 값 그대로). 화면 하단에 '사용자 가중치 적용 · 종합 점수 재계산' 표시.
- 보고서: 회사가 선택돼 있으면 `reportRows()` 로 화면과 같은 회사 점수를 표에 넣는다(연결부 1곳).
- 반응형: 컨테이너 폭 820px 이하 1열, 560px 이하 카드 1열.

## 챗봇 연결 (CHATBOT.md 지침대로)

- 챗봇 연결(chatbot.css + 스크립트 3개 + `{% include "chatbot.html" %}`)은 조원(minjeong)의 chatbot_connect 커밋으로 main 에 들어왔다. 내 쪽에서 넣었던 같은 줄은 병합 전에 되돌렸다(2026-09-23, 백업 `../_merge_backup/`).
- 챗봇은 AI 미연결 데모 응답이며 workspace 에서는 `data-page="workspace"` 로 대시보드 질문을 보여준다.

## 대시보드 표시 규칙 (workspace.js)

- 로딩 / 정상 / 자료 부족 / 조회 실패를 카드 문구("상태: …")로 구분한다. 색상만으로 구분하지 않는다.
- 각 카드에 출처·기준일을 표시하고, `data_class` 를 그대로 표시한다(가상데이터면 "가상데이터").
- 요약 자료의 대상국·HS 와 화면 조건이 다르면 하단에 주의 문구를 낸다. 안정성 카드만 목적국별 결과로 바뀐다.
- 보고서 표의 5개 영역 값도 같은 요약값을 쓴다. 상세(책갈피) 탭은 아직 예시 데이터다.

## 2026-09-26 회사 데이터 교체 (handoff-v1)

팀 공유 문서 `junhee/docs/dashboard_items_team_handoff.txt` 기준으로 회사 데이터를 점수형(v0.1 샘플)에서 **항목형(handoff-v1)** 으로 바꿨다. 작업 규칙은 `junhee/WORK_RULES_0926.md`. 점수는 평가 기준 확정 전이라 계산·표시하지 않는다.

- 삭제: `static/data/companies/{hanbit,daesung,index}.json`, `static/samples/한빛반도체_수출데이터_v0.1.xlsx`, `static/samples/대성일렉트로닉스_수출데이터_v0.1.xlsx`, `junhee/data/processed/companies/*` (v0.1 산출물). 백업은 `../_merge_backup/2026-09-26/`.
- 사용 중지(파일은 남김, 맨 위에 주석): `score_companies.py`, `augment_samples.py`, `make_sample_companies.py`.
- 새 입력: `junhee/data/samples/한빛반도체_수출데이터_v0.2.xlsx`, `대성일렉트로닉스_수출데이터_v0.2.xlsx`, `새벽반도체_수출데이터_v0.1.xlsx` (시트: 기업정보·제품정보·거래처·수출실적·물류·월별집계 + 근거/결측목록). 스크립트는 '근거' 시트를 읽지 않는다(실제 기업명 포함).

실행 순서:

```
python junhee/scripts/build_company_items.py   # samples/*.xlsx + raw 공개자료 → processed/companies/{hanbit,daesung,saebyeok}.json, index.json
python junhee/scripts/publish_static.py        # 검증(허용 status·실제 기업명 없음·SHA 일치) 후 static/data/companies/, static/samples/ 로 복사
```

JSON 구조 (`schema: "handoff-v1"`):

```
{ company_id, company_name, company_name_en, file_name, file_sha256, schema, data_class: "가상 데이터 · 시연용", generated_at,
  score: { status: "미확인", note },                       // 점수 없음
  common: { period{from,to}, products[{id,name,family,input_hsk,analysis_hs6,hs_status,note}], hs_unknown_products, analysis_hs6,
            countries[{name,iso2,export_share,amount_usd}], main_country, main_hs6, currency,
            data_quality{ rows_total, rows_after_dedup, duplicates_removed, cancelled_zero_rows, rows_valid, rows_excluded_from_totals,
                          excluded_by_reason{금액·통화·거래일·목적국·제품ID·거래처ID·순중량·수량 빈칸}, missing_months, rows_with_hs_unknown_product } },
  per_country: { "<국가명>": { regulation[], market[], price[], logistics[], stability[] } } }
item = { key, label, status, value, unit, period, as_of, source, basis, note, rows? (+ 항목별 부가 키) }
status ∈ 확인됨 | 자료 부족 | 미확인 | 검색 결과 없음 | 검색 불가 · 실제 0 은 status 확인됨 + value 0
```

항목별 출처와 '미확인' 사유:

| 영역 | key | 출처 | 비고 |
|---|---|---|---|
| 규제 | export_control_candidates | HSK연계표_20260901.xlsx (입력HSK ↔ HSKCD 정확 대조, CNTRLNO) | 후보 표시, 해당 여부 판정 아님. HSK 빈칸 제품은 '검색 불가' |
| 규제 | import_regulation_records | KOTRA 수입규제 현황 CSV (규제시행국 ISO2 + HS 컬럼 앞자리 일치) | 0건이면 '검색 결과 없음'(규제 없음 판정 아님). 독일은 DE 코드로 검색, 파일에 'EU' 코드는 없음 |
| 규제 | csl_search | ITA CSL (법인명 정규화 후 name·alt_names 정확 일치) | 법인명 없는 거래처는 '검색 불가', 주소 없으면 '명칭만 검색' 표시 |
| 시장성 | destination_imports, korea_share, growth_yoy, growth_3m_yoy, cagr_3y | — | **미확인**: 목적국 수입통계 API 연동 전 |
| 시장성 | korea_exports_to_destination | WTO 관세조치 파일 imports 열(USD, 최신 가용치) | 조치일마다 같은 값이라 연도별 변화는 자료 부족. 파일 없는 나라(베트남)는 '자료 부족' |
| 시장성 | wsts | WSTS Monthly Data (Americas·Europe·Japan·Asia Pacific·Worldwide, 1000 US$) | 최근 13개월 + 전년동월비 |
| 시장성 | company_exports | 회사 수출실적 시트(유효 행) | 연도별·월별, 행이 없는 달은 null |
| 가격 | trade_unit_price | — | **미확인**: 무역통계 API 연동 전 |
| 가격 | company_unit_price | 회사 수출실적(금액 합 ÷ 순중량 합, 둘 다 있는 행) | 제품별·연도별, 실제 판매가 아님 |
| 가격 | baseline_unit_price | — | 자료 부족(한국 전체 수출단가 미확보) |
| 가격 | tariff_reference | WTO C###_C410.csv best_avlbl 조치일별 이력 | 참고치, 확정 세율 아님. 독일은 U918(EU) |
| 가격 | fx_reference | processed/stability.json per_currency (FRED H.10 → 월평균, 13개월) | 결제통화는 기업정보 '금액 통화'. 빈칸(새벽)은 '미확인' |
| 가격 | price_index | processed/price.json export_price_index (한국은행, 컴퓨터·전자·광학기기) | 반도체 개별 가격 아님 |
| 가격 | freight_reference | 관세청 hwpx 월별 표 (해상수출·해상수입·항공수입 구분) | 항로 없는 나라(인도·멕시코·캐나다)는 '자료 부족' |
| 물류 | cargo_flights, flight_counts, vessel_records | — | **미확인**: 인천공항·항만 API 연동 전 |
| 물류 | query_conditions | 회사 물류 시트(운송수단·출발지코드·도착지코드별 건수, 빈칸 건수) | 조회 조건만, 직항·배송시간 확정 아님 |
| 안정성 | destination_monthly_imports, cv, sharp_drops | — | **미확인**: 목적국 수입통계 API 연동 전 |
| 안정성 | company_export_volatility | 회사 월별 수출액(자료 있는 달만 CV, 두 달 다 있을 때만 전월비, −20% 이하 급감) | 보조, 미래 손실 확률 아님 |
| 안정성 | fx_volatility | processed/stability.json per_country (산식 v1.0) | 목적국 결제통화 기준 |
| 안정성 | wsts_volatility | WSTS 최근 13개월 전월비 절대값 평균·급감 횟수(권역별) | 보조 |

결측 처리(새벽반도체 검증): 완전 중복 1행 제거, 취소반품 Y 2건은 실제 0 으로 세고 유효 실적에서 제외, 금액·통화·거래일·목적국 빈칸 24행은 합계에서 제외, 제품ID·거래처ID·순중량·수량 빈칸은 해당 계산에서만 제외, 빈 달(2024-07, 2025-02)은 null. 엑셀 '결측목록' 시트의 건수와 일치함을 확인했다.

## 2026-09-26 홈 Contact Us (현업 의견·건의 접수, 프롬프트 ④)

- 홈(`/`) 상단·모바일·하단 메뉴에 `Contact Us` 링크, `#contact` 섹션(bottom CTA 바로 위). 스타일 `static/css/junhee-contact.css`, 동작 `static/js/junhee-contact.js` (home.css·home.js 는 수정하지 않음). 번역은 `static/js/axport-i18n.js` 에 새 문구만 추가(기존 항목 유지, 'Contact Us' 는 모든 언어에서 그대로).
- 접수 서버: `app.py` 의 `POST /api/contact` 1개. JSON 검증(의견 유형 필수, 내용 10~1000자, 이메일 형식, 이메일이 있으면 동의 필수, 이름 40자), 숨김 입력(honeypot)이 채워지면 저장하지 않고 성공처럼 응답, 같은 IP 1분 3회 초과(검증 실패 포함 모든 요청을 셈) 시 429. 응답은 `{ok:true}` 만 돌려주고 내용을 HTML 로 렌더링하지 않는다.
- 저장: `instance/contact_messages.jsonl` 한 줄 = 1건(시각·유형·분야·이름·이메일·내용). `instance/` 는 `.gitignore` 에 넣었다(개인정보).
- **시연용 한계**: Render 무료 환경은 재배포·재시작 때 `instance/` 파일이 사라진다. 계속 받으려면 구글 폼·노션 등 외부 저장으로 바꿔야 한다.
- 로컬에서 모인 의견을 CSV 로: `python junhee/scripts/export_contact.py` → `instance/contact_messages.csv` (UTF-8 BOM). 결과도 저장소에 넣지 않는다.

## 2026-09-26 밤 상세 탭 index3 형태 복원 · 기간/HS 필터 · 업로드 가이드 (junhee-dashboard.js v3)

- **상세 탭 5개**는 index3 형태(상태 상자 + KPI 4칸 + 3:2 차트/표 패널 + 안내 상자)로 되돌렸고, 헤더 오른쪽 **'항목 전체 보기' 토글**을 켜면 handoff-v1 항목 카드 전체가 아래에 붙는다(localStorage `jd_show_items`, 탭을 옮겨도 유지).
- **기간·HS 필터**는 공통 정보 막대의 드롭다운(전체 기간 / 최근 12·6개월 / 연도별 / 직접 설정 시작~종료 월, 전체 HS / 회사 HS6 목록). 바꾸면 회사 값(수출액·kg 단가·변동·조회 조건·통제번호 후보·관세·한국 수출액)과 점수 5개·종합·전월 대비·6개월 추세를 **브라우저에서 다시 계산**한다. 산식은 `demo_scoring.md` v0.2 를 JS 로 옮긴 것이고, 기본 필터(전체 기간·전체 HS)에서는 회사 JSON 의 `score` 블록과 같은 값이 나오는지 jsdom 스모크로 확인한다(15개 회사·목적국 조합 일치). 이를 위해 `build_company_items.py` 가 회사 JSON 에 `rows_agg`(월·목적국·제품·거래처별 금액/순중량 합), `logistics_agg`, `public_series.wsts_worldwide`(2021-01~ 세계 출하액·전년동월비 4자리), `products[].has_control_candidates` 를 넣는다. 공개자료 항목(WSTS·환율·물가지수·운임·KOTRA·CSL)은 기간 필터와 무관하게 파일 그대로.
- 정보 막대 맨 앞에 **표시 중인 엑셀 파일명** 칩, '기업 데이터' 창의 해당 파일 행에 **'분석 완료 · 대시보드에 표시 중'** 표시. 컨텍스트 바 자료기간은 필터 적용 시 '2024년 2024-01~2024-12' 처럼 바뀐다.
- **업로드 창**: HS CODE 입력이 드롭다운(`<select id="hs-input">`, workspace.html 1곳)으로 바뀌었다. 등록 샘플이면 '전체 HS (회사 제품 전체)' + 회사 HS6 목록으로 채우고, 고른 HS 가 대시보드 HS 필터와 컨텍스트 바(`HS 전체` 또는 코드)에 그대로 적용된다. 등록되지 않은 파일은 기본 854231/854232. 창 왼쪽 아래 **'업로드 가이드'** 버튼 → 모듈이 만드는 `#jd-guide-dialog`(필요 시트·열, 결측 처리 원칙, 등록 샘플 목록).
- 모듈 API 추가: `hsListOf(id)`, `setFilters({period,hs,from,to})`, `filters()`, `period()`, `calc()`, `openGuide()`; `configure({onFilter})` 로 workspace.js 가 컨텍스트 바를 맞추고 현재 탭을 다시 그린다. 레이아웃: `.jd-layout` 은 카드 내용보다 작아지지 않게(`min-height:auto`, 카드 행 `minmax(max-content,1fr)`) 해서 정보 막대가 두 줄이면 창이 스크롤된다.
- 캐시 버스트 css v=8 / junhee js v=9 / workspace js v=9. 검증: 스모크(점수 일치·필터·토글·보고서·가이드) + Playwright QA(`junhee/qa/0926/06_*.png`, 콘솔 오류 0). 미반영: 새 문구(드롭다운 라벨·가이드)의 i18n 항목.
