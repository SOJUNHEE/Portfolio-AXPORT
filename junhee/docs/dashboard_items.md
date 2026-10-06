# 대시보드에 들어갈 항목 공유

> 원문: `junhee/docs/dashboard_items_team_handoff.txt` (원문은 그대로 둔다). 이 문서는 원문 문장을 바꾸지 않고 제목·목록·표로만 정리했다.
> 화면 문구·상태 판단은 이 문서를 기준으로 한다. 맨 아래 **index3 화면 매핑** 표는 junhee 가 추가한 것이다(2026-09-26).

보유 파일의 수록 정보와 기존 API에서 조회·계산할 항목을 정리했어.
아래 내용을 확인할 수 있으면 되고, 화면 구성·배치·표현 방식 등 디자인은 전적으로 맡길게.

API 항목은 실제 응답과 필요한 기간의 자료를 확인한 뒤 제공할 예정이야.
아래 항목이 모두 이미 연동됐다는 의미는 아니고, 자료가 없는 항목은 ‘미확인’ 또는 ‘자료 부족’으로 구분해 줘.

---

## 1. 규제 — 관련 규제 기록이 있는가?

| 항목 | 내용 |
|---|---|
| 수출통제 관련 후보 | 입력한 HSK와 연결된 통제번호와 품목명. |
| 목적국 수입규제 기록 | 관련 품목의 규제 유형, 대상 원산지, 자료에 기재된 진행상황과 기간. |
| 거래처 명단 검색 | 거래처명을 입력한 경우, 보유 CSL에서 검색된 명칭·주소·명단 출처·기재기간. |

> ※ 여기서는 ‘관련 후보나 기록이 발견됐다’는 정보까지만 제공해.
> 바로 ‘수출금지’나 ‘거래금지’로 표시하지 않고, 검색된 기록이 없다는 이유만으로 ‘규제 없음’이라고 판단하지 않아.

## 2. 시장성 — 그 나라가 얼마나 수입하고, 시장이 커지고 있는가?

| 항목 | 내용 |
|---|---|
| 수입시장 규모 | 목적국이 해당 품목을 전 세계에서 수입한 금액과 연간·월별 변화. |
| 한국의 해당국 수출액 | 한국이 그 나라에 해당 품목을 수출한 금액과 변화. |
| 시장 성장률 | 전년 동기 대비 증가율, 최근 3개월의 전년 동기 대비 증가율, 3년 연평균 성장률. |
| 한국산 수입점유율 | 목적국 전체 수입 중 한국산의 비중. 같은 목적국의 수입자료가 확보됐을 때 제공. |
| 반도체 업황 참고정보 | WSTS 파일의 세계·권역별 반도체 매출과 추세. |

> ※ 목적국의 수입액, 한국의 수출액, WSTS 산업매출은 서로 다른 정보로 구분해 줘.
> 성장률은 필요한 기간의 자료가 있을 때만 계산할 예정이야.

## 3. 가격 — 통계상 단가와 관세·환율 수준은 어떠한가?

| 항목 | 내용 |
|---|---|
| 무역통계 단가 | 금액과 중량이 함께 확보된 경우 계산한 kg당 단가와 변화. |
| 기준 대비 단가 | 같은 품목·기간·출처 기준의 한국 전체 수출단가 대비 수준. 전체 범위가 확보됐을 때 제공. |
| 관세 참고치 | WTO 파일에 수록된 목적국·HS6별 관세 참고율과 날짜별 이력. |
| 참고환율 | 선택한 결제통화의 원화 기준 환율과 추세. |
| 관련 산업 가격지수 | 한국은행 파일의 ‘컴퓨터·전자·광학기기’ 등 실제 수록 분류의 수출입물가지수와 등락률. |
| 운송비 참고정보 | 수록 항로의 평균 운송비와 변화. 해상수출·해상수입·항공수입을 구분. |

> ※ 통계 단가는 제품의 실제 판매가가 아니고, HS6 관세 참고치는 확정 적용세율이 아니야.
> 산업 가격지수를 반도체 개별 제품의 가격으로, 항공수입 운송비를 한국발 항공수출 견적으로 표시하지 않아.

## 4. 물류 — 어떤 운항편과 입출항 기록을 확인할 수 있는가?

| 항목 | 내용 |
|---|---|
| 화물 항공편 일정 | 인천공항 화물편의 항공사·편명·상대공항·예정시각·변경시각·운항상태. |
| 운항 횟수 | 조회기간 안의 중복을 제거한 화물편수, 국가별 월간 출발·도착편수. |
| 선박 입출항 기록 | 조회 항만·선박명·입항 및 출항시각 등 실제 API 응답에서 확인된 정보. |

> ※ HS별 반도체 운송실적이 아니라 공항·항만·국가 기준 정보야.
> 출발·도착 방향과 시각의 의미를 실제 응답에서 확인한 뒤 제공할 예정이고,
> 이 기록만으로 직항 여부나 전체 배송시간, 해당 화물의 운송 가능 여부를 확정하지 않아.

## 5. 안정성 — 수입금액이 얼마나 흔들리고, 큰 감소가 얼마나 반복됐는가?

| 항목 | 내용 |
|---|---|
| 월별 수입금액 변화 | 목적국의 해당 품목 수입액과 전월 대비 증감률. |
| 변동계수(CV) | 월별 수입금액이 평균에 비해 얼마나 크게 흔들렸는지 나타내는 값. |
| 급감 이력 | 전월보다 20% 이상 감소한 달, 발생 횟수, 비교 가능한 횟수 대비 급감 빈도. |
| 보조정보 | 한국의 해당국 수출 변동, 결제통화의 환율 변동성, WSTS의 세계·권역별 반도체 매출 변동. |

> ※ 필요한 월별 자료가 확보됐을 때 계산하는 항목이야.
> 과거의 변동을 보여주는 것이지, 미래 손실이나 수출 실패 확률을 의미하지는 않아.

---

## 공통으로 포함할 정보

- 회사·제품명, 입력 HS코드와 실제 분석 HS코드, 목적국.
- 자료기간·기준일·출처, 계산 근거, 자료 부족 여부.
- 실제 값이 0인 경우와 자료가 없는 경우의 구분.
- 점수는 평가 기준과 산출값이 확정된 뒤 추가할 예정.

## 이번 기본 범위에서 제외할 항목

- 수출 가능·금지 확정
- 필수 허가·인증 충족 여부
- 실제 적용 관세·FTA 절감액
- 기업 이익률
- 직항 여부·전체 배송시간·납기 보장·화물 운송 가능 여부

이 항목들은 추가 자료와 검증이 필요해서 이번 기본 구성에서는 제외해 줘.

---

## 공개 API 연동 (2026-09-26 밤)

수집: `python junhee/scripts/fetch_public_apis.py` → `junhee/data/raw/api/*.json` (키는 `junhee/scripts/api_keys.py` 가 프로젝트 밖 조원 키 파일에서 실행 시점에만 읽음, 저장·출력 안 함)
→ `python junhee/scripts/build_company_items.py` → `python junhee/scripts/publish_static.py`. 챗봇 실연결 서버 실행: `python junhee/scripts/run_live.py`.

| API | 쓰는 항목 | 비고 |
|---|---|---|
| UN Comtrade (목적국 보고 수입, 월별·연간) | 수입시장 규모·한국산 점유율·성장률·월별 수입·CV·급감 | 발표 지연: 미국·인도·멕시코·캐나다 2026-07, 독일 2026-06(5월 없음), 중국 월별 2024-12, 베트남 2023-12 |
| UN Comtrade (한국 보고 수출) | 기준 대비 단가 | 2024-08~2025-12 |
| 관세청 품목별 국가별 수출입실적(GW) | 한국의 해당국 수출액·통계상 kg 단가 | 2023-01~2026-08 |
| 관세청 품목별 수출입실적(Itemtrade) | — | 이 키로는 미승인(403). 필요하면 공공데이터포털에서 활용 신청 |
| 인천국제공항공사 화물편 주간 운항 현황 (StatusOfCargoFlightsDSOdp) | 화물편 수·출발·도착·운항 기록 | 조회 시점 기준 약 +6일 |
| 인천국제공항공사 국가별 항공 통계 (AviationStatsByCountry, pax_cargo=N) | 월별 운항 횟수 | 2024-08~2026-08 |
| 해양수산부 선박운항정보 (VsslEtrynd5/Info5) | 선박 입출항 기록 | 부산항(020) 최근 7일 |
| 한국수출입은행 현재환율 | 참고환율 값 | 영업일 매매기준율 (추석 연휴는 직전 영업일) |
| OpenAI | 챗봇 | run_live.py 로 실행할 때만 live |
| WTO·ECOS·국가법령·KOTRA 해외인증 | 이번에는 미사용 | 관세는 WTO 관세조치 파일, 물가지수는 한국은행 파일 유지 · 인증은 기본 범위 제외 항목 |

## index3 화면 매핑 (junhee 추가, 2026-09-26)

화면(`static/js/junhee-dashboard.js`)은 어댑터 `toIndex3Data(companyJson, {country, hs, period})` 가 만든 index3 `AXPORT_DATA` 구조만 읽는다.
회사 JSON 은 `static/data/companies/<id>.json` (schema `handoff-v1`, 만드는 스크립트 `junhee/scripts/build_company_items.py`).
아래 "회사 JSON 값"의 `per_country[목적국].<영역>.<key>` 는 해당 목적국 블록의 항목(item)이고, 기간·HS 필터가 걸리면 회사 파일 값은 `rows_agg`·`logistics_agg` 에서 브라우저가 다시 계산한다.

상태 기준(샘플 3개 · 2026-09-26 확인):

- **확인됨** — 값이 있고 출처·기준일이 있는 칸.
- **미확인** — 연동 전 API 가 필요한 칸. 2026-09-26 밤 공개 API 연동 뒤에는 원자료(`junhee/data/raw/api`)가 없을 때만 남는다.
- **자료 부족** — 파일은 있지만 필요한 값·기간이 모자란 칸 (예: 3년 CAGR 은 48개월 필요, 새벽반도체는 결제통화 빈칸).
- **회사 자료** — 공개 통계 자리에 회사 파일(가상) 값을 넣은 칸. 화면에서 칸 이름 옆에 `회사 자료` 꼬리표를 붙이고, 공개 통계와 한 선으로 섞지 않는다.

| 영역 | 항목 (handoff) | index3 요소 id | 어댑터 필드 | 회사 JSON 값 | 상태 |
|---|---|---|---|---|---|
| 규제 | 수출통제 관련 후보 | `reg-control-count` | `regulation.controlCount` | `regulation.export_control_candidates` 의 후보 있는 제품 수 | 확인됨 |
| 규제 | 수출통제 관련 후보 | `reg-control-list` | `regulation.controls[{no,name,source}]` | `export_control_candidates.rows[].control_numbers·hsk_name·input_hsk` (출처 HSK연계표) | 확인됨 (후보 표시, 판정 아님) |
| 규제 | 목적국 수입규제 기록 | `reg-measure-table` (+ `reg-measure-count`) | `regulation.measures[{type,origin,status,period}]`, `measureCount` | `regulation.import_regulation_records.rows[]` (KOTRA) | 검색 결과 없음 (샘플 3개 모두, 규제 없음 판정 아님) |
| 규제 | 거래처 명단 검색 | `reg-csl-count` | `regulation.cslMatches` | `regulation.csl_search.value` (거래처 법인명 ↔ CSL 정확 일치) | 검색 결과 없음 / 새벽·인도는 검색 불가(법인명 빈칸) |
| 규제 | (상태 박스) | `reg-data-status` | `regulation.status` | 시연 산식 규제 관문 `needs_review` | 검토 필요 · 후보 발견 |
| 시장성 | 수입시장 규모 | `market-import` | `market.importValue` | `market.destination_imports` (UN Comtrade, 최근 12개월 합) | 확인됨 · 중국은 월별 2024-12까지, 베트남은 2023-12까지 |
| 시장성 | 한국의 해당국 수출액 | `market-korea` | `market.koreaExport` | `market.korea_exports_to_destination` (관세청 품목별 국가별 수출입실적, 월별 2023-01~2026-08) | 확인됨 |
| 시장성 | 시장 성장률 (전년 동기) | `market-yoy` | `market.yoy` | `market.growth_yoy` (Comtrade 목적국 수입) · 없으면 회사 월별 수출액(회사 자료) | 확인됨 · 베트남은 24개월 연속 자료 없어 자료 부족 |
| 시장성 | 한국산 수입점유율 | `market-share` | `market.koreaShare` | `market.korea_share` (Comtrade 한국산 ÷ 세계) | 확인됨 |
| 시장성 | 수입시장 규모(월별) · 한국 수출 · 회사 수출 | `marketTrendChart` | `market.monthly[{label,imports,korea,company}]` | imports=Comtrade 월별, korea=관세청 월별, company=`company_exports.rows`(오른쪽 축) | 확인됨 (세 계열을 따로 그림) |
| 시장성 | 시장 성장률 (YoY·최근 3개월·3년 CAGR) | `marketGrowthChart` | `market.growth[{label,value}]` | `growth_yoy`·`growth_3m_yoy`·`cagr_3y` (Comtrade, 48개월 없으면 연간으로 CAGR) | 확인됨 / 일부 나라 자료 부족 |
| 시장성 | 반도체 업황 참고정보 | (종합 시장성 점수 · 항목 전체 보기) | `overview.factors[market]` | `public_series.wsts_worldwide`, `market.wsts` | 확인됨 (산업 매출 · 목적국 수입액과 다른 정보) |
| 가격 | 무역통계 단가 | `price-unit` | `price.unitPrice` | `price.trade_unit_price` (관세청 한국→목적국 수출액 ÷ 중량, 최근 12개월) | 확인됨 |
| 가격 | 기준 대비 단가 | `price-reference-list` | `price.references` | `price.baseline_unit_price` (Comtrade 한국 보고 수출: 목적국 kg 단가 ÷ 전 세계 kg 단가 × 100) | 확인됨 |
| 가격 | 관세 참고치 | `price-tariff` | `price.tariff` | 시연 산식 `weighted_tariff_pct` 또는 `price.tariff_reference.value` (HS6별 최신 조치) | 확인됨 (참고치, 확정 세율 아님) |
| 가격 | 참고환율 | `price-fx` | `price.fx` | `price.fx_reference.value` (한국수출입은행 매매기준율, 최근 영업일) · 추세는 연준 H.10 월평균 | 확인됨 / 새벽반도체: 자료 부족 — 결제통화 미기재 |
| 가격 | 관련 산업 가격지수 | `price-index` | `price.index` | `price.price_index.value` (컴퓨터,전자및광학기기) | 확인됨 (반도체 개별 가격 아님) |
| 가격 | 참고환율 추세 | `fxChart` | `price.fxSeries[{label,value}]` | `fx_reference.rows` | 확인됨 / 새벽: 차트 대신 '자료 부족 — 결제통화 미기재' |
| 가격 | 관세 이력·단가·가격지수·운송비 | `price-reference-list` | `price.references[[이름,값,출처]]` | `tariff_reference.rows`(HS6 최신), `company_unit_price`, `price_index`, `freight_reference.rows`(해상수출·해상수입·항공수입) | 확인됨 (단가 기준 줄은 회사 자료) · 기준 대비 단가 줄 추가 |
| 물류 | 화물 항공편 일정 (편수) | `log-flight-count` | `logistics.flightCount` | `logistics.cargo_flights` (인천공항 화물편 주간 운항, 목적국 공항만, 중복 제거) | 확인됨 |
| 물류 | 화물편 (출발) | `log-departure-count` | `logistics.departures` | `cargo_flights.departures` | 확인됨 |
| 물류 | 화물편 (도착) | `log-arrival-count` | `logistics.arrivals` | `cargo_flights.arrivals` | 확인됨 |
| 물류 | 선박 입출항 기록 | `log-vessel-count` | `logistics.vesselCount` | `logistics.vessel_records` (해양수산부 선박운항정보, 부산항 최근 7일, 이전·다음 항이 목적국) | 확인됨 (0 은 실제 0) |
| 물류 | 운항 횟수 (월별) | `logFlightChart` | `logistics.monthly[{label,dep,arr}]` | `logistics.flight_counts` (인천공항 국가별 항공 통계, 화물기 pax_cargo=N) | 확인됨 |
| 물류 | 화물 항공편 일정 | `log-flight-table` | `logistics.flights` (+ `logistics.queries`) | 본문: `cargo_flights.rows` (항공사·편명·상대공항·예정·상태) / 아래 표: `query_conditions.rows` (회사 자료) | 확인됨 |
| 안정성 | 변동계수(CV) | `stability-cv` | `stability.cv` | 목적국 월별 수입(Comtrade) 최근 24개월 CV · 월별이 없는 나라는 회사 월별 수출액(회사 자료)로 대체 | 확인됨 |
| 안정성 | 급감 이력 (횟수) | `stability-drop-count` | `stability.dropCount` | 목적국 월별 수입 전월비 −20% 이하 (없으면 회사 자료) | 확인됨 |
| 안정성 | 급감 이력 (빈도) | `stability-drop-rate` | `stability.dropRate` | 비교 가능한 달 대비 급감 비율 (목적국 수입, 없으면 회사 자료) | 확인됨 |
| 안정성 | 보조정보 (환율 변동성) | `stability-fx-vol` | `stability.fxVol` | `stability.fx_volatility.value` (목적국 통화 월평균 전월비 절대값 평균) | 확인됨 / 베트남: 자료 부족 |
| 안정성 | 월별 수입금액 변화 | `stabilityChart` | `stability.monthly[{label,value,change}]` | `destination_monthly_imports` (Comtrade) · 없으면 회사 자료 | 확인됨 (빈 달은 끊어서 표시) |
| 안정성 | 급감 이력 (목록) | `stability-drop-table` | `stability.drops[{label,change,value}]` | `sharp_drops.rows` (없으면 회사 자료) | 확인됨 |
| 공통 | 회사·제품명, 입력 HS→분석 HS, 목적국, 자료기간 | 정보 막대 · 사이드바 ANALYSIS | `meta` | `company_name`, `file_name`, `common.products[]`, `common.countries[]`, `common.period` | 확인됨 |
| 공통 | 점수 | 종합 탭 도넛·카드 | `overview` | `score`(파이썬) = 브라우저 `calc()` (산식 `junhee/rules/demo_scoring.md` v0.3) | 가상 데이터 · 시연용 산식 · 평가 기준 확정 전 |
