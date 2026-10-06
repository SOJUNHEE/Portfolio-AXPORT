"use strict";
/* junhee-dashboard.js — 종합 탭(점수형) + 상세 탭 5개(index3 형태, 차트·모션) + handoff 항목 전체 보기 토글 (2026-09-26 v5).
   v5: 어댑터 toIndex3Data(companyJson, {country, hs, period}) → index3 AXPORT_DATA 구조. 화면은 이 구조만 읽는다(항목 문서 junhee/docs/dashboard_items.md).
       조건 선택(목적국·HS·기간)은 사이드바 'ANALYSIS · 분석 조건'(renderSidebar), 정보 막대는 회사·파일·제품만.
   디자인: JH2/index3.html 을 옮긴 junhee-dashboard.css 의 창 틀·파스텔 카드·책갈피 색을 그대로 쓰고, index3 처럼 카드 등장·숫자 카운트업·
          차트 애니메이션·호버 리프트를 켠다(?motion=off 로 끌 수 있음, 검토용).
   데이터: static/data/companies/index.json + <company_id>.json (schema handoff-v1). 회사 JSON 에는 목적국별 handoff 항목(per_country),
          월별 집계(rows_agg: 목적국·제품·거래처), 물류 집계(logistics_agg: 납기·운임·리드타임 합계), WSTS 장기 시계열(public_series)이 있어
          기간·HS 필터를 바꾸면 회사 값과 점수를 브라우저에서 다시 계산한다(평가 기준: junhee/rules/demo_scoring.md v0.3).
   종합 탭은 점수형(SCORE_MODE="score", 사용자 결정). 상세 탭은 index3 형태이고 '항목 전체 보기' 토글로 handoff 항목 카드를 덧붙인다.
   업로드: 결측·오류가 있는 파일은 qualityGate() 가 어느 시트·항목인지 보여주고 "그래도 진행" 확인을 받는다. 업로드 가이드 창에 양식 엑셀 다운로드.
   workspace.js 연결: configure({esc, defaults, getWeights, isCustom, onFilter}) / load / identifyFile / findByFileName / peek / countriesOf / hsListOf /
     select / setCountry / setFilters / filters / period / clear / current / country / calc / panelHTML / detailMeta / detailHTML / mount / destroy /
     replay / reportRows / reportHTML / confirm / qualityGate / openGuide / isAnalyzed */
(() => {
  const SCORE_MODE = "score"; // "score": 점수형 종합 탭(확정 형태). "hidden": 자료 확인 현황 화면.
  const INDEX_URL = "/static/data/companies/index.json";
  const TEMPLATE_URL = "/static/templates/company-data-template.xlsx"; // (junhee) 2026-09-27 sanghyeob 기업 데이터 양식(간편입력 v2)과 같은 파일·경로
  const isEngine = () => !!(current && current.score_source === "engine"); // (junhee) 2026-09-27 서버 엔진이 만든 문서인가
  const RULE_VER = "v0.3";
  // (2026-09-27 배포 QA) 가상 샘플 문서 구분(서버 sample 표시, 이전에 저장된 문서는 파일 이름의 '가상'으로) · 엔진 배점(문서 값 우선)
  const isSampleDoc = () => !!(current && (current.sample || /(^|_)가상(_|\.)/.test(String(current.file_name || ""))));
  const ENGINE_W = { market: 40, price: 20, logistics: 10, stability: 10 }; // 문서에 배점이 없을 때만 쓰는 기본값(analysis_suitability.policy_snapshot 과 같음)
  const engineWeights = () => (current && current.score && current.score.weights) || ENGINE_W;
  const dataClassText = () => current && current.score_source === "engine" ? (isSampleDoc() && !/가상/.test(current.data_class || "") ? "샘플 기업 (가상) · 외부 근거 연계" : current.data_class || "업로드 기업 데이터") : "샘플 기업 (가상)";
  const companyUrl = (id) => `/static/data/companies/${encodeURIComponent(id)}.json`;
  const MOTION = !(new URLSearchParams(location.search).get("motion") === "off" || document.documentElement.dataset.jdMotion === "off");
  if (!MOTION) document.documentElement.dataset.jdMotion = "off";
  const AREAS = [
    { key: "regulation", ko: "규제", ko2: "규제 관문", en: "REGULATION", icon: "shield-check", bg: "#fff5f5", kicker: "REGULATION GATE", title: "규제 기록 및 수출통제 후보",
      notice: "발견된 후보·기록만 표시합니다. 기록이 없어도 ‘규제 없음’으로 판정하지 않으며, 수출금지·거래금지를 확정하지 않습니다.", empty: "수입규제·제재 명단·통제번호 후보를 검토합니다." },
    { key: "market", ko: "시장성", ko2: "시장성", en: "MARKETABILITY", icon: "trend-up", bg: "#faf5ff", kicker: "MARKET DYNAMICS", title: "수입시장 규모 및 성장성",
      notice: "목적국 수입액·한국의 해당국 수출액·WSTS 산업매출은 서로 다른 정보이며 한 차트에 섞지 않습니다. 성장률은 필요한 기간의 자료가 있을 때만 계산합니다.", empty: "목적국 대세계 수입액·한국 수출·성장률을 봅니다." },
    { key: "price", ko: "가격", ko2: "가격", en: "PRICE & TARIFF", icon: "coins", bg: "#f0f9ff", kicker: "PRICE & TARIFF", title: "통계상 단가·관세 참고치·환율",
      notice: "통계 단가는 실제 판매가가 아니고, 관세 참고치는 확정 적용세율이 아닙니다. 산업 가격지수는 반도체 개별 제품 가격이 아니며, 항공수입 운송비는 항공수출 견적이 아닙니다.", empty: "희망판매가 대비 제품원가 여지와 관세·환율 참고치를 봅니다." },
    { key: "logistics", ko: "물류", ko2: "물류", en: "LOGISTICS", icon: "truck", bg: "#fffdf0", kicker: "LOGISTICS & FREIGHT", title: "화물 항공편 및 선박 입출항 기록",
      notice: "직항 여부·전체 배송시간·운송 가능 여부를 확정하지 않습니다. 납기·운임은 회사 파일 값(가상)이며 공개 운항 기록은 API 연동 전입니다.", empty: "30일 공급가능량·출고 준비기간을 봅니다." },
    { key: "stability", ko: "안정성", ko2: "안정성", en: "STABILITY", icon: "shield-plus", bg: "#f0fdf4", kicker: "RISK & STABILITY", title: "수입금액 변동성과 급감 이력",
      notice: "과거 변동이며 미래 손실·수출 실패 확률을 뜻하지 않습니다.", empty: "목적국 월간 수입액의 변동성과 급감 빈도를 봅니다 (국가위험 아님)." },
  ];
  const PALETTE = { regulation: "#e11d48", market: "#8b5cf6", price: "#0284c7", logistics: "#d97706", stability: "#059669" };
  const PALETTE2 = { regulation: "#f43f5e", market: "#a855f7", price: "#0ea5e9", logistics: "#f59e0b", stability: "#10b981" };
  const LINE = { regulation: "#ffe4e6cc", market: "#f3e8ffcc", price: "#e0f2fecc", logistics: "#fef3c7cc", stability: "#d1fae5cc" };
  const STATUSES = ["확인됨", "자료 부족", "미확인", "검색 결과 없음", "검색 불가"];
  const TONE = { "확인됨": "ok", "자료 부족": "warn", "미확인": "muted", "검색 결과 없음": "info", "검색 불가": "bad" };
  const NA = "—";
  const DEFAULT_WEIGHTS = { market: 35, price: 30, logistics: 20, stability: 15 };
  const WKEYS = Object.keys(DEFAULT_WEIGHTS);
  const NEEDED = { regulation: "수출실적 + KOTRA·CSL·HSK 연계표", market: "WSTS 출하액(기준월 3개월 이내) + 6개월 이상 수출실적", price: "목적국 WTO 관세 파일 + HS6 가 있는 제품 + 기준월 이전 조치일", logistics: "물류 시트의 예정·실제 도착일 5건 이상 + 운임(USD)", stability: "기간 안에 거래가 있는 달 6개 이상 + 거래처" };
  // (junhee) 2026-09-27 엔진 문서에서 근거가 없는 요인에 필요한 자료
  const ENGINE_NEEDED = { regulation: "규제는 점수 없이 관문으로 봅니다 (HSK 연계표·KOTRA·CSL 대조)", market: "UN Comtrade·관세청 무역통계 (API 키)", price: "간편입력 원가·희망판매단가 + 환율 (ECOS API 키)", logistics: "간편입력 30일 공급가능수량·출고준비기간", stability: "36개월 월간 수입통계 (UN Comtrade API 키)" };
  const FACTOR_KO = { regulation: "규제 관문", market: "시장성", price: "가격", logistics: "물류", stability: "안정성" };
  // (junhee) 2026-09-27 분석 엔진이 적합도를 판단할 수 있는 대상국(engine/company_import.py COUNTRIES)과
  // HS6(보유 자료 junhee/data/raw/test1_prices 관세표·test1_regulations HSK 연계표에 모두 있는 반도체 HS2022 코드)
  const ENGINE_COUNTRIES = [["US", "미국"], ["CN", "중국"], ["JP", "일본"], ["DE", "독일"], ["VN", "베트남"]];
  const ENGINE_HS = [
    ["집적회로 (8542)", [["854231", "프로세서·컨트롤러"], ["854232", "메모리"], ["854233", "증폭기"], ["854239", "기타 집적회로"], ["854290", "집적회로 부분품"]]],
    ["반도체 소자 (8541)", [["854110", "다이오드"], ["854121", "트랜지스터(1W 미만)"], ["854129", "기타 트랜지스터"], ["854130", "사이리스터·다이액·트라이액"], ["854141", "발광다이오드(LED)"], ["854149", "기타 광반도체 소자"], ["854151", "반도체 기반 변환기(센서)"], ["854159", "기타 반도체 소자"], ["854160", "압전 결정 소자"], ["854190", "반도체 소자 부분품"]]],
    ["반도체 제조장비 (8486)", [["848610", "보울·웨이퍼 제조기기"], ["848620", "반도체 소자·집적회로 제조기기"], ["848630", "평판디스플레이 제조기기"], ["848640", "마스크 제작·조립·운반 기기"], ["848690", "제조기기 부분품"]]],
  ];
  // 드롭다운 <option> 목록. dotted=true 면 값이 8542.32 형식(위젯 HS 입력칸)
  function engineHsOptions(selected, dotted) {
    const sel = String(selected || "").replace(/[.\s]/g, "").slice(0, 6), val = (h) => (dotted ? hsDot(h) : h);
    const known = ENGINE_HS.some(([, list]) => list.some(([h]) => h === sel));
    const extra = sel && /^\d{6}$/.test(sel) && !known ? `<option value="${esc(val(sel))}" selected>${esc(hsDot(sel))} · 파일 HS</option>` : "";
    return extra + ENGINE_HS.map(([g, list]) => `<optgroup label="${esc(g)}">${list.map(([h, n]) => `<option value="${esc(val(h))}"${h === sel ? " selected" : ""}>${esc(hsDot(h))} · ${esc(n)}</option>`).join("")}</optgroup>`).join("");
  }
  const AREA_OF = { company_exports: "market", korea_exports_to_destination: "market", company_unit_price: "price", tariff_reference: "price", company_export_volatility: "stability",
    query_conditions: "logistics", delivery_ontime: "logistics", lead_time: "logistics", freight_ratio: "logistics", shipments_monthly: "logistics", recent_shipments: "logistics", export_control_candidates: "regulation" };

  let cfg = { esc: null, onSelect: null, onFilter: null, getWeights: null, isCustom: null, defaults: DEFAULT_WEIGHTS };
  let index = null, indexError = null, indexPromise = null;
  const docs = {}, pending = {};
  let current = null, selectedCountry = null;
  let filters = { period: "all", hs: "all", from: null, to: null };
  let showItems = false;
  try { showItems = localStorage.getItem("jd_show_items") === "1"; } catch {}
  let charts = [], rafs = [], prevNums = {}, prevN = null, installed = false;
  const calcCache = new Map();

  // ---------------------------------------------------------------- 유틸
  const esc = (v) => (cfg.esc ? cfg.esc(v) : String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]));
  const reduced = () => !MOTION;
  const fin = (v) => v != null && Number.isFinite(+v);
  const color = (k) => PALETTE[k] || "#2563eb";
  const clip = (x) => Math.max(0, Math.min(100, x));
  const r1 = (x) => (x == null ? null : Math.round(x * 10 + 1e-9) / 10);
  const num = (v, d = 0) => (fin(v) ? (+v).toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d }) : NA);
  const pct = (v, d = 1) => (fin(v) ? (v > 0 ? "+" : "") + (+v).toFixed(d) + "%" : NA);
  const usd = (v) => (!fin(v) ? NA : Math.abs(v) >= 1e9 ? "$" + (v / 1e9).toFixed(2) + "B" : Math.abs(v) >= 1e6 ? "$" + (v / 1e6).toFixed(2) + "M" : Math.abs(v) >= 1e3 ? "$" + (v / 1e3).toFixed(1) + "K" : "$" + (+v).toFixed(0));
  const usdB = (v) => (fin(v) ? "$" + (v / 1e9).toFixed(1) + "B" : NA);
  const usdM = (v) => (fin(v) ? "$" + (v / 1e6).toFixed(1) + "M" : NA);
  const ymShort = (ym) => (ym ? String(ym).replace(/^\d{2}(\d{2})-(\d{2})$/, "$1.$2") : "");
  const hsDot = (hs) => (hs ? String(hs).replace(/^(\d{4})(\d+)$/, "$1.$2") : "미확인");
  const ymAdd = (ym, k) => { const [y, m] = String(ym).split("-").map(Number); const n = y * 12 + (m - 1) + k; return `${Math.floor(n / 12)}-${String((n % 12) + 1).padStart(2, "0")}`; };
  const ymRange = (a, b) => { const out = []; let cur = a; while (cur <= b && out.length < 600) { out.push(cur); cur = ymAdd(cur, 1); } return out; };
  const maxS = (a, b) => (a > b ? a : b), minS = (a, b) => (a < b ? a : b);
  const shortSrc = (s) => { s = String(s || ""); const base = s.split(" · ")[0]; return base.length > 34 ? base.slice(0, 32) + "…" : base; };
  const chip = (status) => `<span class="jd-st jd-st-${TONE[status] || "muted"}">${esc(status)}</span>`;
  const chipCount = (status, n) => (n ? `<span class="jd-st jd-st-${TONE[status] || "muted"}">${esc(status)} ${n}</span>` : "");
  const pill = (text, tone) => `<span class="jd-pill ${tone}">${text}</span>`;
  const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  const pstdev = (a) => { const m = mean(a); return Math.sqrt(a.reduce((x, y) => x + (y - m) ** 2, 0) / a.length); };
  // 카운트업 숫자: data-cnt(목표값) + data-fmt(표시 형식). mount() 의 countUp 이 0 → 목표값으로 올린다 (index3 카운터와 같은 easeOut)
  const FMT = { int: (v) => num(v, 0), d1: (v) => (+v).toFixed(1), d2: (v) => (+v).toFixed(2), pct1: (v) => (+v).toFixed(1) + "%", pct2: (v) => (+v).toFixed(2) + "%", spct1: (v) => pct(v, 1),
    usd: usd, usdM: usdM, usdB: usdB, kg: (v) => num(v, 0) + " USD/kg", day1: (v) => (+v).toFixed(1) + "일", cnt: (v) => num(v, 0) + "건", times: (v) => num(v, 0) + "회", pm1: (v) => "±" + (+v).toFixed(1) + "%", ratio2: (v) => (+v).toFixed(2), krw2: (v) => num(v, 2) };
  const fmtCnt = (v, f) => (FMT[f] || FMT.d1)(v);
  const cnt = (v, f) => (fin(v) ? `<span class="jd-cnt" data-cnt="${+v}" data-fmt="${f}">${fmtCnt(v, f)}</span>` : NA);

  // ---------------------------------------------------------------- 데이터
  function fetchJson(url) {
    return fetch(url, { cache: "no-store" }).then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }
  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (!indexPromise)
      indexPromise = fetchJson(INDEX_URL).then((doc) => { if (!doc || !Array.isArray(doc.companies)) throw new Error("index.json 형식 오류"); index = doc; indexError = null; return index; })
        .catch((e) => { indexError = e; indexPromise = null; console.error("JunheeDashboard index:", e); return null; });
    return indexPromise;
  }
  const entries = () => (index ? index.companies : []);
  const findByFileName = (name) => entries().find((c) => c.file_name === name) || null;
  const findById = (id) => entries().find((c) => c.company_id === id) || null;
  async function sha256Hex(file) {
    const h = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
    return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }
  async function identifyFile(file) {
    await loadIndex();
    if (!index) return { status: "error", message: "등록된 샘플 목록을 불러오지 못했습니다." };
    if (!(window.crypto && crypto.subtle)) return { status: "error", message: "이 브라우저에서는 파일 해시를 계산할 수 없습니다 (https 또는 localhost 필요)." };
    try { const sha = await sha256Hex(file); const entry = entries().find((c) => c.file_sha256 === sha) || null; return entry ? { status: "matched", entry, sha } : { status: "unregistered", sha }; }
    catch (e) { return { status: "error", message: String((e && e.message) || e) }; }
  }
  function peek(companyId) {
    if (docs[companyId]) return Promise.resolve(docs[companyId]);
    if (!pending[companyId])
      pending[companyId] = fetchJson(companyUrl(companyId)).then((doc) => { if (!doc || doc.schema !== "handoff-v1" || !doc.per_country) throw new Error("회사 JSON 스키마가 handoff-v1 이 아님"); docs[companyId] = doc; return doc; })
        .catch((e) => { delete pending[companyId]; throw e; });
    return pending[companyId];
  }
  const countriesOf = (companyId) => (docs[companyId] ? docs[companyId].common.countries.map((c) => c.name) : null);
  const hsListOf = (companyId) => (docs[companyId] ? docs[companyId].common.analysis_hs6 || [] : null);
  async function select(companyId, country) {
    await loadIndex();
    if (!findById(companyId)) return null;
    const doc = await peek(companyId);
    prevN = current ? confirmed().n : null;
    prevNums = current ? snapshot() : {};
    const same = current && current.company_id === doc.company_id;
    current = doc;
    if (!same) { filters = { period: "all", hs: "all", from: null, to: null }; calcCache.clear(); }
    selectedCountry = country && doc.per_country[country] ? country : doc.common.main_country;
    if (cfg.onSelect) cfg.onSelect(current);
    formalChrome(); // (junhee) 2026-09-27 엔진 문서에서 돌아올 때 판단 기준 표시 복원
    return current;
  }
  // (junhee) 2026-09-27 서버 엔진이 만든 문서(등록 샘플 목록에 없는 업로드 파일)를 바로 연다
  function selectDoc(doc, country) {
    if (!doc || doc.schema !== "handoff-v1" || !doc.per_country || !doc.common) return null;
    prevN = current ? confirmed().n : null;
    prevNums = current ? snapshot() : {};
    current = doc;
    docs[doc.company_id] = doc;
    filters = { period: "all", hs: "all", from: null, to: null };
    calcCache.clear();
    selectedCountry = country && doc.per_country[country] ? country : doc.common.main_country;
    if (cfg.onSelect) cfg.onSelect(current);
    formalChrome(); // (junhee) 창 제목의 판단 기준 표시를 문서에 맞춘다
    return current;
  }
  function setCountry(name) { if (!current || !current.per_country[name]) return false; prevNums = snapshot(); selectedCountry = name; return true; }
  function setFilters(f) {
    if (!current) return false;
    const next = { ...filters, ...(f || {}) };
    if (next.hs !== "all" && !(current.common.analysis_hs6 || []).includes(next.hs)) next.hs = "all";
    prevNums = snapshot();
    filters = next;
    return true;
  }
  function clear() { current = null; selectedCountry = null; prevN = null; prevNums = {}; filters = { period: "all", hs: "all", from: null, to: null }; calcCache.clear(); if (cfg.onSelect) cfg.onSelect(null); formalChrome(); }
  const weights = () => { const w = (cfg.getWeights && cfg.getWeights()) || cfg.defaults || DEFAULT_WEIGHTS; const out = {}; WKEYS.forEach((k) => (out[k] = Number.isFinite(+w[k]) ? +w[k] : DEFAULT_WEIGHTS[k])); return out; };
  const isDefaultWeights = () => { const w = weights(), d = cfg.defaults || DEFAULT_WEIGHTS; return WKEYS.every((k) => w[k] === d[k]); };
  const isCustom = () => (cfg.isCustom ? !!cfg.isCustom() : !isDefaultWeights());

  // ---------------------------------------------------------------- 기간·HS 필터, 월별 집계
  function periodRange() {
    if (!current) return null;
    const P = current.common.period, F = P.from, T = P.to;
    let from = F, to = T, label = "전체 기간";
    const p = filters.period;
    if (p === "12m") { from = maxS(F, ymAdd(T, -11)); label = "최근 12개월"; }
    else if (p === "6m") { from = maxS(F, ymAdd(T, -5)); label = "최근 6개월"; }
    else if (/^\d{4}$/.test(p)) { from = maxS(F, p + "-01"); to = minS(T, p + "-12"); label = p + "년"; }
    else if (p === "custom" && filters.from && filters.to) { from = maxS(F, filters.from); to = minS(T, filters.to); if (from > to) [from, to] = [to, from]; label = "직접 설정"; }
    return { from, to, asOf: to, label, isDefault: from === F && to === T, months: ymRange(from, to) };
  }
  const productHs = () => Object.fromEntries((current ? current.common.products : []).map((p) => [p.id, p.analysis_hs6 || ""]));
  function rowsFor(country, from, to) {
    const ph = productHs(), hs = filters.hs;
    return (current.rows_agg || []).filter((r) => r.c === country && r.m >= from && r.m <= to && (hs === "all" || (r.p && ph[r.p] === hs)));
  }
  function logsFor(country, from, to) {
    const ph = productHs(), hs = filters.hs;
    return (current.logistics_agg || []).filter((l) => l.c === country && l.m >= from && l.m <= to && (hs === "all" || (l.p && ph[l.p] === hs)));
  }
  const itemRaw = (key, k) => { const b = current && selectedCountry && current.per_country[selectedCountry]; return b ? (b[key] || []).find((it) => it.key === k) || null : null; };

  // ---------------------------------------------------------------- 점수 (demo_scoring v0.3 를 브라우저에서 계산)
  function scReg(win, p1, p2, cands) {
    const total = win.reduce((a, r) => a + r.a, 0);
    const share = total > 0 ? win.filter((r) => cands.has(r.p)).reduce((a, r) => a + r.a, 0) / total : 0;
    const p3 = 20 * share;
    return { score: r1(clip(100 - p1 - p2 - p3)), state: "ok", needs_review: p1 + p2 + p3 > 0,
      note: `수입규제 ${p1 ? "기록 있음" : "기록 없음"} · CSL ${p2 ? "일치 있음" : "일치 없음"} · 통제번호 후보 품목 비중 ${(share * 100).toFixed(0)}% (검토 필요, 해당 확정 아님)`,
      inputs: { P1_kotra: p1, P2_csl: p2, P3_hsk: r1(p3), hsk_candidate_share: Math.round(share * 1e4) / 1e4 } };
  }
  function scMarket(rows, M, wsts) {
    const cand = wsts.filter((x) => x.month <= M && x.month >= ymAdd(M, -3) && fin(x.value_thousand_usd));
    const w = cand.length ? cand[cand.length - 1] : null;
    if (!w || !fin(w.yoy_pct)) return { score: null, state: "insufficient", note: `${M} 기준 3개월 이내 WSTS 출하액(전년동월비) 없음` };
    const recent = rows.filter((r) => r.m >= ymAdd(M, -2) && r.m <= M).reduce((a, r) => a + r.a, 0);
    const prev = rows.filter((r) => r.m >= ymAdd(M, -5) && r.m <= ymAdd(M, -3)).reduce((a, r) => a + r.a, 0);
    if (prev <= 0) return { score: null, state: "insufficient", note: "직전 3개월 수출실적이 없어 증가율을 계산할 수 없음" };
    const growth = (recent / prev - 1) * 100, f = clip(50 + w.yoy_pct / 2), g = clip(50 + growth);
    return { score: r1(0.5 * f + 0.5 * g), state: "ok", note: `세계 출하 전년동월비 ${pct(w.yoy_pct)}(${w.month}) · 최근 3개월 수출액 ${pct(growth)}`,
      inputs: { wsts_yoy_pct: Math.round(w.yoy_pct * 100) / 100, wsts_month: w.month, wsts_value_thousand_usd: w.value_thousand_usd, company_growth_3m_pct: Math.round(growth * 100) / 100, recent_3m_usd: recent, prev_3m_usd: prev, f: r1(f), g: r1(g) } };
  }
  function scPrice(win, M, tariff) {
    if (!tariff || tariff.status !== "확인됨" || !tariff.rows) return { score: null, state: "insufficient", note: (tariff && tariff.note) || "WTO 관세조치 파일 없음" };
    const ph = productHs(), byHs = {};
    win.forEach((r) => { const h = r.p ? ph[r.p] : ""; if (h) byHs[h] = (byHs[h] || 0) + r.a; });
    const hsList = Object.keys(byHs);
    if (!hsList.length) return { score: null, state: "insufficient", note: "HS6 가 있는 제품의 수출실적 없음" };
    const rates = {};
    for (const h of hsList) { const rs = tariff.rows.filter((x) => x.hs6 === h && fin(x.best_avlbl_pct) && x.year_dt.slice(0, 7) <= M); if (!rs.length) return { score: null, state: "insufficient", note: `HS ${hsDot(h)}: ${M} 이전 관세 조치일 없음 (파일 수록 ${tariff.period || ""})` }; rates[h] = rs[rs.length - 1].best_avlbl_pct; }
    const tot = hsList.reduce((a, h) => a + byHs[h], 0), r = hsList.reduce((a, h) => a + rates[h] * byHs[h] / tot, 0), t = clip(100 - 2 * r);
    return { score: r1(t), state: "ok", note: `가중 관세 참고율 ${r.toFixed(2)}% · 마진 자료 없음(원가·비용 시트 미포함) → 관세 항목만 반영`, inputs: { weighted_tariff_pct: Math.round(r * 1000) / 1000, t: r1(t), m: null, tariff_by_hs6: rates } };
  }
  function scLog(lwin) {
    const s = (k) => lwin.reduce((a, l) => a + (l[k] || 0), 0);
    const tr = s("tr"), ot = s("ot");
    if (tr < 5) return { score: null, state: "insufficient", note: `추적 창 안에 예정·실제 도착일이 모두 있는 물류 행 ${tr}건 (5건 이상 필요)` };
    const f = s("fr"), a = s("fa");
    if (!(a > 0)) return { score: null, state: "insufficient", note: "운임과 연결된 수출금액이 있는 물류 행 없음" };
    const ontime = (ot / tr) * 100, fr = (f / a) * 100, c = clip(100 - 10 * fr);
    return { score: r1(0.7 * ontime + 0.3 * c), state: "ok", note: `납기 준수율 ${ontime.toFixed(1)}% (${ot}/${tr}건) · 운송비 비중 ${fr.toFixed(2)}% → c ${c.toFixed(1)} (회사 물류 자료, 배송시간 확정 아님)`,
      inputs: { ontime_pct: Math.round(ontime * 100) / 100, tracked_rows: tr, ontime_rows: ot, freight_ratio_pct: Math.round(fr * 1000) / 1000, freight_usd: Math.round(f * 100) / 100, linked_amount_usd: Math.round(a * 100) / 100, c: r1(c) } };
  }
  function scStab(win) {
    const totals = {};
    win.forEach((r) => (totals[r.m] = (totals[r.m] || 0) + r.a));
    const months = Object.keys(totals);
    if (months.length < 6) return { score: null, state: "insufficient", note: `기간 안에 거래가 있는 달이 ${months.length}개 (6개 이상 필요)` };
    const rc = win.filter((r) => r.cu), tot = rc.reduce((a, r) => a + r.a, 0);
    if (tot <= 0) return { score: null, state: "insufficient", note: "거래처가 연결된 수출실적 없음" };
    const byC = {}; rc.forEach((r) => (byC[r.cu] = (byC[r.cu] || 0) + r.a));
    const hhi = Object.values(byC).reduce((a, v) => a + (v / tot) ** 2, 0), conc = clip((1 - hhi) * 100);
    const vals = months.map((m) => totals[m]), cv = (pstdev(vals) / mean(vals)) * 100, cvs = clip(100 - 2 * cv);
    return { score: r1(0.5 * conc + 0.5 * cvs), state: "ok", note: `거래처 집중도 HHI ${hhi.toFixed(2)} · 월별 수출액 변동계수 ${cv.toFixed(0)}% (목적국 내 거래처 기준, 국가위험 아님)`,
      inputs: { hhi_customer: Math.round(hhi * 1e4) / 1e4, conc: r1(conc), cv_pct: Math.round(cv * 100) / 100, cv_score: r1(cvs), months_with_sales: months.length } };
  }
  function overallOf(per, w) {
    const ok = WKEYS.filter((k) => per[k].state === "ok"), missing = WKEYS.filter((k) => per[k].state !== "ok");
    const sum = ok.reduce((a, k) => a + w[k], 0);
    if (!ok.length || sum <= 0) return { score: null, missing };
    return { score: ok.reduce((a, k) => a + w[k] * per[k].score, 0) / sum, missing };
  }
  // ---------------------------------------------------------------- 판정 · 평가 문장 (평가 기준 v0.3)
  // 등급: 85 이상 매우 좋음 · 70 이상 양호 · 55 이상 보통 · 40 이상 미흡 · 그 밖 취약
  const GRADE = [[85, "매우 좋습니다.", "매우 좋음"], [70, "양호합니다.", "양호"], [55, "보통 수준입니다.", "보통"], [40, "다소 미흡합니다.", "미흡"], [-1, "취약합니다.", "취약"]];
  const gradeOf = (x) => GRADE.find((g) => x >= g[0]);
  // 받침에 따라 은/는 · 이/가 (한글 끝 글자 기준)
  const josa = (word, withBatchim, without) => { const w = String(word), c = w.charCodeAt(w.length - 1); return c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 ? withBatchim : without; };
  // 규제 관문 판정: 수입규제 기록·제재 명단 일치 → 보류 / 통제번호 후보 품목 → 조건부 통과 / 그 밖 → 통과
  function gateOf(reg) {
    const i = (reg && reg.inputs) || {};
    if (i.P1_kotra || i.P2_csl) return { key: "hold", label: "보류", text: "수입규제 기록 또는 제재 명단 일치가 있어 추가 검토 전까지 판정을 보류합니다." };
    if (i.hsk_candidate_share > 0) return { key: "cond", label: "조건부 통과", text: `통제번호 후보 품목(수출액 비중 ${Math.round(i.hsk_candidate_share * 100)}%)이 있어 선적 전 전략물자 해당 여부 확인이 필요합니다.` };
    return { key: "pass", label: "통과", text: "검색된 수입규제·제재 명단 기록과 통제번호 후보가 없어 규제 관문을 통과했습니다." };
  }
  // 종합 판정: 규제 관문이 보류면 판정 보류, 아니면 종합 점수 구간 (조건부 통과면 '전략물자 확인 조건' 을 붙인다)
  function verdictOf(score, gate) {
    if (gate.key === "hold") return { key: "hold", label: "판정 보류", tone: "bad" };
    if (score == null) return { key: "na", label: "판정 불가 (자료 부족)", tone: "muted" };
    const base = score >= 80 ? ["fit", "수출 적합", "ok"] : score >= 65 ? ["good", "수출 가능 (보완 권고)", "info"] : score >= 50 ? ["improve", "보완 후 추진", "warn"] : ["recheck", "재검토", "bad"];
    return { key: base[0], label: base[1] + (gate.key === "cond" ? " · 전략물자 확인 조건" : ""), tone: base[2] };
  }
  // (junhee) 2026-09-27 업로드 파일을 sanghyeob 엔진으로 분석한 문서(score_source "engine")는 브라우저 재계산 대신 엔진 점수를 그대로 쓴다.
  // 엔진은 규제를 점수에 더하지 않는 관문으로 보고, 미평가 항목은 정책 기준 50점으로 계산한다(근거 반영률을 함께 표시).
  function engineCalc() {
    const w = weights(), key = JSON.stringify([current.company_id, selectedCountry, w, "engine"]);
    if (calcCache.has(key)) return calcCache.get(key);
    const pr = periodRange(), s = current.score.per_country[selectedCountry] || {}, so = s.overall || {};
    const factors = AREAS.map((a) => {
      const f = (s.factors || []).find((x) => x.key === a.key) || { state: "insufficient", note: "" };
      return { key: a.key, score: f.score == null ? null : f.score, state: f.state === "ok" ? "ok" : "insufficient", delta: null, series: f.series || [null], series_months: f.series_months || [pr.asOf],
        note: f.note || "", inputs: f.inputs || {}, needs_review: !!f.needs_review, gate: a.key === "regulation" };
    });
    let score = so.score == null ? null : so.score, excluded = so.excluded || [];
    if (isCustom()) { const ov = overallOf(Object.fromEntries(factors.map((f) => [f.key, f])), w); score = ov.score; excluded = ov.missing; } // 사용자 가중치: 근거가 있는 요인만 다시 평균
    const gate = so.regulation_gate === "BLOCKED"
      ? { key: "hold", label: "보류", text: "규제 확인 결과 진행 제한 사유가 있어 추가 검토 전까지 판정을 보류합니다." }
      : { key: "cond", label: "검토 필요", text: "통제번호 후보·수입규제·거래 상대 이름 확인이 필요합니다. 규제는 점수에 더하지 않는 별도 관문입니다." };
    const verdict = gate.key === "hold" ? { key: "hold", label: "판정 보류", tone: "bad" }
      : score == null ? { key: "na", label: "판정 불가 (자료 부족)", tone: "muted" }
      : isCustom() ? { key: "custom", label: `사용자 가중치 참고점수 (엔진 등급: ${so.grade || "—"})`, tone: "info" } // (2026-09-27 배포 QA) 엔진 등급·판단 근거 부족 기준이 아닌 화면 참고점수
      : { key: so.grade_code || "engine", label: so.grade || "참고 적합도", tone: so.tone || "info" };
    const overall = { score: r1(score), state: score != null ? "ok" : "insufficient", delta: null, series: [r1(score)], excluded, recomputed: isCustom(), needs_regulation_review: true, gate, verdict, note: so.note };
    const miss = (current.engine && current.engine.missing) || { fields: [], missing_sheets: [] }, scoredMiss = (miss.fields || []).filter((f) => f.scored);
    const missText = scoredMiss.length || (miss.missing_sheets || []).length ? ` 입력 결측: ${[...scoredMiss.map((f) => `${f.label}(${f.cell})`), ...(miss.missing_sheets || []).map((m) => m + " 시트")].join("·")} — 해당 항목은 값을 채우지 않고 정책 기준 50점으로 계산했습니다.` : ""; // (junhee) 2026-09-27
    const highlights = (s.highlights || "") + (so.note ? ` (${so.note})` : "") + missText + (isCustom() ? " 사용자 가중치로 근거 반영률이 0%가 아닌 영역만 다시 평균한 화면 참고점수입니다(영역 점수 안의 정책 기준 50점은 그대로 포함). 엔진 등급·판단 근거 부족 기준은 적용되지 않습니다." : "");
    const out = { pr, rows: [], logs: [], per: {}, factors, overall, highlights, items: {} };
    calcCache.set(key, out);
    return out;
  }
  function calc() {
    if (!current || !selectedCountry) return null;
    if (current.score_source === "engine") return engineCalc(); // (junhee)
    const w = weights(), key = JSON.stringify([current.company_id, selectedCountry, filters, w]);
    if (calcCache.has(key)) return calcCache.get(key);
    const pr = periodRange(), country = selectedCountry, rows = rowsFor(country, pr.from, pr.to), logs = logsFor(country, pr.from, pr.to);
    const kotra = itemRaw("regulation", "import_regulation_records"), csl = itemRaw("regulation", "csl_search"), tariff = itemRaw("price", "tariff_reference");
    const p1 = kotra && kotra.status === "확인됨" && kotra.value > 0 ? 30 : 0, p2 = csl && csl.status === "확인됨" && csl.value > 0 ? 40 : 0;
    const cands = new Set(current.common.products.filter((p) => p.has_control_candidates).map((p) => p.id));
    const wsts = (current.public_series && current.public_series.wsts_worldwide) || [];
    const months7 = []; for (let k = 6; k >= 0; k--) months7.push(ymAdd(pr.asOf, -k));
    const per = {};
    months7.forEach((M) => {
      const lo = maxS(pr.from, ymAdd(M, -11));
      const win = rows.filter((r) => r.m >= lo && r.m <= M), lwin = logs.filter((l) => l.m >= lo && l.m <= M);
      per[M] = { regulation: scReg(win, p1, p2, cands), market: scMarket(rows, M, wsts), price: scPrice(win, M, tariff), logistics: scLog(lwin), stability: scStab(win) };
    });
    const asOf = pr.asOf, prevM = ymAdd(asOf, -1), series6 = months7.slice(1);
    const factors = AREAS.map((a) => {
      const cur = per[asOf][a.key], prev = per[prevM][a.key];
      return { key: a.key, score: cur.score, state: cur.state, delta: cur.state === "ok" && prev.state === "ok" ? r1(cur.score - prev.score) : null,
        series: series6.map((m) => per[m][a.key].score), series_months: series6, note: cur.note, inputs: cur.inputs || {}, needs_review: !!cur.needs_review, gate: a.key === "regulation" };
    });
    const ov = overallOf(per[asOf], w), ovPrev = overallOf(per[prevM], w);
    const overall = { score: r1(ov.score), state: ov.score != null ? "ok" : "insufficient", delta: ov.score != null && ovPrev.score != null ? r1(ov.score - ovPrev.score) : null,
      series: series6.map((m) => r1(overallOf(per[m], w).score)), excluded: ov.missing, recomputed: isCustom(), needs_regulation_review: !!per[asOf].regulation.needs_review };
    const oks = factors.filter((f) => f.state === "ok" && f.key !== "regulation");
    const best = oks.length ? oks.reduce((x, y) => (y.score > x.score ? y : x)) : null, worst = oks.length ? oks.reduce((x, y) => (y.score < x.score ? y : x)) : null;
    const gate = gateOf(per[asOf].regulation), verdict = verdictOf(overall.score, gate);
    overall.gate = gate; overall.verdict = verdict;
    let hl = "";
    if (overall.score != null) hl += `종합 ${overall.score.toFixed(1)}점으로 ${country} 수출 적합도가 ${gradeOf(overall.score)[1]} 판정은 '${verdict.label}'입니다. `;
    else hl += "종합 점수를 계산할 자료가 부족합니다. ";
    if (best && worst && best !== worst) {
      const bn = FACTOR_KO[best.key], wn = FACTOR_KO[worst.key];
      hl += `${bn}${josa(bn, "이", "가")} ${best.score.toFixed(0)}점으로 가장 좋고, ${wn}${josa(wn, "은", "는")} ${worst.score.toFixed(0)}점으로 ${worst.score >= 70 ? "양호하지만 상대적으로 낮습니다" : "보완이 필요합니다"}. `;
    }
    if (overall.delta != null) hl += Math.abs(overall.delta) < 0.05 ? "종합 점수는 전월과 같습니다. " : `종합 점수는 전월 대비 ${overall.delta > 0 ? "+" : ""}${overall.delta.toFixed(1)}점 ${overall.delta > 0 ? "상승했습니다" : "하락했습니다"}. `;
    hl += gate.text + " ";
    if (ov.missing.length) hl += `${ov.missing.map((k) => FACTOR_KO[k]).join("·")} 요인은 자료가 부족해 종합 점수에서 제외했습니다. `;
    hl += `(${pr.label} ${pr.from}~${pr.to}${filters.hs !== "all" ? ` · HS ${hsDot(filters.hs)}` : ""} 기준)`;
    const out = { pr, rows, logs, per, factors, overall, highlights: hl, items: companyItems(country, pr, rows, logs) };
    calcCache.set(key, out);
    return out;
  }
  // 회사 값에서 나오는 handoff 항목을 기간·HS 필터로 다시 만든다 (공개자료 항목은 JSON 그대로)
  function companyItems(country, pr, rows, logs) {
    const c = current.common, months = pr.months, ph = productHs(), src = current.file_name;
    const base = (k) => itemRaw(AREA_OF[k], k) || {};
    const totals = {}; rows.forEach((r) => (totals[r.m] = (totals[r.m] || 0) + r.a));
    const monthly = months.map((m) => ({ month: m, value_usd: m in totals ? Math.round(totals[m] * 100) / 100 : null, rows: rows.filter((r) => r.m === m).reduce((a, r) => a + r.n, 0) }));
    const yearly = {}; rows.forEach((r) => { const y = r.m.slice(0, 4); yearly[y] = (yearly[y] || 0) + r.a; });
    const hsTag = filters.hs !== "all" ? ` · HS ${hsDot(filters.hs)}` : "", per = `${pr.from}~${pr.to}`;
    const out = {};
    out.company_exports = { ...base("company_exports"), key: "company_exports", label: `회사 자료 · ${country} 수출액 (연도별·월별)`, status: rows.length ? "확인됨" : "자료 부족", value: Math.round(rows.reduce((a, r) => a + r.a, 0) * 100) / 100, unit: "USD",
      period: per, as_of: pr.to, source: src + " · 수출실적 시트", basis: `유효 행의 금액 합 · ${pr.label}${hsTag} · 행이 없는 달은 결측(자료 없음)`, note: "회사 자료 · 회사 자체 수출 흐름 (목적국 수입액 아님)", rows: monthly, yearly: Object.keys(yearly).sort().map((y) => ({ year: y, value_usd: Math.round(yearly[y] * 100) / 100 })) };
    const byPY = {}; let exW = 0;
    rows.forEach((r) => { if (!r.p || !ph[r.p]) return; if (!(r.w > 0)) { exW += r.n; return; } const k = r.p + "|" + r.m.slice(0, 4); byPY[k] = byPY[k] || { p: r.p, y: r.m.slice(0, 4), a: 0, w: 0, n: 0 }; byPY[k].a += r.aw; byPY[k].w += r.w; byPY[k].n += r.nw; exW += r.n - r.nw; });
    const prows = Object.values(byPY).sort((a, b) => (a.p + a.y).localeCompare(b.p + b.y)).map((v) => { const p = c.products.find((x) => x.id === v.p) || {}; return { product_id: v.p, product: p.name, hs6: p.analysis_hs6 || null, year: v.y, usd_per_kg: Math.round((v.a / v.w) * 100) / 100, rows_used: v.n }; });
    const A = Object.values(byPY).reduce((a, v) => a + v.a, 0), W = Object.values(byPY).reduce((a, v) => a + v.w, 0);
    out.company_unit_price = { ...base("company_unit_price"), key: "company_unit_price", label: "회사 자료 · kg당 단가 (제품별·연도별)", status: prows.length ? "확인됨" : "자료 부족", value: W > 0 ? Math.round((A / W) * 100) / 100 : null, unit: "USD/kg (전체)", period: per, as_of: pr.to, source: src + " · 수출실적 시트",
      basis: `금액 합 ÷ 순중량(kg) 합 (두 값이 모두 있는 행만) · ${pr.label}${hsTag} · 순중량 빈칸으로 제외 ${exW}행 · 제품ID 빈칸 행 제외`, note: "회사 자료 · 통계 단가는 실제 판매가가 아님", rows: prows };
    const present = monthly.filter((x) => x.value_usd != null).map((x) => x.value_usd), drops = []; let comparable = 0;
    for (let i = 1; i < monthly.length; i++) { const a = monthly[i - 1].value_usd, b = monthly[i].value_usd; if (a == null || b == null) { monthly[i].mom_pct = null; continue; } comparable++; const mom = a > 0 ? (b / a - 1) * 100 : null; monthly[i].mom_pct = r1(mom); if (mom != null && mom <= -20) drops.push({ month: monthly[i].month, mom_pct: r1(mom), value_usd: b }); }
    if (monthly.length) monthly[0].mom_pct = null;
    const cv = present.length >= 2 && mean(present) > 0 ? (pstdev(present) / mean(present)) * 100 : null;
    out.company_export_volatility = { ...base("company_export_volatility"), key: "company_export_volatility", label: `회사 자료 · ${country} 월별 수출액 변동(보조)`, status: present.length >= 2 ? "확인됨" : "자료 부족", value: r1(cv), unit: "CV %", period: per, as_of: pr.to, source: src + " · 수출실적 시트",
      basis: `자료 있는 달 ${present.length}개의 월별 합계 CV(모표준편차÷평균) · 전월비는 두 달 모두 자료가 있을 때만(${comparable}회) · ${pr.label}${hsTag}`, note: "회사 자료 · 과거 변동이며 미래 손실·수출 실패 확률이 아님", rows: monthly.map((x) => ({ ...x })), drops, drop_count: drops.length, comparable_months: comparable, drop_rate_pct: comparable ? r1((drops.length / comparable) * 100) : null, missing_months: monthly.filter((x) => x.value_usd == null).map((x) => x.month) };
    // ---- 물류 (logistics_agg 로 다시 계산) ----
    const presentM = new Set(rows.map((r) => r.m)), lsrc = src + " · 물류 시트", lsum = (k) => logs.reduce((a, l) => a + (l[k] || 0), 0);
    const bym = {}; logs.forEach((l) => { const g = (bym[l.m] = bym[l.m] || { air: 0, sea: 0, other: 0, total: 0, tr: 0, ot: 0 }); if (l.mode === "항공") g.air += l.n; else if (l.mode === "해상") g.sea += l.n; else g.other += l.n; g.total += l.n; g.tr += l.tr; g.ot += l.ot; });
    const grp = {}, blanks = { "운송수단 빈칸": 0, "도착지코드 빈칸": 0, "선적일 빈칸": 0 };
    logs.forEach((l) => { const k = [l.mode, l.o, l.d].join("|"); grp[k] = grp[k] || { mode: l.mode, origin_code: l.o, destination_code: l.d, shipments: 0 }; grp[k].shipments += l.n; blanks["운송수단 빈칸"] += l.blank_mode; blanks["도착지코드 빈칸"] += l.blank_dest; blanks["선적일 빈칸"] += l.blank_date; });
    const qrows = Object.values(grp).sort((a, b) => b.shipments - a.shipments), qn = lsum("n");
    out.query_conditions = { ...base("query_conditions"), key: "query_conditions", label: "조회 조건(회사 자료)", status: qrows.length ? "확인됨" : "자료 부족", value: qn, unit: "선적 건수", period: per, as_of: pr.to, source: lsrc,
      basis: `유효 수출실적과 실적ID 로 연결된 물류 행을 운송수단·출발지코드·도착지코드별로 센 것 (공항 IATA · 항만 UN/LOCODE) · ${pr.label}${hsTag}`, note: "직항 여부·전체 배송시간·운송 가능 여부를 확정하지 않음", rows: qrows, blanks };
    out.shipments_monthly = { ...base("shipments_monthly"), key: "shipments_monthly", label: "회사 자료 · 월별 선적 건수 (운송수단별)", status: logs.length ? "확인됨" : "자료 부족", value: qn, unit: "건", period: per, as_of: pr.to, source: lsrc,
      basis: `유효 수출실적과 실적ID 로 연결된 물류 행을 거래월·운송수단별로 센 것 · 거래가 없는 달은 자료 없음 · ${pr.label}${hsTag}`, note: "회사 자료",
      rows: months.map((m) => { const g = bym[m]; return presentM.has(m) ? { month: m, air: g ? g.air : 0, sea: g ? g.sea : 0, other: g ? g.other : 0, total: g ? g.total : 0 } : { month: m, air: null, sea: null, other: null, total: null }; }) };
    if (base("delivery_ontime").rows) {
      const TR = lsum("tr"), OT = lsum("ot");
      out.delivery_ontime = { ...base("delivery_ontime"), status: TR ? "확인됨" : "자료 부족", value: TR ? r1((OT / TR) * 100) : null, period: per, as_of: pr.to, tracked: TR, ontime: OT,
        basis: `예정·실제 도착일이 모두 있는 ${TR}건 중 실제도착일 ≤ 예정도착일 ${OT}건 · 날짜 역전 행 제외 · ${pr.label}${hsTag}`,
        rows: months.map((m) => { const g = bym[m], has = presentM.has(m); return { month: m, tracked: has ? (g ? g.tr : 0) : null, ontime: has ? (g ? g.ot : 0) : null, rate_pct: g && g.tr ? r1((g.ot / g.tr) * 100) : null }; }),
        blanks: { "예정도착일 빈칸": lsum("blank_eta"), "실제도착일 빈칸": lsum("blank_ata"), "날짜 역전 오류": lsum("err") } };
      const byMode = {};
      logs.forEach((l) => { const g = (byMode[l.mode] = byMode[l.mode] || { lt: 0, ln: 0, min: null, max: null, pl: 0, pn: 0, fr: 0, fa: 0, fw: 0, nf: 0 }); g.lt += l.lt; g.ln += l.ln; if (l.ltmin != null) g.min = g.min == null ? l.ltmin : Math.min(g.min, l.ltmin); if (l.ltmax != null) g.max = g.max == null ? l.ltmax : Math.max(g.max, l.ltmax); g.pl += l.pl; g.pn += l.pn; g.fr += l.fr; g.fa += l.fa; g.fw += l.fw; g.nf += l.nf; });
      const LT = lsum("lt"), LN = lsum("ln");
      out.lead_time = { ...base("lead_time"), status: LN ? "확인됨" : "자료 부족", value: LN ? r1(LT / LN) : null, period: per, as_of: pr.to,
        rows: ["항공", "해상"].filter((md) => byMode[md] && byMode[md].ln).map((md) => { const g = byMode[md]; return { mode: md, shipments: g.ln, avg_days: r1(g.lt / g.ln), min_days: g.min, max_days: g.max, planned_avg_days: g.pn ? r1(g.pl / g.pn) : null }; }) };
      const FR = lsum("fr"), FA = lsum("fa");
      out.freight_ratio = { ...base("freight_ratio"), status: FA > 0 ? "확인됨" : "자료 부족", value: FA > 0 ? Math.round((FR / FA) * 1e5) / 1e3 : null, period: per, as_of: pr.to,
        basis: `운임이 있는 ${lsum("nf")}건의 운임 합 ÷ 연결된 수출실적 금액 합 × 100 · 운송수단별 kg당 운임은 참고 · ${pr.label}${hsTag}`,
        rows: ["항공", "해상"].filter((md) => byMode[md] && byMode[md].nf).map((md) => { const g = byMode[md]; return { mode: md, shipments: g.nf, freight_usd: Math.round(g.fr * 100) / 100, amount_usd: Math.round(g.fa * 100) / 100, ratio_pct: g.fa ? Math.round((g.fr / g.fa) * 1e5) / 1e3 : null, usd_per_kg: g.fw ? Math.round((g.fr / g.fw) * 100) / 100 : null }; }),
        blanks: { "운임 빈칸": lsum("blank_fr") } };
    }
    const rsb = base("recent_shipments");
    if (rsb.rows) { const rr = rsb.rows.filter((r) => r.ship_date.slice(0, 7) >= pr.from && r.ship_date.slice(0, 7) <= pr.to); out.recent_shipments = { ...rsb, rows: rr, value: rr.length, note: (rsb.note || "") + (filters.hs !== "all" ? " · HS 필터는 최근 기록에 적용하지 않음" : "") }; }
    if (filters.hs !== "all") {
      const ec = base("export_control_candidates");
      if (ec.rows) { const rowsF = ec.rows.filter((r) => { const p = c.products.find((x) => x.id === r.product_id); return p && p.analysis_hs6 === filters.hs; }); out.export_control_candidates = { ...ec, rows: rowsF, value: rowsF.filter((r) => r.status === "확인됨").length, basis: (ec.basis || "") + ` · HS ${hsDot(filters.hs)} 제품만` }; }
      const tr = base("tariff_reference");
      if (tr.rows) { const rowsF = tr.rows.filter((r) => r.hs6 === filters.hs); out.tariff_reference = { ...tr, rows: rowsF, value: rowsF.length ? { [filters.hs]: rowsF[rowsF.length - 1].best_avlbl_pct } : null, status: rowsF.length ? tr.status : "자료 부족" }; }
      const ke = base("korea_exports_to_destination");
      if (ke.rows) {
        const rowsF = ke.rows.filter((r) => r.hs6 === filters.hs);
        if (rowsF.length && rowsF[0].exp_usd != null) { // 관세청 월별 (2026-09-26~): 최근 12개월 합
          const last = rowsF.reduce((a, r) => (r.month > a ? r.month : a), ""), from = ymAdd(last, -11);
          out.korea_exports_to_destination = { ...ke, rows: rowsF, value: rowsF.filter((r) => r.month >= from).reduce((a, r) => a + r.exp_usd, 0), basis: (ke.basis || "") + ` · HS ${hsDot(filters.hs)} 만` };
        } else { const ly = rowsF.length ? rowsF.reduce((a, r) => (r.year_dt_year > a ? r.year_dt_year : a), "") : null; out.korea_exports_to_destination = { ...ke, rows: rowsF, value: rowsF.length ? rowsF.filter((r) => r.year_dt_year === ly).reduce((a, r) => a + r.imports_usd, 0) : null, status: rowsF.length ? ke.status : "자료 부족" }; }
      }
    }
    return out;
  }
  const areaItems = (key) => {
    const b = current && selectedCountry && current.per_country[selectedCountry];
    if (!b) return [];
    const ov = (calc() || {}).items || {};
    return (b[key] || []).map((it) => ov[it.key] || it);
  };
  const itemOf = (key, k) => areaItems(key).find((it) => it.key === k) || null;
  function counts(items) { const c = {}; STATUSES.forEach((s) => (c[s] = 0)); items.forEach((it) => { c[it.status] = (c[it.status] || 0) + 1; }); c.total = items.length; return c; }
  function confirmed() { let n = 0, m = 0; AREAS.forEach((a) => { const c = counts(areaItems(a.key)); n += c["확인됨"]; m += c.total; }); return { n, m }; }
  const factorScore = (key) => { const c = calc(); return c ? c.factors.find((f) => f.key === key) || null : null; };
  const overallNow = () => { const c = calc(); return c ? c.overall : null; };
  function snapshot() { const o = {}, ov = overallNow(); if (ov) o.overall = ov.score; AREAS.forEach((a) => { const f = factorScore(a.key); if (f) o[a.key] = f.score; }); return o; }
  const fscoreState = (f) => (!current ? "empty" : f && f.state === "ok" ? "ok" : "insufficient");
  function deltaHTML(d, col, withParen) {
    if (d == null || !Number.isFinite(d)) return `<span class="jd-delta none">–</span>`;
    const cls = d > 0.05 ? "up" : d < -0.05 ? "down" : "flat", sym = cls === "up" ? "↑" : cls === "down" ? "↓" : "–", txt = cls === "flat" ? "0.0" : (d > 0 ? "+" : "") + d.toFixed(1);
    return `<span class="jd-delta ${cls}"${cls === "up" && col ? ` style="color:${col}"` : ""} aria-label="지난달 대비 ${cls === "up" ? "상승" : cls === "down" ? "하락" : "변화 없음"} ${txt}">${sym} ${txt}</span>${withParen ? ' <span class="jd-paren">(지난달 대비)</span>' : ""}`;
  }
  const valueText = (it) => {
    if (!it) return NA;
    const v = it.value; if (v == null) return NA;
    if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${hsDot(k)} ${fin(x) ? x.toFixed(1) + "%" : NA}`).join(" · ");
    const u = it.unit || "";
    if (/USD\/kg/.test(u)) return num(v, 0) + " USD/kg";
    if (/^USD/.test(u)) return usd(v);
    if (/^KRW\//.test(u)) return num(v, 2) + " " + u;
    if (/10억 달러/.test(u)) return "$" + (+v).toFixed(1) + "B";
    if (/^CV %/.test(u) || /^%|%$/.test(u) || /절대값 평균 %/.test(u)) return (+v).toFixed(u === "%" && it.key === "freight_ratio" ? 2 : 1) + "%";
    if (u === "일") return (+v).toFixed(1) + "일";
    if (typeof v === "number") return num(v, Number.isInteger(v) ? 0 : 2) + (u ? " " + u.split(" ")[0] : "");
    return esc(v);
  };
  const metaText = (it) => [it.period ? `기간 ${esc(it.period)}` : "", it.as_of ? `기준일 ${esc(it.as_of)}` : "", it.source ? `출처 ${esc(shortSrc(it.source))}` : ""].filter(Boolean).join(" · ");

  // ---------------------------------------------------------------- 공통 정보 막대 (회사명·파일명·제품 목록만. 조건 선택은 사이드바 'ANALYSIS · 분석 조건')
  function infobarHTML(v) {
    if (!v) return `<div class="jd-infobar jd-infobar-empty"><span><i class="ph ph-upload-simple"></i>회사 선택 전 · 바탕화면의 기업 파일을 열면 회사·파일·제품이 여기에 표시됩니다.</span><span class="jd-ib-chip">참고 적합도 v1 · 분석 엔진</span></div>`;
    const m = v.meta, q = m.quality || {}, ex = q.rows_excluded_from_totals || 0, ic = q.issue_counts || {}, nIss = (q.issues || []).length;
    const prods = m.products.map((p) => `<span class="jd-ib-prod${p.dim ? " dim" : ""}" title="${esc(p.family || "")}">${esc(p.name)} <em>${esc(p.inputHsk || "미확인")}→${esc(p.hs6 || "미확인")}</em></span>`).join("");
    return `<div class="jd-infobar">
      <span class="jd-ib-company"><i class="ph ph-buildings"></i><b>${esc(m.company)}</b><em>${isEngine() && !isSampleDoc() ? "업로드" : "가상 샘플"}</em></span>
      <span class="jd-ib-file" title="현재 대시보드에 표시 중인 엑셀 파일"><i class="ph ph-microsoft-excel-logo"></i>${esc(m.file)}</span>
      <span class="jd-ib-prods">제품 ${prods}</span>
      <span class="jd-ib-chip">${esc(m.dataClass)}</span>
      ${nIss ? `<button type="button" class="jd-ib-btn" data-jd="quality">결측·오류 ${nIss}곳${ex ? ` · 합계 제외 ${ex}행` : ""}${ic.error ? ` · 오류 ${ic.error}` : ""} (보기)</button>` : ""}
    </div>`;
  }
  // ---------------------------------------------------------------- 사이드바 'ANALYSIS · 분석 조건' (목적국 · HS · 현재 적용 조건)
  // workspace.html 을 고치지 않고 #window-sidebar 의 PREFERENCES 제목 앞에 끼워 넣는다. 조건을 바꾸면 cfg.onFilter → 모든 탭 재렌더.
  // (2026-09-27) 기간 선택은 사이드바에서 뺐다(사용자 요청). 엔진 문서는 엔진 지원 대상국·HS6 전체를 보여 주고, 바꾸면 cfg.onEngineConditions 로 다시 계산한다.
  function sideHTML(v) {
    const opt = (val, t, cur) => `<option value="${esc(val)}"${String(cur) === String(val) ? " selected" : ""}>${esc(t)}</option>`;
    const field = (icon, label, ctl) => `<label class="jd-side-field"><span><i class="ph ph-${icon}"></i>${label}</span>${ctl}</label>`;
    const cap = `<div class="sidebar-caption jd-side-cap">ANALYSIS · 분석 조건</div>`;
    if (!v) return `${cap}<div class="jd-side-body" aria-disabled="true">${field("globe-hemisphere-west", "목적국", `<select disabled aria-label="목적국"><option>—</option></select>`)}${field("barcode", "HS", `<select disabled aria-label="HS 코드"><option>—</option></select>`)}<p class="jd-side-applied muted">회사 파일을 열면 선택할 수 있습니다</p></div>`;
    const m = v.meta;
    if (isEngine()) {
      const c0 = (current.common.countries || [])[0] || {}, iso = c0.iso2 || "", hs6 = String((current.engine && current.engine.hs) || (current.common.analysis_hs6 || [])[0] || "").slice(0, 6);
      const known = ENGINE_COUNTRIES.some(([c]) => c === iso);
      const ctry = `<select data-jd="engine-country" aria-label="목적국 (분석 엔진 지원국)">${known ? "" : opt(iso, c0.name || iso, iso)}${ENGINE_COUNTRIES.map(([c, n]) => opt(c, `${n} (${c})`, iso)).join("")}</select>`;
      const hs = `<select data-jd="engine-hs" aria-label="분석 HS 코드 (분석 엔진 지원 HS6)">${engineHsOptions(hs6)}</select>`;
      return `${cap}<div class="jd-side-body">${field("globe-hemisphere-west", "목적국", ctry)}${field("barcode", "HS", hs)}<p class="jd-side-applied" aria-live="polite"><b>적용</b> ${esc(`${c0.name || iso} · HS ${hsDot(hs6)} · 바꾸면 다시 계산`)}</p></div>`;
    }
    const ctry = `<select data-jd="country" aria-label="목적국 (수출 비중 순)">${m.countries.map((c) => opt(c.name, `${c.name}${fin(c.share) ? ` · ${(c.share * 100).toFixed(1)}%` : ""}`, m.country)).join("")}</select>`;
    const hs = `<select data-jd="hs" aria-label="분석 HS 코드">${opt("all", "전체 HS", m.hs)}${m.hsList.map((h) => opt(h, "HS " + hsDot(h), m.hs)).join("")}</select>`;
    return `${cap}<div class="jd-side-body">${field("globe-hemisphere-west", "목적국", ctry)}${field("barcode", "HS", hs)}<p class="jd-side-applied" aria-live="polite"><b>적용</b> ${esc(`${m.hs === "all" ? "HS 전체" : "HS " + hsDot(m.hs)} · ${m.country}`)}</p></div>`;
  }
  function refreshSidebar() { // 다시 계산이 끝나거나 실패하면 현재 문서 조건으로 되돌려 그린다
    const b = document.querySelector("#window-sidebar .jd-side-analysis");
    if (b) b.dataset.html = "";
    renderSidebar(view());
  }
  function renderSidebar(v) {
    const side = document.getElementById("window-sidebar");
    if (!side) return;
    let box = side.querySelector(".jd-side-analysis");
    if (!box) {
      box = document.createElement("div");
      box.className = "jd-side-analysis";
      const pref = side.querySelector(".sidebar-caption.second");
      side.insertBefore(box, pref || side.querySelector(".sidebar-bottom"));
    }
    const html = sideHTML(v);
    if (box.dataset.html !== html) { box.innerHTML = html; box.dataset.html = html; }
  }
  function issuesHTML(q) {
    const issues = (q && q.issues) || [];
    const tone = { error: "bad", warn: "warn", info: "muted" };
    return table(["구분", "시트 · 엑셀 행", "항목", "건수", "식별자 (앞 6개)", "영향"], issues.map((i) => [`<span class="jd-st jd-st-${tone[i.severity] || "muted"}">${esc(i.kind)}</span>`, esc(i.sheet) + (i.row_numbers?.length ? `<br><small>${i.row_numbers.map(esc).join(", ")}행</small>` : ""), esc(i.field), num(i.count) + "건",
      i.ids && i.ids.length ? i.ids.map(esc).join(", ") + (i.count > i.ids.length ? " …" : "") : NA, esc(i.effect)]), "결측·오류 없음");
  }
  function qualityHTML() {
    if (!current) return "";
    const q = current.common.data_quality || {};
    return `<p class="modal-description">${esc(current.company_name)} · ${esc(current.file_name)} · 전체 ${q.rows_total}행 중 유효 ${q.rows_valid}행 (합계 제외 ${q.rows_excluded_from_totals || 0}행). 빈칸은 0 이나 임의 값으로 채우지 않았고, 아래 항목은 해당 계산에서만 제외했습니다.</p>
      ${issuesHTML(q)}
      <p class="jd-quality-months"><b>빈 달(행이 통째로 없는 달)</b> ${q.missing_months && q.missing_months.length ? q.missing_months.map(esc).join(", ") + " · 0 이 아니라 자료 없음으로 표시" : "없음"}</p>`;
  }

  // ---------------------------------------------------------------- index3 어댑터
  // toIndex3Data(companyJson, {country, hs, period, from, to}) → JH2/index3.html 의 AXPORT_DATA 와 같은 구조
  //   regulation{status, controls[{no,name,source}], measures[{type,origin,status,period}], cslMatches}
  //   market{period, importValue, koreaExport, yoy, koreaShare, monthly[{label,imports,korea}], growth[{label,value}]}
  //   price{unitPrice, tariff, fx, index, fxSeries[{label,value}], references[[이름,값,출처]]}
  //   logistics{period, flightCount, departures, arrivals, vesselCount, monthly[{label,value}], flights[[...]]}
  //   stability{status, cv, dropCount, dropRate, fxVol, monthly[{label,value,change}]}
  // + meta(회사·파일·제품·조건) + overview(점수형 종합) + 영역마다 info{값 이름: {status, source, asOf, note, company}}.
  // company:true 는 공개 통계가 아니라 회사 파일 값(가상)으로 채운 칸이다 → 화면에 '회사 자료' 표시.
  // 화면(종합·상세 5개 탭)은 이 구조만 읽는다. 회사 JSON 구조가 바뀌면 이 어댑터만 고친다. 매핑 표: junhee/docs/dashboard_items.md
  const viewCache = new Map();
  function withState(doc, opts, fn) {
    const save = { current, selectedCountry, filters };
    current = doc;
    selectedCountry = opts.country && doc.per_country[opts.country] ? opts.country : doc.common.main_country;
    filters = { period: opts.period || "all", hs: opts.hs && (doc.common.analysis_hs6 || []).includes(opts.hs) ? opts.hs : "all", from: opts.from || null, to: opts.to || null };
    try { return fn(); } finally { current = save.current; selectedCountry = save.selectedCountry; filters = save.filters; }
  }
  function toIndex3Data(doc, opts = {}) {
    if (!doc || doc.schema !== "handoff-v1") return null;
    const key = JSON.stringify([doc.company_id, opts.country || null, opts.hs || "all", opts.period || "all", opts.from || null, opts.to || null, weights(), isCustom()]);
    if (viewCache.has(key)) return viewCache.get(key);
    const v = withState(doc, opts, buildView);
    if (viewCache.size > 60) viewCache.clear();
    viewCache.set(key, v);
    return v;
  }
  const view = () => (current ? toIndex3Data(current, { country: selectedCountry, ...filters }) : null);
  const ST_OK = "확인됨";
  const pubInfo = (it) => (it ? { status: it.status, source: it.source || null, asOf: it.as_of || null, period: it.period || null, note: it.note || null, basis: it.basis || null, company: false } : { status: "자료 부족", company: false });
  const valOk = (it) => (it && it.status === ST_OK && it.value != null ? it.value : null);
  // 회사 월별 수출액으로 성장률(전년 동기·최근 3개월 전년 동기·3년 CAGR). 비교 구간에 자료 없는 달이 하나라도 있으면 계산하지 않는다(자료 부족).
  function companyGrowth(rows) {
    const m = {}; rows.forEach((r) => (m[r.month] = r.value_usd));
    const last = rows.length ? rows[rows.length - 1].month : null;
    const sum = (end, n) => { let s = 0; for (let i = 0; i < n; i++) { const x = m[ymAdd(end, -i)]; if (x == null) return null; s += x; } return s; };
    const gr = (a, b) => (a != null && b != null && b > 0 ? r1((a / b - 1) * 100) : null);
    if (!last) return { yoy: null, m3: null, cagr: null };
    const a12 = sum(last, 12), b36 = sum(ymAdd(last, -36), 12);
    return { yoy: gr(a12, sum(ymAdd(last, -12), 12)), m3: gr(sum(last, 3), sum(ymAdd(last, -12), 3)), cagr: a12 != null && b36 != null && b36 > 0 ? r1((Math.pow(a12 / b36, 1 / 3) - 1) * 100) : null, last };
  }
  // 종합 카드 한 줄 평가 문장: 점수 등급(매우 좋습니다·양호합니다·보통 수준입니다·다소 미흡합니다·취약합니다) + 회사 값 근거
  function cardLine(f, gate) {
    const i = f.inputs || {};
    if (f.key === "regulation") return gate ? gate.text : "";
    if (f.state !== "ok") return `${FACTOR_KO[f.key]} 평가에 필요한 자료가 부족합니다. ${f.note || ""}`;
    if (current && current.score_source === "engine") return `${FACTOR_KO[f.key]}: ${f.note || ""}`; // (junhee) 엔진 문서: 엔진 항목별 점수 설명 (2026-09-27 배포 QA: 옛 등급 형용사 제거)
    const g = gradeOf(f.score)[1];
    if (f.key === "market") return `시장성이 ${g} 세계 반도체 출하 전년동월비 ${pct(i.wsts_yoy_pct)}, 최근 3개월 수출 ${pct(i.company_growth_3m_pct)}.`;
    if (f.key === "price") return `${i.weighted_tariff_pct === 0 ? "관세 부담이 없어 " : ""}가격 조건이 ${g} 가중 관세 참고율 ${fin(i.weighted_tariff_pct) ? (+i.weighted_tariff_pct).toFixed(2) + "%" : NA}.`;
    if (f.key === "logistics") return `물류 운영이 ${g} 납기 준수율 ${fin(i.ontime_pct) ? (+i.ontime_pct).toFixed(1) + "%" : NA}, 운송비 비중 ${fin(i.freight_ratio_pct) ? (+i.freight_ratio_pct).toFixed(2) + "%" : NA}.`;
    if (f.key === "stability") return `거래 안정성이 ${g} 거래처 집중도 HHI ${fin(i.hhi_customer) ? (+i.hhi_customer).toFixed(2) : NA}, 월별 수출액 변동계수 ${fin(i.cv_pct) ? (+i.cv_pct).toFixed(0) + "%" : NA}.`;
    return f.note || "";
  }
  function buildView() {
    const k = calc(), pr = k.pr, c = current.common, country = selectedCountry, src = current.file_name, w = weights();
    const g = (a, kk) => itemOf(a, kk);
    const co = (it, extra) => ({ ...pubInfo(it), company: true, source: src + (it && it.source && it.source.includes(" · ") ? " · " + it.source.split(" · ").slice(1).join(" · ") : ""), ...(extra || {}) });
    const fac = (kk) => k.factors.find((f) => f.key === kk);
    const meta = { company: current.company_name, companyEn: current.company_name_en || "", file: current.file_name, dataClass: dataClassText(), // (junhee) 엔진 문서는 파일의 자료 구분
      products: c.products.map((p) => ({ name: p.name, family: p.family, inputHsk: p.input_hsk, hs6: p.analysis_hs6, dim: filters.hs !== "all" && p.analysis_hs6 !== filters.hs })),
      country, countries: c.countries.map((x) => ({ name: x.name, share: x.export_share })), hs: filters.hs, hsList: c.analysis_hs6 || [],
      period: { key: filters.period, from: pr.from, to: pr.to, label: pr.label, isDefault: pr.isDefault, asOf: pr.asOf, full: c.period },
      applied: `${pr.label} ${pr.from}~${pr.to} · ${filters.hs === "all" ? "HS 전체" : "HS " + hsDot(filters.hs)} · ${country}`, quality: c.data_quality || {}, currency: c.currency, ruleVer: RULE_VER };
    const ov = k.overall;
    const overview = { status: ov.score != null ? "ok" : "insufficient", score: ov.score, gate: ov.gate, verdict: ov.verdict, grade: ov.score != null ? (isEngine() ? `근거 반영률 ${Math.round((current.engine && current.engine.coverage_pct) || 0)}%` : gradeOf(ov.score)[2]) : null, /* (junhee) 엔진 문서는 엔진 등급과 섞이지 않게 반영률 */ delta: ov.delta, excluded: ov.excluded || [], custom: isCustom(), weights: w, needsReview: !!ov.needs_regulation_review,
      factors: k.factors.map((f) => ({ key: f.key, score: f.score, state: f.state, delta: f.delta, series: f.series, seriesMonths: f.series_months, line: cardLine(f, ov.gate), note: f.note, weight: f.key === "regulation" ? null : w[f.key] })),
      highlight: k.highlights };
    // ---- 규제
    const ec = g("regulation", "export_control_candidates"), ir = g("regulation", "import_regulation_records"), cs = g("regulation", "csl_search"), fr0 = fac("regulation");
    const searched = (it) => it && (it.status === ST_OK || it.status === "검색 결과 없음");
    const controls = (ec && ec.rows ? ec.rows : []).filter((r) => r.status === ST_OK && (r.control_numbers || []).length).map((r) => ({
      no: r.control_numbers.slice(0, 3).join(", ") + (r.control_numbers.length > 3 ? ` 외 ${r.control_numbers.length - 3}개` : ""), all: r.control_numbers,
      name: `${r.hsk_name || "품목명 없음"} · ${r.product} (HSK ${r.input_hsk})`, source: ec.source, product: r.product }));
    const measures = (ir && ir.rows ? ir.rows : []).map((r) => { const s = String(r.type_and_status || ""), mm = s.match(/^(.*?)\s*\(([^)]*)\)\s*$/); return { type: mm ? mm[1] : s || r.item || NA, origin: r.target_origin || NA, status: mm ? mm[2] : "원문 확인", period: r.period_raw || NA, item: r.item }; });
    const regulation = { status: !ec ? "자료 부족" : "규제 관문 " + ov.gate.label, gate: ov.gate,
      controls, controlCount: searched(ec) ? controls.length : null, controlNumbers: [...new Set(controls.flatMap((x) => x.all))].length,
      measures, measureCount: searched(ir) ? ir.value : null, cslMatches: searched(cs) ? cs.value : null, cslChecked: cs && cs.rows ? cs.rows.length : 0,
      info: { controls: pubInfo(ec), measures: pubInfo(ir), cslMatches: pubInfo(cs) } };
    // ---- 공개 통계(API) 행을 HS 필터로 다시 합치는 도우미 (행에 hs6 가 있음). 빈 달은 0 으로 채우지 않는다.
    const hsOk = (h) => filters.hs === "all" || !h || h === filters.hs;
    const sumBy = (rows, field) => { const o = {}; (rows || []).forEach((r) => { if (!hsOk(r.hs6) || r[field] == null) return; o[r.month] = (o[r.month] || 0) + r[field]; }); return o; };
    const winSum = (s, end, n) => { let tot = 0; for (let i = 0; i < n; i++) { const x = s[ymAdd(end, -i)]; if (x == null) return null; tot += x; } return tot; };
    const latestFull = (s, fn) => { for (const e of Object.keys(s).sort().reverse()) { const x = fn(e); if (x != null) return [e, x]; } return [null, null]; };
    const growthOf = (s) => ({
      yoy: latestFull(s, (e) => { const a = winSum(s, e, 12), b = winSum(s, ymAdd(e, -12), 12); return a != null && b ? (a / b - 1) * 100 : null; }),
      m3: latestFull(s, (e) => { const a = winSum(s, e, 3), b = winSum(s, ymAdd(e, -12), 3); return a != null && b ? (a / b - 1) * 100 : null; }),
      cagr: latestFull(s, (e) => { const a = winSum(s, e, 12), b = winSum(s, ymAdd(e, -36), 12); return a != null && b ? (Math.pow(a / b, 1 / 3) - 1) * 100 : null; }) });
    // ---- 시장성: 목적국 수입(Comtrade) · 한국의 해당국 수출(관세청) · 회사 수출(회사 자료)은 서로 다른 계열
    const di = g("market", "destination_imports"), ke = g("market", "korea_exports_to_destination"), ks = g("market", "korea_share"), ce = g("market", "company_exports");
    const gy = g("market", "growth_yoy"), g3i = g("market", "growth_3m_yoy"), gci = g("market", "cagr_3y");
    const cRows = ce && ce.status === ST_OK ? ce.rows || [] : [], gr = companyGrowth(cRows);
    const diOk = di && di.status === ST_OK, diMonthly = diOk && di.granularity === "monthly";
    const wS = diMonthly ? sumBy(di.rows, "world_usd") : {}, kS = diMonthly ? sumBy(di.rows, "korea_usd") : {}, keS = ke && ke.status === ST_OK ? sumBy(ke.rows, "exp_usd") : {};
    let importValue = valOk(di), koreaShare = valOk(ks), koreaExport = valOk(ke);
    let pubG = { yoy: valOk(gy), m3: valOk(g3i), cagr: valOk(gci) };
    if (filters.hs !== "all") {
      if (diMonthly) { const end = di.as_of, a = winSum(wS, end, 12), b = winSum(kS, end, 12); importValue = a; koreaShare = a && b != null ? r1((b / a) * 100) : null; const gg = growthOf(wS); pubG = { yoy: r1(gg.yoy[1]), m3: r1(gg.m3[1]), cagr: pubG.cagr != null && gci && /연간/.test(gci.period || "") ? pubG.cagr : r1(gg.cagr[1]) }; }
      else if (diOk) { const y = di.as_of, rs = (di.rows || []).filter((r) => r.year === y && hsOk(r.hs6)); importValue = rs.reduce((x, r) => x + (r.world_usd || 0), 0) || null; const kk = rs.reduce((x, r) => x + (r.korea_usd || 0), 0); koreaShare = importValue ? r1((kk / importValue) * 100) : null; }
      if (Object.keys(keS).length) koreaExport = winSum(keS, ke.as_of, 12);
    }
    const pubGrowthAny = [pubG.yoy, pubG.m3, pubG.cagr].some((x) => x != null);
    const gSrc = pubGrowthAny ? pubG : { yoy: gr.yoy, m3: gr.m3, cagr: gr.cagr };
    const gInfoCo = (vv, note) => (vv == null ? { status: "자료 부족", company: true, source: src, note } : { status: ST_OK, company: true, source: src + " · 수출실적 시트", asOf: gr.last || null });
    const lastM = [...Object.keys(wS), ...Object.keys(keS)].sort().pop() || pr.to;
    const trendMonths = ymRange(ymAdd(lastM, -23), lastM);
    const cMap = Object.fromEntries(cRows.map((r) => [r.month, r.value_usd]));
    const market = { period: diOk ? `${di.period || ""}${ke && ke.as_of ? ` · 한국 수출 ~${ke.as_of}` : ""}` : `${pr.from}~${pr.to}`, importValue, koreaExport, yoy: gSrc.yoy, koreaShare,
      monthly: trendMonths.map((m) => ({ label: ymShort(m), month: m, imports: m in wS ? wS[m] : null, korea: m in keS ? keS[m] : null, company: m in cMap ? cMap[m] : null })),
      hasCompanyInTrend: trendMonths.some((m) => cMap[m] != null),
      growth: [{ label: "전년 동기", value: gSrc.yoy }, { label: "최근 3개월", value: gSrc.m3 }, { label: "3년 CAGR", value: gSrc.cagr }],
      growthCompany: !pubGrowthAny,
      info: { importValue: pubInfo(di), koreaExport: pubInfo(ke), koreaShare: pubInfo(ks),
        yoy: pubGrowthAny ? { ...pubInfo(gy), status: gSrc.yoy == null ? "자료 부족" : ST_OK } : gInfoCo(gr.yoy, "목적국 성장률 자료 부족 → 회사 월별 수출액으로 대체 (비교할 24개월 필요)"),
        imports: { ...pubInfo(di), status: Object.keys(wS).length ? ST_OK : diOk ? "자료 부족" : pubInfo(di).status, note: diOk && !diMonthly ? "월별 자료 없음 (연간만 제공)" : di && di.note },
        korea: pubInfo(ke), company: co(ce),
        growth: pubGrowthAny ? [pubInfo(gy), pubInfo(g3i), pubInfo(gci)] : [gInfoCo(gr.yoy, "24개월 자료 필요"), gInfoCo(gr.m3, "전년 같은 3개월 필요"), gInfoCo(gr.cagr, "48개월 필요")] } };
    // ---- 가격: 통계 단가(관세청 한국→목적국) · 기준 대비(Comtrade 같은 출처) · 관세 · 환율 · 물가지수 · 운송비
    const t = g("price", "tariff_reference"), fx = g("price", "fx_reference"), pi = g("price", "price_index"), up = g("price", "company_unit_price"), frt = g("price", "freight_reference"), fp = fac("price");
    const tu = g("price", "trade_unit_price"), bu = g("price", "baseline_unit_price");
    let tariff = fp && fp.state === "ok" && fin(fp.inputs.weighted_tariff_pct) ? fp.inputs.weighted_tariff_pct : null;
    if (tariff == null && t && t.status === ST_OK && t.value && typeof t.value === "object") { const vs = Object.values(t.value).filter(fin); if (vs.length && vs.every((x) => x === vs[0])) tariff = vs[0]; }
    const fxNoCur = fx && fx.status !== ST_OK && /통화/.test(fx.note || "");
    const fxInfo = fxNoCur ? { status: "자료 부족", note: "결제통화 미기재", source: src + " · 기업정보 시트 '금액 통화' 빈칸", company: true } : pubInfo(fx);
    let unitPrice = valOk(tu), unitPub = unitPrice != null;
    if (unitPub && filters.hs !== "all") { const u = sumBy(tu.rows, "exp_usd"), kgS = sumBy(tu.rows, "exp_kg"), end = tu.as_of, a = winSum(u, end, 12), b = winSum(kgS, end, 12); unitPrice = a != null && b ? Math.round((a / b) * 100) / 100 : null; }
    if (unitPrice == null) { unitPrice = valOk(up); unitPub = false; }
    const refs = [];
    if (t && t.rows && t.rows.length) { const latest = {}; t.rows.forEach((r) => (latest[r.hs6] = r)); Object.values(latest).filter((r) => hsOk(r.hs6)).forEach((r) => refs.push({ name: `관세 참고치 · HS ${hsDot(r.hs6)}`, value: fin(r.best_avlbl_pct) ? r.best_avlbl_pct.toFixed(1) + "%" : NA, source: `WTO HS6 참고율 · 조치일 ${r.year_dt}`, status: ST_OK })); }
    else refs.push({ name: "관세 참고치", value: "자료 부족", source: (t && t.note) || "WTO 관세조치 파일 없음", status: "자료 부족" });
    if (bu) refs.push(bu.status === ST_OK ? { name: "기준 대비 단가", value: `${num(bu.value, 1)} (한국 전체 = 100)`, source: `${String(bu.source || "").split(" · ")[0]} · ${bu.period || ""}`, status: ST_OK } : { name: "기준 대비 단가", value: "자료 부족", source: bu.note || "", status: "자료 부족" });
    refs.push(up && up.status === ST_OK ? { name: "단가 기준 (회사)", value: num(up.value, 0) + " USD/kg", source: "금액 ÷ 중량 · 회사 수출실적 시트", status: ST_OK, company: true } : { name: "단가 기준 (회사)", value: "자료 부족", source: "금액·중량이 함께 있는 행 없음", status: "자료 부족", company: true });
    refs.push(pi && pi.status === ST_OK ? { name: "산업 가격지수", value: `${num(pi.value, 1)} (전월비 ${pct(pi.mom_pct)})`, source: `한국은행 실제 분류 · ${(pi.label || "").replace("수출입물가지수 · ", "")}`, status: ST_OK } : { name: "산업 가격지수", value: pi ? pi.status : "자료 부족", source: "한국은행 수출입물가지수", status: pi ? pi.status : "자료 부족" });
    const frRows = frt && frt.rows ? frt.rows : [];
    if (frRows.length) frRows.forEach((r) => refs.push({ name: `운송비 · ${r.mode} ${r.route}`, value: `${num(r.value)} ${r.unit}`, source: `관세청 ${r.month} · 전월비 ${pct(r.mom_pct)}${r.mode === "항공수입" ? " · 항공수출 견적 아님" : ""}`, status: ST_OK }));
    else refs.push({ name: "운송비", value: "자료 부족", source: (frt && frt.note) || "수록 항로 확인 필요", status: "자료 부족" });
    const price = { unitPrice, unitPub, tariff, fx: fxNoCur ? null : valOk(fx), fxUnit: fx && fx.unit, fxAsOf: fx && fx.as_of, index: valOk(pi),
      fxSeries: fx && fx.status === ST_OK ? (fx.rows || []).map((r) => ({ label: ymShort(r.month), month: r.month, value: r.value })) : [],
      references: refs.map((r) => [r.name, r.value, r.source]), refMeta: refs,
      info: { unitPrice: unitPub ? pubInfo(tu) : co(up), tariff: { ...pubInfo(t), status: tariff == null ? "자료 부족" : ST_OK }, fx: fxInfo, index: pubInfo(pi), fxSeries: fxInfo } };
    // ---- 물류: 인천공항 화물편 주간 일정 · 국가별 월간 화물기 운항 · 해수부 선박 입출항 (공항·항만·국가 기준)
    const cf = g("logistics", "cargo_flights"), fc = g("logistics", "flight_counts"), vr = g("logistics", "vessel_records"), q = g("logistics", "query_conditions");
    const cfOk = cf && cf.status === ST_OK, fcOk = fc && fc.status === ST_OK;
    const logistics = { period: cfOk ? cf.period : `${pr.from}~${pr.to}`, flightCount: valOk(cf), departures: cfOk ? cf.departures : null, arrivals: cfOk ? cf.arrivals : null, vesselCount: valOk(vr),
      monthly: (fcOk ? fc.rows || [] : []).map((r) => ({ label: ymShort(r.month), month: r.month, value: r.total, dep: r.dep, arr: r.arr })),
      flights: (cfOk ? cf.rows || [] : []).map((r) => [`${r.airline || ""} ${r.flight || ""}`.trim(), `${r.direction === "출발" ? "→" : "←"} ${r.airport || ""} (${r.airport_code || ""})`, r.scheduled ? `${r.scheduled.slice(4, 6)}-${r.scheduled.slice(6, 8)} ${r.scheduled.slice(8, 10)}:${r.scheduled.slice(10, 12)}` : NA, r.status || "예정"]),
      vessels: (vr && vr.rows) || [], queries: (q && q.rows ? q.rows : []).map((r) => ({ mode: r.mode, origin: r.origin_code, dest: r.destination_code, count: r.shipments })),
      info: { flightCount: pubInfo(cf), departures: pubInfo(cf), arrivals: pubInfo(cf), vesselCount: pubInfo(vr), monthly: pubInfo(fc), flights: pubInfo(cf), queries: co(q) } };
    // ---- 안정성: 목적국 월별 수입(Comtrade)으로 CV·급감 · 없으면 회사 월별 수출액으로 대체(회사 자료)
    const vo = g("stability", "company_export_volatility"), fv = g("stability", "fx_volatility"), dm = g("stability", "destination_monthly_imports"), vok = vo && vo.status === ST_OK;
    const dmOk = dm && dm.status === ST_OK && Object.keys(wS).length >= 6;
    let stability;
    if (dmOk) {
      const last = Object.keys(wS).sort().pop(), first = Object.keys(wS).sort()[0], span = ymRange(ymAdd(last, -23), last).filter((m) => m >= first);
      const mrows = []; let prev = null, comparable = 0; const drops = [];
      span.forEach((m) => { const v = m in wS ? wS[m] : null; let ch = null; if (v != null && prev != null && prev > 0) { comparable++; ch = r1((v / prev - 1) * 100); if (ch <= -20) drops.push({ label: m, change: ch, value: v }); } mrows.push({ label: ymShort(m), month: m, value: v, change: ch }); prev = v; });
      const present = mrows.map((x) => x.value).filter((x) => x != null), cv = present.length >= 6 ? r1((pstdev(present) / mean(present)) * 100) : null;
      const inf = { ...pubInfo(dm), company: false };
      stability = { status: "목적국 수입통계 계산값", pub: true, cv, dropCount: drops.length, dropRate: comparable ? r1((drops.length / comparable) * 100) : null, comparable,
        fxVol: valOk(fv), fxGrade: fv && fv.grade, monthly: mrows, drops, missing: mrows.filter((x) => x.value == null).map((x) => x.month),
        info: { cv: inf, dropCount: inf, dropRate: inf, fxVol: pubInfo(fv), monthly: inf, destination: pubInfo(dm) } };
    } else {
      stability = { status: vok ? "회사 자료 계산값" : "자료 부족", pub: false, cv: vok ? vo.value : null, dropCount: vok ? vo.drop_count : null, dropRate: vok ? vo.drop_rate_pct : null, comparable: vok ? vo.comparable_months : null,
        fxVol: valOk(fv), fxGrade: fv && fv.grade, monthly: (vo && vo.rows ? vo.rows : []).map((r) => ({ label: ymShort(r.month), month: r.month, value: r.value_usd, change: r.mom_pct })),
        drops: (vo && vo.drops ? vo.drops : []).map((d) => ({ label: d.month, change: d.mom_pct, value: d.value_usd })), missing: (vo && vo.missing_months) || [],
        pubNote: dm ? dm.note : null,
        info: { cv: co(vo), dropCount: co(vo), dropRate: co(vo), fxVol: pubInfo(fv), monthly: co(vo), destination: pubInfo(dm) } };
    }
    return { meta, overview, regulation, market, price, logistics, stability };
  }

  // ---------------------------------------------------------------- 종합 탭 (index3 tabView-all: 왼쪽 도넛 패널 + 오른쪽 5개 요인 카드. 점수형)
  const CARD = {
    regulation: { eb: "#f43f5e", tile: "#f43f5e", ink: "#e11d48", dots: "#fda4af", line: "#ffe4e6cc" },
    market: { eb: "#a855f7", tile: "#9333ea", ink: "#9333ea", dots: "#d8b4fe", line: "#f3e8ffcc" },
    price: { eb: "#0ea5e9", tile: "#0284c7", ink: "#0284c7", dots: "#7dd3fc", line: "#e0f2fecc" },
    logistics: { eb: "#f59e0b", tile: "#f59e0b", ink: "#d97706", dots: "#fcd34d", line: "#fef3c7cc" },
    stability: { eb: "#059669", tile: "#059669", ink: "#059669", dots: "#6ee7b7", line: "#d1fae5cc" },
  };
  // index3 스파크라인: 굵은 꺾은선 + 끝 점 + 꼬리 (viewBox 80×32, 안정성은 140×32)
  function sparkSVG(key, series) {
    const wide = key === "stability", W = wide ? 140 : 80, x0 = wide ? 16 : 14, x1 = wide ? 118 : 68, tail = wide ? 132 : 76, col = color(key);
    const vals = (series || []).map((x) => (fin(x) ? +x : null)), nums = vals.filter((x) => x != null);
    if (nums.length < 2) return `<svg class="jd-spark-svg${wide ? " wide" : ""}" viewBox="0 0 ${W} 32" aria-hidden="true"></svg>`;
    const lo = Math.min(...nums), hi = Math.max(...nums), span = hi - lo || 1, n = vals.length;
    const pts = vals.map((x, i) => (x == null ? null : [x0 + ((x1 - x0) * i) / (n - 1), 24 - ((x - lo) / span) * 15])).filter(Boolean);
    const last = pts[pts.length - 1], all = [...pts, [tail, last[1]]].map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
    return `<svg class="jd-spark-svg${wide ? " wide" : ""}" viewBox="0 0 ${W} 32" role="img" aria-label="최근 6개월 점수 추세: ${vals.map((x) => (x == null ? "없음" : x.toFixed(1))).join(", ")}"><polyline class="jd-spark-poly" stroke="${col}" points="${all}"/><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="${wide ? 2.8 : 2.6}" fill="${col}"/></svg>`;
  }
  function overallPanel(v) {
    const o = v ? v.overview : null, score = o && o.status === "ok" ? o.score : null, state = !v ? "empty" : score != null ? "ok" : "insufficient";
    let chipTop = `<span class="jd-chip muted">업로드 전</span>`;
    if (o && score != null) { const d = o.delta, cls = d == null ? "muted" : d > 0.05 ? "up" : d < -0.05 ? "down" : "flat"; chipTop = `<span class="jd-chip ${cls}"><i class="ph ph-trend-${cls === "down" ? "down" : "up"}"></i>전월 대비 ${d == null ? "–" : (d > 0 ? "+" : "") + d.toFixed(1) + "점"}</span>`; }
    else if (o) chipTop = `<span class="jd-chip muted">종합 자료 부족</span>`;
    const rows = AREAS.map((a) => {
      const f = o ? o.factors.find((x) => x.key === a.key) : null;
      let sc = `<span class="jd-fscore empty">—<small> / 100</small></span>`, dl = `<span class="jd-delta none"></span>`;
      if (f && f.state === "ok") { sc = `<span class="jd-fscore"><span class="jd-num" data-key="${a.key}" data-to="${f.score}" data-decimals="0">${(+f.score).toFixed(0)}</span><small> / 100</small></span>`; dl = deltaHTML(f.delta, null, false); }
      else if (f) sc = `<span class="jd-fscore insufficient" title="${esc(f.note || "")}">자료 부족</span>`;
      return `<li><span class="jd-dot" style="background:${PALETTE2[a.key]}"></span><span class="jd-fname" title="${a.key === "regulation" ? "관문 · 종합 점수 제외" : ((!current || isEngine()) && !(o && o.custom) ? `엔진 배점 ${engineWeights()[a.key]}/80` : `비중 ${o ? o.weights[a.key] : DEFAULT_WEIGHTS[a.key]}%`)}">${a.ko2}</span>${sc}${dl}</li>`;
    }).join("");
    const point = o ? esc(o.highlight || "") : "바탕화면의 기업 파일을 열면 회사 값으로 핵심 포인트를 만듭니다.";
    const off = score == null ? 465 : 465 - (465 * Math.max(0, Math.min(100, score))) / 100;
    return `<section class="jd-panel jd-overall" data-state="${state}" aria-label="종합 수출적합도">
      <div><div class="jd-overall-head"><div><small class="jd-eyebrow">Overall Export Suitability</small><h3>종합 수출적합도</h3></div>${chipTop}</div>
      <p class="jd-sub">시장성·가격·물류·안정성 4개 영역의 참고 적합도입니다. 규제는 별도 관문이며 수출 성공확률이 아닙니다.</p>
      <div class="jd-gauge-wrap"><div class="jd-gauge" role="img" aria-label="종합 점수 ${score == null ? "없음" : (+score).toFixed(1) + " / 100"}">
        <svg viewBox="0 0 180 180" aria-hidden="true"><defs><linearGradient id="jd-gauge-grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#2563EB"/><stop offset="60%" stop-color="#38BDF8"/><stop offset="100%" stop-color="#6366F1"/></linearGradient></defs>
        <circle cx="90" cy="90" r="74" stroke="#EEF2F6" stroke-width="16" fill="none"/><circle class="jd-gauge-ring" cx="90" cy="90" r="74" stroke="url(#jd-gauge-grad)" stroke-width="16" data-offset="${off}" style="stroke-dashoffset:${reduced() ? off : 465}"/></svg>
        <div class="jd-gauge-center"><strong class="jd-num" data-key="overall" data-to="${score == null ? "" : score}" data-decimals="1">${score == null ? NA : (+score).toFixed(1)}</strong><span>/ 100</span></div></div></div></div>
      ${o && o.verdict ? `<div class="jd-verdict jd-verdict-${o.verdict.tone}" title="${esc(o.gate.text)}"><span>${isEngine() ? "참고 등급" : "종합 판정"}</span><b>${esc(o.verdict.label)}</b>${o.grade ? `<em>${esc(o.grade)}</em>` : ""}</div>` : ""}
      <div class="jd-factors"><div class="jd-factors-title">요인별 점수</div><ul>${rows}</ul></div>
      <div class="jd-point"><div class="jd-point-head"><span><i class="ph ph-compass"></i>핵심 포인트</span><button type="button" class="jd-link" data-open-tab="market">상세 리포트 보기 →</button></div><p>${point}</p></div>
    </section>`;
  }
  // (junhee) 2026-09-28 카드 한 줄 요약(큰 점수 아래). 예전 카드 아래 줄(엔진 설명 전체)을 짧게 줄인 것.
  // 4개 언어 문장을 data-l-* 로 함께 두고 언어가 바뀌면 통째로 바꾼다(낱말 번역으로 섞이지 않게 data-no-translate).
  const SUM_LANGS = ["ko", "en", "zh", "ja"];
  const sumTx = (s, l) => (l === "ko" || !window.JunheeReportI18n ? s : JunheeReportI18n.tx(String(s), l));
  const GATE_L = { "검토 필요": ["Review required", "需要审查", "要確認"], "보류": ["On hold", "暂缓", "保留"] };
  function cardSummary(a, f, o, state) {
    const per = {};
    if (state === "empty") return "";
    if (a.key === "regulation" && isEngine()) {
      const ec = itemOf("regulation", "export_control_candidates"), im = itemOf("regulation", "import_regulation_records"), cs = itemOf("regulation", "csl_search");
      const codes = ec && String(ec.unit || "").match(/통제번호 (\d+)개/), g = (o && o.gate && o.gate.label) || "검토 필요";
      const okv = (it) => it && it.status === "확인됨" && it.value != null;
      SUM_LANGS.forEach((l, ix) => {
        const gl = ix ? (GATE_L[g] || [g, g, g])[ix - 1] : g;
        const p1 = okv(ec) ? [`HSK 후보 ${ec.value}개${codes ? `(통제번호 ${codes[1]})` : ""}`, `${ec.value} HSK candidates${codes ? ` (${codes[1]} control nos.)` : ""}`, `HSK候选 ${ec.value}个${codes ? `（管制编号 ${codes[1]}）` : ""}`, `HSK候補 ${ec.value}件${codes ? `（統制番号 ${codes[1]}）` : ""}`][ix] : ["HSK 후보 미확인", "HSK candidates unconfirmed", "HSK候选未确认", "HSK候補 未確認"][ix];
        const p2 = okv(im) ? [`수입규제 ${im.value}건`, `import restrictions ${im.value}`, `进口限制 ${im.value}件`, `輸入規制 ${im.value}件`][ix] : ["수입규제 미확인", "import restrictions unconfirmed", "进口限制未确认", "輸入規制 未確認"][ix];
        const p3 = okv(cs) ? [`거래처 일치 ${cs.value}건`, `party matches ${cs.value}`, `交易方匹配 ${cs.value}件`, `取引先一致 ${cs.value}件`][ix] : ["거래처 미확인", "parties unconfirmed", "交易方未确认", "取引先 未確認"][ix];
        per[l] = [gl, p1, p2, p3].join(" · ");
      });
    } else if (state === "ok" && isEngine()) {
      const d = engD(a.key), comps = (d.components || []).filter((c) => fin(c.score));
      if (!comps.length) return "";
      const best = comps.reduce((x, y) => (y.score > x.score ? y : x)), worst = comps.reduce((x, y) => (y.score < x.score ? y : x));
      const mark = (c, ix) => (c.status === "ASSUMED" ? ["(기준)", " (policy)", "（基准）", "（基準）"][ix] : "");
      SUM_LANGS.forEach((l, ix) => {
        const cov = [`근거 ${num(d.coverage_pct, 0)}%`, `Evidence ${num(d.coverage_pct, 0)}%`, `依据 ${num(d.coverage_pct, 0)}%`, `根拠 ${num(d.coverage_pct, 0)}%`][ix];
        const one = (c) => `${sumTx(c.label, l)} ${num(c.score, 0)}${mark(c, ix)}`;
        per[l] = best === worst || comps.length < 2 ? `${cov} · ${one(best)}`
          : `${cov} · ${["강점", "Strength", "强项", "強み"][ix]} ${one(best)} · ${["보완", "Improve", "待补", "補完"][ix]} ${one(worst)}`;
      });
    } else if (state === "ok" && f && f.line) {
      SUM_LANGS.forEach((l) => (per[l] = f.line)); // 엔진 문서가 아니면(예전 샘플) 기존 설명 문장
    } else return "";
    const lang = (window.AXPI18n && AXPI18n.language) || "ko", text = per[lang] || per.ko;
    return `<div class="jd-card-sum" data-no-translate title="${esc(text)}"${SUM_LANGS.map((l) => ` data-l-${l}="${esc(per[l] || per.ko)}"`).join("")}>${esc(text)}</div>`;
  }
  window.addEventListener("axp:language-changed", (e) => {
    const l = (e.detail && e.detail.language) || (window.AXPI18n && AXPI18n.language) || "ko";
    document.querySelectorAll(".jd-card-sum").forEach((el) => { const t = el.getAttribute("data-l-" + l) || el.getAttribute("data-l-ko") || ""; el.textContent = t; el.title = t; });
  });
  function cardHTML(a, v) {
    const o = v ? v.overview : null, f = o ? o.factors.find((x) => x.key === a.key) : null, K = CARD[a.key];
    const state = !v ? "empty" : f && f.state === "ok" ? "ok" : "insufficient";
    let main;
    const sum = cardSummary(a, f, o, state); // (junhee) 2026-09-28 한 줄 요약: 점수·그래프 줄 바로 아래 카드 전체 폭(전월 대비 값이 없으면 '–' 줄 대신)
    if (state === "ok") main = `<div><div class="jd-score"><strong class="jd-num" data-key="${a.key}" data-to="${f.score}" data-decimals="0">${(+f.score).toFixed(0)}</strong><small>/ 100</small></div>${f.delta == null && sum ? "" : `<div class="jd-delta-line">${deltaHTML(f.delta, K.ink, true)}</div>`}</div>${sparkSVG(a.key, f.series)}`;
    else if (state === "insufficient") main = `<div><div class="jd-score insufficient">자료 부족</div><div class="jd-need">필요 자료: ${esc(isEngine() ? ENGINE_NEEDED[a.key] : NEEDED[a.key])}</div>${sum}</div>`;
    else main = `<div><div class="jd-score empty"><strong>—</strong><small>/ 100</small></div></div>`;
    const note = f ? esc(f.line) : a.empty;
    return `<article class="jd-card jd-card-${a.key}" style="--c:${K.tile};--c2:${K.eb};--ink:${K.ink};--dots:${K.dots};--line:${K.line};--bg:${a.bg}" data-state="${state}">
      <div><div class="jd-card-head"><span class="jd-tile"><i class="ph ph-${a.icon}"></i></span><div><small>${a.en}</small><h4>${a.ko2}</h4></div><i class="ph ph-dots-three jd-card-dots" aria-hidden="true"></i></div>
      <div class="jd-card-main">${main}</div>${state === "ok" ? sum : ""}</div>
      <div class="jd-card-foot">${state === "empty" ? `<span class="jd-note" title="${note}">${note}</span>` : ""}<button type="button" class="jd-more" data-open-tab="${a.key}">더보기 →</button></div>
    </article>`;
  }
  function panelHTML() {
    const v = view();
    const err = indexError ? `<span class="jd-error">등록 샘플 목록을 불러오지 못했습니다 (${esc(indexError.message || indexError)})</span>` : "";
    let meta = v ? `${esc(v.meta.file)} · 생성 ${esc(String(current.generated_at || "").slice(0, 10))}` : "바탕화면의 가상 샘플 파일이나 업로드한 기업 파일을 열면 분석 결과가 표시됩니다.";
    if (v) { const o = v.overview, w = o.weights; meta = `${o.custom ? `사용자 가중치(시장성 ${w.market}·가격 ${w.price}·물류 ${w.logistics}·안정성 ${w.stability}) · 화면 참고점수 재계산(엔진 등급 아님)` : (isEngine() ? `엔진 배점 시장성 ${engineWeights().market}·가격 ${engineWeights().price}·물류 ${engineWeights().logistics}·안정성 ${engineWeights().stability} (근거 없는 항목은 정책 기준 50점)` : "기본 가중치 35·30·20·15")}${o.excluded.length ? ` · 자료 부족 ${isEngine() && !o.custom ? "(근거 반영률 0%)" : "제외"}: ${o.excluded.map((kk) => FACTOR_KO[kk]).join("·")}${isEngine() && !o.custom ? "" : " (재정규화)"}` : ""} · ${meta}`; }
    return `${infobarHTML(v)}<div class="jd-layout">${overallPanel(v)}<div class="jd-cards">${AREAS.map((a) => cardHTML(a, v)).join("")}</div></div><div class="jd-foot"><span><i class="ph ph-info"></i>${!current || isEngine() ? "판단 기준 참고 적합도 v1(분석 엔진) · 규제는 별도 관문 · 등급: 근거 배점 40 미만 판단 근거 부족 · 70 이상 조건부 검토 유망 · 50 이상 조건부 검토 · 50 미만 준비 보완 필요 · 수출 성공확률 아님" + (v && v.overview.custom ? " · 사용자 가중치 참고점수에는 이 등급 기준을 적용하지 않음" : "") : `평가 기준 ${RULE_VER} · 규제는 관문 판정(종합 점수와 별도) · 판정 구간: 80 이상 수출 적합 · 65 이상 수출 가능 · 50 이상 보완 후 추진 · 50 미만 재검토`}</span><span>${err || meta}</span></div>`;
  }
  // ---------------------------------------------------------------- 상세 탭 5개 (index3 VIEW 2~6 그대로: 헤더+상태 박스 / KPI 4칸 / 3:2 패널)
  // 제목·영문 소제목·KPI 칸 이름·표 머리글·안내 문구는 index3 원문. 값은 어댑터(toIndex3Data) 구조에서만 읽는다.
  const ameta = (key) => AREAS.find((a) => a.key === key);
  const I3 = {
    regulation: { kicker: "REGULATION GATE", title: "규제 기록 및 수출통제 후보", sub: "발견된 후보·기록을 보여주며, 기록 부재를 ‘규제 없음’으로 판정하지 않습니다.", box: "DATA STATUS" },
    market: { kicker: "MARKET DYNAMICS", title: "수입시장 규모 및 성장성", sub: "목적국 수입·한국 수출·반도체 업황을 서로 다른 지표로 구분합니다.", box: "DATA PERIOD" },
    price: { kicker: "PRICE & TARIFF", title: "통계상 단가·관세 참고치·환율", sub: "통계 단가는 실제 판매가가 아니며, 관세는 참고치로 표시합니다.", box: "REFERENCE" },
    logistics: { kicker: "LOGISTICS & FREIGHT", title: "화물 항공편 및 선박 입출항 기록", sub: "공항·항만·국가 기준의 운항 기록을 보여주며 배송시간을 추정하지 않습니다.", box: "QUERY PERIOD" },
    stability: { kicker: "RISK & STABILITY", title: "수입금액 변동성과 급감 이력", sub: "과거 월별 변동을 보여주는 지표이며 미래 손실·수출 실패 확률을 의미하지 않습니다.", box: "CALCULATION" },
  };
  function detailMeta(key) { const a = I3[key]; return a ? { kicker: a.kicker, title: a.title, sub: a.sub } : null; }
  // 상태 글자: 확인됨이 아니면 값 대신 상태를 쓴다 (index3 setText: null → '자료 부족'). '회사 자료' 표시는 칸 이름 옆 작은 꼬리표.
  const tagCo = `<em class="jd-tag-co" title="공개 통계가 아니라 회사 파일(가상) 값">회사 자료</em>`;
  const stText = (inf) => (inf && inf.status && inf.status !== ST_OK ? inf.status : "자료 부족");
  function kpi3(label, value, small, inf, fmt) {
    const has = value != null && (!inf || inf.status === ST_OK || inf.status === "검색 결과 없음");
    const title = inf ? [inf.status, inf.note, inf.source ? "출처 " + inf.source : "", inf.asOf ? "기준일 " + inf.asOf : ""].filter(Boolean).join(" · ") : "";
    return `<div class="jd-kpi"${title ? ` title="${esc(title)}"` : ""}><span>${label}${inf && inf.company ? tagCo : ""}</span><strong${has ? "" : ' class="sm na"'}>${has ? (fmt ? fmt(value) : esc(value)) : esc(stText(inf))}</strong><small>${small}</small></div>`;
  }
  const srcChip = (text) => `<span class="jd-mini-source">${text}</span>`;
  const panel = (cls, title, sub, chipHTML, body, gap) => `<section class="jd-panel-box ${cls}"><div class="jd-box-head${gap ? " mb2" : ""}"><div><h3 class="jd-section-title">${title}</h3><p class="jd-section-sub">${sub}</p></div>${chipHTML || ""}</div>${body}</section>`;
  const table3 = (head, bodyRows) => `<div class="jd-table-wrap"><table class="jd-data-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${bodyRows}</tbody></table></div>`;
  const canvas3 = (id, aria) => `<div class="jd-chart-wrap"><canvas id="${id}" class="jd-detail-chart" data-chart="${id}" role="img" aria-label="${esc(aria)}"></canvas></div>`;
  const noChart = (text) => `<div class="jd-chart-wrap jd-chart-empty"><div class="jd-empty">${esc(text)}</div></div>`;
  const note3 = (text) => `<div class="jd-note3"><i class="ph ph-info"></i>${text}</div>`;
  const foot3 = (text) => `<div class="jd-foot3">${text}</div>`;
  const pill3 = (text, tone) => `<span class="jd-pill ${tone}">${esc(text)}</span>`;
  const emptyRow = (n, text) => `<tr><td colspan="${n}" class="jd-td-empty">${text}</td></tr>`;
  const money = (x) => (!fin(x) ? NA : x >= 1e9 ? "$" + (x / 1e9).toFixed(1) + " B" : x >= 1e6 ? "$" + (x / 1e6).toFixed(1) + " M" : "$" + Math.round(x).toLocaleString("ko-KR"));

  function detailBody(key, v) {
    if (key === "regulation") {
      const r = v.regulation, i = r.info;
      const kp = kpi3("통제번호 후보", r.controlCount, "HSK 연결 후보", i.controls, (x) => cnt(x, "int"))
        + kpi3("수입규제 기록", r.measureCount, "관련 기록 건수", i.measures, (x) => cnt(x, "int"))
        + kpi3("거래처 CSL 검색", r.cslMatches, "검색 결과", i.cslMatches, (x) => (i.cslMatches.status === "검색 결과 없음" ? `<span class="jd-sm">검색 결과 없음</span>` : cnt(x, "int")))
        + `<div class="jd-kpi jd-gate-${r.gate.key}" title="${esc(r.gate.text)}"><span>검토 상태</span><strong class="sm">${esc(r.gate.label)}</strong><small>${r.gate.key === "pass" ? "규제 관문 통과" : r.gate.key === "cond" ? "선적 전 전략물자 확인" : "추가 검토 후 재판정"}</small></div>`;
      const mrows = r.measures.length ? r.measures.map((x) => `<tr><td>${esc(x.type)}</td><td>${esc(x.origin)}</td><td>${pill3(x.status, "warn")}</td><td>${esc(x.period)}</td></tr>`).join("")
        : emptyRow(4, `${esc(stText(i.measures))} — 기록이 없다는 뜻이며 규제 없음 판정이 아닙니다${i.measures.asOf ? ` · 기준일 ${esc(i.measures.asOf)}` : ""}`);
      const left = panel("", "관련 규제 기록", "규제 유형·원산지·진행상황·기간", srcChip("검색 기록 기반"), table3(["유형", "대상 원산지", "진행상황", "기간"], mrows), true);
      const list = r.controls.length ? r.controls.map((x) => `<div class="jd-list-item" title="${esc(x.all.join(", "))}"><div class="jd-list-row"><b>${esc(x.no)}</b><span class="jd-cand">후보</span></div><div class="jd-list-name">${esc(x.name)}</div><div class="jd-list-meta">출처: ${esc(x.source || NA)}</div></div>`).join("")
        : `<div class="jd-empty">${esc(r.controlCount === 0 ? "연결된 통제번호 후보 없음 (판정 아님)" : stText(i.controls))}</div>`;
      const right = panel("", "수출통제 후보", "입력 HSK와 연결된 통제번호", srcChip("후보"), `<div class="jd-list">${list}</div>` + note3("후보가 발견되었다는 사실만 표시합니다. 수출금지·거래금지 여부는 별도 검증이 필요합니다."), true);
      return { status: r.status, kpis: kp, left, right };
    }
    if (key === "market") {
      const m = v.market, i = m.info, hasCo = m.monthly.some((x) => x.imports != null || x.korea != null || x.company != null), hasG = m.growth.some((x) => x.value != null);
      const kp = kpi3("수입시장 규모", m.importValue, "목적국 → 전세계", i.importValue, (x) => money(x))
        + kpi3("한국 수출액", m.koreaExport, "한국 → 목적국", i.koreaExport, (x) => money(x))
        + kpi3("YoY 성장률", m.yoy, m.growthCompany ? "전년 동기 대비 · 회사 월별 수출액" : "전년 동기 대비", i.yoy, (x) => cnt(x, "spct1"))
        + kpi3("한국산 점유율", m.koreaShare, "목적국 수입 기준", i.koreaShare, (x) => cnt(x, "pct1"));
      const left = panel("chart", `수입시장과 한국 수출 추이${m.hasCompanyInTrend ? tagCo : ""}`, "월별 금액 · 단위는 실제 API 응답에 맞춰 변경", srcChip("무역통계"), hasCo ? canvas3("marketTrendChart", "목적국 총수입·한국 수출·회사 수출 월별 금액") : noChart("자료 부족 — 목적국 수입·한국 수출 월별 자료 없음"));
      const right = panel("chart", `성장률 비교${hasG && m.growthCompany ? tagCo : ""}`, "YoY · 최근 3개월 · 3년 CAGR", srcChip("계산값"), (hasG ? canvas3("marketGrowthChart", m.growthCompany ? "회사 월별 수출액 기준 성장률" : "목적국 수입액 성장률") : noChart("자료 부족 — 비교 기간의 월별 자료가 모두 있어야 계산합니다")) + foot3("자료가 충분한 기간에서만 성장률을 계산합니다."));
      return { status: m.period, kpis: kp, left, right };
    }
    if (key === "price") {
      const p = v.price, i = p.info;
      const kp = kpi3("통계상 단가", p.unitPrice, p.unitPub ? "kg당 수출입 통계" : "kg당 · 회사 금액÷순중량 (판매가 아님)", i.unitPrice, (x) => cnt(x, "kg"))
        + kpi3("관세 참고율", p.tariff, "HS6·목적국 기준", i.tariff, (x) => cnt(x, "pct1"))
        + kpi3("참고환율", p.fx, "선택 통화 / KRW", i.fx, (x) => cnt(x, "krw2") + `<span class="jd-unit"> KRW</span>`)
        + kpi3("산업 가격지수", p.index, "한국은행 실제 분류", i.index, (x) => cnt(x, "d1"));
      const fxEmpty = i.fx.note === "결제통화 미기재" ? "자료 부족 — 결제통화 미기재" : `${stText(i.fx)}${i.fx.note ? " — " + i.fx.note : ""}`;
      const left = panel("chart", "참고환율 추이", "선택 결제통화의 원화 기준 환율", srcChip("환율 API"), p.fxSeries.length ? canvas3("fxChart", `참고환율 월평균 (${p.fxUnit || ""})`) : noChart(fxEmpty));
      const refs = p.refMeta.map((x) => `<div class="jd-ref3"><div><div class="jd-ref3-name">${esc(x.name)}${x.company ? tagCo : ""}</div><div class="jd-ref3-src">${esc(x.source)}</div></div><b${x.status === ST_OK ? "" : ' class="na"'}>${esc(x.value)}</b></div>`).join("");
      const right = panel("", "가격 관련 참고정보", "실제 판매가·적용세율과 구분", "", `<div class="jd-ref3-list">${refs}</div>` + note3("산업 가격지수는 반도체 개별 제품 가격이 아니며, 운송비는 수록 항로의 참고정보입니다."), true);
      return { status: "통계·WTO·환율", kpis: kp, left, right };
    }
    if (key === "logistics") {
      const l = v.logistics, i = l.info, hasCo = l.monthly.some((x) => x.dep != null || x.arr != null);
      const kp = kpi3("화물편 수", l.flightCount, "중복 제거 기준", i.flightCount) + kpi3("출발편", l.departures, "조회기간 기준", i.departures) + kpi3("도착편", l.arrivals, "조회기간 기준", i.arrivals) + kpi3("선박 기록", l.vesselCount, "API 응답 기준", i.vesselCount);
      const left = panel("chart", "월별 운항 횟수", "국가별 출발·도착편 수", srcChip("공항 API"), hasCo ? canvas3("logFlightChart", "국가별 월간 화물기 출발·도착편") : noChart(`${stText(i.monthly)} — 인천공항 국가별 운항 통계`));
      const flights = l.flights.length ? l.flights.slice(0, 40).map((x) => `<tr><td>${esc(x[0])}</td><td>${esc(x[1])}</td><td>${esc(x[2])}</td><td>${pill3(x[3], /변경|지연|결항/.test(x[3]) ? "warn" : "info")}</td></tr>`).join("")
        : i.flights.status === ST_OK ? emptyRow(4, "조회 기간에 이 나라와 오가는 인천공항 화물편 없음 (실제 0)") : `<tr class="jd-tr-unknown"><td colspan="4">${esc(stText(i.flights))} — 인천공항 화물편</td></tr>`;
      const qrows = l.queries.length ? l.queries.map((x) => `<tr><td>${esc(x.mode)}</td><td>${esc(x.origin)}→${esc(x.dest)}</td><td>${num(x.count)}건</td></tr>`).join("") : emptyRow(3, esc(stText(i.queries)));
      const right = panel("", "최근 운항 기록", "항공사·편명·상대공항·상태", "", table3(["항공사/편명", "상대공항", "예정", "상태"], flights)
        + `<div class="jd-subtable"><div class="jd-subtable-title">조회 조건${tagCo}</div>${table3(["운송수단", "출발→도착 코드", "건수"], qrows)}</div>` + foot3("직항 여부·전체 배송시간·운송 가능 여부는 이 기록만으로 확정하지 않습니다."), true);
      return { status: l.period, kpis: kp, left, right };
    }
    if (key === "stability") {
      const s = v.stability, i = s.info, hasCo = s.monthly.some((x) => x.value != null);
      const kp = kpi3("변동계수 CV", s.cv, s.pub || s.cv == null ? "월별 수입금액 기준" : "회사 월별 수출액 기준", i.cv, (x) => cnt(x, "pct1"))
        + kpi3("급감 횟수", s.dropCount, "전월 대비 -20% 이하", i.dropCount, (x) => cnt(x, "times"))
        + kpi3("급감 빈도", s.dropRate, s.dropRate != null ? `비교 가능한 기간 기준 (${s.comparable}회)` : "비교 가능한 기간 기준", i.dropRate, (x) => cnt(x, "pct1"))
        + kpi3("환율 변동성", s.fxVol, "보조정보", i.fxVol, (x) => cnt(x, "pm1"));
      const left = panel("chart", `월별 수입금액과 증감률${hasCo && !s.pub ? tagCo : ""}`, "전월 대비 변화가 한눈에 보이도록 구성", srcChip("무역통계"), hasCo ? canvas3("stabilityChart", s.pub ? "목적국 월별 수입금액과 전월 대비 증감" : "회사 월별 수출액(백만 달러)과 전월 대비 증감") : noChart("자료 부족 — 목적국 월별 수입통계 없음"));
      const drows = s.drops.length ? s.drops.map((x) => `<tr><td>${esc(x.label)}</td><td class="jd-neg">${pct(x.change)}</td><td>${money(x.value)}</td></tr>`).join("") : emptyRow(3, s.cv == null ? esc(stText(i.dropCount)) : "급감 기록 없음");
      const right = panel("", `급감 이력${hasCo && !s.pub ? tagCo : ""}`, "전월 대비 20% 이상 감소한 달", "", table3(["월", "전월 대비", hasCo && !s.pub ? "수출액" : "수입액"], drows)
        + (!s.pub && s.pubNote ? `<p class="jd-foot3 jd-foot3-tight">목적국 수입통계: ${esc(s.pubNote)} → 회사 월별 수출액으로 대체</p>` : "")
        + (s.missing.length ? `<p class="jd-foot3 jd-foot3-tight">자료 없는 달 ${s.missing.map(esc).join(", ")} · 0 이 아니라 결측이며 전월비 계산에서 제외</p>` : "")
        + note3("급감 이력은 과거 관측값이며 미래의 손실 가능성을 뜻하지 않습니다."), true);
      return { status: s.status, kpis: kp, left, right };
    }
    return null;
  }
  const EMPTY_KPI = { regulation: [["통제번호 후보", "HSK 연결 후보"], ["수입규제 기록", "관련 기록 건수"], ["거래처 CSL 검색", "검색 결과"], ["검토 상태", "추가 검증 필요"]], market: [["수입시장 규모", "목적국 → 전세계"], ["한국 수출액", "한국 → 목적국"], ["YoY 성장률", "전년 동기 대비"], ["한국산 점유율", "목적국 수입 기준"]], price: [["통계상 단가", "kg당 수출입 통계"], ["관세 참고율", "HS6·목적국 기준"], ["참고환율", "선택 통화 / KRW"], ["산업 가격지수", "한국은행 실제 분류"]], logistics: [["화물편 수", "중복 제거 기준"], ["출발편", "조회기간 기준"], ["도착편", "조회기간 기준"], ["선박 기록", "API 응답 기준"]], stability: [["변동계수 CV", "월별 수입금액 기준"], ["급감 횟수", "전월 대비 -20% 이하"], ["급감 빈도", "비교 가능한 기간 기준"], ["환율 변동성", "보조정보"]] };
  function detailHTML(key) {
    const a = ameta(key), m3 = I3[key];
    if (!a || !m3) return "";
    const v = view();
    if (v && isEngine()) return engineDetailHTML(key, v); // (junhee) 2026-09-27 엔진 문서: sanghyeob 방식 세부 탭
    const head = (statusText) => `<div class="jd-head"><div class="jd-head-text"><span class="jd-kicker">${m3.kicker}</span><h2>${m3.title}</h2><p>${m3.sub}</p></div><div class="jd-status-box"><small>${m3.box}</small><b>${esc(statusText)}</b></div></div>`;
    if (!v) return `<div class="jd-detail" data-key="${key}">${infobarHTML(null)}${head("회사 선택 전")}<div class="jd-kpis four">${EMPTY_KPI[key].map(([l, s]) => `<div class="jd-kpi"><span>${l}</span><strong>—</strong><small>${s}</small></div>`).join("")}</div>${emptyBox("바탕화면의 기업 파일을 열면 이 영역의 값이 표시됩니다.")}<div class="jd-foot"><span><i class="ph ph-info"></i>참고 적합도 v1 · 분석 엔진</span><span>기업 파일을 열면 값이 계산됩니다</span></div></div>`;
    const d = detailBody(key, v), cc = counts(areaItems(key));
    const extra = showItems ? `<div class="jd-items-head"><h3>세부사항 · handoff 항목 전체 (${cc["확인됨"]}/${cc.total} 확인됨)</h3><p>${STATUSES.map((s) => chipCount(s, cc[s])).join("")}</p></div><div class="jd-items">${itemsHTML(key)}</div>` : "";
    return `<div class="jd-detail${showItems ? " jd-with-items" : ""}" data-key="${key}">${infobarHTML(v)}${head(d.status)}<div class="jd-kpis four">${d.kpis}</div><div class="jd-detail-grid five"><div class="jd-col span3">${d.left}</div><div class="jd-col span2">${d.right}</div></div>${extra}
      <div class="jd-foot"><span><i class="ph ph-info"></i>'회사 자료' 칸은 공개 통계가 아니라 회사 파일 값 · 실제 0 은 "0", 자료 없음은 상태 글자(미확인·자료 부족)</span><span class="jd-foot-right">${esc(v.meta.file)} · ${esc(v.meta.applied)}</span></div></div>`;
  }
  // 항목 전체 보기 카드·결측 창용 보조 함수
  const kpi = (label, value, foot, status) => `<div class="jd-kpi"><span>${label}</span><strong${status && status !== "확인됨" ? ' class="sm"' : ""}>${value}</strong><small>${status ? chip(status) + " " : ""}${foot || ""}</small></div>`;
  const box = (title, sub, body, chipText, foot) => `<section class="jd-panel-box"><div class="jd-box-head"><div><h4 class="jd-section-title">${title}</h4>${sub ? `<p class="jd-section-sub">${sub}</p>` : ""}</div>${chipText ? `<span class="jd-mini-source">${chipText}</span>` : ""}</div>${body}${foot ? `<small class="jd-box-foot">${foot}</small>` : ""}</section>`;
  const table = (head, rows, emptyText) => `<div class="jd-table-wrap"><table class="jd-data-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.length ? rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${head.length}" class="jd-td-empty">${emptyText}</td></tr>`}</tbody></table></div>`;
  const chartWrap = (name, aria) => `<div class="jd-chart-wrap"><canvas class="jd-detail-chart" data-chart="${name}" role="img" aria-label="${aria}"></canvas></div>`;
  const emptyBox = (text) => `<div class="jd-empty">${text}</div>`;
  const info = (text) => `<div class="jd-info-box"><i class="ph ph-info"></i><span>${text}</span></div>`;
  const statusBox = (label, value) => `<div class="jd-status-box"><small>${label}</small><b>${value}</b></div>`;
  const refRow = (label, value, foot) => `<div class="jd-ref-row"><div><b>${label}</b>${foot ? `<small>${foot}</small>` : ""}</div><strong>${value}</strong></div>`;
  const listItem = (title, badge, name, meta) => `<div class="jd-list-item"><div class="jd-list-row"><b>${title}</b>${badge}</div><div class="jd-list-name">${name}</div><div class="jd-list-meta">${meta}</div></div>`;
  const ctrlList = (arr) => (arr && arr.length ? `<span class="jd-ctrl-list">${arr.slice(0, 6).map((x) => `<code class="jd-ctrl">${esc(x)}</code>`).join("")}${arr.length > 6 ? `<code class="jd-ctrl">+${arr.length - 6}</code>` : ""}</span>` : NA);
  const pubLine = (it) => (it ? `출처 ${esc(it.source || "-")} · 기준일 ${esc(it.as_of || "없음")}` : "공개자료 없음");
  const st = (it) => (it ? it.status : "자료 부족");
  const vt = (it, f) => (it && it.status === "확인됨" ? (f ? f(it) : valueText(it)) : NA);
  const shipPill = (status) => { const t = status === "정시" ? "ok" : /^지연/.test(status) ? "warn" : status === "날짜 오류" ? "bad" : "muted"; return `<span class="jd-st jd-st-${t}">${esc(status)}</span>`; };
  // ---- handoff 항목 카드 (항목 전체 보기) ----
  function itemCard(it, body, opts = {}) {
    if (!it) return "";
    const ok = it.status === "확인됨", v = ok ? valueText(it) : NA;
    const unit = ok && it.unit && !/USD|KRW|%|10억|^일$/.test(it.unit) ? `<small>${esc(it.unit)}</small>` : ok && it.unit && /%$/.test(it.unit) && typeof it.value !== "object" ? `<small>${esc(it.unit)}</small>` : "";
    return `<section class="jd-panel-box jd-item${opts.span ? " span2" : ""}" data-status="${esc(it.status)}" data-key="${esc(it.key)}">
      <div class="jd-box-head"><div><h4 class="jd-section-title">${opts.tag ? `<span class="jd-tag">${opts.tag}</span>` : ""}${esc(it.label)}</h4><p class="jd-section-sub">${metaText(it) || esc(it.note || "")}</p></div>${chip(it.status)}</div>
      ${opts.noValue ? "" : `<div class="jd-item-value"><strong>${v}</strong>${unit}</div>`}${body || ""}
      <small class="jd-box-foot">${it.basis ? `근거: ${esc(it.basis)}` : ""}${it.basis && it.note ? " · " : ""}${it.note ? esc(it.note) : ""}${it.source && !metaText(it).includes("출처") ? ` · 출처 ${esc(it.source)}` : ""}</small></section>`;
  }
  function unknownCard(items, title, note) {
    const list = items.filter(Boolean);
    if (!list.length) return "";
    return `<section class="jd-panel-box jd-item jd-item-unknown" data-status="미확인"><div class="jd-box-head"><div><h4 class="jd-section-title">${title}</h4><p class="jd-section-sub">${esc(note)}</p></div>${chip(list[0].status)}</div><div class="jd-ref-list">${list.map((it) => `<div class="jd-ref-row"><div><b>${esc(it.label)}</b><small>${esc(it.note || "")}</small></div><strong>${chip(it.status)}</strong></div>`).join("")}</div></section>`;
  }
  const blanksLine = (it) => (it && it.blanks ? `<p class="jd-dim jd-mt">빈칸·오류: ${Object.entries(it.blanks).map(([a, b]) => `${esc(a)} ${b}건`).join(" · ")}</p>` : "");
  function bodyFor(key, it) {
    const k = it.key, rows = it.rows || [];
    if (k === "export_control_candidates") return table(["제품", "입력 HSK", "HSK 품목명", "통제번호 후보", "상태"], rows.map((r) => [esc(r.product), esc(r.input_hsk || "미확인"), esc(r.hsk_name || NA), r.control_numbers && r.control_numbers.length ? `<span class="jd-st jd-st-warn">후보 ${r.control_numbers.length}</span> ${ctrlList(r.control_numbers)}` : NA, chip(r.status) + (r.note ? ` <small class="jd-dim">${esc(r.note)}</small>` : "")]), "제품 없음");
    if (k === "import_regulation_records") return table(["품목명", "규제형태(진행상황)", "대상 원산지", "기간·판정(원문)", "한국 대상", "일치 HS"], rows.map((r) => [esc(r.item), esc(r.type_and_status), esc(r.target_origin), `<span class="jd-wrap">${esc(r.period_raw || NA)}</span>`, esc(r.korea_targeted || NA), esc((r.matched_hs || []).join(", "))]), "검색 결과 없음 — 기록이 없다는 뜻이며 규제 없음 판정이 아닙니다");
    if (k === "csl_search") return table(["거래처", "법인명", "검색 결과", "일치 명단(명칭 · 출처 · 기재기간)", "비고"], rows.map((r) => [esc(r.customer_id) + (r.alias ? `<br><small class="jd-dim">${esc(r.alias)}</small>` : ""), esc(r.name || "(법인명 없음)"), chip(r.status), r.matches && r.matches.length ? r.matches.map((m) => `<div class="jd-wrap"><b>${esc(m.name)}</b> · ${esc(m.source)} · ${esc(m.start_date || "?")}~${esc(m.end_date || "")}<br><small class="jd-dim">${esc(m.addresses || "")}</small></div>`).join("") : NA, esc(r.note || "")]), "이 목적국의 거래처가 없습니다");
    if (k === "korea_exports_to_destination") return table(["HS6", "조치 연도", "수입액(USD)"], rows.map((r) => [hsDot(r.hs6), esc(r.year_dt_year), usd(r.imports_usd)]), "자료 부족");
    if (k === "wsts") { const latest = {}; rows.forEach((r) => { latest[r.region] = r; }); return chartWrap("wsts", "WSTS 세계 월별 매출") + table(["권역", "최신 월", "매출(10억 달러)", "전년동월비"], Object.values(latest).map((r) => [esc(r.region), esc(r.month), fin(r.value_thousand_usd) ? (r.value_thousand_usd / 1e6).toFixed(2) : NA, pct(r.yoy_pct)]), NA); }
    if (k === "company_exports") return chartWrap("company-exports", "회사 월별 수출액") + table(["연도", "수출액(USD)"], (it.yearly || []).map((y) => [esc(y.year), usd(y.value_usd)]), NA) + (rows.some((r) => r.value_usd == null) ? `<p class="jd-dim jd-mt">자료 없는 달: ${rows.filter((r) => r.value_usd == null).map((r) => esc(r.month)).join(", ")} (0 이 아니라 결측)</p>` : "");
    if (k === "company_unit_price") return table(["제품", "HS6", "연도", "USD/kg", "사용 행"], rows.map((r) => [esc(r.product), hsDot(r.hs6), esc(r.year), num(r.usd_per_kg, 0), esc(r.rows_used)]), "계산 가능한 행 없음");
    if (k === "tariff_reference") return table(["HS6", "조치일", "관세 참고율"], rows.map((r) => [hsDot(r.hs6), esc(r.year_dt), fin(r.best_avlbl_pct) ? r.best_avlbl_pct.toFixed(2) + "%" : NA]), "자료 부족");
    if (k === "fx_reference") return chartWrap("fx", "참고환율");
    if (k === "price_index") return table(["기간", "지수"], rows.map((r) => [esc(r.period), fin(r.value) ? num(r.value, 2) : NA]), NA) + `<p class="jd-dim jd-mt">전월비 ${pct(it.mom_pct)} · 전년동월비 ${pct(it.yoy_pct)}</p>`;
    if (k === "freight_reference") return table(["구분", "항로", "단위", "최신 월", "값", "전월비", "전년비"], rows.map((r) => [`<span class="jd-st jd-st-${r.mode === "해상수출" ? "info" : r.mode === "해상수입" ? "muted" : "warn"}">${esc(r.mode)}</span>`, esc(r.route), esc(r.unit), esc(r.month), num(r.value), pct(r.mom_pct), pct(r.yoy_pct)]), "수록 항로 없음");
    if (k === "query_conditions") return table(["운송수단", "출발지코드", "도착지코드", "선적 건수"], rows.map((r) => [esc(r.mode), esc(r.origin_code), esc(r.destination_code), esc(r.shipments)]), "연결된 물류 행 없음") + blanksLine(it);
    if (k === "delivery_ontime") return (rows.some((r) => r.rate_pct != null) ? chartWrap("ontime", "월별 납기 준수율") : "") + table(["월", "추적 건수", "정시", "준수율"], rows.filter((r) => r.tracked != null).map((r) => [esc(r.month), esc(r.tracked), esc(r.ontime), fin(r.rate_pct) ? r.rate_pct.toFixed(1) + "%" : NA]), "추적 가능한 행 없음") + blanksLine(it);
    if (k === "lead_time") return table(["수단", "건수", "평균(일)", "계획 평균(일)", "최소", "최대"], rows.map((r) => [esc(r.mode), esc(r.shipments), esc(r.avg_days), fin(r.planned_avg_days) ? r.planned_avg_days : NA, esc(r.min_days), esc(r.max_days)]), "실제 도착일 있는 행 없음");
    if (k === "freight_ratio") return table(["수단", "건수", "운임 합(USD)", "수출금액(USD)", "비중", "kg당 운임"], rows.map((r) => [esc(r.mode), esc(r.shipments), usd(r.freight_usd), usd(r.amount_usd), fin(r.ratio_pct) ? (+r.ratio_pct).toFixed(2) + "%" : NA, fin(r.usd_per_kg) ? num(r.usd_per_kg, 2) : NA]), "운임 있는 행 없음") + blanksLine(it);
    if (k === "shipments_monthly") return rows.some((r) => r.total != null) ? chartWrap("shipments", "월별 선적 건수") : "";
    if (k === "recent_shipments") return table(["물류ID", "수단", "구간", "선적일", "예정 도착", "실제 도착", "상태"], rows.map((r) => [esc(r.id), esc(r.mode), `${esc(r.origin_code)}→${esc(r.destination_code)}`, esc(r.ship_date), esc(r.eta || NA), esc(r.ata || NA), shipPill(r.status)]), "선적 기록 없음");
    if (k === "company_export_volatility") return `<div class="jd-kpis three"><div class="jd-kpi"><span>변동계수 CV</span><strong>${fin(it.value) ? it.value + "%" : NA}</strong><small>자료 있는 달 기준</small></div><div class="jd-kpi"><span>급감 횟수</span><strong>${it.drop_count ?? NA}회</strong><small>전월비 −20% 이하</small></div><div class="jd-kpi"><span>급감 빈도</span><strong>${fin(it.drop_rate_pct) ? it.drop_rate_pct + "%" : NA}</strong><small>비교 가능 ${it.comparable_months ?? NA}회 대비</small></div></div>` + chartWrap("volatility", "월별 수출액") + table(["급감 월", "전월비", "수출액"], (it.drops || []).map((d) => [esc(d.month), `<b class="jd-neg">${pct(d.mom_pct)}</b>`, usdM(d.value_usd)]), "급감 기록 없음") + (it.missing_months && it.missing_months.length ? `<p class="jd-dim jd-mt">자료 없는 달: ${it.missing_months.map(esc).join(", ")} · 전월비 계산에서 제외</p>` : "");
    if (k === "fx_volatility") return it.status === "확인됨" ? `<div class="jd-ref-list"><div class="jd-ref-row"><div><b>등급(과거 10년 대비)</b></div><strong>${esc(it.grade || NA)}</strong></div><div class="jd-ref-row"><div><b>최고</b><small>${esc(it.high ? it.high.month : "")}</small></div><strong>${it.high ? num(it.high.value, 2) : NA}</strong></div><div class="jd-ref-row"><div><b>최저</b><small>${esc(it.low ? it.low.month : "")}</small></div><strong>${it.low ? num(it.low.value, 2) : NA}</strong></div></div>` : "";
    if (k === "wsts_volatility") return table(["권역", "기간", "전월비 절대값 평균", "−20% 급감"], rows.map((r) => [esc(r.region), esc(r.period), fin(r.mean_abs_mom_pct) ? r.mean_abs_mom_pct + "%" : NA, `${r.drops_20pct}회/${r.comparable_months}`]), NA);
    return "";
  }
  // 공개 통계 항목 카드 본문 (행이 길어 최근 것만)
  function pubBody(it) {
    const k = it.key, rows = it.rows || [], B = (x) => (fin(x) ? "$" + (x / 1e9).toFixed(2) + "B" : NA);
    if (k === "destination_imports") {
      const agg = {}; rows.forEach((r) => { const key2 = r.month || r.year; agg[key2] = agg[key2] || { w: 0, k: 0 }; agg[key2].w += r.world_usd || 0; agg[key2].k += r.korea_usd || 0; });
      return table(["기간", "전 세계 수입", "한국산", "한국 비중"], Object.keys(agg).sort().slice(-12).reverse().map((m) => [esc(m), B(agg[m].w), B(agg[m].k), agg[m].w ? ((agg[m].k / agg[m].w) * 100).toFixed(1) + "%" : NA]), "자료 없음");
    }
    if (k === "korea_exports_to_destination" && rows.length && rows[0].exp_usd != null) {
      const agg = {}; rows.forEach((r) => { agg[r.month] = (agg[r.month] || 0) + r.exp_usd; });
      return table(["월", "한국 → 목적국 수출액"], Object.keys(agg).sort().slice(-12).reverse().map((m) => [esc(m), B(agg[m])]), "자료 없음");
    }
    if (k === "trade_unit_price") {
      const agg = {}; rows.forEach((r) => { agg[r.month] = agg[r.month] || { u: 0, kg: 0 }; agg[r.month].u += r.exp_usd || 0; agg[r.month].kg += r.exp_kg || 0; });
      return table(["월", "수출액", "중량(kg)", "USD/kg"], Object.keys(agg).sort().slice(-12).reverse().map((m) => [esc(m), B(agg[m].u), num(agg[m].kg), agg[m].kg ? num(agg[m].u / agg[m].kg, 0) : NA]), "자료 없음");
    }
    if (k === "baseline_unit_price") return table(["HS6", "목적국 수출 USD/kg", "전 세계 수출 USD/kg", "비율"], rows.map((r) => [hsDot(r.hs6), num(r.dest_usd_per_kg, 0), num(r.world_usd_per_kg, 0), fin(r.ratio_pct) ? r.ratio_pct + "%" : NA]), "자료 없음");
    if (k === "cargo_flights") return table(["구분", "항공사·편명", "상대공항", "예정", "상태"], rows.slice(0, 30).map((r) => [esc(r.direction), esc(`${r.airline || ""} ${r.flight || ""}`), esc(`${r.airport || ""} (${r.airport_code || ""})`), esc(r.scheduled ? `${r.scheduled.slice(4, 6)}-${r.scheduled.slice(6, 8)} ${r.scheduled.slice(8, 10)}:${r.scheduled.slice(10, 12)}` : ""), esc(r.status)]), "조회 기간에 해당 화물편 없음 (실제 0)");
    if (k === "flight_counts") return table(["월", "출발편", "도착편", "합계"], rows.slice(-12).reverse().map((r) => [esc(r.month), r.dep == null ? NA : num(r.dep), r.arr == null ? NA : num(r.arr), r.total == null ? NA : num(r.total)]), "자료 없음");
    if (k === "vessel_records") return table(["선박", "국적", "종류", "이전 항", "다음 항", "입항", "출항"], rows.slice(0, 30).map((r) => [esc(r.vessel), esc(r.flag), esc(r.kind), esc(r.prev), esc(r.next), esc(r.arrival), esc(r.departure)]), "조회 기간에 해당 기록 없음 (실제 0)");
    if (k === "destination_monthly_imports") return table(["월", "수입액", "전월비"], rows.slice().reverse().map((r) => [esc(r.month), B(r.value_usd), r.mom_pct == null ? NA : pct(r.mom_pct)]), "자료 없음");
    if (k === "sharp_drops") return table(["월", "전월비", "수입액"], rows.map((r) => [esc(r.month), `<b class="jd-neg">${pct(r.mom_pct)}</b>`, B(r.value_usd)]), "급감 기록 없음");
    return "";
  }
  function itemsHTML(key) {
    const g = (k) => itemOf(key, k), card = (k, opts) => { const it = g(k); return it ? itemCard(it, (it.status === "확인됨" ? pubBody(it) : "") || bodyFor(key, it), opts) : ""; };
    const pubOrUnknown = (keys, title, note, opts) => (keys.every((k) => !g(k) || g(k).status === "미확인") ? unknownCard(keys.map(g), title, note) : keys.map((k) => card(k, opts && opts[k])).join(""));
    if (key === "regulation") return card("export_control_candidates", { span: true, noValue: true }) + card("import_regulation_records", { span: true, noValue: true }) + card("csl_search", { span: true, noValue: true });
    if (key === "market") return pubOrUnknown(["destination_imports", "korea_share", "growth_yoy", "growth_3m_yoy", "cagr_3y"], "목적국 수입시장 규모·점유율·성장률", "목적국 수입통계 API 연동 전", { destination_imports: { span: true } }) + card("korea_exports_to_destination") + card("wsts", { span: true, noValue: true }) + card("company_exports", { span: true });
    if (key === "price") return pubOrUnknown(["trade_unit_price", "baseline_unit_price"], "무역통계 단가 · 기준 대비 단가", "무역통계 API 연동 전", {}) + card("company_unit_price") + card("tariff_reference", { span: true }) + card("fx_reference") + card("price_index") + card("freight_reference", { span: true, noValue: true });
    if (key === "logistics") return pubOrUnknown(["cargo_flights", "flight_counts", "vessel_records"], "화물 항공편 일정 · 운항 횟수 · 선박 입출항 기록", "미확인(인천공항·항만 API 연동 전)", { cargo_flights: { span: true }, vessel_records: { span: true } }) + card("delivery_ontime", { span: true }) + card("lead_time") + card("freight_ratio") + card("shipments_monthly", { span: true, noValue: true }) + card("recent_shipments", { span: true, noValue: true }) + card("query_conditions");
    if (key === "stability") return pubOrUnknown(["destination_monthly_imports", "cv", "sharp_drops"], "목적국 월별 수입금액 · 변동계수 · 급감 이력", "미확인(목적국 수입통계 API 연동 전)", {}) + card("company_export_volatility", { span: true, noValue: true, tag: "보조" }) + card("fx_volatility", { tag: "보조" }) + card("wsts_volatility", { tag: "보조", noValue: true });
    return "";
  }

  // 한 영역의 항목 전체 표 (세부사항 화면 · 각 상세 탭의 '세부사항' 공용). withTabBtn=false 면 탭 이동 버튼 없음
  function areaSection(key, withTabBtn = true) {
    const a = { key }, eng = isEngine();
    const val = (it) => (it.status === "확인됨" ? (eng ? esc(engVal(it.value, it.unit)) : valueText(it)) : NA);
    const when = (it) => esc([it.period, it.as_of].filter(Boolean).join(" · ") || NA);
    const items = areaItems(a.key), cc = counts(items);
    const rows = items.map((it) => [`<b>${esc(it.label || it.key)}</b>${it.note ? `<br><small class="jd-dim">${esc(it.note)}</small>` : ""}`, val(it), chip(it.status), when(it), esc(it.source ? shortSrc(it.source) : NA)]);
    const btn = !withTabBtn ? "" : `<button type="button" class="small-button" data-open-tab="${a.key}">${esc(FACTOR_KO[a.key])} 탭</button>`;
    return `<section class="jd-panel-box jd-item span2" data-key="${a.key}"><div class="jd-box-head"><div><h4 class="jd-section-title">${esc(FACTOR_KO[a.key])} · 확인됨 ${cc["확인됨"]}/${cc.total}</h4><p class="jd-section-sub">${STATUSES.map((s) => chipCount(s, cc[s])).join("")}</p></div>${btn}</div>${table(["항목", "값", "상태", "기간 · 기준일", "출처"], rows, "이 영역의 항목이 없습니다")}</section>`;
  }
  // (junhee) 2026-09-27 왼쪽 사이드바 '세부사항 (항목 전체 보기)': 다섯 영역의 모든 항목을 한 화면에 (값을 채우지 않고 상태 그대로)
  function allItemsHTML() {
    const v = view();
    const head = (b) => `<div class="jd-head"><div class="jd-head-text"><span class="jd-kicker">DETAILS · ALL ITEMS</span><h2>세부사항 · 항목 전체 보기</h2><p>규제·시장성·가격·물류·안정성의 모든 항목입니다. 자료 없음·조회 실패는 값을 채우지 않고 상태로 표시합니다. 영역 이름 옆 버튼으로 해당 상세 탭을 엽니다.</p></div>${b}</div>`;
    if (!v) return `<div class="jd-detail" data-key="items">${infobarHTML(null)}${head(statusBox("CONFIRMED", "회사 선택 전"))}${emptyBox("바탕화면의 기업 파일을 열면 모든 항목이 여기에 표시됩니다.")}</div>`;
    const { n, m } = confirmed(), eng = isEngine();
    const areas = AREAS.map((a) => areaSection(a.key)).join("");
    return `<div class="jd-detail jd-with-items" data-key="items">${infobarHTML(v)}${head(statusBox("CONFIRMED", `확인됨 ${n} / ${m}`))}<div class="jd-items">${areas}</div>
      <div class="jd-foot"><span><i class="ph ph-info"></i>${eng ? "분석 엔진(참고 적합도 v1)" : "평가 기준 " + RULE_VER} · 실제 0 은 "0", 자료 없음은 상태 글자(미확인·자료 부족)</span><span class="jd-foot-right">${esc(v.meta.file)}</span></div></div>`;
  }

  // ---------------------------------------------------------------- 보고서
  function scoreRows() {
    const ov = overallNow(), w = weights();
    const rows = AREAS.map((a) => { const f = factorScore(a.key); const val = !f ? NA : f.state === "ok" ? `${(+f.score).toFixed(1)} / 100 (전월 대비 ${f.delta == null ? "–" : (f.delta > 0 ? "+" : "") + (+f.delta).toFixed(1)}) — ${f.note || ""}` : `자료 부족 — ${f.note || ""}`; return [a.ko2, val, a.key === "regulation" ? "관문 고정" : isEngine() && !isCustom() ? `엔진 배점 ${engineWeights()[a.key]}/80` : w[a.key] + "%"]; });
    rows.push(["종합", ov && ov.score != null ? `${(+ov.score).toFixed(1)} / 100 (전월 대비 ${ov.delta == null ? "–" : (ov.delta > 0 ? "+" : "") + (+ov.delta).toFixed(1)})${ov.excluded && ov.excluded.length ? (isEngine() && !isCustom() ? " — 근거 반영률 0%(정책 기준 50점으로 계산): " + ov.excluded.map((k) => FACTOR_KO[k]).join("·") : " — 자료 부족 제외: " + ov.excluded.map((k) => FACTOR_KO[k]).join("·") + " (재정규화)") : ""}${ov.recomputed ? (isEngine() ? " · 사용자 가중치 화면 참고점수(엔진 등급 아님)" : " · 사용자 가중치로 재계산") : ""}` : "자료 부족", isCustom() ? "사용자 가중치" : isEngine() ? "엔진 배점" : "기본 가중치"]);
    return rows;
  }
  const confirmRows = () => AREAS.map((a) => { const cc = counts(areaItems(a.key)); return [a.ko, current ? `확인됨 ${cc["확인됨"]} / ${cc.total} (자료 부족 ${cc["자료 부족"]} · 미확인 ${cc["미확인"]} · 검색 결과 없음 ${cc["검색 결과 없음"]} · 검색 불가 ${cc["검색 불가"]})` : "회사 선택 전", current && !isEngine() ? "평가 기준 " + RULE_VER : "참고 적합도 v1"]; });
  const reportRows = () => (current ? scoreRows() : confirmRows());
  function reportHTML(meta = {}) {
    const style = `<style>body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:900px;margin:40px auto;padding:24px;color:#24344f;line-height:1.7;font-size:13px}h1{font-size:26px}h2{margin-top:32px;font-size:18px}table{width:100%;border-collapse:collapse;font-size:11.5px}td,th{padding:8px 9px;text-align:left;border-bottom:1px solid #e5e9f1;vertical-align:top}th{background:#f5f7fb}.note{background:#fff7ed;border:1px solid #fed7aa;padding:14px 16px;border-radius:8px;color:#9a3412}.notice{background:#eef2ff;padding:10px 14px;border-radius:8px;color:#526a9c;font-size:12px}small{color:#7f8a9d}@media print{body{margin:0;padding:10px}h2{break-after:avoid}table{break-inside:avoid}}</style>`;
    if (!current) return `<!doctype html><html lang="ko"><meta charset="utf-8"><title>AXPORT 수출 분석 보고서</title>${style}<body><p>AXPORT / EXPORT INTELLIGENCE</p><h1>수출 분석 보고서</h1><div class="note"><b>참고 적합도 v1 · 분석 엔진</b></div><p>회사 선택 전입니다. 바탕화면의 기업 파일을 열면 점수·판정과 항목이 이 보고서에 채워집니다. 예시 수치는 넣지 않습니다.</p><p>생성일: ${esc(meta.generated || new Date().toLocaleString("ko-KR"))}</p></body></html>`;
    const c = current.common, q = c.data_quality || {}, k = calc(), cell = (v) => `<td>${v}</td>`, { n, m } = confirmed();
    const areaTables = AREAS.map((a) => `<h2>${esc(isEngine() ? ENG_HEAD[a.key][0] : a.ko2 + " — " + a.title)}</h2><p class="notice">${esc(isEngine() ? ENG_HEAD[a.key][1] : a.notice)}</p><table><tr><th>항목</th><th>상태</th><th>값</th><th>기간 · 기준일</th><th>출처</th><th>계산 근거 · 비고</th></tr>${areaItems(a.key).map((it) => `<tr>${cell(esc(it.label))}${cell(esc(it.status))}${cell(it.status === "확인됨" ? valueText(it) + (it.unit && !/USD|KRW|%|10억|^일$/.test(it.unit) ? " " + esc(it.unit) : "") : "—")}${cell([it.period, it.as_of].filter(Boolean).map(esc).join(" · ") || "—")}${cell(esc(it.source || "—"))}${cell([it.basis, it.note].filter(Boolean).map(esc).join(" · ") || "—")}</tr>`).join("")}</table>`).join("");
    const issues = (q.issues || []).map((i) => `<tr>${cell(esc(i.kind))}${cell(esc(i.sheet))}${cell(esc(i.field))}${cell(i.count + "건")}${cell(esc((i.ids || []).join(", ")) || "—")}${cell(esc(i.effect))}</tr>`).join("");
    return `<!doctype html><html lang="ko"><meta charset="utf-8"><title>AXPORT 수출 분석 보고서</title>${style}<body>
      <p>AXPORT / EXPORT INTELLIGENCE</p><h1>수출 분석 보고서</h1>
      <div class="note"><b>종합 판정: ${esc(k.overall.verdict ? k.overall.verdict.label : "판정 불가")}${k.overall.score != null ? ` · 종합 ${(+k.overall.score).toFixed(1)}점` : ""} · 규제 관문 ${esc(k.overall.gate ? k.overall.gate.label : "")}</b><br>${isEngine() ? "판단 기준 참고 적합도 v1(분석 엔진)" : "평가 기준 " + RULE_VER} · ${esc(k.overall.gate ? k.overall.gate.text : "")} · 자료 없는 항목은 미확인/자료 부족으로 표시 · AXPORT는 수출허가 여부를 최종 판정하지 않습니다</div>
      <p>${isEngine() && !isSampleDoc() ? "회사" : "회사(가상)"}: ${esc(current.company_name)} (${esc(current.company_name_en || "")})<br>파일: ${esc(current.file_name)}<br>제품: ${c.products.map((p) => `${esc(p.name)} [${esc(p.input_hsk || "미확인")}→${esc(p.analysis_hs6 || "미확인")}]`).join(", ")}<br>목적국: ${esc(selectedCountry)} · 분석 기간: ${esc(k.pr.label)} ${esc(k.pr.from)}~${esc(k.pr.to)} · HS: ${filters.hs === "all" ? "전체" : hsDot(filters.hs)}<br>자료 구분: ${esc(dataClassText())}${isEngine() ? `<br>유효 행 ${q.rows_valid == null ? "—" : q.rows_valid}/${q.rows_total == null ? "—" : q.rows_total} · 누락 월은 상세 탭의 월별 수입 차트에서 확인` : `<br>유효 행 ${q.rows_valid}/${q.rows_total} (합계 제외 ${q.rows_excluded_from_totals || 0}, 중복 제거 ${q.duplicates_removed || 0}, 취소 ${q.cancelled_zero_rows || 0}) · 빈 달 ${q.missing_months && q.missing_months.length ? q.missing_months.map(esc).join(", ") : "없음"}`}<br>생성일: ${esc(meta.generated || new Date().toLocaleString("ko-KR"))}</p>
      <h2>종합 수출적합도 (${isEngine() ? "참고 적합도 v1 · 분석 엔진" : "평가 기준 " + RULE_VER})</h2><table><tr><th>영역</th><th>점수 · 전월 대비 · 근거</th><th>적용 비중</th></tr>${scoreRows().map((r) => `<tr>${r.map((x) => cell(esc(x))).join("")}</tr>`).join("")}</table><p><small>${esc(k.highlights)}</small></p>
      <h2>영역별 자료 확인 현황 — 확인됨 ${n} / ${m} 항목</h2><table><tr><th>영역</th><th>확인 현황</th><th>비고</th></tr>${confirmRows().map((r) => `<tr>${r.map((x) => cell(esc(x))).join("")}</tr>`).join("")}</table>
      ${issues ? `<h2>파일의 결측·오류 (${(q.issues || []).length}곳 · 값을 채우지 않고 해당 계산에서만 제외)</h2><table><tr><th>구분</th><th>시트</th><th>항목</th><th>건수</th><th>식별자(앞 6개)</th><th>영향</th></tr>${issues}</table>` : ""}
      ${areaTables}
      <p><small>${isEngine() ? (isSampleDoc() ? "출처: 가상 샘플 기업 파일과 분석 엔진이" : "출처: 업로드 기업 파일과 분석 엔진이") + " 조회한 공개자료(UN Comtrade·관세청·ECOS·국가법령정보·WTO 관세조치·HSK 연계표·KOTRA·ITA CSL·WSTS·한국은행). 계산 근거는 sanghyeob 분석 엔진(suitability-reference-v1)과 항목별 '계산 근거' 열 참조." : "출처: 회사 파일(가상)과 공개자료(KOTRA·ITA CSL·HSK 연계표·WTO 관세조치·WSTS·연준 H.10·한국은행·관세청). 계산 근거는 표의 '계산 근거' 열과 junhee/rules/demo_scoring.md 참조."}</small></p></body></html>`;
  }

  // ---------------------------------------------------------------- 차트·애니메이션 (index3: 도넛 1.3s easeOut, 카운터 1.2s, 차트 기본 애니메이션)
  function destroy() { charts.forEach((ch) => { try { ch.destroy(); } catch {} }); charts = []; rafs.forEach((id) => (id < 0 ? clearTimeout(-id) : cancelAnimationFrame(id))); rafs = []; }
  const ctx2d = (canvas) => (canvas && canvas.getContext ? canvas.getContext("2d") : null);
  const GAUGE_MS = 1300, COUNT_MS = 1200, easeOut = (p) => 1 - Math.pow(1 - p, 3);
  // index3 도넛: SVG 원(r=74, 둘레 465) stroke-dashoffset 을 1.3s cubic-bezier(.16,1,.3,1) 로 줄이고, 가운데 숫자는 1.2s easeOut 카운터
  function drawGauge(root) {
    const ring = root.querySelector(".jd-gauge-ring"), counter = root.querySelector(".jd-gauge-center .jd-num");
    if (!ring) return;
    const to = parseFloat(ring.dataset.offset), target = counter ? parseFloat(counter.dataset.to) : NaN;
    const from = Number.isFinite(prevNums.overall) ? prevNums.overall : 0;
    if (!Number.isFinite(target)) { ring.style.strokeDashoffset = 465; if (counter) counter.textContent = NA; return; }
    if (reduced() || from === target) { ring.style.transition = "none"; ring.style.strokeDashoffset = to; if (counter) counter.textContent = target.toFixed(1); return; }
    ring.style.transition = "none";
    ring.style.strokeDashoffset = 465 - (465 * Math.max(0, Math.min(100, from))) / 100;
    ring.getBoundingClientRect();
    const id = setTimeout(() => { ring.style.transition = ""; ring.style.strokeDashoffset = to; }, 80);
    rafs.push(-id); // destroy() 에서 cancel (음수는 setTimeout id)
    const t0 = performance.now();
    const step = (now) => { const p = Math.min(1, (now - t0) / COUNT_MS); if (counter) counter.textContent = (from + (target - from) * easeOut(p)).toFixed(1); if (p < 1) rafs.push(requestAnimationFrame(step)); };
    if (counter) counter.textContent = from.toFixed(1);
    rafs.push(requestAnimationFrame(step));
  }
  function countUp(root) {
    root.querySelectorAll('.jd-num[data-to][data-key]:not([data-key="overall"])').forEach((el) => {
      const to = parseFloat(el.dataset.to), dec = parseInt(el.dataset.decimals || "0", 10);
      if (!Number.isFinite(to)) return;
      const from = Number.isFinite(prevNums[el.dataset.key]) ? prevNums[el.dataset.key] : 0;
      if (reduced() || from === to) { el.textContent = to.toFixed(dec); return; }
      const t0 = performance.now();
      const step = (now) => { const p = Math.min(1, (now - t0) / GAUGE_MS); el.textContent = (from + (to - from) * easeOut(p)).toFixed(dec); if (p < 1) rafs.push(requestAnimationFrame(step)); else el.textContent = to.toFixed(dec); };
      rafs.push(requestAnimationFrame(step));
    });
    // 상세 탭 KPI 숫자: 0 → 값 (index3 카운터와 같은 easeOut)
    root.querySelectorAll(".jd-cnt[data-cnt]").forEach((el) => {
      const to = parseFloat(el.dataset.cnt), fmt = el.dataset.fmt;
      if (!Number.isFinite(to)) return;
      if (reduced()) { el.textContent = fmtCnt(to, fmt); return; }
      const t0 = performance.now();
      const step = (now) => { const p = Math.min(1, (now - t0) / COUNT_MS); el.textContent = fmtCnt(to * easeOut(p), fmt); if (p < 1) rafs.push(requestAnimationFrame(step)); else el.textContent = fmtCnt(to, fmt); };
      el.textContent = fmtCnt(0, fmt); rafs.push(requestAnimationFrame(step));
    });
  }
  function baseOpts(extra) {
    const o = { responsive: true, maintainAspectRatio: false, animation: reduced() ? false : { duration: 900, easing: "easeOutQuart" },
      plugins: { legend: { display: false, labels: { boxWidth: 8, font: { size: 9 }, color: "#64748b" } }, tooltip: { displayColors: false, titleFont: { size: 10 }, bodyFont: { size: 10 } } },
      scales: { x: { grid: { display: false }, border: { display: false }, ticks: { font: { size: 9 }, color: "#a1aabc", maxRotation: 0, autoSkip: true } }, y: { grid: { color: "#f1f5f9" }, border: { display: false }, ticks: { font: { size: 9 }, color: "#b1b9c7", maxTicksLimit: 5 } } } };
    return extra ? extra(o) : o;
  }
  const line = (data, col, opts) => ({ data, borderColor: col, backgroundColor: col + "18", borderWidth: 2.2, tension: 0.35, pointRadius: 2.5, pointBackgroundColor: col, pointBorderWidth: 0, fill: true, spanGaps: false, ...(opts || {}) });
  const axisTitle = (text) => ({ display: true, text, font: { size: 9 }, color: "#a1aabc" });
  // index3 chartBase: 범례 boxWidth 8·9px, 툴팁 10px, x 격자 없음, y 격자 #F1F5F9, 눈금 9px
  function i3Opts(extra) {
    const font = { size: 9, family: "'Noto Sans KR Variable', 'Noto Sans KR', sans-serif" };
    const o = { responsive: true, maintainAspectRatio: false, animation: reduced() ? false : undefined,
      plugins: { legend: { labels: { boxWidth: 8, font } }, tooltip: { titleFont: { size: 10 }, bodyFont: { size: 10 } } },
      scales: { x: { grid: { display: false }, ticks: { font, maxRotation: 0, autoSkipPadding: 10 } }, y: { grid: { color: "#F1F5F9" }, ticks: { font } } } };
    return extra ? extra(o, font) : o;
  }
  // index3 차트 id 로 그린다. 값은 어댑터 구조(view)에서만 읽는다. 미확인·자료 부족 계열은 범례에 상태를 붙이고 값은 비워 둔다.
  function i3Chart(id) {
    const v = view();
    if (!v) return null;
    const M = (x) => (fin(x) ? x / 1e6 : null);
    if (id === "marketTrendChart") {
      const m = v.market, B = (x) => (fin(x) ? x / 1e9 : null);
      const ds = [
        { label: `목적국 총수입 (${m.info.imports.status === ST_OK ? "Comtrade" : m.info.imports.status})`, data: m.monthly.map((x) => B(x.imports)), borderColor: "#8B5CF6", backgroundColor: "rgba(139,92,246,.08)", fill: true, tension: 0.35, pointRadius: 2, yAxisID: "y" },
        { label: `한국 수출 (${m.info.korea.status === ST_OK ? "관세청" : m.info.korea.status})`, data: m.monthly.map((x) => B(x.korea)), borderColor: "#2563EB", tension: 0.35, pointRadius: 2, yAxisID: "y" } ];
      if (m.hasCompanyInTrend) ds.push({ label: "회사 수출 (회사 자료 · 오른쪽 축 M)", data: m.monthly.map((x) => M(x.company)), borderColor: "#0D9488", borderDash: [4, 3], tension: 0.35, pointRadius: 2, yAxisID: "y1", spanGaps: false });
      return { type: "line", data: { labels: m.monthly.map((x) => x.label), datasets: ds },
        options: i3Opts((o, font) => { o.plugins.tooltip.callbacks = { label: (c) => `${c.dataset.label}: ${c.parsed.y == null ? "자료 없음" : c.parsed.y.toFixed(2) + (c.dataset.yAxisID === "y1" ? " M" : " B")}` }; o.scales.y.title = { display: true, text: "USD B", font };
          if (m.hasCompanyInTrend) o.scales.y1 = { position: "right", grid: { display: false }, ticks: { font }, title: { display: true, text: "USD M", font } }; return o; }) };
    }
    if (id === "marketGrowthChart") {
      const gr = v.market.growth;
      return { type: "bar", data: { labels: gr.map((x) => (x.value == null ? [x.label, "자료 부족"] : x.label)), datasets: [{ label: "성장률 (회사 자료)", data: gr.map((x) => x.value), backgroundColor: "#8B5CF6", borderRadius: 7, barThickness: 24 }] },
        options: i3Opts((o) => { o.plugins.legend.display = false; o.scales.y.ticks.callback = (x) => x + "%"; o.plugins.tooltip.callbacks = { label: (c) => (c.parsed.y == null ? "자료 부족" : pct(c.parsed.y)) }; return o; }) };
    }
    if (id === "fxChart") {
      const p = v.price;
      return { type: "line", data: { labels: p.fxSeries.map((x) => x.label), datasets: [{ label: `참고환율 (${p.fxUnit || ""})`, data: p.fxSeries.map((x) => x.value), borderColor: "#0284C7", backgroundColor: "rgba(2,132,199,.08)", fill: true, tension: 0.3, pointRadius: 2 }] },
        options: i3Opts((o) => { o.plugins.legend.display = false; o.plugins.tooltip.callbacks = { label: (c) => `${c.parsed.y.toFixed(2)} ${p.fxUnit || ""}` }; return o; }) };
    }
    if (id === "logFlightChart") {
      const l = v.logistics;
      return { type: "bar", data: { labels: l.monthly.map((x) => x.label), datasets: [
        { label: "출발편", data: l.monthly.map((x) => x.dep), backgroundColor: "#D97706", borderRadius: 5, maxBarThickness: 18 },
        { label: "도착편", data: l.monthly.map((x) => x.arr), backgroundColor: "#FBBF24", borderRadius: 5, maxBarThickness: 18 } ] },
        options: i3Opts((o, font) => { o.plugins.tooltip.callbacks = { label: (c) => `${c.dataset.label}: ${c.parsed.y == null ? "자료 없음" : c.parsed.y + "편"}` }; o.scales.y.beginAtZero = true; o.scales.y.ticks.precision = 0; o.scales.y.title = { display: true, text: "편 (화물기)", font }; return o; }) };
    }
    if (id === "stabilityChart") {
      const s = v.stability, red = (x) => fin(x.change) && x.change <= -20, S = s.pub ? (x) => (fin(x) ? x / 1e9 : null) : M, unit = s.pub ? "B" : "M";
      return { type: "line", data: { labels: s.monthly.map((x) => x.label), datasets: [{ label: s.pub ? "목적국 월별 수입액" : "월별 수출액 (회사 자료)", data: s.monthly.map((x) => S(x.value)), borderColor: "#059669", backgroundColor: "rgba(5,150,105,.08)", fill: true, tension: 0.3,
        pointRadius: s.monthly.map((x) => (red(x) ? 4.5 : 3)), pointBackgroundColor: s.monthly.map((x) => (red(x) ? "#E11D48" : "#059669")), spanGaps: false }] },
        options: i3Opts((o, font) => { o.plugins.legend.display = false; o.plugins.tooltip.callbacks = { label: (c) => `$${c.parsed.y.toFixed(2)}${unit} · 전월비 ${pct(s.monthly[c.dataIndex] && s.monthly[c.dataIndex].change)}` }; o.scales.y.title = { display: true, text: "USD " + unit, font }; return o; }) };
    }
    return null;
  }
  function detailChart(name) {
    const k = calc();
    if (!k) return null;
    if (name === "market-trend") {
      const wsts = (current.public_series && current.public_series.wsts_worldwide) || [], ce = itemOf("market", "company_exports"), ms = (ce && ce.rows) || [];
      const wRows = wsts.filter((x) => x.month >= k.pr.from && x.month <= k.pr.to);
      const w = wRows.length >= 3 ? wRows : wsts.slice(-13);
      const months = [...new Set([...w.map((x) => x.month), ...ms.map((x) => x.month)])].sort();
      const wm = Object.fromEntries(w.map((x) => [x.month, x.value_thousand_usd / 1e6])), cm = Object.fromEntries(ms.map((x) => [x.month, x.value_usd == null ? null : x.value_usd / 1e6]));
      const datasets = [{ label: "세계 출하액 (USD B)", yAxisID: "y", ...line(months.map((mo) => (mo in wm ? wm[mo] : null)), color("market")) }, { label: "기업 월별 수출액 (USD M)", yAxisID: "y1", ...line(months.map((mo) => (mo in cm ? cm[mo] : null)), "#2563eb", { fill: false, borderDash: [4, 3] }) }];
      return { type: "line", data: { labels: months.map(ymShort), datasets }, options: baseOpts((o) => { o.plugins.legend.display = true; o.plugins.tooltip.callbacks = { label: (t) => `${t.dataset.label}: ${t.parsed.y == null ? "—" : t.parsed.y.toFixed(2)}` }; o.scales.y.title = axisTitle("USD B"); o.scales.y1 = { position: "right", grid: { display: false }, border: { display: false }, ticks: { font: { size: 9 }, color: "#b1b9c7", maxTicksLimit: 5 }, title: axisTitle("USD M") }; return o; }) };
    }
    if (name === "market-growth") {
      const f = factorScore("market"), inp = (f && f.inputs) || {}, wsts = (current.public_series && current.public_series.wsts_worldwide) || [];
      const wm = inp.wsts_month ? wsts.find((x) => x.month === inp.wsts_month) : null, prev = wm ? wsts.find((x) => x.month === ymAdd(wm.month, -1)) : null;
      const mom = wm && prev && prev.value_thousand_usd ? (wm.value_thousand_usd / prev.value_thousand_usd - 1) * 100 : null;
      const vals = [fin(inp.wsts_yoy_pct) ? inp.wsts_yoy_pct : null, fin(mom) ? mom : null, fin(inp.company_growth_3m_pct) ? inp.company_growth_3m_pct : null];
      return { type: "bar", data: { labels: ["세계 출하 전년동월비", "세계 출하 전월비", "기업 최근 3개월"], datasets: [{ data: vals, backgroundColor: [color("market"), color("market") + "99", "#2563eb"], borderRadius: 7, barThickness: 26 }] }, options: baseOpts((o) => { o.scales.y.ticks.callback = (v) => v + "%"; o.plugins.tooltip.callbacks = { label: (t) => (t.parsed.y == null ? "자료 부족" : pct(t.parsed.y)) }; return o; }) };
    }
    if (name === "price-fx" || name === "fx") {
      const it = itemOf("price", "fx_reference"), rows = (it && it.rows) || [];
      return { type: "line", data: { labels: rows.map((r) => ymShort(r.month)), datasets: [line(rows.map((r) => r.value), color("price"))] }, options: baseOpts((o) => { o.plugins.tooltip.callbacks = { label: (t) => `${t.parsed.y.toFixed(2)} ${(it && it.unit) || ""}` }; return o; }) };
    }
    if (name === "log-freight") {
      const fr = itemOf("price", "freight_reference"), sea = (fr && fr.rows ? fr.rows : []).filter((r) => r.mode === "해상수출");
      const months = [...new Set(sea.flatMap((r) => (r.series || []).map((x) => x.month)))].sort();
      const datasets = sea.map((r, i) => ({ label: r.route, ...line(months.map((mo) => { const h = (r.series || []).find((x) => x.month === mo); return h ? h.value : null; }), i === 0 ? color("logistics") : "#b45309", { fill: i === 0 }) }));
      return { type: "line", data: { labels: months.map(ymShort), datasets }, options: baseOpts((o) => { o.plugins.legend.display = datasets.length > 1; o.plugins.tooltip.callbacks = { label: (t) => `${t.dataset.label}: ${t.parsed.y == null ? "—" : num(t.parsed.y)}천원/2TEU` }; return o; }) };
    }
    if (name === "log-shipments" || name === "shipments" || name === "ontime") {
      const sm = itemOf("logistics", "shipments_monthly"), on = itemOf("logistics", "delivery_ontime"), rows = (sm && sm.rows) || [], om = Object.fromEntries(((on && on.rows) || []).map((r) => [r.month, r.rate_pct]));
      const col = color("logistics"), lineCol = "#0f766e", months = rows.length ? rows.map((r) => r.month) : ((on && on.rows) || []).map((r) => r.month);
      const datasets = [];
      if (name !== "ontime") datasets.push({ type: "bar", label: "항공", data: rows.map((r) => r.air), backgroundColor: col, borderRadius: 4, stack: "s", yAxisID: "y" }, { type: "bar", label: "해상", data: rows.map((r) => r.sea), backgroundColor: "#b45309", borderRadius: 4, stack: "s", yAxisID: "y" });
      if (name !== "shipments") datasets.push({ type: "line", label: "납기 준수율 %", data: months.map((m) => (m in om ? om[m] : null)), borderColor: lineCol, backgroundColor: lineCol, borderWidth: 2, tension: 0.3, pointRadius: 2.5, pointBackgroundColor: lineCol, yAxisID: name === "ontime" ? "y" : "y1", spanGaps: false, fill: false });
      return { type: name === "ontime" ? "line" : "bar", data: { labels: months.map(ymShort), datasets }, options: baseOpts((o) => {
        o.plugins.legend.display = datasets.length > 1;
        o.plugins.tooltip.callbacks = { label: (t) => `${t.dataset.label}: ${t.parsed.y == null ? "—" : t.dataset.type === "line" ? t.parsed.y.toFixed(1) + "%" : t.parsed.y + "건"}` };
        if (name === "ontime") { o.scales.y.min = 0; o.scales.y.max = 100; o.scales.y.ticks.callback = (v) => v + "%"; }
        else { o.scales.x.stacked = true; o.scales.y.stacked = true; o.scales.y.title = axisTitle("건"); if (name !== "shipments") o.scales.y1 = { position: "right", min: 0, max: 100, grid: { display: false }, border: { display: false }, ticks: { font: { size: 9 }, color: "#b1b9c7", callback: (v) => v + "%" } }; }
        return o; }) };
    }
    if (name === "stab-monthly" || name === "volatility" || name === "company-exports") {
      const it = itemOf("stability", "company_export_volatility"), rows = (it && it.rows) || [], col = color(name === "company-exports" ? "market" : "stability");
      const red = (r) => name !== "company-exports" && fin(r.mom_pct) && r.mom_pct <= -20;
      return { type: "line", data: { labels: rows.map((r) => ymShort(r.month)), datasets: [line(rows.map((r) => (fin(r.value_usd) ? r.value_usd / 1e6 : null)), col, { pointRadius: rows.map((r) => (red(r) ? 4.5 : 2.5)), pointBackgroundColor: rows.map((r) => (red(r) ? "#e11d48" : col)) })] },
        options: baseOpts((o) => { o.plugins.tooltip.callbacks = { label: (t) => `$${t.parsed.y.toFixed(2)}M · 전월비 ${pct(rows[t.dataIndex] && rows[t.dataIndex].mom_pct)}` }; o.scales.y.title = axisTitle("USD M"); return o; }) };
    }
    if (name === "wsts") {
      const it = itemOf("market", "wsts"), rows = (it && it.rows ? it.rows : []).filter((r) => r.region === "Worldwide");
      return { type: "line", data: { labels: rows.map((r) => ymShort(r.month)), datasets: [line(rows.map((r) => (fin(r.value_thousand_usd) ? r.value_thousand_usd / 1e6 : null)), color("market"))] }, options: baseOpts((o) => { o.plugins.tooltip.callbacks = { label: (t) => `세계 매출 $${t.parsed.y.toFixed(2)}B` }; o.scales.y.title = axisTitle("USD B"); return o; }) };
    }
    return null;
  }
  // ---------------------------------------------------------------- (junhee) 2026-09-27 엔진 문서 세부 탭 — sanghyeob 방식(적합도 항목·계산식·확인 항목·출처)
  // 차트를 메인(왼쪽 넓은 칸 맨 위)에 둔다. 모션: 선이 왼쪽부터 그려지며 면이 채워지고(막대는 0에서 차례로 차오름), 최신 관측점은 계속 맥박처럼 움직인다.
  // 동작 줄이기(OS 설정·?motion=off)면 모션 없이 그린다. 새 스타일 없음: 기존 jd-* 클래스만 쓴다.
  const calm = () => reduced() || !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  const ENG_ST = { OBSERVED: ["확인됨", "ok"], OBSERVED_ZERO: ["확인됨(0)", "ok"], COMPANY_REPORTED: ["기업 기재", "info"], COMPANY_QUOTE: ["기업 기재", "info"], ASSUMED: ["정책 기준 50점", "warn"],
    REFERENCE_ONLY: ["참고치", "info"], REFERENCE_PROVISIONAL: ["참고(잠정)", "info"], PROVISIONAL: ["잠정", "info"], PARTIAL_SAMPLE: ["일부 표본", "info"], PARTIAL: ["일부", "info"], IDENTITY: ["기준 통화", "muted"],
    REVIEW_REQUIRED: ["검토 필요", "warn"], FETCH_ERROR: ["검색 불가", "bad"], KEY_NOT_CONFIGURED: ["키 없음", "bad"], INVALID_DATA: ["자료 오류", "bad"], MISSING: ["자료 없음", "muted"], INSUFFICIENT: ["자료 부족", "muted"],
    WINDOW_UNAVAILABLE: ["비교기간 미확정", "muted"], NOT_VERIFIED: ["미확인", "muted"], NOT_COMPARABLE: ["비교 불가", "muted"], INSUFFICIENT_COMPARISON: ["비교 보류", "muted"], OK: ["확인됨", "ok"], RECEIVED: ["수신", "ok"],
    FIXED_OFFSET_ONLY: ["확인", "info"], DECLARED_UNVERIFIED: ["기재·미확인", "muted"], INCOMPATIBLE_SCOPE: ["범위 밖", "muted"],
    DOCUMENT_METADATA_INCOMPLETE: ["기재 누락", "warn"], COMPANY_REPORTED_UNVERIFIED: ["기업 기재·미확인", "muted"], DATASET_NOT_LISTED: ["자료 목록 없음", "muted"],
    DATASET_LISTED_NO_OBSERVATION: ["관측 없음", "muted"], DOCUMENT_SCOPE_MISMATCH: ["범위 불일치", "muted"], CALCULATED_REFERENCE: ["계산됨", "ok"], UNVERIFIED: ["미확인", "muted"],
    TARIFF_MISSING: ["관세 자료 없음", "muted"], COMPARABLE: ["비교 가능", "ok"], PENDING_METHODOLOGY: ["산식 보류", "muted"],
    // (2026-09-27) 엔진 상태 코드가 영어 그대로 보이던 것
    READ: ["원문 읽음", "ok"], READY: ["준비됨", "ok"], PRESENT: ["있음", "ok"], COMPLETED_OBSERVED: ["관측 완료", "ok"], APPROVED_PARTIAL: ["일부 승인", "muted"],
    CALENDAR_UNVERIFIED: ["달력 미확인", "muted"], VALUATION_UNVERIFIED: ["평가기준 미확인", "muted"], FORMULA_NOT_VERIFIED: ["산식 미검증", "muted"],
    PROPOSED_OR_UNVERIFIED: ["제안·미확인", "muted"], NAME_CANDIDATE: ["이름 후보", "warn"], CANDIDATE_NOT_APPLICABILITY: ["후보(적용 판정 아님)", "muted"],
    LEGACY_VALUES: ["옛 양식 값", "muted"], DUPLICATE_ID: ["ID 중복", "bad"], MISSING_ID: ["ID 누락", "bad"], INVALID_SCHEMA: ["양식 오류", "bad"], INVALID_SCORE_INPUT: ["점수 입력 오류", "bad"] };
  const engSt = (st) => { const e = ENG_ST[st] || [st ? String(st) : "—", "muted"]; return `<span class="jd-st jd-st-${e[1]}">${esc(e[0])}</span>`; };
  const engVal = (v, unit) => {
    if (v == null || v === "") return NA;
    if (typeof v === "object") return Object.entries(v).map(([k, x]) => `${hsDot(k)} ${num(x, 2)}%`).join(" · ");
    if (!fin(v)) return String(v);
    if (unit === "USD") return usd(+v);
    if (unit === "ratio" || unit === "비율") return pct(+v * 100);
    if (unit === "%") return num(v, 1) + "%";
    return num(v, Math.abs(v) < 10 && v % 1 ? 2 : 0) + (unit ? " " + unit : "");
  };
  const ENG_HEAD = {
    regulation: ["규제 관문 · 확인 후보", "통제번호·수입규제·거래 상대 이름 후보를 보여 줍니다. 후보는 판정이 아니며 규제는 점수에 더하지 않는 별도 관문입니다."],
    market: ["시장성 · 수입시장 규모와 성장", "대세계 수입액·한국 수출·성장률을 배점 40으로 평가합니다. 누락 월은 0으로 채우지 않습니다."],
    price: ["가격 · 제품원가 여지와 환율", "희망판매가에서 제품원가를 뺀 여지를 배점 20으로 평가합니다. 통계 단가·관세는 참고치입니다."],
    logistics: ["물류 · 공급·출고 준비", "30일 공급가능량·출고 준비기간·국제운송 조건을 배점 10으로 평가합니다. 운송비는 관세청 보도자료 참고치입니다."],
    stability: ["안정성 · 수입 변동성과 급감", "36개월 월간 수입의 변동계수·급감 빈도를 배점 10으로 평가합니다. 과거 변동이며 미래 손실 확률이 아닙니다."],
  };
  const engD = (key) => (current && current.engine_detail && current.engine_detail[key]) || { components: [], charts: {}, checks: [], warnings: [], sources: [] };
  function engMainChart(key, d) {
    const ch = d.charts || {}, has = (a) => Array.isArray(a) && a.some((x) => x && x.v != null);
    if (key === "market") return has(ch.imports) ? panel("chart", "월간 대세계 수입액 (USD)", `UN Comtrade · ${ch.imports.length}개월 중 ${ch.imports.filter((x) => x.v != null).length}개월 관측`, srcChip("Comtrade"), canvas3("eng-market-imports", "월간 대세계 수입액 추이")) : panel("chart", "월간 대세계 수입액", "자료 부족", srcChip("Comtrade"), noChart("월간 수입 관측이 없습니다 (API 키·발표 지연 확인)"));
    if (key === "stability") return has(ch.imports) ? panel("chart", "36개월 월간 수입액 (USD)", "변동계수·급감 계산 기간 · 빈 달은 자료 없음", srcChip("Comtrade"), canvas3("eng-stability-imports", "36개월 월간 수입액")) : panel("chart", "36개월 월간 수입액", "자료 부족", srcChip("Comtrade"), noChart("비교기간의 월간 수입 관측이 없습니다"));
    if (key === "price") return has(ch.fx) ? panel("chart", "원/달러 환율 (매매기준율)", `한국은행 ECOS 일별 · ${ch.fx.length}일`, srcChip("ECOS"), canvas3("eng-price-fx", "원/달러 환율 추이")) : panel("chart", "원/달러 환율", "자료 부족", srcChip("ECOS"), noChart("환율 관측이 없습니다 (ECOS API 키 확인)"));
    if (key === "logistics") return ch.freight && Object.keys(ch.freight).length ? panel("chart", "해상 수출 운송비 (노선별)", "관세청 보도자료 · 천원/2TEU · 참고치", srcChip("관세청"), canvas3("eng-logistics-freight", "노선별 해상 수출 운송비")) : panel("chart", "해상 수출 운송비", "자료 부족", srcChip("관세청"), noChart("이 대상국 노선의 운송비 참고치가 없습니다"));
    return panel("chart", "규제 확인 후보 수", "HSK 연계표 · KOTRA 수입규제 · ITA CSL · 기업 증빙 목록", srcChip("보유 원문"), has(ch.counts) ? canvas3("eng-regulation-counts", "규제 확인 후보 수") : noChart("후보 수를 확인하지 못했습니다"));
  }
  function engSideChart(key, d) {
    const ch = d.charts || {};
    if (key === "market" && (ch.growth || []).length) return panel("chart", "수입 성장률", "누계 전년동기 · 최근 3개월 전년동기 · 3년 CAGR", srcChip("계산값"), canvas3("eng-market-growth", "수입 성장률"));
    if (key === "stability" && (ch.changes || []).some((x) => x.v != null)) return panel("chart", "전월 대비 변화율", "−20% 이하 급감 달은 진하게 표시", srcChip("계산값"), canvas3("eng-stability-changes", "전월 대비 수입 변화율"));
    if (key === "regulation" && (d.candidates || []).length)
      return panel("list", "HSK 통제번호 연결 후보", `${d.candidates.length}개 HSK · 후보이며 해당 판정 아님`, srcChip("HSK 연계표"), `<div class="jd-list">${d.candidates.slice(0, 12).map((c) => `<div class="jd-list-row"><span class="jd-list-name">${esc(c.name || "품목명 없음")} <small class="jd-dim">HSK ${esc(c.hsk || "")}</small></span><span class="jd-list-meta">${esc(c.codes.slice(0, 3).join(", "))}${c.codes.length > 3 ? ` 외 ${c.codes.length - 3}` : ""}</span></div>`).join("")}</div>`);
    if ((d.components || []).length) return panel("chart", "적합도 항목별 점수", `0~100점 · 회색은 정책 기준 50점(근거 없음)`, srcChip("참고 적합도 v1"), canvas3(`eng-${key}-components`, "적합도 항목별 점수"));
    return "";
  }
  function engComponentsHTML(key, d, withChart) {
    if (key === "regulation") return "";
    const comps = d.components || [];
    if (!comps.length) return panel("table", "적합도 항목", "이 영역의 항목이 없습니다", "", emptyBox("엔진이 이 영역의 항목을 만들지 않았습니다."));
    const rows = comps.map((c) => `<tr title="${esc(c.formula || "")}"><td>${esc(c.label)}</td><td>${esc(engVal(c.value, c.unit))}${c.period ? `<br><small class="jd-dim">${esc(c.period)}</small>` : ""}</td><td><b>${fin(c.score) ? num(c.score, 1) : NA}</b></td><td>${fin(c.weight) ? num(c.weight, 0) : NA} → ${fin(c.contribution) ? num(c.contribution, 2) : NA}</td><td>${engSt(c.status)}</td></tr>`).join("");
    return panel("table", `적합도 항목 · 참고점수 ${fin(d.score) ? num(d.score, 1) : NA}/100`, `배점 ${d.raw_max} 중 ${fin(d.raw_score) ? num(d.raw_score, 1) : NA}점 · 근거 반영률 ${fin(d.coverage_pct) ? num(d.coverage_pct, 0) : NA}% · 행에 마우스를 올리면 산식`, srcChip("참고 적합도 v1"),
      (withChart ? canvas3(`eng-${key}-components`, "적합도 항목별 점수") : "") + `<div class="jd-table-wrap"><table class="jd-data-table"><thead><tr><th>항목</th><th>값</th><th>점수</th><th>배점 → 기여</th><th>상태</th></tr></thead><tbody>${rows}</tbody></table></div>`);
  }
  // (junhee) 2026-09-27 입력 결측(업로드 파일의 빈 칸·빠진 시트): 어느 셀이 비었고 점수에 어떤 영향이 있는지
  // 입력 결측(업로드 파일의 빈 칸·빠진 시트): 어느 셀이 비었고 점수에 어떤 영향이 있는지 — 목록 카드 안의 한 구역
  function engMissingRows(key) {
    const miss = (current && current.engine && current.engine.missing) || null;
    if (!miss) return "";
    const area = { price: /^가격/, logistics: /^물류|단위/ }[key];
    const fields = (miss.fields || []).filter((f) => (area ? area.test(f.impact) : key === "regulation" && !f.scored));
    const sheets = key === "regulation" || key === "market" ? [] : miss.missing_sheets || [];
    if (!fields.length && !sheets.length) return "";
    return `<p class="jd-subtable-title">입력 결측 ${fields.length + sheets.length}건 · 값을 채우지 않음</p><div class="jd-list">${fields.map((f) => `<div class="jd-list-row"><span class="jd-list-name">${esc(f.label)} <small class="jd-dim">${esc(f.cell)}</small><br><small class="jd-dim">${esc(f.impact)}</small></span>${engSt(f.scored ? "ASSUMED" : "MISSING")}</div>`).join("")}${sheets.map((m) => `<div class="jd-list-row"><span class="jd-list-name">${esc(m)} 시트 없음</span>${engSt("MISSING")}</div>`).join("")}</div>`;
  }
  const engCheckRows = (d) => { const checks = (d.checks || []).slice(0, 10); return checks.length ? `<p class="jd-subtable-title">확인 항목 ${checks.length}건</p><div class="jd-list">${checks.map((c) => `<div class="jd-list-row"><span class="jd-list-name">${esc(c.label || "확인")}${c.detail ? `<br><small class="jd-dim">${esc(String(c.detail).slice(0, 160))}</small>` : ""}</span>${engSt(c.status)}</div>`).join("")}</div>` : ""; };
  const engWarnRows = (d) => { const warns = (d.warnings || []).filter(Boolean).slice(0, 6); return warns.length ? `<p class="jd-subtable-title">해석 시 유의사항</p><ul class="jd-guide-list">${warns.map((w) => `<li>${esc(String(w).slice(0, 220))}</li>`).join("")}</ul>` : ""; };
  const engSourceRows = (d) => { const srcs = d.sources || []; return `<p class="jd-subtable-title">출처 ${srcs.length}건 · 조회일 기준</p>` + (srcs.length ? `<div class="jd-list">${srcs.slice(0, 12).map((s) => `<div class="jd-list-row"><span class="jd-list-name">${esc(s.provider || "")} · ${esc(String(s.name || "").slice(0, 60))}<br><small class="jd-dim">${esc([s.period, s.retrieved_at].filter(Boolean).join(" · "))}</small></span>${engSt(s.status || "OK")}</div>`).join("")}${srcs.length > 12 ? `<p class="jd-dim">외 ${srcs.length - 12}건</p>` : ""}</div>` : emptyBox("연결된 출처가 없습니다.")); };
  // 목록 카드 하나: 칸 높이 안에서 스크롤(.jd-ref-list) — 옆 카드와 높이를 맞춘다
  // 출처 표(전체 폭): 제공기관·자료·기간·조회일·상태
  const engSourceTable = (d) => { const srcs = d.sources || []; return panel("list", `출처 ${srcs.length}건`, "보유 원문·공식 조회 · 조회일 기준", "", table(["제공기관", "자료", "기간", "조회일", "상태"], srcs.map((s) => [esc(s.provider || "—"), `<span class="jd-wrap">${esc(String(s.name || "").slice(0, 120))}</span>`, esc(s.period || "—"), esc(String(s.retrieved_at || "—").slice(0, 10)), engSt(s.status || "OK")]), "연결된 출처가 없습니다")); };
  const engListPanel = (title, sub, body) => panel("list", title, sub, "", `<div class="jd-ref-list">${body}</div>`);
  function engListHTML(key, d) {
    return engListPanel("확인 항목 · 유의사항 · 출처", "분석 엔진이 남긴 근거", engMissingRows(key) + engCheckRows(d) + engWarnRows(d) + engSourceRows(d));
  }
  function engineDetailHTML(key, v) {
    const a = I3[key], d = engD(key), items = areaItems(key), cc = counts(items);
    const statusText = key === "regulation" ? "규제 관문 " + ((v.overview.gate && v.overview.gate.label) || "검토 필요") : !fin(d.score) || !d.coverage_pct ? "자료 부족" : `참고점수 ${num(d.score, 1)} · 반영률 ${num(d.coverage_pct, 0)}%`;
    const head = `<div class="jd-head"><div class="jd-head-text"><span class="jd-kicker">${a.kicker}</span><h2>${ENG_HEAD[key][0]}</h2><p>${ENG_HEAD[key][1]}</p></div><div class="jd-status-box"><small>SUITABILITY</small><b>${esc(statusText)}</b></div></div>`;
    // 지표 카드: 근거가 있는 적합도 항목 값을 먼저, 모자라면 확인된 엔진 지표로 채운다
    const compCards = (d.components || []).filter((c) => c.status !== "ASSUMED" && c.value != null).map((c) => ({ label: c.label, value: c.value, unit: c.unit, period: c.period, status: "확인됨" }));
    const top = [...compCards, ...items.filter((i) => i.status === "확인됨"), ...items.filter((i) => i.status !== "확인됨")].slice(0, 4);
    const side = engSideChart(key, d); // 위쪽 오른쪽: 보조 차트(없으면 적합도 항목 점수 차트)
    const kpis = top.map((i) => kpi(esc(i.label), esc(engVal(i.value, i.unit)), esc(i.period || ""), i.status)).join("");
    const extra = showItems ? `<div class="jd-items-head"><h3>세부사항 · ${esc(FACTOR_KO[key])} 항목 전체</h3></div><div class="jd-items">${areaSection(key, false)}</div>` : ""; // (2026-09-27) 왼쪽 사이드바 '세부사항'으로 켜고 끈다
    // (2026-09-27) 위·아래 두 줄 모두 같은 격자(3:2, 같은 높이). 위: 메인 차트 | 보조 차트. 아래: 적합도 항목표 | 확인 항목·유의사항·출처(스크롤)
    // (2026-09-27) 아래 두 줄: [적합도 항목표 | 확인 항목·유의사항] + [출처 표(전체 폭)]. 카드 안 스크롤 없이 내용 높이만큼(jd-grow)
    const bottomLeft = key === "regulation" ? engListPanel("확인 항목", "규제 검토에 필요한 확인", engMissingRows(key) + engCheckRows(d)) : engComponentsHTML(key, d, false);
    const bottomRight = key === "regulation" ? engListPanel("해석 시 유의사항", "규제 후보를 읽을 때", engWarnRows(d)) : engListPanel("확인 항목 · 유의사항", "분석 엔진이 남긴 근거", engMissingRows(key) + engCheckRows(d) + engWarnRows(d));
    const row = (l, r, grow) => `<div class="jd-detail-grid five${grow ? " jd-grow" : ""}"><div class="jd-col span3">${l}</div><div class="jd-col span2">${r}</div></div>`; // grow: 내용 높이만큼(세부 목록)
    const wide = (body) => `<div class="jd-detail-grid five jd-grow"><div class="jd-col jd-span-all">${body}</div></div>`;
    return `<div class="jd-detail${showItems ? " jd-with-items" : ""}" data-key="${key}">${infobarHTML(v)}${head}<div class="jd-kpis four">${kpis}</div>${row(engMainChart(key, d), side || engListHTML(key, d))}${row(bottomLeft, bottomRight, true)}${wide(engSourceTable(d))}${extra}
      <div class="jd-foot"><span><i class="ph ph-info"></i>분석 엔진(참고 적합도 v1) · 자료 없음·조회 실패는 값을 채우지 않고 상태로 표시 · 수출 성공확률이 아님</span><span class="jd-foot-right">${esc(v.meta.file)}</span></div></div>`;
  }
  // ---- 모션: 선 그리기 + 면 채우기 / 막대 차오르기 / 최신점 맥박
  function drawInLine(n) {
    if (calm()) return false;
    const step = Math.max(8, Math.min(45, 1200 / Math.max(1, n)));
    const bottom = (ctx) => ctx.chart.scales.y.getPixelForValue(ctx.chart.scales.y.min);
    const prevY = (ctx) => { if (ctx.index === 0) return bottom(ctx); const p = ctx.chart.getDatasetMeta(ctx.datasetIndex).data[ctx.index - 1]; const y = p ? p.getProps(["y"], true).y : NaN; return Number.isFinite(y) ? y : bottom(ctx); };
    const delay = (flag) => (ctx) => { if (ctx.type !== "data" || ctx[flag]) return 0; ctx[flag] = true; return ctx.index * step; };
    return { x: { type: "number", easing: "linear", duration: step, from: NaN, delay: delay("xStarted") }, y: { type: "number", easing: "easeOutQuad", duration: step * 3, from: prevY, delay: delay("yStarted") } };
  }
  // (junhee) 2026-09-28 물류 운송비 차트용: 점은 제자리에 두고 그리는 영역을 왼쪽→오른쪽으로 일정한 속도로 드러낸다(ms 동안).
  // 점이 적고 세로축이 0에서 시작하지 않아 점마다 위아래로 크게 튀던(뻑뻑하던) 모션을, 다른 차트의 선 그리기 속도·길이(약 1.2초)에 맞춘다.
  function revealPlugin(ms) {
    return {
      id: "jdReveal",
      install(chart) {
        chart.$jdReveal = 0;
        const t0 = performance.now();
        const tick = (t) => { if (!chart.canvas || !chart.ctx) return; chart.$jdReveal = Math.min(1, (t - t0) / ms); chart.draw(); if (chart.$jdReveal < 1) rafs.push(requestAnimationFrame(tick)); };
        rafs.push(requestAnimationFrame(tick));
      },
      beforeDatasetsDraw(chart) { if (!(chart.$jdReveal < 1)) return; const a = chart.chartArea; chart.ctx.save(); chart.ctx.beginPath(); chart.ctx.rect(a.left - 6, a.top - 12, (a.right - a.left + 12) * chart.$jdReveal, a.bottom - a.top + 24); chart.ctx.clip(); },
      afterDatasetsDraw(chart) { if (chart.$jdReveal < 1) chart.ctx.restore(); },
    };
  }
  const growBars = () => (calm() ? false : { duration: 900, easing: "easeOutQuart", delay: (ctx) => (ctx.type === "data" && ctx.mode === "default" ? ctx.dataIndex * 90 + ctx.datasetIndex * 60 : 0) });
  function pulse(data, col) {
    let last = -1;
    data.forEach((x, i) => { if (x != null) last = i; });
    return { label: "최신 관측", data: data.map((x, i) => (i === last ? x : null)), borderColor: col, backgroundColor: col, showLine: false, pointRadius: 5, pointHoverRadius: 7, order: -1,
      animations: calm() ? false : { radius: { duration: 1200, easing: "easeInOutSine", from: 3.5, to: 7.5, loop: true } } };
  }
  const areaLine = (label, data, col) => ({ label, data, borderColor: col, backgroundColor: col + "26", fill: "origin", tension: 0.35, borderWidth: 2.2, pointRadius: 0, pointHoverRadius: 4, spanGaps: false });
  function engOpts(n, extra) {
    return i3Opts((o, font) => { o.animations = drawInLine(n); o.plugins.legend.labels.filter = (it) => it.text !== "최신 관측"; o.interaction = { intersect: false, mode: "index" }; return extra ? extra(o, font) : o; });
  }
  // (junhee) 2026-09-28 차트 안 글자(캔버스라 화면 번역기가 닿지 않음)를 현재 언어로. 언어를 바꾸면 workspace.js 가 탭을 다시 그려 차트도 다시 만든다.
  // '최신 관측'은 범례·툴팁 걸러내기 조건이라 번역하지 않는다.
  const cT = (s) => (window.AXPI18n && AXPI18n.language !== "ko" && s != null ? AXPI18n.t(String(s)) : s);
  function engineChart(id) {
    if (!isEngine() || !id || id.indexOf("eng-") !== 0) return null;
    const parts = id.split("-"), key = parts[1], name = parts[2], d = engD(key), ch = d.charts || {}, col = color(key);
    if (name === "imports") {
      const rows = ch.imports || [], data = rows.map((r) => (r.v == null ? null : r.v / 1e6));
      return { type: "line", data: { labels: rows.map((r) => ymShort(r.m)), datasets: [areaLine(cT("대세계 수입액 (USD M)"), data, col), pulse(data, col)] },
        options: engOpts(rows.length, (o, font) => { o.scales.y.title = { display: true, text: "USD M", font }; o.plugins.tooltip.filter = (c) => c.dataset.label !== "최신 관측"; o.plugins.tooltip.callbacks = { label: (c) => `${c.dataset.label}: ${c.parsed.y == null ? cT("자료 없음") : num(c.parsed.y, 1)}` }; return o; }) };
    }
    if (name === "fx") {
      const rows = ch.fx || [], data = rows.map((r) => r.v);
      return { type: "line", data: { labels: rows.map((r) => String(r.d || "").slice(5)), datasets: [areaLine(cT("원/달러"), data, col), pulse(data, col)] },
        options: engOpts(rows.length, (o, font) => { o.scales.y.title = { display: true, text: "KRW/USD", font }; o.scales.y.beginAtZero = false; o.plugins.tooltip.filter = (c) => c.dataset.label !== "최신 관측"; return o; }) };
    }
    if (name === "freight") {
      const routes = Object.entries(ch.freight || {}), months = [...new Set(routes.flatMap((e) => e[1].map((r) => r.m)))].sort(), tints = [col, PALETTE2[key] || "#94a3b8", "#64748b", "#0ea5e9"];
      const sets = routes.map((e, i) => { const by = Object.fromEntries(e[1].map((r) => [r.m, r.v])); return areaLine(cT(e[0]), months.map((m) => (m in by ? by[m] : null)), tints[i % tints.length]); });
      if (sets.length) sets.push(pulse(sets[0].data, tints[0]));
      const reveal = calm() ? null : revealPlugin(1200); // (junhee) 2026-09-28 다른 차트와 같은 부드러운 그리기
      return { type: "line", data: { labels: months.map(ymShort), datasets: sets }, plugins: reveal ? [reveal] : [], options: engOpts(months.length, (o, font) => { o.scales.y.title = { display: true, text: cT("천원/2TEU"), font }; o.scales.y.beginAtZero = false; o.plugins.tooltip.filter = (c) => c.dataset.label !== "최신 관측"; if (reveal) o.animations = { x: false, y: false }; return o; }) };
    }
    if (name === "growth") {
      const g = ch.growth || [];
      return { type: "bar", data: { labels: g.map((x) => (x.v == null ? [cT(x.label), cT("자료 부족")] : cT(x.label))), datasets: [{ label: cT("성장률 %"), data: g.map((x) => x.v), backgroundColor: g.map((x) => (x.v != null && x.v < 0 ? "#f43f5e" : col)), borderRadius: 7, maxBarThickness: 34 }] },
        options: i3Opts((o) => { o.animation = growBars(); o.plugins.legend.display = false; return o; }) };
    }
    if (name === "changes") {
      const c = ch.changes || [];
      return { type: "bar", data: { labels: c.map((x) => ymShort(x.m)), datasets: [{ label: cT("전월 대비 %"), data: c.map((x) => x.v), backgroundColor: c.map((x) => (x.drop ? "#e11d48" : col + "99")), borderRadius: 3 }] },
        options: i3Opts((o) => { o.animation = growBars(); o.plugins.legend.display = false; return o; }) };
    }
    if (name === "counts") {
      const c = ch.counts || [];
      return { type: "bar", data: { labels: c.map((x) => cT(x.label)), datasets: [{ label: cT("후보 수"), data: c.map((x) => x.v), backgroundColor: c.map((x, i) => [col, PALETTE2[key], "#fb7185", "#94a3b8"][i % 4]), borderRadius: 7, maxBarThickness: 40 }] },
        options: i3Opts((o) => { o.indexAxis = "y"; o.animation = growBars(); o.plugins.legend.display = false; o.scales.x.grid = { color: "#F1F5F9" }; o.scales.y.grid = { display: false }; return o; }) };
    }
    if (name === "components") {
      const comps = d.components || [], tone = { ASSUMED: "#cbd5e1", COMPANY_REPORTED: PALETTE2[key] || col };
      return { type: "bar", data: { labels: comps.map((x) => cT(x.label)), datasets: [{ label: cT("항목 점수 (0~100)"), data: comps.map((x) => x.score), backgroundColor: comps.map((x) => tone[x.status] || col), borderRadius: 6, maxBarThickness: 18 }] },
        options: i3Opts((o) => { o.indexAxis = "y"; o.animation = growBars(); o.plugins.legend.display = false; o.scales.x = { min: 0, max: 100, grid: { color: "#F1F5F9" }, ticks: o.scales.x.ticks }; o.scales.y.grid = { display: false }; return o; }) };
    }
    return null;
  }
  function drawDetailCharts(root) {
    if (!window.Chart) return;
    root.querySelectorAll("canvas.jd-detail-chart").forEach((canvas) => { const conf = engineChart(canvas.dataset.chart) || i3Chart(canvas.dataset.chart) || detailChart(canvas.dataset.chart); /* (junhee) 엔진 차트 먼저 */ if (!conf || !ctx2d(canvas)) return; try { charts.push(new Chart(canvas, conf)); } catch (e) { console.error("JunheeDashboard chart:", canvas.dataset.chart, e); } });
  }

  // ---------------------------------------------------------------- 창 크롬에 넣는 요소 · 대화상자
  function ensureBarActions() {
    const bar = document.querySelector(".context-bar");
    if (!bar || bar.querySelector(".jd-bar-actions")) return;
    const box = document.createElement("div");
    box.className = "jd-bar-actions";
    box.innerHTML = `<button type="button" class="jd-bar-btn" data-action="weights" aria-label="가중치 설정"><i class="ph ph-sliders-horizontal"></i><span>가중치 설정</span></button><button type="button" class="jd-bar-btn primary" data-action="report" aria-label="보고서 다운로드"><i class="ph ph-download-simple"></i><span>보고서</span></button>`;
    bar.appendChild(box);
    if (window.AXPI18n && typeof AXPI18n.translateDOM === "function") AXPI18n.translateDOM(box);
  }
  const closeDialog = (d) => { if (!d) return; if (typeof d.close === "function") { if (d.open) d.close(); } else d.removeAttribute("open"); }; // dialog 미지원 환경(jsdom) 보호
  function dialogEl(id, cls, titleHTML) {
    let d = document.getElementById(id);
    if (d) return d;
    d = document.createElement("dialog"); d.id = id; d.className = "modal small " + cls;
    d.innerHTML = `<div class="modal-title">${titleHTML}<button type="button" class="icon-btn jd-close" aria-label="닫기"><i class="ph ph-x"></i></button></div><div class="jd-dialog-body"></div>`;
    document.body.appendChild(d);
    d.querySelector(".jd-close").onclick = () => closeDialog(d);
    d.addEventListener("click", (e) => { if (e.target === d) closeDialog(d); });
    return d;
  }
  function openQuality() { const d = dialogEl("jd-quality-dialog", "jd-quality", `<div><span class="eyebrow">DATA QUALITY</span><h2>결측·오류 목록</h2></div>`); d.querySelector(".jd-dialog-body").innerHTML = qualityHTML(); if (typeof d.showModal === "function") d.showModal(); }
  function guideHTML() {
    // (junhee) 2026-09-27 업로드 가이드 정리: 올리는 방법 → 입력 항목 → 분석 가능 대상국·HS → 판단 기준 → 빈 칸 처리 → 샘플 (기존 스타일 클래스만 사용)
    const hsGroups = ENGINE_HS.map(([g, list]) => `<li><b>${esc(g)}</b> ${list.length}개 — ${list.slice(0, 3).map(([h, n]) => `${esc(hsDot(h))} ${esc(n)}`).join(", ")}${list.length > 3 ? " 등" : ""}</li>`).join("");
    const samples = [["가온반도체", "대형 종합 메모리 제조사형"], ["누리하이테크", "HBM 특화 제조사형"], ["미리내전자", "가격·수량·출고기간을 비워 둔 빈 칸(결측) 예시"]]
      .map(([c, k]) => `<li><b>${esc(c)}</b> — ${esc(k)}</li>`).join("");
    return `<p class="jd-guide-dl-row"><a class="button primary jd-guide-dl" href="${TEMPLATE_URL}" download><i class="ph ph-download-simple"></i>간편입력 양식(엑셀) 내려받기</a><span class="jd-dim">한 파일에 제품 한 가지</span></p>
      <h4 class="jd-guide-h">1. 올리는 방법</h4>
      <ol class="jd-guide-list">
        <li>양식을 내려받아 <b>제품명·제품 설명</b>과 <b>작성기준일</b>을 채웁니다. 모르는 칸은 비워 두어도 됩니다.</li>
        <li>바탕화면 <b>기업 파일 업로드</b> 아이콘이나 위젯 <b>기업 분석 데이터 업로드</b>에 엑셀을 올립니다. (.xlsx·.xls, 20 MB 이하)</li>
        <li>기업명·HS 코드·대상국을 고르면 <b>종합 수출적합도</b>가 계산됩니다. 사이드바에서 대상국·HS를 바꾸면 같은 파일로 다시 계산합니다.</li>
      </ol>
      <p class="jd-dim">기존 상세 양식(8시트)도 올릴 수 있습니다. 분석 결과는 로그인한 계정에 저장됩니다.</p>
      <h4 class="jd-guide-h">2. 입력 항목</h4>
      ${table(["항목", "구분", "쓰임"], [["제품명 · 제품 설명", "필수", "분석 대상 제품 · 규제 후보 검토"], ["작성기준일", "필수", "가격·공급 계획은 작성일부터 30일만 반영"], ["단위원가 · 희망판매단가 (+통화)", "선택", "가격 평가"], ["희망수출수량", "선택", "물류: 30일 희망물량 충족"], ["30일 공급가능수량 · 출고준비기간(일)", "선택", "물류: 공급·출고 준비"], ["제조국 · 판매단위", "선택", "가격·수량 단위"], ["희망거래조건 · 사양서 · 인증자료 · 추가 설명", "선택", "규제·서류 검토 참고"]])}
      <h4 class="jd-guide-h">3. 분석할 수 있는 대상국 · HS 코드</h4>
      <ul class="jd-guide-list">
        <li><b>대상국 ${ENGINE_COUNTRIES.length}개</b> — ${ENGINE_COUNTRIES.map(([, n]) => esc(n)).join(" · ")}</li>
        ${hsGroups}
      </ul>
      <h4 class="jd-guide-h">4. 판단 기준 (참고 적합도 v1)</h4>
      <ul class="jd-guide-list">
        <li>시장성 40 · 가격 20 · 물류 10 · 안정성 10 = 80점을 100점으로 환산합니다. <b>규제는 점수에 더하지 않고</b> 별도 관문으로 봅니다.</li>
        <li>근거가 없는 항목은 정책 기준 50점으로 계산하고, <b>근거 반영률</b>을 함께 표시합니다.</li>
        <li>70점 이상 조건부 검토 유망 · 50점 이상 조건부 검토 · 50점 미만 준비 보완 필요. 근거 배점이 40 미만이면 판단 근거 부족입니다. <b>수출 성공확률이 아닙니다.</b></li>
      </ul>
      <h4 class="jd-guide-h">5. 빈 칸(결측) 처리</h4>
      <ul class="jd-guide-list">
        <li>빈 칸은 0이나 임의 값으로 채우지 않고 <b>자료 부족</b>으로 둡니다.</li>
        <li>분석 전에 빈 칸의 셀 위치와 점수 영향을 보여 주고 진행 여부를 묻습니다. 결과 화면에서는 종합 탭과 세부사항에 <b>입력 결측</b>으로 표시합니다.</li>
      </ul>
      <h4 class="jd-guide-h">6. 바탕화면 샘플 파일</h4>
      <ul class="jd-guide-list">${samples}</ul>
      <p class="jd-dim">샘플은 모두 가상 기업이며 기본 조건은 미국 · HS 8542.32입니다. 공개 통계는 조회 시점의 자료입니다.</p>`;
  }
  function openGuide() {
    const d = dialogEl("jd-guide-dialog", "jd-guide", `<div><span class="eyebrow">UPLOAD GUIDE</span><h2>기업 데이터 업로드 가이드</h2></div>`), body = d.querySelector(".jd-dialog-body");
    body.innerHTML = guideHTML();
    if (typeof d.showModal === "function") d.showModal();
    body.scrollTop = 0; // 다시 열면 맨 위부터
  }
  function confirm(opts = {}) {
    return new Promise((resolve) => {
      let d = document.getElementById("jd-confirm-dialog");
      if (!d) { d = document.createElement("dialog"); d.id = "jd-confirm-dialog"; document.body.appendChild(d); }
      d.className = "modal small jd-confirm" + (opts.wide ? " jd-confirm-wide" : "");
      d.innerHTML = `<div class="modal-title"><div><span class="eyebrow">${esc(opts.eyebrow || "CONFIRM")}</span><h2>${esc(opts.title || "확인")}</h2></div><button type="button" class="icon-btn jd-cancel" aria-label="닫기"><i class="ph ph-x"></i></button></div>
        <p class="modal-description jd-confirm-msg">${esc(opts.message || "")}</p>${opts.html ? `<div class="jd-confirm-html">${opts.html}</div>` : ""}
        <div class="modal-actions"><button type="button" class="button secondary jd-cancel">${esc(opts.cancel || "취소")}</button><button type="button" class="button primary jd-ok${opts.danger ? " jd-danger" : ""}">${esc(opts.ok || "확인")}</button></div>`;
      let done = false;
      const finish = (v) => { if (done) return; done = true; closeDialog(d); resolve(v); };
      d.querySelectorAll(".jd-cancel").forEach((b) => (b.onclick = () => finish(false)));
      d.querySelector(".jd-ok").onclick = () => finish(true);
      d.onclose = () => finish(false);
      d.onclick = (e) => { if (e.target === d) finish(false); };
      if (typeof d.showModal === "function") d.showModal(); else d.setAttribute("open", "");
      const cancelBtn = d.querySelector(".modal-actions .jd-cancel");
      if (cancelBtn) cancelBtn.focus();
    });
  }
  // 업로드 시 결측·오류 확인: 어느 시트·항목인지 보여주고 "그래도 진행" 을 받는다. 결측이 없으면 바로 true.
  async function qualityGate(companyId) {
    let doc;
    try { doc = await peek(companyId); } catch {
      await confirm({ eyebrow: "DATA CHECK", title: "파일 검증 결과를 불러오지 못했습니다", message: "결측치·오류를 확인할 수 없어 분석을 시작하지 않았습니다. 잠시 후 다시 시도해 주세요.", ok: "확인", cancel: "닫기" });
      return false;
    }
    const q = (doc.common && doc.common.data_quality) || {}, issues = q.issues || [];
    if (!issues.length) return true;
    const ic = q.issue_counts || {};
    const sum = `<p class="jd-gate-sum">${ic.error ? `<span class="jd-st jd-st-bad">오류 ${ic.error}</span>` : ""}${ic.warn ? `<span class="jd-st jd-st-warn">결측 ${ic.warn}</span>` : ""}${ic.info ? `<span class="jd-st jd-st-muted">참고 ${ic.info}</span>` : ""}<span class="jd-dim">유효 ${q.rows_valid}/${q.rows_total}행 · 합계 제외 ${q.rows_excluded_from_totals || 0}행</span></p>`;
    return confirm({ eyebrow: "DATA CHECK", title: "결측치·오류가 있는 파일입니다", wide: true,
      message: `${doc.file_name} 에 빈칸·오류가 ${issues.length}곳 있습니다. 해당 부분은 정확한 산출이 어려워 '자료 부족'·'미확인'으로 표시되고 점수·집계에서 제외됩니다(값을 채우거나 추정하지 않음). 그래도 진행하시겠습니까?`,
      html: sum + issuesHTML(q) + `<p class="jd-dim jd-mt">식별자는 앞 6개와 해당 엑셀 행 위치를 표시합니다. 등록된 기업 파일만 분석하므로 수정한 파일은 관리자가 다시 등록한 뒤 분석할 수 있습니다.</p>`,
      ok: "그래도 진행", cancel: "취소하고 파일 보완" });
  }
  function ensureGuideButton() {
    const actions = document.querySelector("#upload-dialog .modal-actions");
    if (!actions) return;
    if (!actions.querySelector(".jd-guide-btn")) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "button secondary jd-guide-btn"; b.innerHTML = `<i class="ph ph-book-open-text"></i>업로드 가이드`;
      b.onclick = openGuide;
      actions.prepend(b);
    }
    if (!actions.querySelector(".jd-tpl-btn")) {
      const a = document.createElement("a");
      a.className = "button secondary jd-tpl-btn"; a.href = TEMPLATE_URL; a.setAttribute("download", ""); a.innerHTML = `<i class="ph ph-file-xls"></i>양식 다운로드`;
      actions.prepend(a);
    }
  }
  // ---------------------------------------------------------------- 정식 서비스 문구 (workspace.html 의 시연·예시 문구를 바꾼다)
  // i18n 사전에 없는 새 문구라 요소에 data-no-translate 를 달고 언어별 문구를 직접 넣는다(언어 변경 때 다시 적용).
  const FORMAL = {
    uploadDesc: { ko: "기업 파일과 수출 조건을 선택해 분석을 시작하세요.", en: "Select a company file and export conditions to start the analysis.", zh: "选择企业文件和出口条件，开始分析。", ja: "企業ファイルと輸出条件を選んで分析を開始します。" },
    privacy: { ko: "파일은 분석 서버로 보내 분석하고, 결과를 이 작업공간에 저장합니다.", en: "Files are sent to the analysis server and the results are saved to this workspace.", zh: "文件会发送到分析服务器进行分析，结果保存在此工作区中。", ja: "ファイルは分析サーバーに送信して分析し、結果をこのワークスペースに保存します。" } /* (2026-10-05) 로그인 없이 사용 */, // (junhee) 2026-09-27 엔진 전용
    uploadNote: { ko: "샘플과 업로드 파일 모두 분석 엔진의 참고 적합도(시장성 40·가격 20·물류 10·안정성 10, 규제는 별도 관문)로 판정합니다. 첫 분석은 공개 통계 조회로 수 분 걸릴 수 있습니다.", en: "Samples and uploaded files are judged by the analysis engine's reference suitability (market 40 · price 20 · logistics 10 · stability 10, regulation as a separate gate). The first run may take a few minutes to query public statistics.", zh: "样本和上传文件均由分析引擎的参考适合度判定（市场性40·价格20·物流10·稳定性10，规制为单独关卡）。首次分析需查询公开统计，可能需要几分钟。", ja: "サンプルとアップロードファイルはすべて分析エンジンの参考適合度（市場性40・価格20・物流10・安定性10、規制は別途の関門）で判定します。初回は公開統計の照会に数分かかる場合があります。" }, // (junhee) 2026-09-27 엔진 전용
    weightNote: { ko: "기본 상태의 종합 점수는 분석 엔진 배점(시장성 40·가격 20·물류 10·안정성 10)입니다. 가중치를 바꾸면 영역 점수를 이 비율로 다시 평균한 화면 참고점수가 표시되며 엔진 등급 기준은 적용되지 않습니다. 규제 관문은 가중치와 별도입니다.", en: "By default the overall score uses the engine weights (market 40 · price 20 · logistics 10 · stability 10). Changing weights shows an on-screen reference score that re-averages the area scores; engine grade rules do not apply. The regulation gate is separate.", zh: "默认综合分数采用分析引擎配分（市场性40·价格20·物流10·稳定性10）。调整权重后显示按该比例重新平均各领域分数的界面参考分，不适用引擎等级标准。监管关口与权重无关。", ja: "初期状態の総合スコアは分析エンジンの配点（市場性40・価格20・物流10・安定性10）です。重みを変えると領域スコアをその比率で再平均した画面上の参考スコアを表示し、エンジンの等級基準は適用しません。規制ゲートは重みとは別です。" },
    helpNote: { ko: "점수와 판정은 분석 엔진이 기업 파일과 공개 통계(UN Comtrade·관세청·한국은행 ECOS·국가법령정보)로 계산합니다. 조회하지 못한 항목은 '검색 불가'·'자료 부족'으로 표시하고 값을 채우지 않습니다.", en: "Scores and verdicts are calculated by the analysis engine from the company file and public statistics (UN Comtrade, Korea Customs, Bank of Korea ECOS, national law data). Items that could not be retrieved are shown as unavailable and never filled in.", zh: "分数与判定由分析引擎根据企业文件和公开统计（UN Comtrade、韩国关税厅、韩国银行ECOS、国家法令信息）计算。未能查询的项目显示为无法检索或资料不足，不会填补数值。", ja: "スコアと判定は分析エンジンが企業ファイルと公開統計（UN Comtrade・関税庁・韓国銀行ECOS・国家法令情報）で計算します。照会できなかった項目は検索不可・資料不足と表示し、値を補完しません。" }, // (junhee) 2026-09-27 엔진 전용
    sideChip: { ko: "수출 적합도 참고 평가", en: "Export suitability reference", zh: "出口适合度参考评估", ja: "輸出適合度の参考評価" },
    sideText: { ko: "회사 자료와 공개 통계 기준 · 참고 적합도 v1", en: "Company data and public statistics · reference suitability v1", zh: "基于企业数据与公开统计 · 参考适合度 v1", ja: "企業データと公開統計に基づく · 参考適合度 v1" },
    winBadge: { ko: "참고 적합도 v1", en: "Reference suitability v1", zh: "参考适合度 v1", ja: "参考適合度 v1" },
    reportTitle: { ko: "수출 분석 보고서", en: "Export analysis report", zh: "出口分析报告", ja: "輸出分析レポート" },
    reportDesc: { ko: "현재 분석 조건과 가중치를 반영한 수출 분석 보고서입니다.", en: "Export analysis report reflecting the current conditions and weights.", zh: "反映当前分析条件和权重的出口分析报告。", ja: "現在の分析条件と重みを反映した輸出分析レポートです。" },
  };
  function formalChrome() {
    const lang = (window.AXPI18n && AXPI18n.language) || "ko", tx = (k) => FORMAL[k][lang] || FORMAL[k].ko;
    const put = (sel, key, keepIcon) => { document.querySelectorAll(sel).forEach((el) => { el.setAttribute("data-no-translate", ""); const icon = keepIcon ? el.querySelector("i") : null; el.textContent = tx(key); if (icon) el.prepend(icon); }); };
    put("#upload-dialog > .modal-description", "uploadDesc");
    put("#upload-dialog .upload-privacy", "privacy", true);
    put("#upload-dialog .demo-notice", "uploadNote");
    put("#weights-dialog .demo-notice", "weightNote");
    put("#help-dialog .demo-notice", "helpNote");
    put(".sidebar-bottom .mini-chip", "sideChip", true);
    put(".sidebar-bottom > p", "sideText");
    put("#analysis-window .window-demo", "winBadge");
    if (isEngine()) document.querySelectorAll("#analysis-window .window-demo, .sidebar-bottom > p").forEach((el) => (el.textContent = lang === "ko" ? "참고 적합도 v1 · 분석 엔진" : "Reference suitability v1 · engine")); // (junhee) 엔진 문서의 판단 기준
    put("#report-dialog .modal-title h2", "reportTitle");
    put("#report-dialog > .modal-description", "reportDesc");
    const chipIcon = document.querySelector(".sidebar-bottom .mini-chip i");
    if (chipIcon) chipIcon.className = "ph ph-seal-check";
    const dl = document.getElementById("report-download");
    if (dl) dl.setAttribute("download", "AXPORT_수출분석보고서.html");
    const frame = document.getElementById("report-preview");
    if (frame) frame.title = tx("reportTitle");
  }
  function installOnce() {
    if (installed) return;
    installed = true;
    document.addEventListener("click", (e) => {
      const q = e.target.closest('[data-jd="quality"]');
      if (q) { openQuality(); return; }
      const t = e.target.closest('[data-jd="toggle-items"]');
      if (t) { showItems = !showItems; try { localStorage.setItem("jd_show_items", showItems ? "1" : "0"); } catch {} if (cfg.onFilter) cfg.onFilter({ ...filters, rerender: true }); }
    });
    document.addEventListener("change", (e) => {
      const el = e.target.closest("[data-jd]");
      if (!el || !current) return;
      const kind = el.dataset.jd;
      if (kind === "engine-country" || kind === "engine-hs") { // (junhee) 2026-09-27 엔진 문서: 대상국·HS 를 바꾸면 같은 파일로 다시 계산
        const body = el.closest(".jd-side-body");
        // 바꾼 칸만 보낸다(대상국만 바꾸면 파일의 8·10자리 HS 를 6자리로 줄이지 않음)
        const next = kind === "engine-country" ? { country: el.value } : { hs: el.value };
        if (body) body.querySelectorAll("select").forEach((s) => (s.disabled = true));
        Promise.resolve(cfg.onEngineConditions ? cfg.onEngineConditions(next) : null).finally(() => refreshSidebar());
        return;
      }
      if (kind === "period") { const pr0 = periodRange(); setFilters({ period: el.value, from: el.value === "custom" ? filters.from || pr0.from : filters.from, to: el.value === "custom" ? filters.to || pr0.to : filters.to }); }
      else if (kind === "from" || kind === "to") setFilters({ period: "custom", [kind]: el.value });
      else if (kind === "hs") setFilters({ hs: el.value });
      else if (kind === "country") { if (!setCountry(el.value)) return; if (cfg.onFilter) cfg.onFilter({ ...filters, country: selectedCountry }); return; }
      else return;
      if (cfg.onFilter) cfg.onFilter({ ...filters, hs: filters.hs });
    });
    ensureGuideButton();
    formalChrome();
    window.addEventListener("axp:language-changed", formalChrome);
  }
  function mount(root, key) {
    destroy();
    if (!root) return;
    root.dataset.jdTab = key || "overview";
    installOnce(); ensureBarActions(); ensureGuideButton();
    renderSidebar(view());
    if (!key || key === "overview") { drawGauge(root); countUp(root); prevN = current ? confirmed().n : null; prevNums = snapshot(); }
    else { drawDetailCharts(root); countUp(root); }
  }
  function replay() { prevN = null; prevNums = {}; }

  window.JunheeDashboard = Object.freeze({
    SCORE_MODE, TEMPLATE_URL,
    configure(opts) { cfg = { ...cfg, ...(opts || {}) }; },
    load: () => loadIndex(),
    ready: () => !!index,
    entries, findByFileName, findById, identifyFile, peek, countriesOf, hsListOf, select, selectDoc, setCountry, setFilters, clear,
    filters: () => ({ ...filters }),
    period: () => { const p = periodRange(); return p ? { from: p.from, to: p.to, label: p.label, isDefault: p.isDefault } : null; },
    current: () => current,
    country: () => selectedCountry,
    calc,
    panelHTML, detailMeta, detailHTML, mount, destroy, replay, reportRows, reportHTML, confirm, qualityGate, openGuide,
    toIndex3Data, view, renderSidebar: refreshSidebar, allItemsHTML,
    itemsOn: () => showItems,
    setItems(on) { showItems = !!on; try { localStorage.setItem("jd_show_items", showItems ? "1" : "0"); } catch {} return showItems; },
    itemCount(key) { const c = counts(key && key !== "items" && key !== "overview" ? areaItems(key) : AREAS.flatMap((a) => areaItems(a.key))); return { ok: c["확인됨"], total: c.total }; },
    ENGINE_COUNTRIES, ENGINE_HS, engineHsOptions,
    isAnalyzed: (fileName) => !!(current && current.file_name === fileName),
  });
})();
