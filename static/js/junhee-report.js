"use strict";
/* (junhee) 2026-09-28 수출 분석 보고서 — juyeon 보고서 틀(juyeon/static/js/axport-report.js v0.6)을 그대로 쓰고,
   내용은 현재 분석 엔진 문서(score_source "engine")의 수출적합성 결과로 채운다.
   - CSS·섹션 순서·클래스·표 모양은 juyeon 원본 그대로(아래 css 는 원본 문자열 복사).
   - 점수·등급·근거 반영률·항목 값은 JunheeDashboard.calc() / current() 에 이미 있는 값만 쓰고 새로 계산하지 않는다.
   - juyeon 원본과 같은 한국어 문구는 axport-report-l10n.js 사전으로 번역하고, 엔진용으로 바꾼 문구는 여기서 4개 언어로 쓴다.
   - 엔진이 만든 항목 이름·계산 근거(한국어)는 원문 그대로 두고 사전에 있는 낱말만 번역된다. */
(() => {
  const E = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"})[c]);
  const num = (x, d=1) => x == null || !Number.isFinite(+x) ? "—" : (+x).toLocaleString(window.AXPI18n?.locale || "ko-KR", {minimumFractionDigits:d, maximumFractionDigits:d});
  const css = `
:root{--navy:#102642;--blue:#1960ac;--ink:#182e48;--muted:#5e7085;--border:#dde6ef;--light:#f3f7fb;--accent:#00a3b5;--amber:#a96810;--amber-bg:#fff6e7;--red:#a63c3d;--red-bg:#fff0ef}
*{box-sizing:border-box}html{background:#e9eef4}body{max-width:960px;margin:26px auto;background:white;box-shadow:0 12px 55px #1f355022;font-family:"Noto Sans KR","Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif;color:var(--ink);font-size:11px;line-height:1.63;word-break:keep-all;overflow-wrap:anywhere}
main{padding:36px 42px 46px}.brand{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--navy);padding-bottom:13px;margin-bottom:29px}.brand strong{font-size:20px;letter-spacing:-.7px;color:var(--navy)}.brand small,.meta-label,.eyebrow{font-size:9px;letter-spacing:1.4px;font-weight:800;color:var(--blue)}.brand .right{font-size:9px;text-align:right;color:var(--muted)}
.cover{min-height:1000px;display:flex;flex-direction:column}.eyebrow{margin:1px 0 9px}.cover h1{font-size:34px;letter-spacing:-1.3px;line-height:1.28;margin:0 0 8px;color:var(--navy)}.subtitle{margin:0 0 26px;font-size:13px;color:var(--muted)}.cover-meta{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:0 0 20px}.meta-box{background:var(--light);border:1px solid var(--border);padding:11px 13px;border-radius:8px;min-height:56px}.meta-box .meta-label{display:block;margin-bottom:5px}.meta-box strong{font-size:11px;line-height:1.5}
.decision{border:1px solid #e4c78d;background:var(--amber-bg);padding:19px 19px 17px;border-radius:10px;margin:2px 0 20px;break-inside:avoid}.decision.red{background:var(--red-bg);border-color:#ecc4c4}.decision .flag{display:inline-block;font-size:10px;border:1px solid currentColor;border-radius:99px;padding:2px 9px;color:var(--amber);font-weight:800;margin-bottom:7px}.decision.red .flag{color:var(--red)}.decision h2{font-size:20px;color:var(--navy);margin:0 0 5px}.decision p{margin:0;font-size:11px}
.section-title{display:flex;align-items:end;gap:10px;margin:18px 0 12px;break-after:avoid}.section-title b{font-size:15px;color:var(--navy)}.section-title span{font-size:10px;color:var(--muted)}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.metric{padding:14px 15px 12px;border:1px solid var(--border);border-radius:8px;break-inside:avoid}.metric .name{color:var(--muted);font-size:10px;font-weight:700}.metric .number{color:var(--navy);font-size:20px;font-weight:800;line-height:1.6;letter-spacing:-.6px}.metric .foot{font-size:9px;color:var(--muted)}.metric .number.unrated{font-size:17px;color:var(--amber)}
.executive{margin:13px 0 0;padding:14px 17px;border-left:3px solid var(--blue);background:var(--light)}.executive strong{display:block;margin-bottom:6px}.executive ol{padding-left:17px;margin:0}.executive li{margin:0 0 6px}.executive li:last-child{margin-bottom:0}.cover-foot{margin-top:auto;border-top:1px solid var(--border);padding-top:13px;font-size:9px;color:var(--muted)}
.sheet{border-top:1px solid var(--border);padding-top:22px;margin-top:26px}.sheet-head{display:flex;gap:10px;align-items:center;margin:0 0 9px}.sheet-head .index{width:25px;height:25px;line-height:25px;text-align:center;border-radius:6px;color:#fff;background:var(--navy);font-weight:800}.sheet h2{font-size:17px;color:var(--navy);margin:0}.sheet .desc{color:var(--muted);font-size:10px;margin:0 0 14px}.subhead{color:var(--navy);font-size:12px;margin:16px 0 7px}.alert{background:var(--amber-bg);border-left:3px solid #dda446;padding:10px 13px;margin:12px 0;font-size:10px}.alert.red{background:var(--red-bg);border-color:#b94746}
.kpi-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:12px 0}.kpi{padding:11px;border:1px solid var(--border);border-radius:7px;background:var(--light)}.kpi span{font-size:9px;color:var(--muted);display:block}.kpi b{font-size:14px;color:var(--navy)}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:10px}th{text-align:left;color:var(--navy);font-size:9px;background:#eaf1f8;border-bottom:1.4px solid #a8bfd5;padding:9px 10px}td{vertical-align:top;padding:10px;border-bottom:1px solid var(--border);overflow-wrap:anywhere}tr{break-inside:avoid}thead{display:table-header-group}td.note{font-size:9px;color:var(--muted);line-height:1.5}td strong{color:var(--ink)}.status{display:inline-block;font-size:9px;font-weight:700;padding:2px 6px;border-radius:4px;background:#e9eff7;color:#244a79}.status.good{background:#e9f7f2;color:#146e56}.status.warn{background:#fff0d9;color:#a15f13}.status.bad{background:#fff0ef;color:#a23f44}.method{margin:4px 0 0;color:var(--muted);font-size:9px}.source{color:#557089;margin:3px 0 0;font-size:9px}.legend{border-radius:7px;border:1px solid var(--border);background:var(--light);padding:12px 15px;color:var(--muted);font-size:10px}.appendix{margin-top:28px}.appendix table{font-size:9.5px}.appendix td{padding:8px}.appendix .area{font-size:12px;font-weight:800;color:var(--navy);margin:20px 0 9px}.no-data{color:var(--muted)}.print-actions{padding:8px 18px;background:var(--navy);color:white;text-align:right}.print-actions button{border:0;background:#fff;color:var(--navy);padding:9px 16px;border-radius:6px;cursor:pointer;font-weight:700}footer{border-top:1px solid var(--border);padding-top:14px;margin-top:27px;font-size:9px;color:var(--muted)}
@page{size:A4 portrait;margin:13mm 12mm 15mm;@bottom-right{content:"AXPORT  /  " counter(page);font-size:8px;color:#7a8899}}@page:first{@bottom-right{content:none}} @media print{html,body{background:#fff;max-width:none;margin:0;padding:0;box-shadow:none;-webkit-print-color-adjust:exact;print-color-adjust:exact} main{padding:0}.print-actions{display:none}.cover{min-height:0;height:261mm;break-after:page;page-break-after:always}.sheet{break-before:page;margin:0;padding-top:0;border:0}.sheet+.sheet{break-before:page}.sheet-head{break-after:avoid}.appendix{break-before:page}.appendix .area{break-after:avoid}.appendix table{break-inside:auto}table{break-inside:auto}.meta-box,.metric,.decision,.executive{break-inside:avoid}.cover-foot{margin-top:auto}} @media(max-width:620px){body{margin:0}main{padding:22px 16px}.cover-meta,.kpi-strip{grid-template-columns:1fr 1fr}.metrics{grid-template-columns:1fr}.cover h1{font-size:26px}}
.coverage-wrap{padding:13px 16px;background:#f6f9fc;border:1px solid var(--border);border-radius:9px;margin:0 0 17px;break-inside:avoid}
.coverage-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:8px}.coverage-head b{font-size:12px;color:var(--navy)}.coverage-head small{font-size:9px;color:var(--muted)}
.coverage-bar{height:11px;overflow:hidden;display:flex;background:#e0e6ee;border-radius:10px}.coverage-bar>i{height:100%;display:block}.coverage-current{background:#2776b5}.coverage-proxy{background:#05939c}.coverage-old{background:#e9a946}.coverage-missing{background:#d6dce5}
.coverage-legend{display:flex;flex-wrap:wrap;gap:9px 15px;margin-top:8px;font-size:9px;color:var(--muted)}.coverage-legend i{display:inline-block;width:9px;height:9px;margin-right:5px;vertical-align:-1px;border-radius:2px}
.badge-proxy{display:inline-block;border-radius:50px;padding:2px 7px;font-size:9px;font-weight:700;color:#075e63;background:#e1f6f6;margin:0 0 0 5px}.badge-old{display:inline-block;border-radius:50px;padding:2px 7px;font-size:9px;font-weight:700;color:#975e0c;background:#fff3d8;margin:0 0 0 5px}.result-detail{font-size:9px;color:var(--muted);margin-top:5px;line-height:1.6}
.scenario{background:#f4f8fc;border:1px solid var(--border);padding:14px;border-radius:8px;margin-top:14px;break-inside:avoid}.scenario-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.scenario label{display:block;font-size:9px;color:var(--muted);font-weight:700}.scenario input{margin-top:4px;border:1px solid #cbd8e5;padding:7px;border-radius:5px;width:100%;font-size:12px}.scenario button{margin-top:11px;background:#1b5f9c;border:0;color:white;padding:9px 15px;border-radius:5px;font-weight:700;cursor:pointer}.reg-gate{border:1px solid #e4c78d;background:#fffaf0;border-radius:8px;padding:12px 15px;margin:-7px 0 12px;font-size:10px;break-inside:avoid}.reg-gate.red{background:var(--red-bg);border-color:#e7b6b6}.reg-gate b{display:block;color:var(--navy);font-size:11px;margin-bottom:3px}.reg-gate p{margin:0;color:var(--muted)}.data-note{border-left:3px solid #0a9398;background:#f1fbfb;padding:9px 12px;font-size:10px;margin:9px 0}.scenario-out{margin-top:10px;background:white;border:1px solid #d0dfed;border-radius:7px;padding:9px 12px;min-height:30px;font-size:11px;font-weight:650}.scenario-hint{font-size:9px;color:var(--muted);margin:7px 0 0}.footnote-strong{border-left:3px solid #dcab52;background:#fffaf0;padding:9px 12px;margin:10px 0;font-size:10px}
@media print{.scenario-grid,.scenario button{display:none}.scenario-out{border:0;padding:4px 0;background:none}.scenario{background:#fff}.coverage-wrap{background:#f6f9fc}} 
@media print{.cover{height:auto;min-height:0;display:block;break-inside:avoid;page-break-inside:avoid}.cover-meta{display:flex;align-items:flex-start}.cover-meta .meta-box{flex:1;min-height:0}.cover-foot{margin-top:14px}.cover .executive{padding:9px 13px}.cover .executive li{margin:0 0 2px}.cover .metrics .metric{padding:8px 10px}.cover .brand{margin-bottom:14px}.cover h1{font-size:29px;line-height:1.18}.cover .subtitle{margin-bottom:14px}.cover .cover-meta{margin-bottom:11px}.cover .decision{padding:11px 14px;margin:0 0 9px}.cover .coverage-wrap{padding:8px 12px;margin-bottom:8px}.cover .section-title{margin:7px 0}.cover .metric .foot{font-size:8px}.cover .metric .number{font-size:17px}.cover .metric .number.unrated{font-size:14px}}
`;
  const lang = () => window.AXPI18n?.language || "ko";
  // 엔진용 문구: 한국어·영어·중국어·일본어
  const L = (ko, en, zh, ja) => ({ ko, en, zh, ja })[lang()] || ko;
  const t18 = (s) => (window.AXPI18n && AXPI18n.language === lang() ? AXPI18n.t(String(s ?? "")) : String(s ?? ""));
  // 엔진 원문(회사·파일 이름, 항목 이름·계산 근거, 부족 근거 등)은 사전의 낱말 치환으로 섞이지 않게 번역 전에 자리표로 바꿔 두고, 번역 뒤 원문 그대로 되돌린다.
  let keep = [];
  const P = (html) => { keep.push(String(html)); return `${keep.length - 1}`; };
  const K = (s) => P(E(s));
  // 엔진 문구 번역(junhee-report-i18n.js 표). 표에 없는 문장은 원문 그대로
  const X = (s) => (s == null || lang() === "ko" || !window.JunheeReportI18n ? s : JunheeReportI18n.tx(String(s), lang()));
  const restore = (html) => html.replace(/(\d+)/g, (_, i) => keep[+i]);
  // 엔진이 쓰는 고정 이름표(analysis_suitability 항목·등급, engine_adapter 상태·시장 지표) — 한국어가 아닐 때만 옮긴다
  const NAMES = {
    "대세계 수입시장 규모": ["World import market size", "全球进口市场规模", "対世界輸入市場規模"],
    "한국의 해당국 수출규모": ["Korea's exports to the destination", "韩国对该国出口规模", "韓国の対象国向け輸出規模"],
    "수입 누계 성장": ["Year-to-date import growth", "进口累计增长", "輸入累計成長"],
    "수입 3년 성장": ["3-year import growth", "进口3年增长", "輸入3年成長"],
    "최근 3개월 수입 성장": ["Last 3 months import growth", "最近3个月进口增长", "直近3か月輸入成長"],
    "희망가격의 제품원가 차감 여지": ["Cost headroom in target price", "目标售价扣除产品成本的空间", "希望価格の製品原価控除余地"],
    "30일 희망물량 충족": ["30-day target volume coverage", "30天目标数量满足度", "30日希望数量の充足"],
    "출고 준비기간": ["Dispatch lead time", "出货准备期", "出荷準備期間"],
    "국제운송 실행조건": ["International transport conditions", "国际运输执行条件", "国際輸送の実行条件"],
    "수입 변동성": ["Import volatility", "进口波动性", "輸入変動性"],
    "수입 급감 빈도": ["Frequency of sharp import drops", "进口骤降频率", "輸入急減頻度"],
    "대세계 연간 수입시장 규모": ["Annual world import market size", "全球年度进口市场规模", "対世界年間輸入市場規模"],
    "한국의 해당국 연간 수출액": ["Korea's annual exports to the destination", "韩国对该国年度出口额", "韓国の対象国向け年間輸出額"],
    "수입액 누계 전년동기 증가율": ["Year-to-date import growth (YoY)", "进口额累计同比增长率", "輸入額累計の前年同期比"],
    "최근 3개월 수입액 전년동기 증가율": ["Last 3 months import growth (YoY)", "最近3个月进口额同比增长率", "直近3か月輸入額の前年同期比"],
    "수입액 3년 CAGR": ["3-year import CAGR", "进口额3年CAGR", "輸入額3年CAGR"],
    "세계 반도체 산업 매출(국가·HS 시장과 별도)": ["Global semiconductor sales (separate from country/HS market)", "全球半导体行业销售额（与国家·HS市场分开）", "世界半導体産業売上（国・HS市場とは別）"],
    "HSK 통제번호 연결 후보": ["HSK control-number candidates", "HSK管制编号关联候选", "HSK統制番号の候補"],
    "목적국·HS 수입규제 후보": ["Destination/HS import-restriction candidates", "目的国·HS进口限制候选", "輸出先・HS輸入規制の候補"],
    "거래처·최종사용자 이름 일치 후보": ["Counterparty/end-user name matches", "交易方·最终用户名称匹配候选", "取引先・最終需要者の名称一致候補"],
    "조건부 검토 유망": ["Promising, subject to review", "有条件审查·前景良好", "条件付き検討・有望"],
    "조건부 검토": ["Conditional review", "有条件审查", "条件付き検討"],
    "준비 보완 필요": ["Preparation needed", "需补充准备", "準備の補完が必要"],
    "판단 근거 부족": ["Insufficient evidence", "判断依据不足", "判断根拠不足"],
    "규제상 진행 제한": ["Restricted by regulation", "受监管限制", "規制上の進行制限"],
    "규제 요건 확인 필요": ["Regulatory requirements to confirm", "需确认监管要件", "規制要件の確認が必要"],
    "검토 필요": ["Review required", "需要审查", "要確認"],
    "보류": ["On hold", "暂缓", "保留"],
    "판정 보류": ["Verdict on hold", "暂缓判定", "判定保留"],
    "관측": ["observed", "观测", "観測"], "관측(0)": ["observed (0)", "观测（0）", "観測（0）"],
    "기업 기재": ["company entry", "企业填报", "企業記載"], "정책 기준 50점": ["policy midpoint 50", "政策基准50分", "政策基準50点"],
  };
  const nm = (s) => { const k = String(s ?? ""), ix = ["en", "zh", "ja"].indexOf(lang()); if (ix < 0) return K(k); const v = NAMES[k]; if (v) return E(v[ix]); const m = k.match(/^사용자 가중치 참고점수 \(엔진 등급: (.*)\)$/); return m ? E(L("", "User-weighted reference score (engine grade: ", "用户权重参考分（引擎等级：", "ユーザー重み参考点数（エンジン等級：")) + nm(m[1]) + E(L("", ")", "）", "）")) : K(X(k)); };
  const ST = { OBSERVED: "관측", OBSERVED_ZERO: "관측(0)", ASSUMED: "정책 기준 50점", COMPANY_REPORTED: "기업 기재" };

  function statusTag(s) {
    const tone = s === "확인됨" ? "good" : s === "검색 불가" ? "bad" : s === "검색 결과 없음" ? "" : "warn";
    return `<span class="status ${tone}">${E(s || "미확인")}</span>`;
  }
  const prettyUsd = (v) => v == null || !Number.isFinite(+v) ? "—" : (+v >= 1e9 ? "$"+num(+v/1e9,2)+"B" : +v >= 1e6 ? "$"+num(+v/1e6,2)+"M" : "$"+num(v,0));
  // 엔진 항목 값 표시: 확인된 값만, 단위는 엔진 문서 그대로
  function valueText(it) {
    if (!it || it.status !== "확인됨" || it.value == null) return "—";
    const v = it.value, u = String(it.unit || "");
    if (typeof v === "object") { const x = Object.values(v)[0]; return Number.isFinite(+x) ? num(x, 2) + "%" : "—"; }
    if (typeof v !== "number") return E(v) + (u ? " " + E(X(u)) : "");
    if (u === "USD" || /^USD \(/.test(u)) return prettyUsd(v) + (u === "USD" ? "" : " " + E(String(X(u)).replace(/^USD\s*/, "")));
    if (u === "%") return num(v, 2) + "%";
    if (u === "ratio" || u === "비율") return num(v * 100, 1) + "%";
    return num(v, Math.abs(v) < 10 && v % 1 ? 2 : Math.abs(v) < 1000 && v % 1 ? 1 : 0) + (u ? " " + E(X(u)) : "");
  }
  function appendixTable(area) {
    const rows=(area.items||[]).map(it=>`<tr><td style="width:26%"><strong>${nm(it.label)}</strong><br/>${statusTag(it.status)}</td><td style="width:17%"><strong>${P(valueText(it))}</strong></td><td style="width:20%">${[it.period?K(it.period):"",it.as_of?`기준 ${K(it.as_of)}`:""].filter(Boolean).join(" / ")||"미확인"}</td><td style="width:37%"><div>${it.source?K(X(it.source)):"출처 미확인"}</div><div class="method">${[it.basis,it.note].filter(Boolean).length?K([X(it.basis),X(it.note)].filter(Boolean).join(" / ")):"—"}</div></td></tr>`).join("");
    return `<div class="area">${E(area.title)} <span style="font-weight:400;color:#6b7e94;font-size:10px">(${area.items.length}개 지표)</span></div><table><colgroup><col style="width:26%"/><col style="width:17%"/><col style="width:20%"/><col style="width:37%"/></colgroup><thead><tr><th>항목 / 상태</th><th>표시값</th><th>기간 / 기준일</th><th>출처 / 계산 근거</th></tr></thead><tbody>${rows}</tbody></table>`;
  }
  function metric(label, f, d) {
    const good = f && f.state === "ok" && f.score != null, cov = d && d.coverage_pct;
    const value = good ? num(f.score)+" / 100" : "자료 부족";
    const badge = good && Number.isFinite(+cov) && cov < 100 ? `<span class="badge-old">${E(L(`근거 ${num(cov,0)}%`, `Evidence ${num(cov,0)}%`, `依据 ${num(cov,0)}%`, `根拠 ${num(cov,0)}%`))}</span>` : "";
    const foot = d && d.raw_max ? L(`배점 ${num(d.raw_max,0)} 중 ${num(d.raw_score,1)}점 · 근거 반영률 ${num(cov,0)}%`, `${num(d.raw_score,1)} of ${num(d.raw_max,0)} points · evidence coverage ${num(cov,0)}%`, `配分 ${num(d.raw_max,0)} 中 ${num(d.raw_score,1)} 分 · 依据反映率 ${num(cov,0)}%`, `配点 ${num(d.raw_max,0)} 中 ${num(d.raw_score,1)} 点 · 根拠反映率 ${num(cov,0)}%`) : L("자료 없음", "No data", "无数据", "データなし");
    return `<div class="metric"><div class="name">${E(label)}${badge}</div><div class="number ${!good?"unrated":""}">${value}</div><div class="foot">${E(foot)}</div></div>`;
  }
  const AREA_TITLE = {
    regulation: () => L("규제 관문 · 확인 후보", "Regulatory gate · review candidates", "监管关口 · 核查候选", "規制ゲート · 確認候補"),
    market: () => L("시장성 · 수입시장 규모와 성장", "Market · import size and growth", "市场性 · 进口市场规模与增长", "市場性 · 輸入市場の規模と成長"),
    price: () => L("가격 · 제품원가 여지와 환율", "Price · cost headroom and FX", "价格 · 产品成本空间与汇率", "価格 · 製品原価の余地と為替"),
    logistics: () => L("물류 · 공급·출고 준비", "Logistics · supply and dispatch readiness", "物流 · 供货与出货准备", "物流 · 供給・出荷準備"),
    stability: () => L("안정성 · 수입 변동성과 급감", "Stability · import volatility and sharp drops", "稳定性 · 进口波动与骤降", "安定性 · 輸入の変動と急減"),
  };
  const DOMAIN = {
    market: () => L("목적국 시장성", "Destination market", "目的国市场性", "輸出先の市場性"),
    price: () => L("가격 · 제품원가 여지", "Price · cost headroom", "价格 · 产品成本空间", "価格 · 製品原価の余地"),
    logistics: () => L("물류 · 공급·출고 준비", "Logistics · supply readiness", "物流 · 供货与出货准备", "物流 · 供給・出荷準備"),
    stability: () => L("시장 안정성", "Market stability", "市场稳定性", "市場の安定性"),
  };
  const GATE_TEXT = {
    hold: () => L("규제 확인 결과 진행 제한 사유가 있어 추가 검토 전까지 판정을 보류합니다.", "Regulatory checks found restrictions, so the verdict is on hold pending further review.", "监管核查发现限制事由，在进一步审查前暂缓判定。", "規制確認で制限事由が見つかったため、追加審査まで判定を保留します。"),
    cond: () => L("통제번호 후보·수입규제·거래 상대 이름 확인이 필요합니다. 규제는 점수에 더하지 않는 별도 관문입니다.", "Control-number candidates, import restrictions and counterparty names need review. Regulation is a separate gate and is not added to the score.", "需要核查管制编号候选、进口限制和交易对象名称。监管是不计入分数的单独关口。", "統制番号候補・輸入規制・取引相手名の確認が必要です。規制は点数に加えない別のゲートです。"),
  };

  // 엔진 문서 → 보고서 모델 (값은 대시보드가 이미 가진 것만)
  function model(opts) {
    const D = window.JunheeDashboard, cur = D && D.current(), country = D && D.country(), k = D && D.calc();
    if (!cur || !country || !k || cur.score_source !== "engine") return null;
    const items = cur.per_country[country] || {}, det = cur.engine_detail || {}, eng = cur.engine || {}, c = cur.common || {};
    const sc = (cur.score.per_country[country] || {}).overall || {}, p = (D.period && D.period()) || c.period || {};
    const hs = String(eng.hs || (c.analysis_hs6 || [])[0] || ""), gate = k.overall.gate || { key: "cond", label: "검토 필요" };
    return {
      company: cur.company_name, sample: !!(cur.sample || /(^|_)가상(_|\.)/.test(String(cur.file_name || ""))),
      country, hs, hsDot: hs.length === 6 ? hs.slice(0, 4) + "." + hs.slice(4) : hs, file: cur.file_name,
      from: p.from || "—", to: p.to || "—", asOf: eng.as_of || "—", generated: opts.generated || "",
      rule: L("참고 적합도 v1", "Reference suitability v1", "参考适合度 v1", "参考適合度 v1"),
      score: k.overall.score, verdict: k.overall.verdict ? k.overall.verdict.label : sc.grade, custom: !!k.overall.recomputed,
      cov: sc.coverage_pct != null ? sc.coverage_pct : eng.coverage_pct, weights: cur.score.weights || {},
      gate: { key: gate.key, label: gate.label, text: (GATE_TEXT[gate.key] || GATE_TEXT.cond)() },
      factors: Object.fromEntries(k.factors.map((f) => [f.key, f])), detail: det,
      areas: ["regulation", "market", "price", "logistics", "stability"].map((key) => ({ key, title: AREA_TITLE[key](), items: items[key] || [] })),
      items, gaps: (eng.gaps || []).map(String), missing: eng.missing || {}, products: c.products || [],
      quality: c.data_quality || {}, scenario: opts.scenario || {},
    };
  }

  function render(opts = {}) {
    keep = [];
    const m = model(opts);
    if (!m) return null;
    const by = m.factors, det = m.detail, spot = (area, key) => (m.items[area] || []).find((i) => i.key === key);
    const ec = spot("regulation", "export_control_candidates"), im = spot("regulation", "import_regulation_records"), cs = spot("regulation", "csl_search");
    const tariff = spot("price", "tariff_reference"), fx = spot("price", "fx_reference"), cv = spot("stability", "cv");
    const marked = m.gate.key === "hold" ? "red" : "";
    const gateTag = (s) => `<span class="status warn">${nm(s)}</span>`;
    // 영역 근거 문장: 한국어는 엔진 문장 원문, 다른 언어는 같은 엔진 항목(이름·점수·상태)으로 다시 조립
    const regN = (it) => { const x = String((it && it.unit) || "").match(/통제번호 (\d+)개/); return x ? +x[1] : it && it.value; };
    const noteOf = (key) => {
      const f = by[key] || {};
      if (lang() === "ko") return K(f.note || "");
      if (key === "regulation") {
        const g = (f.inputs && f.inputs.engine_gate) || "REVIEW_REQUIRED";
        const parts = ["export_control_candidates", "import_regulation_records", "csl_search"].map((k2) => spot("regulation", k2)).filter(Boolean)
          .map((it) => nm(it.label) + " " + (it.status === "확인됨" && it.value != null ? E(num(it.key === "export_control_candidates" ? regN(it) : it.value, 0)) : E(L("", "unconfirmed", "未确认", "未確認"))));
        return E(L("", `Treated as a gate, not a score (${g}).`, `作为关口而非分数处理（${g}）。`, `点数ではなくゲートとして扱います（${g}）。`)) + " " + parts.join(" · ");
      }
      const d = det[key];
      if (!d || !(d.components || []).length) return K(X(f.note || ""));
      return E(L("", `Evidence coverage ${num(d.coverage_pct,0)}%`, `依据反映率 ${num(d.coverage_pct,0)}%`, `根拠反映率 ${num(d.coverage_pct,0)}%`)) + " · "
        + d.components.map((c) => `${nm(c.label)} ${E(num(c.score,0))}${E(L("", " pts", "分", "点"))} (${nm(ST[c.status] || c.status)})`).join(" · ");
    };
    const cov = Number.isFinite(+m.cov) ? +m.cov : 0, gap = Math.max(0, 100 - cov), gapL = Math.max(0, 100 - Math.round(cov)); // gapL: 표시용(반올림한 근거 반영률과 합이 100)
    const W = m.weights, total = ["market", "price", "logistics", "stability"].reduce((a, key) => a + (+W[key] || 0), 0);
    const scope = m.hs ? `HS ${m.hsDot}` : "HS —";
    const allHs = [...new Set(m.products.map((p) => p.analysis_hs6).filter(Boolean))].join(", ");
    const counts = m.areas.reduce((o, a) => { a.items.forEach((it) => { o.total++; if (it.status === "확인됨") o.ok++; }); return o; }, { total: 0, ok: 0 });
    const wText = L(`시장성 ${W.market}·가격 ${W.price}·물류 ${W.logistics}·안정성 ${W.stability}`, `market ${W.market}, price ${W.price}, logistics ${W.logistics}, stability ${W.stability}`, `市场性 ${W.market}·价格 ${W.price}·物流 ${W.logistics}·稳定性 ${W.stability}`, `市場性 ${W.market}・価格 ${W.price}・物流 ${W.logistics}・安定性 ${W.stability}`);
    const txt = m.score == null
      ? L(`근거가 확인된 영역의 결과를 개별 제공합니다. 근거 반영률 ${num(cov,0)}%입니다.`, `Results are shown only for areas with evidence. Evidence coverage is ${num(cov,0)}%.`, `仅单独提供已确认依据的领域结果。依据反映率为 ${num(cov,0)}%。`, `根拠が確認された分野の結果のみ個別に示します。根拠反映率は ${num(cov,0)}% です。`)
      : L(`분석 엔진이 ${wText} 배점으로 계산한 참고 적합도입니다. 근거 반영률 ${num(cov,0)}%이며 근거가 없는 배점은 정책 기준 50점으로 계산했습니다. 수출 성공확률이나 실제 이익률을 뜻하지 않습니다.`, `Reference suitability calculated by the analysis engine with points of ${wText}. Evidence coverage is ${num(cov,0)}%; points without evidence use the policy midpoint of 50. It is not a probability of export success or an actual margin.`, `分析引擎按 ${wText} 配分计算的参考适合度。依据反映率 ${num(cov,0)}%，无依据的配分按政策基准 50 分计算。不代表出口成功概率或实际利润率。`, `分析エンジンが ${wText} の配点で算出した参考適合度です。根拠反映率は ${num(cov,0)}% で、根拠のない配点は政策基準の50点で計算しました。輸出成功確率や実際の利益率ではありません。`)
        + (m.custom ? " " + L("화면에서 가중치를 바꿔 근거가 있는 영역만 다시 평균한 화면 참고점수입니다.", "Weights were changed on screen, so this is an on-screen reference score re-averaged over areas with evidence.", "已在界面中调整权重，这是仅对有依据领域重新平均的界面参考分。", "画面で重みを変更したため、根拠のある分野だけを再平均した画面参考点数です。") : "");
    // 우선 확인할 사항: 규제 관문 → 엔진이 남긴 부족 근거 → 입력 결측 → 수익성 시나리오
    const reasons = [];
    if (m.gate.key === "hold") reasons.push("규제 또는 제한 명단 일치 기록의 원문과 실제 적용 여부를 확인하세요.");
    else reasons.push("제품 사양서로 전략물자 해당 여부를 확인하고 수출허가 필요성을 검토하세요.");
    m.gaps.slice(0, 2).forEach((g) => reasons.push(K(X(g))));
    const missFields = (m.missing.fields || []).filter((f) => f.scored), missSheets = m.missing.missing_sheets || [];
    if (missFields.length) reasons.push(L(`기업 파일의 빈 칸(${K(missFields.map((f) => X(f.label)).join("·"))})을 채우고 다시 분석하세요. 지금은 해당 항목을 정책 기준 50점으로 계산했습니다.`, `Fill in the blank cells in the company file (${K(missFields.map((f) => X(f.label)).join(", "))}) and re-run the analysis. Those items currently use the policy midpoint of 50.`, `请填写企业文件中的空白单元格（${K(missFields.map((f) => X(f.label)).join("、"))}）后重新分析。目前这些项目按政策基准 50 分计算。`, `企業ファイルの空欄（${K(missFields.map((f) => X(f.label)).join("・"))}）を埋めて再分析してください。現在は該当項目を政策基準の50点で計算しています。`));
    reasons.push(L("보고서 창의 수익성 시나리오에 판매단가·부대비용·관세 가정을 입력하면 손익분기 원가를 계산합니다. 가격 점수는 운임·보험·관세·수수료 차감 전 기준입니다.", "Enter the selling price, extra costs and tariff assumption in the report dialog's profitability scenario to calculate the break-even cost. The price score is before freight, insurance, tariffs and fees.", "在报告窗口的盈利情景中输入销售单价、附加费用和关税假设，即可计算盈亏平衡成本。价格分数为扣除运费、保险、关税和手续费之前的数值。", "レポート画面の収益シナリオに販売単価・付帯費用・関税の仮定を入力すると損益分岐原価を計算します。価格点数は運賃・保険・関税・手数料を差し引く前の基準です。"));
    if ((m.quality.issues || []).length) reasons.push("원본 파일의 결측·오류 내역을 검토한 후 분석을 재실행하세요.");
    const sc=m.scenario||{}, sale=sc.sale===""||sc.sale==null?null:Number(sc.sale), extras=sc.extras===""||sc.extras==null?null:Number(sc.extras), tax=sc.tax===""||sc.tax==null?null:Number(sc.tax), cost=sc.cost===""||sc.cost==null?null:Number(sc.cost);
    const scenarioValid=sale!=null&&Number.isFinite(sale)&&sale>0&&extras!=null&&Number.isFinite(extras)&&extras>=0&&tax!=null&&Number.isFinite(tax)&&tax>=0&&(cost==null||(Number.isFinite(cost)&&cost>=0));
    const maxCost=scenarioValid?sale-extras-sale*tax/100:null;
    const scenarioSummary=scenarioValid?`가정 손익분기 최대 제품원가 ${num(maxCost,2)} USD/개 (판매단가 ${num(sale,2)}, 부대비용 ${num(extras,2)}, 관세 가정 ${num(tax,2)}%). ${cost==null?"실제 원가 미입력으로 이익률은 미산정":`가정 단위이익 ${num(maxCost-cost,2)} USD, 가정 이익률 ${num((maxCost-cost)/sale*100,1)}%`}. 제품별 계약조건에 따라 결과가 달라집니다.`:"가정을 입력하지 않았습니다. 판매단가·부대비용·관세만 입력해도 감당 가능한 최대 제품원가를 계산할 수 있습니다.";
    const pts = L("배점", "Points", "配分", "配点");
    const tableRows = ["regulation", "market", "price", "logistics", "stability"].map((key) => {
      const f = by[key] || {}, d = det[key] || {};
      const label = key === "regulation" ? "규제 확인" : DOMAIN[key]();
      const result = key === "regulation" ? gateTag(m.gate.label) : f.state === "ok" && f.score != null ? `${num(f.score)} / 100` : statusTag("자료 부족");
      return `<tr><td><strong>${E(label)}</strong></td><td>${result}</td><td>${key === "regulation" ? "관문 / 비점수" : E(`${pts} ${num(d.raw_max != null ? d.raw_max : W[key], 0)}`)}</td><td class="note">${noteOf(key)}</td></tr>`;
    }).join("");
    const quality=(m.quality.issues||[]).map(i=>`<tr><td>${K(X(i.sheet))} / ${K(X(i.field))}</td><td>${K(X(i.kind))}</td><td>${E(i.count)}건</td><td>${K(X(i.effect))}</td></tr>`).join("");
    const marketRows = (m.items.market || []).map((it) => `<tr><td>${nm(it.label)}</td><td>${it.status === "확인됨" ? P(valueText(it)) : statusTag(it.status)}</td><td>${[it.period?K(it.period):"",it.as_of?`기준 ${K(it.as_of)}`:""].filter(Boolean).join(" / ")||"미확인"}${it.basis ? `<div class="source">${K(X(it.basis))}</div>` : ""}</td></tr>`).join("");
    const ecHsk = ec && ec.value, ecCodes = regN(ec);
    const ecText = ec && ec.status === "확인됨" ? E(L(`HSK ${num(ecHsk,0)}개 · 통제번호 ${num(ecCodes,0)}개`, `${num(ecHsk,0)} HSK · ${num(ecCodes,0)} control numbers`, `HSK ${num(ecHsk,0)} 个 · 管制编号 ${num(ecCodes,0)} 个`, `HSK ${num(ecHsk,0)} 件 · 統制番号 ${num(ecCodes,0)} 件`)) : "미확인";
    const regKpi = (it) => it ? (it.status === "확인됨" ? `${E(it.status)} · ${P(valueText(it))}` : E(it.status)) : "미확인";
    const cond = (key) => { const f = by[key] || {}; return f.state === "ok" && f.score != null ? num(f.score) + " / 100" : statusTag("자료 부족"); };
    const logWarn = (det.logistics && det.logistics.warnings || []).filter(Boolean).slice(0, 2);
    const raw = `<!doctype html><html lang="ko"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>AXPORT 수출 분석 보고서 - ${K(m.company)}</title><style>${css}</style></head><body><main>
<section class="cover"><div class="brand"><strong>AXPORT<span style="color:#08a0b4">.</span></strong><div class="right">EXPORT INTELLIGENCE<br/>ANALYSIS REPORT / ${E(m.rule)}</div></div>
<p class="eyebrow">EXPORT DECISION SUPPORT / EXECUTIVE SUMMARY</p><h1>수출 의사결정<br/>분석 보고서</h1><p class="subtitle">${K(m.company)} | ${E(t18(m.country))} | ${E(scope)}</p>
<div class="cover-meta"><div class="meta-box"><span class="meta-label">기업 분석기간</span><strong>${E(m.from)} — ${E(m.to)}</strong></div><div class="meta-box"><span class="meta-label">공개 통계 시점</span><strong>${E(L(`분석 기준일 ${m.asOf}`, `Analysis date ${m.asOf}`, `分析基准日 ${m.asOf}`, `分析基準日 ${m.asOf}`))}</strong></div><div class="meta-box"><span class="meta-label">작성일</span><strong>${E(m.generated)}</strong></div></div>
<div class="decision"><span class="flag">EXPORT SUITABILITY / ${E(L("참고 적합도", "Reference suitability", "参考适合度", "参考適合度"))}</span><h2>${m.score==null?E(L("판단 근거 부족 · 영역별 결과만 제공", "Insufficient evidence · area results only", "判断依据不足 · 仅提供各领域结果", "判断根拠不足 · 分野別の結果のみ")):`${E(L("참고 적합도", "Reference suitability", "参考适合度", "参考適合度"))} ${num(m.score)} / 100 · ${nm(m.verdict)}`}</h2><p>${E(txt)}</p></div>
<div class="reg-gate ${marked}"><b>수출 실행 요건: ${nm(m.gate.label)}</b><p>${E(m.gate.text)} 규제 확인은 정량 점수와 별도이며 높은 점수가 선적 승인을 뜻하지 않습니다.</p></div>
<div class="coverage-wrap"><div class="coverage-head"><b>점수에 사용한 데이터 구성</b><small>${E(L(`근거 반영률 ${num(cov,0)}% / 배점 합계 ${num(total,0)}`, `Evidence coverage ${num(cov,0)}% / total points ${num(total,0)}`, `依据反映率 ${num(cov,0)}% / 配分合计 ${num(total,0)}`, `根拠反映率 ${num(cov,0)}% / 配点合計 ${num(total,0)}`))}</small></div><div class="coverage-bar" aria-label="${E(L(`근거 반영 ${num(cov,0)}%, 정책 기준 50점 ${num(gapL,0)}%`, `With evidence ${num(cov,0)}%, policy midpoint ${num(gapL,0)}%`, `有依据 ${num(cov,0)}%，政策基准 ${num(gapL,0)}%`, `根拠あり ${num(cov,0)}%、政策基準 ${num(gapL,0)}%`))}"><i class="coverage-current" style="width:${Math.min(100,Math.max(0,cov))}%"></i><i class="coverage-missing" style="width:${Math.min(100,Math.max(0,gap))}%"></i></div><div class="coverage-legend"><span><i class="coverage-current"></i>${E(L(`공개 통계·기업 기재 근거 ${num(cov,0)}%`, `Public statistics and company entries ${num(cov,0)}%`, `公开统计·企业填报依据 ${num(cov,0)}%`, `公開統計・企業記載の根拠 ${num(cov,0)}%`))}</span>${gap>0?`<span><i class="coverage-missing"></i>${E(L(`근거 없음 · 정책 기준 50점 ${num(gapL,0)}%`, `No evidence · policy midpoint 50 ${num(gapL,0)}%`, `无依据 · 政策基准 50 分 ${num(gapL,0)}%`, `根拠なし · 政策基準50点 ${num(gapL,0)}%`))}</span>`:""}</div><div class="result-detail">${E(gap>0?L("근거가 없는 배점은 값을 채우지 않고 정책 기준 50점으로 계산했습니다. 유리·불리를 확인했다는 뜻이 아닙니다.", "Points without evidence are not filled in; they are calculated at the policy midpoint of 50. This does not mean they were confirmed as favorable or unfavorable.", "无依据的配分不填补数值，按政策基准 50 分计算，并不表示已确认有利或不利。", "根拠のない配点は値を補わず政策基準の50点で計算しました。有利・不利を確認したという意味ではありません。"):L("모든 배점에 근거가 반영됐습니다. 기업 기재값도 근거에 포함되며 정확도나 수출 성공확률이 아닙니다.", "Evidence covers all points. Company entries count as evidence; this is not accuracy or a probability of export success.", "所有配分均已反映依据。企业填报值也计入依据，并非准确度或出口成功概率。", "すべての配点に根拠が反映されました。企業記載値も根拠に含まれ、精度や輸出成功確率ではありません。"))}</div></div>
<div class="section-title"><b>확보된 핵심 근거</b><span>사업성 지표와 규제 검토는 서로 독립적으로 해석</span></div>
<div class="metrics">${metric(DOMAIN.market(),by.market,det.market)}${metric(DOMAIN.price(),by.price,det.price)}${metric(DOMAIN.logistics(),by.logistics,det.logistics)}${metric(DOMAIN.stability(),by.stability,det.stability)}</div>
<div class="executive"><strong>우선 확인할 사항</strong><ol>${reasons.slice(0,4).map(r=>`<li>${E(r)}</li>`).join("")}</ol></div>
<div class="cover-foot">${E(m.sample?L("가상 샘플 기업 자료와 기준일이 다른 공개 통계를 함께 사용합니다.", "Uses fictional sample company data together with public statistics that have different reference dates.", "同时使用虚构样本企业数据和基准日不同的公开统计。", "架空サンプル企業のデータと基準日の異なる公開統計を併用します。"):L("업로드한 기업 자료와 기준일이 다른 공개 통계를 함께 사용합니다.", "Uses the uploaded company data together with public statistics that have different reference dates.", "同时使用上传的企业数据和基准日不同的公开统计。", "アップロードした企業データと基準日の異なる公開統計を併用します。"))} 특정 기준일의 검색 결과는 허가, 제재·전략물자 비해당 또는 운송 가능성을 증명하지 않습니다. 자료 확인 ${counts.ok}/${counts.total}은 의사결정 준비율이 아닙니다.</div></section>
<section class="sheet"><div class="sheet-head"><span class="index">01</span><h2>분석 범위 및 평가 방법</h2></div><p class="desc">기업 내부 성과와 공개 통계의 기준일 및 품목 범위가 다를 수 있습니다. 시장 통계의 대상 HS를 반드시 확인하세요.</p>
<div class="kpi-strip"><div class="kpi"><span>기업 분석기간</span><b>${E(m.from)}~${E(m.to)}</b></div><div class="kpi"><span>대상 국가 / 선택 HS</span><b>${E(t18(m.country))} / ${E(scope)}</b></div><div class="kpi"><span>지표 수집 상태</span><b>${counts.ok} / ${counts.total}개 확인</b></div></div>
<div class="legend"><strong>평가 기준 ${E(m.rule)}</strong><br/>${E(L(`배점: ${wText} (합계 ${num(total,0)}). 영역 점수는 적합도 항목 점수(0~100)를 항목 배점으로 가중해 100점으로 환산하고, 참고 적합도는 영역 점수를 배점으로 가중평균합니다. 시장성은 목적국 대세계 수입 규모·한국 수출 규모·수입 성장률, 가격은 희망판매가 대비 제품원가 여지, 물류는 30일 공급가능량·출고 준비기간·국제운송 조건, 안정성은 36개월 월간 수입 변동계수·급감 빈도로 평가합니다. 근거가 없는 항목은 정책 기준 50점으로 계산하고 근거 반영률을 함께 표시합니다. 규제는 점수에 더하지 않는 별도 관문입니다. 기준선과 등급은 초기 서비스 정책이며 실제 수출성과로 검증한 모형이 아닙니다.`,
  `Points: ${wText} (total ${num(total,0)}). Each area score weights its suitability items (0–100) by item points and converts to 100; the reference suitability is the point-weighted average of area scores. Market uses the destination's world imports, Korea's exports and import growth; price uses the cost headroom versus the target selling price; logistics uses 30-day supply capacity, dispatch lead time and international transport conditions; stability uses the 36-month coefficient of variation and frequency of sharp drops in monthly imports. Items without evidence use the policy midpoint of 50, shown together with evidence coverage. Regulation is a separate gate and is not added to the score. Baselines and grades are initial service policy, not a model validated against actual export results.`,
  `配分：${wText}（合计 ${num(total,0)}）。领域分数按项目配分对适合度项目分数（0~100）加权并换算为 100 分，参考适合度为各领域分数按配分的加权平均。市场性评估目的国全球进口规模、韩国出口规模和进口增长率；价格评估目标售价下的产品成本空间；物流评估30天供货能力、出货准备期和国际运输条件；稳定性评估36个月月度进口的变异系数和骤降频率。无依据的项目按政策基准 50 分计算，并同时显示依据反映率。监管是不计入分数的单独关口。基准线和等级为初期服务政策，并非经实际出口绩效验证的模型。`,
  `配点：${wText}（合計 ${num(total,0)}）。分野点数は適合度項目点数（0〜100）を項目配点で加重して100点に換算し、参考適合度は分野点数の配点加重平均です。市場性は輸出先の対世界輸入規模・韓国の輸出規模・輸入成長率、価格は希望販売価格に対する製品原価の余地、物流は30日供給可能量・出荷準備期間・国際輸送条件、安定性は36か月の月次輸入の変動係数・急減頻度で評価します。根拠のない項目は政策基準の50点で計算し、根拠反映率を併記します。規制は点数に加えない別のゲートです。基準線と等級は初期サービス方針であり、実際の輸出成果で検証したモデルではありません。`))}</div>
<h3 class="subhead">평가 결과와 제외 사유</h3><table><colgroup><col style="width:21%"/><col style="width:17%"/><col style="width:15%"/><col style="width:47%"/></colgroup><thead><tr><th>영역</th><th>결과</th><th>${E(pts)}</th><th>주요 근거 · 한계</th></tr></thead><tbody>${tableRows}</tbody></table>
<h3 class="subhead">품목 및 원본 데이터</h3><div class="legend">${E(L(`선택 품목: ${scope}. 기업 등록 HS6: ${allHs || "미확인"}. 원본 파일: ${K(m.file)}. 유효 행: ${m.quality.rows_valid ?? "미확인"}/${m.quality.rows_total ?? "미확인"}.`, `Selected item: ${scope}. Company HS6 codes: ${allHs || "unconfirmed"}. Source file: ${K(m.file)}. Valid rows: ${m.quality.rows_valid ?? "unconfirmed"}/${m.quality.rows_total ?? "unconfirmed"}.`, `所选品目：${scope}。企业登记 HS6：${allHs || "未确认"}。原始文件：${K(m.file)}。有效行：${m.quality.rows_valid ?? "未确认"}/${m.quality.rows_total ?? "未确认"}。`, `選択品目：${scope}。企業登録HS6：${allHs || "未確認"}。元ファイル：${K(m.file)}。有効行：${m.quality.rows_valid ?? "未確認"}/${m.quality.rows_total ?? "未確認"}。`))}${missSheets.length ? " " + E(L(`파일에 없는 시트: ${K(missSheets.map(X).join("·"))} — 값을 채우지 않았습니다.`, `Sheets not in the file: ${K(missSheets.map(X).join(", "))} — no values were filled in.`, `文件中没有的工作表：${K(missSheets.map(X).join("、"))} — 未填补数值。`, `ファイルにないシート：${K(missSheets.map(X).join("・"))} — 値を補っていません。`)) : ""} ${E(L("국제 무역통계는 상위 HS6 범위이며 개별 제품·모델의 시장규모가 아닙니다.", "International trade statistics cover the parent HS6 range, not the market size of an individual product or model.", "国际贸易统计为上位 HS6 范围，并非单个产品或型号的市场规模。", "国際貿易統計は上位HS6の範囲であり、個別製品・モデルの市場規模ではありません。"))}</div></section>
<section class="sheet"><div class="sheet-head"><span class="index">02</span><h2>규제 검토 및 시장 분석</h2></div><p class="desc">제한 명단 정확 일치 검색은 예비 확인이며 법률상 거래 가능 여부의 결론이 아닙니다.</p>
<div class="alert ${marked}"><b>규제 상태: ${nm(m.gate.label)}</b><br/>${E(m.gate.text)}<br/>HSK 연계표는 통제번호 후보 탐색용입니다. 거래처 법인명 정확 일치 검색의 한계로 별칭·현지어·최종사용자 및 최신 목록은 별도 확인해야 합니다.</div>
<div class="kpi-strip"><div class="kpi"><span>통제번호 후보</span><b>${ecText}</b></div><div class="kpi"><span>수입규제 검색</span><b>${regKpi(im)}</b></div><div class="kpi"><span>제한 명단 검색</span><b>${regKpi(cs)}</b></div></div>
<h3 class="subhead">목적국 수입시장 (선택 HS 기준)</h3><table><colgroup><col style="width:30%"/><col style="width:22%"/><col style="width:48%"/></colgroup><thead><tr><th>지표</th><th>확인값</th><th>기간 및 범위</th></tr></thead><tbody>${marketRows}<tr><td>${E(L("시장성 참고점수", "Market reference score", "市场性参考分", "市場性参考点数"))}</td><td>${cond("market")}</td><td>${noteOf("market")}</td></tr></tbody></table>
<p class="alert">${E(L(`시장성은 HS ${m.hsDot}의 UN Comtrade 목적국 대세계 수입과 관세청 한국 수출로 계산합니다. WSTS 세계 반도체 매출은 국가·HS 시장과 별도인 산업 배경 정보로 점수에 넣지 않습니다. 누락 월은 0으로 채우지 않습니다.`, `Market is calculated from the destination's UN Comtrade world imports and Korea Customs exports for HS ${m.hsDot}. WSTS global semiconductor sales are industry background separate from the country and HS market and are not scored. Missing months are not filled with zero.`, `市场性依据 HS ${m.hsDot} 的 UN Comtrade 目的国全球进口和韩国关税厅出口计算。WSTS 全球半导体销售额是独立于国家·HS 市场的行业背景信息，不计入分数。缺失月份不以 0 填补。`, `市場性はHS ${m.hsDot}のUN Comtradeによる輸出先の対世界輸入と韓国関税庁の輸出から算出します。WSTS世界半導体売上は国・HS市場とは別の産業背景情報で、点数には含めません。欠損月を0で埋めません。`))}</p></section>
<section class="sheet"><div class="sheet-head"><span class="index">03</span><h2>${E(L("가격·수익성·물류·시장 안정성", "Price, profitability, logistics and market stability", "价格·盈利性·物流·市场稳定性", "価格・収益性・物流・市場の安定性"))}</h2></div><div class="alert"><b>${E(L("가격 점수", "Price score", "价格分数", "価格点数"))}: ${by.price && by.price.state==="ok" && by.price.score!=null?num(by.price.score)+" / 100":E(L("관련 자료 일부 부족", "Some related data missing", "部分相关资料不足", "関連資料が一部不足"))}</b><br/>${E(L("희망판매가에서 제품원가를 뺀 여지(기업 기재)로 계산합니다. 운임·보험·관세·수수료 차감 전이며 순이익률이 아닙니다. 관세·통계 단가·환율은 참고치로 함께 표시합니다.", "Calculated from the headroom between the target selling price and product cost (company entry). It is before freight, insurance, tariffs and fees and is not a net margin. Tariffs, statistical unit values and FX are shown as references.", "按目标售价减去产品成本的空间（企业填报）计算。为扣除运费、保险、关税和手续费之前的数值，并非净利润率。关税、统计单价和汇率作为参考一并显示。", "希望販売価格から製品原価を差し引いた余地（企業記載）で計算します。運賃・保険・関税・手数料の控除前で、純利益率ではありません。関税・統計単価・為替は参考値として併記します。"))}</div>
<div class="kpi-strip"><div class="kpi"><span>관세 참고</span><b>${tariff && tariff.status==="확인됨" ? P(valueText(tariff)) : "미확인"}</b></div><div class="kpi"><span>${E(L("원/달러 참고환율", "KRW/USD reference rate", "韩元/美元参考汇率", "ウォン/ドル参考レート"))}</span><b>${fx && fx.status==="확인됨" ? P(valueText(fx)) : "미확인"}</b></div><div class="kpi"><span>${E(L("36개월 수입 변동계수", "36-month import CV", "36个月进口变异系数", "36か月輸入変動係数"))}</span><b>${cv && cv.status==="확인됨" ? P(valueText(cv)) : "자료 부족"}</b></div></div>
<table><colgroup><col style="width:25%"/><col style="width:20%"/><col style="width:55%"/></colgroup><thead><tr><th>영역</th><th>평가 상태</th><th>해석 및 기준</th></tr></thead><tbody><tr><td>${E(DOMAIN.price())}</td><td>${cond("price")}</td><td>${noteOf("price")}<div class="source">${E(L("기업 파일의 희망판매가·제품원가 · 관세(WTO)·환율(한국은행 ECOS)은 참고", "Target price and product cost from the company file · tariffs (WTO) and FX (Bank of Korea ECOS) are references", "企业文件中的目标售价·产品成本 · 关税（WTO）和汇率（韩国银行 ECOS）仅供参考", "企業ファイルの希望販売価格・製品原価 · 関税（WTO）・為替（韓国銀行ECOS）は参考"))}</div></td></tr><tr><td>${E(DOMAIN.logistics())}</td><td>${cond("logistics")}</td><td>${noteOf("logistics")}<div class="source">${E(L("기업 기재 공급가능량·출고 준비기간 · 운송비는 관세청 보도자료 참고치", "Supply capacity and dispatch lead time from company entries · freight is a Korea Customs press-release reference", "企业填报的供货能力·出货准备期 · 运费为关税厅新闻稿参考值", "企業記載の供給可能量・出荷準備期間 · 運送費は関税庁報道資料の参考値"))}</div></td></tr><tr><td>${E(DOMAIN.stability())}</td><td>${cond("stability")}</td><td>${noteOf("stability")}<div class="source">${E(L("UN Comtrade 36개월 월간 수입 · 과거 변동이며 미래 손실 확률이 아님", "UN Comtrade 36-month monthly imports · past volatility, not a probability of future loss", "UN Comtrade 36个月月度进口 · 历史波动，并非未来损失概率", "UN Comtrade 36か月の月次輸入 · 過去の変動であり将来の損失確率ではない"))}</div></td></tr></tbody></table>
<div class="scenario"><h3 class="subhead" style="margin-top:0">가정 수익성·손익분기 원가 계산 (추가 입력 최소화)</h3><div class="data-note" id="scenario-prefilled">${E(scenarioSummary)}</div><div class="scenario-grid"><label>예상 판매단가 (USD/개)<input id="sale" value="${E(sc.sale ?? "")}" type="number" min="0" step="0.01" placeholder="예: 100" /></label><label>제품 단위원가 (USD/개, 선택)<input id="cost" value="${E(sc.cost ?? "")}" type="number" min="0" step="0.01" placeholder="몰라도 손익분기 원가 계산 가능" /></label><label>기타 수출 부대비용 (USD/개)<input id="extras" value="${E(sc.extras ?? "")}" type="number" min="0" step="0.01" placeholder="예: 12" /></label><label>관세 시나리오 (%)<input id="tax" value="${E(sc.tax ?? "")}" type="number" min="0" step="0.1" placeholder="직접 가정값 입력" /></label></div><button type="button" onclick="calcScenario()">가정 수익성 계산</button><div id="scenario-result" class="scenario-out" aria-live="polite">${E(scenarioSummary)}</div><p class="scenario-hint">예상 판매단가와 부대비용은 동일한 USD/개 단위로 입력해야 합니다. 관세를 수출자가 부담한다는 가정으로만 계산하며 실제 계약 조건·Incoterms·환율·세금에 따라 달라집니다. 입력한 값은 이 HTML에서만 계산되며 대시보드 점수에 자동 반영되지 않습니다. PDF에 포함하려면 계산한 뒤 인쇄하세요.</p></div>
<h3 class="subhead">추가 확인 항목</h3><div class="legend">${E(L("운송비는 관세청이 공표한 국가·지역별 참고 통계이며 실제 견적, 운송수단, Incoterms, 화물보험료를 대신하지 않습니다.", "Freight is a country/region reference statistic published by Korea Customs and does not replace actual quotes, transport modes, Incoterms or cargo insurance.", "运费为关税厅公布的国家/地区参考统计，不能替代实际报价、运输方式、Incoterms 和货物保险费。", "運送費は関税庁が公表した国・地域別の参考統計であり、実際の見積・輸送手段・Incoterms・貨物保険料の代わりにはなりません。"))}${logWarn.length ? " " + K(logWarn.map(X).join(" ")) : ""}</div></section>
<section class="sheet appendix"><div class="sheet-head"><span class="index">A</span><h2>부록 · 전체 상세 지표와 산출 근거</h2></div><p class="desc">기존 공개자료 및 기업 자료를 보존했습니다. 항목별 기준일·수록 HS·자료 상태를 먼저 확인하세요. 확인됨은 자료가 존재한다는 뜻이며 수출 가능성 확정을 의미하지 않습니다.</p>
${lang() === "ko" ? "" : `<p class="desc">${E(L("", "Company-entered product names and source file names are kept in their original language.", "企业填报的产品名称和原始文件名保留原文。", "企業が記載した製品名と元ファイル名は原文のまま表示します。"))}</p>`}
${m.areas.map(appendixTable).join("")}
${quality?`<h3 class="subhead">원본 파일의 결측·오류</h3><table><thead><tr><th>시트 / 열</th><th>유형</th><th>건수</th><th>계산 영향</th></tr></thead><tbody>${quality}</tbody></table>`:""}
<footer><strong>데이터와 방법론</strong> | ${E(L("기업 엑셀 자료와 분석 엔진이 조회한 공개자료(UN Comtrade·관세청·한국은행 ECOS·국가법령정보·WTO 관세조치·HSK 연계표·KOTRA·ITA CSL·WSTS). 자료 수집일은 개별 항목의 기준일과 다릅니다. 최신 규정의 확정적인 법률 해석·통관·허가 자문이 아닙니다.", "Company Excel data and public data retrieved by the analysis engine (UN Comtrade, Korea Customs, Bank of Korea ECOS, Korean law database, WTO tariff measures, HSK crosswalk, KOTRA, ITA CSL, WSTS). Retrieval dates differ from each item's reference date. This is not definitive legal, customs or licensing advice on current regulations.", "企业 Excel 数据及分析引擎查询的公开资料（UN Comtrade、关税厅、韩国银行 ECOS、国家法令信息、WTO 关税措施、HSK 对照表、KOTRA、ITA CSL、WSTS）。资料收集日与各项目基准日不同。并非对最新法规的确定性法律解释、通关或许可咨询。", "企業Excelデータと分析エンジンが照会した公開資料（UN Comtrade・関税庁・韓国銀行ECOS・国家法令情報・WTO関税措置・HSK対応表・KOTRA・ITA CSL・WSTS）。資料収集日は各項目の基準日と異なります。最新規定の確定的な法的解釈・通関・許可の助言ではありません。"))} 평가 기준 ${E(m.rule)}.</footer></section></main><script>const RSTR=${JSON.stringify(window.AXPORTReportL10n?.scenario(window.AXPI18n?.language) || {})};function calcScenario(){
 var ids=['sale','cost','extras','tax'], v=ids.map(function(id){return document.getElementById(id).value.trim()}),out=document.getElementById('scenario-result');
 if(!v[0]||!v[2]||!v[3]){out.textContent=RSTR.missing;return;}
 var sale=Number(v[0]),cost=v[1]===''?null:Number(v[1]),extras=Number(v[2]),tax=Number(v[3]);
 if([sale,extras,tax].some(function(x){return !Number.isFinite(x)||x<0;})||sale<=0||(cost!==null&&(!Number.isFinite(cost)||cost<0))){out.textContent=RSTR.invalid;return;}
 var duty=sale*tax/100,maximum=sale-extras-duty;
 var result=RSTR.cost+maximum.toFixed(2)+RSTR.unit+RSTR.tariff+duty.toFixed(2)+RSTR.unit+').';
 if(cost!==null){var profit=maximum-cost,margin=profit/sale*100; result+=RSTR.profit+profit.toFixed(2)+' USD'+RSTR.margin+margin.toFixed(1)+'%.';}
 else result+=RSTR.noCost;
 if(maximum<0) result+=RSTR.warning;
 out.textContent=result+RSTR.disclaimer;
}</script></body></html>`;
    return restore(window.AXPORTReportL10n?.translateHTML(raw, lang()) || raw);
  }
  window.JunheeReport = Object.freeze({ render, available: () => !!model({}) });
})();
