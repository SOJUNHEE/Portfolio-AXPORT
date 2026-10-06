"use strict";
/* junhee-widgets-bridge.js — 바탕화면 위젯(minjung/AXPORT_widget 이 /app 에 끼워 넣는 widgets.js) 과 junhee 대시보드 연결 (2026-09-26 · 프롬프트 ⑥).
   minjung 파일은 수정하지 않고 DOM·이벤트로만 연결한다. widgets.js 는 </head> 끝에 defer 로 붙어 이 파일보다 늦게 실행되므로 DOMContentLoaded 에서 시작한다.
   1) 배치 맞춤: 위젯 영역(#sx-board)이 바탕화면 아이콘 열과 겹치지 않게 --jd-board-left 계산. '위젯 편집 모드'로 옮긴 위치(localStorage axsx.team.widgets.v1)가
      화면 밖으로 나가면 '배치 초기화'(#sx-reset) 를 누른 것과 같은 효과를 준다(저장 키 형식은 건드리지 않음). 창 크기 변경·분석 창 열기·전체 화면 해제 때 다시 맞춘다.
   2) 회사 파일 아이콘 → '반도체 수출 데이터' 위젯: workspace.js 의 아이콘 끌기 끝(end)에서 dropAt()/loadDesktopFile() 를 부른다.
      끄는 동안 드롭 영역 강조, 놓으면 위젯의 숨은 입력 #sx-file 에 DataTransfer 로 파일을 넣고 change 를 보낸다(위젯이 원래 쓰는 accept 흐름).
      등록 샘플이면 static/data/companies/index.json(JunheeDashboard) 으로 HS·대상 국가·기업명을 채운다. 자동 제출하지 않는다.
   API: window.JunheeWidgetBridge = { ready, dropAt(x, y) → "upload" | "board" | null, loadDesktopFile(file) → Promise<boolean>, fit() } */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const SYSTEM_ICONS = ["analysis", "trash", "upload", "company-file"]; // (2026-09-27) 기업 파일 업로드 아이콘은 위젯 드롭 대상 표시에서 제외
  const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  let fitTimer = 0, lastDoc = null;

  const board = () => $("#sx-board");
  const uploadCard = () => $('[data-sx-widget="upload"]');
  const visible = (el) => !!el && !el.hidden && !el.closest("[hidden]") && el.getClientRects().length > 0;
  const inRect = (r, x, y) => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
  const ready = () => !!(board() && $("#sx-file") && $("#sx-form"));

  // ---- 1) 배치 맞춤 ------------------------------------------------------------
  function boardLeft() {
    // 끌고 있는 아이콘(workspace.js 가 style z-index 를 넣음)은 빼고 격자에 놓인 아이콘만 잰다
    // (junhee) 2026-09-28 기본 아이콘 두 열(시스템 아이콘 열 · 파일 열, workspace.js 격자 18 + 열×112px)만 잰다.
    // 사용자가 그보다 오른쪽으로 옮긴 아이콘 때문에 위젯 영역이 밀려 줄어들지 않게 한다(아이콘은 위젯 위층에 그대로 놓인다).
    const icons = $$("#desktop-icons .desktop-icon").filter((i) => !i.style.zIndex && i.offsetLeft < 18 + 2 * 112);
    if (!icons.length) return;
    const deskLeft = ($("#desktop") || document.body).getBoundingClientRect().left;
    const right = Math.max(...icons.map((i) => i.getBoundingClientRect().right)) - deskLeft;
    document.documentElement.style.setProperty("--jd-board-left", Math.max(140, Math.round(right + 18)) + "px");
  }
  // 자유 배치(편집 모드로 옮긴 뒤): 카드 높이를 위젯 영역 아래 끝까지로 제한(넘치면 카드 안쪽 스크롤). 기본 배치에서 줄어 있던 카드가
  // 자유 배치에서 원래 높이로 늘어나 화면 아래로 잘리는 것을 막는다. 기본 배치로 돌아가면 widgets.js 가 style 을 지운다.
  function clampFree() {
    const b = board(), canvas = $("#sx-canvas");
    if (!b || !canvas || !canvas.classList.contains("sx-free")) return;
    const remembered = readHeights();
    $$("[data-sx-widget]", canvas).forEach((w) => {
      if (w.hidden || w.classList.contains("jd-resizing")) return; // 크기 조절 중에는 건드리지 않음
      const avail = Math.max(120, b.clientHeight - 8 - w.offsetTop), want = avail + "px"; // 캔버스 높이(영역 - 안쪽 여백 8) 까지
      if (w.style.maxHeight !== want) w.style.maxHeight = want;
      // 기본 배치에서의 높이를 그대로 (환율은 내용 높이). 옮기지 않은 카드가 줄거나 늘어 배치가 깨지지 않게 한다
      const h = remembered[w.dataset.sxWidget];
      if (Number.isFinite(h)) { const hv = Math.min(h, avail) + "px"; if (w.style.height !== hv) w.style.height = hv; }
    });
  }
  // 편집 모드로 옮긴 위젯이 위젯 영역 밖으로 나가 거의 보이지 않는지 (위쪽·왼쪽·오른쪽 밖, 또는 아래쪽에서 60px 도 안 보임)
  function outOfView() {
    const b = board(), canvas = $("#sx-canvas");
    if (!b || !canvas || !canvas.classList.contains("sx-free")) return false;
    const br = b.getBoundingClientRect();
    return $$("[data-sx-widget]", canvas).some((w) => {
      if (w.hidden) return false;
      const r = w.getBoundingClientRect();
      return r.top > br.bottom - 60 || r.right > br.right + 1 || r.left < br.left - 1 || r.top < br.top - 1;
    });
  }
  // 기본 배치의 업로드 위젯을 화면(창) 가로 정중앙으로: 격자 칸 가운데 → 화면 가운데까지 옮기되 아이콘 열·오른쪽 위젯 열과 겹치지 않게 제한
  function centerUpload() {
    const card = uploadCard(), canvas = $("#sx-canvas"), bd = board();
    if (!card || !canvas || !bd) return;
    if (canvas.classList.contains("sx-free") || card.hidden || innerWidth <= 900) { card.style.removeProperty("--jd-upload-shift"); return; }
    const cur = parseFloat(card.style.getPropertyValue("--jd-upload-shift")) || 0, r = card.getBoundingClientRect();
    const natural = r.left - cur, want = innerWidth / 2 - r.width / 2;
    const bl = bd.getBoundingClientRect().left + 4;
    const right = $$('[data-sx-widget]:not([data-sx-widget="upload"])', canvas).filter((w) => !w.hidden).map((w) => w.getBoundingClientRect().left);
    const limitR = (right.length ? Math.min(...right) : bd.getBoundingClientRect().right) - 16;
    const left = Math.max(bl, Math.min(want, limitR - r.width));
    const shift = Math.round(left - natural) + "px";
    if (card.style.getPropertyValue("--jd-upload-shift") !== shift) card.style.setProperty("--jd-upload-shift", shift);
  }
  function fit() {
    if (!ready()) return;
    boardLeft();
    requestAnimationFrame(centerUpload);
    // 위젯 영역 폭이 바뀌면 widgets.js 가 ResizeObserver 로 위치를 다시 잡으므로, 그 뒤(250ms)에 검사한다
    setTimeout(() => {
      if (outOfView()) {
        $("#sx-reset")?.click(); // '배치 초기화'와 같은 효과 (positions=null 저장은 widgets.js 가 한다)
        document.documentElement.dataset.jdWidgetsReset = String(Date.now());
      } else clampFree();
    }, 250);
  }
  const fitSoon = () => { clearTimeout(fitTimer); fitTimer = setTimeout(fit, 120); };

  // ---- 2) 아이콘 → 위젯 ---------------------------------------------------------
  // 놓은 위치: 반도체 수출 데이터 위젯 위면 "upload", 다른 위젯·위젯 영역이면 "board"(아이콘은 원래 칸으로), 그 밖이면 null(기존 처리)
  function dropAt(x, y) {
    if (!ready()) return null;
    const win = $("#analysis-window");
    if (win && !win.hidden && inRect(win.getBoundingClientRect(), x, y)) return null;
    const card = uploadCard();
    if (visible(card) && inRect(card.getBoundingClientRect(), x, y)) return "upload";
    const b = board();
    if (visible(b) && $$("[data-sx-widget]", b).some((w) => visible(w) && inRect(w.getBoundingClientRect(), x, y))) return "board";
    // (junhee) 2026-09-28 위젯을 닫아 둔 빈 영역에도 아이콘을 자유롭게 놓는다(보이는 위젯 카드 위에 놓을 때만 원래 칸으로). 이전: 업로드 위젯이 숨겨지면 위젯 영역 전체를 막음
    return null;
  }
  const hsDot = (hs) => String(hs || "").replace(/^(\d{4})(\d+)$/, "$1.$2");
  const setError = (msg) => { const e = $("#sx-error"); if (e) e.textContent = msg || ""; };
  async function fileFor(f) {
    if (f && typeof File !== "undefined" && f.raw instanceof File) return f.raw; // 내가 올린 파일: 이미 가진 File
    if (f && f.sample) {
      const res = await fetch("/static/samples/" + encodeURIComponent(f.source_name || f.name), { cache: "no-store" }); // (junhee) 이름을 바꿔도 원본 샘플 파일
      if (!res.ok) throw new Error("샘플 파일을 불러오지 못했습니다 (HTTP " + res.status + ")");
      return new File([await res.blob()], f.name, { type: XLSX });
    }
    return null;
  }
  async function fillFields(f) {
    const D = window.JunheeDashboard;
    if (!D) return false;
    await D.load();
    const entry = D.findByFileName(f.name) || f.match || null;
    if (!entry) { lastDoc = null; restoreDefaults(); return false; } // 등록되지 않은 파일: 기본 선택지로 되돌리고 기존 안내를 그대로 쓴다
    const company = $("#sx-company");
    if (company) company.value = entry.company_name;
    try {
      const doc = await D.peek(entry.company_id);
      lastDoc = doc;
      companyOptions(doc, entry); // HS CODE = 회사 HS6 목록(주요 HS 선택) · 대상국 = 회사 목적국(수출 비중 순, 주요 목적국 선택)
    } catch (e) { console.error("JunheeWidgetBridge country:", e); }
    return true;
  }
  // (junhee) 2026-09-27 분석 엔진용: 바탕화면 파일의 기업명·HS·대상국을 위젯 입력칸에
  function fillEngine(d) {
    lastDoc = null;
    restoreDefaults();
    const company = $("#sx-company"), hs = $("#sx-hs"), sel = $("#jd-sx-hs"), ctry = $("#sx-country");
    if (company && d.company) company.value = d.company;
    if (hs && d.hs && d.hs !== "all") {
      const v = hsDot(d.hs);
      if (sel && ![...sel.options].some((o) => o.value === v)) sel.add(new Option(v, v));
      if (sel) sel.value = v;
      hs.value = v;
      hs.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (ctry && d.country && [...ctry.options].some((o) => o.value === d.country)) ctry.value = d.country;
  }
  // (junhee) 2026-09-27 바탕화면 '기업 데이터 업로드' 아이콘과 위젯 연동
  const uploadVisible = () => ready() && visible(uploadCard());
  function flash(card) {
    card.classList.add("jd-drop-card");
    setTimeout(() => card.classList.remove("jd-drop-card"), 900);
  }
  function focusUpload() {
    const card = uploadCard();
    if (!uploadVisible()) return false;
    card.scrollIntoView({ block: "nearest", behavior: "smooth" });
    flash(card);
    ($("#sx-file-button") || $("#sx-form .sx-primary"))?.focus({ preventScroll: true });
    return true;
  }
  function loadOsFile(file) {
    const card = uploadCard(), input = $("#sx-file");
    if (!uploadVisible() || !input || !file) return false;
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event("change", { bubbles: true })); // widgets.js accept() → #excel-input
    lastDoc = null;
    restoreDefaults();
    flash(card);
    $("#sx-form .sx-primary")?.focus({ preventScroll: true });
    return true;
  }
  // (junhee) 2026-09-27 분석 진행 표시: 첫 분석은 공개 통계 조회로 수 분 걸리므로 위젯 버튼을 잠그고 진행 문구를 보여 준다
  let privacyText = null;
  window.addEventListener("axp:analysis-progress", (e) => {
    const d = (e && e.detail) || {}, btn = $("#sx-form .sx-primary"), note = $(".jd-sx-privacy span");
    if (btn) btn.disabled = !!d.busy;
    if (!note) return;
    if (d.busy) {
      if (privacyText == null) privacyText = note.textContent;
      note.textContent = d.message || "분석 중입니다…";
    } else if (privacyText != null) {
      note.textContent = privacyText;
      privacyText = null;
    }
  });
  let busy = false;
  async function loadDesktopFile(f) {
    const card = uploadCard(), input = $("#sx-file");
    if (!ready() || !visible(card) || !input || busy || !f) return false;
    busy = true;
    setError("");
    try {
      const file = await fileFor(f);
      if (!file) { setError("이 파일은 다시 선택해 주세요. (내용을 가진 파일만 위젯에 넣을 수 있습니다)"); return false; }
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event("change", { bubbles: true })); // widgets.js accept() → 기존 업로드 흐름(#excel-input)
      // (junhee) 2026-09-27 새 업로드 복사본 대신 바탕화면 파일 자체를 분석 대상으로(같은 아이콘이 하나 더 생기지 않음) + 그 파일의 기업명·HS·대상국
      const bound = window.AXWorkspace && AXWorkspace.bindPending ? AXWorkspace.bindPending(f.id) : null;
      if (bound) fillEngine(bound);
      else await fillFields(f);
      card.classList.add("jd-drop-card");
      setTimeout(() => card.classList.remove("jd-drop-card"), 900);
      $("#sx-form .sx-primary")?.focus({ preventScroll: true });
      return true;
    } catch (e) {
      console.error("JunheeWidgetBridge:", e);
      setError(String((e && e.message) || e));
      return false;
    } finally {
      busy = false;
    }
  }
  // 끄는 동안 강조: workspace.js 가 아이콘에 pointer capture 를 걸어 두므로 pointermove 가 아이콘에서 올라온다
  function markDrag(ev) {
    const icon = ev.target && ev.target.closest && ev.target.closest("#desktop-icons .desktop-icon[data-id]");
    const drop = $("#sx-drop");
    if (!drop) return;
    const on = !!(icon && !SYSTEM_ICONS.includes(icon.dataset.id) && (ev.buttons & 1) && icon.hasPointerCapture && icon.hasPointerCapture(ev.pointerId) && dropAt(ev.clientX, ev.clientY) === "upload");
    drop.classList.toggle("jd-drop-hover", on);
  }
  const clearMark = () => $("#sx-drop")?.classList.remove("jd-drop-hover");

  // 위젯에서 고른 대상 국가(ISO 코드)가 분석 창 대상국 목록(회사 목적국 한글 이름)에 있으면 그 이름으로 맞춘다.
  // (widgets.js 는 ISO 코드를 새 옵션으로 넣으므로 그대로 두면 기존 분석기가 주요 목적국을 쓴다)
  // workspace.js 의 분석 제출 처리보다 먼저(문서 capture 단계) 동기로 바꿔야 기존 분석기가 읽는다.
  function mapCountry() {
    const sel = $("#country-input");
    if (!sel || !lastDoc || !/^[A-Z]{2}$/.test(sel.value)) return;
    const label = $("#file-label")?.textContent || "";
    if (!label.includes(lastDoc.company_name) && !label.includes(lastDoc.file_name)) return;
    const hit = (lastDoc.common.countries || []).find((c) => c.iso2 === sel.value);
    if (hit && [...sel.options].some((o) => o.value === hit.name)) sel.value = hit.name;
  }

  // ---- 3) 위젯 머리 아이콘: 대시보드(index3) 카드 타일 모양 — 28px · 둥근 8px · 영역 색 옅은 바탕 + Phosphor 아이콘 ----
  const ICON = { fx: ["fx", "currency-circle-dollar"], news: ["news", "newspaper"], weather: ["weather", "cloud-sun"], upload: ["upload", "upload-simple"] };
  const CUR = { USD: ["US", "미국 달러", "US dollar"], KRW: ["KR", "원화", "KRW"], CNY: ["CN", "위안화", "CNY"], EUR: ["EU", "유로", "euro"], JPY: ["JP", "엔화", "JPY"], GBP: ["GB", "파운드", "GBP"], TWD: ["TW", "대만 달러", "TWD"], VND: ["VN", "동", "VND"] };
  function decorateHeads() {
    $$("[data-sx-widget]").forEach((w) => {
      const h = $(".sx-handle", w), def = ICON[w.dataset.sxWidget];
      if (!h || !def || $(".jd-wicon", h)) return;
      const tile = document.createElement("span");
      tile.className = "jd-wicon " + def[0];
      tile.setAttribute("aria-hidden", "true");
      tile.innerHTML = `<i class="ph ph-${def[1]}"></i>`;
      const grip = $(".sx-grip", h);
      if (grip) grip.after(tile); else h.prepend(tile);
    });
  }
  function decorateFx() {
    const ko = lang() === "ko";
    $$("#sx-fx-rows .sx-rate").forEach((row) => {
      if (row.dataset.jdFx) return;
      const pairEl = row.firstElementChild, m = String(pairEl?.textContent || "").replace(/\s/g, "").match(/^([A-Z]{3})\/([A-Z]{3})$/);
      if (!m) return;
      row.dataset.jdFx = "1";
      const a = CUR[m[1]], b = CUR[m[2]];
      const flag = document.createElement("span");
      flag.className = "jd-flag";
      flag.setAttribute("aria-hidden", "true");
      flag.innerHTML = `${a ? a[0] : m[1].slice(0, 2)}<i class="ph ph-arrow-right"></i>${b ? b[0] : m[2].slice(0, 2)}`;
      const meta = document.createElement("div");
      meta.className = "jd-fx-meta";
      pairEl.textContent = `${m[1]} / ${m[2]}`;
      meta.append(pairEl);
      if (a && b) { const d = document.createElement("em"); d.textContent = ko ? `1 ${a[1]}당 ${b[1]}` : `${b[2]} per 1 ${a[2]}`; meta.append(d); }
      row.prepend(flag, meta);
    });
  }

  // ---- 4) '반도체 수출 데이터' 위젯 → '기업 데이터 업로드' 창과 같은 형식 ----
  // 순서: 드롭 영역(엑셀) → 파일명 → 개인정보 안내 → 기업명 → HS CODE(선택) · 대상국(선택) → 오류 → [양식 다운로드][업로드 가이드] … [샘플 파일 사용][분석 화면 보기 →]
  // widgets.js 의 요소·id·제출 흐름은 그대로 두고 배치·문구만 바꾼다. HS 는 숨긴 #sx-hs 에 값을 넣고 input 이벤트를 보낸다(검증은 widgets.js).
  const lang = () => (window.AXPI18n && AXPI18n.language) || "ko";
  const it = (ko) => (window.AXPI18n ? AXPI18n.t(ko) : ko); // 업로드 창에 이미 있는 문구는 i18n 사전 번역을 그대로 쓴다
  const OWN = {
    title: { ko: "기업 분석 데이터 업로드", en: "Company analysis upload", zh: "企业分析数据上传", ja: "企業分析データのアップロード" }, // (junhee) 2026-09-27 이름 변경
    intro: { ko: "기업 파일과 수출 조건을 선택해 분석을 시작하세요.", en: "Select a company file and export conditions to start the analysis.", zh: "选择企业文件和出口条件，开始分析。", ja: "企業ファイルと輸出条件を選んで分析を開始します。" },
    privacy: { ko: "파일은 분석 서버로 보내 분석하고, 결과를 이 작업공간에 저장합니다.", en: "Files are sent to the analysis server and the results are saved to this workspace.", zh: "文件会发送到分析服务器进行分析，结果保存在此工作区中。", ja: "ファイルは分析サーバーに送信して分析し、結果をこのワークスペースに保存します。" } /* (2026-10-05) 로그인 없이 사용 */, // (junhee) 2026-09-27 엔진 전용 — 대시보드 업로드 창과 같은 문구
    template: { ko: "양식 다운로드", en: "Template", zh: "下载模板", ja: "様式ダウンロード" },
    guide: { ko: "업로드 가이드", en: "Upload guide", zh: "上传指南", ja: "アップロードガイド" },
    hsHint: { ko: "회사 파일의 HS6 목록", en: "HS6 codes in the company file", zh: "企业文件中的 HS6 列表", ja: "企業ファイルの HS6 一覧" },
    edit: { ko: "위젯 편집 모드", en: "Edit widgets", zh: "编辑组件", ja: "ウィジェット編集" },
    reset: { ko: "배치 초기화", en: "Reset layout", zh: "重置布局", ja: "配置をリセット" },
  };
  const own = (k) => OWN[k][lang()] || OWN[k].ko;
  let defaultCountries = null, formReady = false;
  const ENGINE_ISO = ["US", "CN", "JP", "DE", "VN"];
  function mk(tag, cls, html) { const n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; }
  function buildUploadForm() {
    const card = uploadCard(), form = $("#sx-form");
    if (!card || !form || formReady) return;
    formReady = true;
    card.classList.add("jd-upload-form");
    // 머리: NEW ANALYSIS + 기업 데이터 업로드
    const h2 = $("#sx-upload-title");
    if (h2 && !h2.parentElement.classList.contains("jd-head-text")) {
      h2.removeAttribute("data-sx-t");
      const box = mk("div", "jd-head-text");
      h2.before(box);
      box.append(mk("small", "", "NEW ANALYSIS"), h2);
    }
    const intro = $(".sx-intro", card);
    intro?.removeAttribute("data-sx-t");
    // 드롭 영역
    const drop = $("#sx-drop");
    const dropIcon = $("i", drop); if (dropIcon) dropIcon.className = "ph ph-microsoft-excel-logo";
    const dropTitle = $("strong", drop); dropTitle?.removeAttribute("data-sx-t");
    const dropSmall = $("small", drop); if (dropSmall) dropSmall.innerHTML = "";
    // 기업명 · HS · 대상국 (업로드 창 .field / .form-row 모양)
    const companyLabel = $(".sx-company", form), companySpan = $("span", companyLabel);
    companySpan?.removeAttribute("data-sx-extra");
    companyLabel.classList.add("jd-field");
    const fields = $(".sx-fields", form);
    const [hsLabel, ctryLabel] = $$("label", fields);
    hsLabel.classList.add("jd-field");
    ctryLabel.classList.add("jd-field");
    const hsText = hsLabel.firstChild; // "HS CODE " 텍스트
    const hsSmall = $("small", hsLabel);
    const hsSel = mk("select", "jd-sx-hs");
    hsSel.id = "jd-sx-hs";
    hsSel.setAttribute("aria-label", "HS CODE");
    $("#sx-hs").after(hsSel);
    $("#sx-hs").hidden = true;
    hsSel.addEventListener("change", () => { const hs = $("#sx-hs"); hs.value = hsSel.value; hs.dispatchEvent(new Event("input", { bubbles: true })); });
    if (hsSmall) hsSmall.className = "jd-field-hint";
    $("span", ctryLabel)?.removeAttribute("data-sx-t");
    // (junhee) 2026-09-27 대상국은 분석 엔진이 판단하는 나라만(US·CN·JP·DE·VN, engine/company_import.py). 대만(TW)은 엔진이 거부하므로 뺀다.
    [...$("#sx-country").options].forEach((o) => { if (!ENGINE_ISO.includes(o.value)) o.remove(); });
    defaultCountries = $("#sx-country").innerHTML;
    // 배치: 드롭 → 파일명 → 개인정보 → 기업명 → HS·대상국 → 오류 → 버튼
    const fileLabel = $("#sx-file-label"), err = $("#sx-error"), actions = $(".sx-form-actions", form);
    const privacy = mk("div", "jd-sx-privacy", `<i class="ph ph-lock-key"></i><span></span>`);
    form.prepend(drop);
    drop.after(fileLabel);
    fileLabel.after(privacy);
    privacy.after(companyLabel);
    companyLabel.after(fields);
    fields.after(err);
    // 버튼: 왼쪽 양식 다운로드 · 업로드 가이드, 오른쪽 샘플 파일 사용 · 분석 화면 보기
    const left = mk("div", "jd-sx-actions-left");
    const tpl = mk("a", "jd-sx-btn", `<i class="ph ph-file-xls"></i><span></span>`);
    tpl.href = (window.JunheeDashboard && JunheeDashboard.TEMPLATE_URL) || "#"; tpl.setAttribute("download", "");
    const guide = mk("button", "jd-sx-btn", `<i class="ph ph-book-open-text"></i><span></span>`);
    guide.type = "button";
    guide.addEventListener("click", () => window.JunheeDashboard && JunheeDashboard.openGuide());
    left.append(tpl, guide);
    const sample = $("#sx-sample");
    sample.removeAttribute("data-sx-extra");
    sample.classList.add("jd-sx-btn");
    const right = mk("div", "jd-sx-actions-right");
    right.append(sample, $(".sx-primary", actions));
    actions.replaceChildren(left, right);
    $(".sx-primary span", right)?.removeAttribute("data-sx-t");
    // 샘플 파일 사용: widgets.js 가 기존 '샘플 파일 사용' 을 누른 뒤, 그 샘플 회사로 칸을 채운다
    sample.addEventListener("click", () => setTimeout(() => { const name = ($("#file-label")?.textContent || "").split(" · ")[0].trim(); if (name) fillFields({ name }); }, 0));
    hsLabel.dataset.jdText = "1";
    uploadTexts();
    resetHsOptions();
    function keepHsText() { if (hsText && hsText.nodeType === 3) hsText.nodeValue = "HS CODE "; }
    keepHsText();
  }
  function uploadTexts() {
    const card = uploadCard();
    if (!card || !formReady) return;
    const set = (el, text) => { if (el) el.textContent = text; };
    set($("#sx-upload-title"), own("title"));
    set($(".sx-intro", card), own("intro"));
    set($("#sx-drop strong"), it("엑셀 파일을 끌어 놓거나 선택하세요"));
    set($("#sx-drop small"), it(".xlsx, .xls · 파일당 최대 20 MB"));
    set($(".jd-sx-privacy span"), own("privacy"));
    set($(".sx-company span", card), it("기업명"));
    set($(".sx-fields label:nth-child(2) span", card), it("대상국"));
    set($(".sx-fields .jd-field-hint", card), own("hsHint"));
    set($(".jd-sx-actions-left a span", card), own("template"));
    set($(".jd-sx-actions-left button span", card), own("guide"));
    set($("#sx-sample"), it("샘플 파일 사용"));
    set($(".sx-primary span", card), it("분석 화면 보기"));
  }
  // HS 선택지: 회사 파일 전(기본) = 위젯의 품목 칩(메모리 8542.32 · 시스템 8542.31 · 장비 8486.20), 회사 파일 후 = 회사 HS6 목록
  function resetHsOptions() {
    const sel = $("#jd-sx-hs");
    if (!sel) return;
    const cur = $("#sx-hs").value, J = window.JunheeDashboard;
    if (J && J.engineHsOptions) { // (junhee) 2026-09-27 분석 엔진이 판단하는 HS6 전체(집적회로·반도체 소자·제조장비)
      sel.innerHTML = J.engineHsOptions(cur, true);
      if (sel.value !== cur) sel.dispatchEvent(new Event("change"));
      return;
    }
    sel.innerHTML = $$(".sx-tags [data-sx-hs]").map((b) => `<option value="${b.dataset.sxHs}">${b.dataset.sxHs} · ${String(b.querySelector("span")?.textContent || "").trim()}</option>`).join("");
    if ([...sel.options].some((o) => o.value === cur)) sel.value = cur;
  }
  function companyOptions(doc, entry) {
    const sel = $("#jd-sx-hs"), ctry = $("#sx-country");
    const list = (doc.common.analysis_hs6 || []).map(hsDot);
    if (sel && list.length) {
      sel.innerHTML = list.map((h) => `<option value="${h}">HS ${h}</option>`).join("");
      sel.value = hsDot(entry.main_hs6) && list.includes(hsDot(entry.main_hs6)) ? hsDot(entry.main_hs6) : list[0];
      sel.dispatchEvent(new Event("change"));
    }
    if (ctry) {
      const countries = (doc.common.countries || []).filter((c) => c.iso2);
      if (countries.length) {
        ctry.innerHTML = countries.map((c) => `<option value="${c.iso2}">${c.name} (${c.iso2})${Number.isFinite(c.export_share) ? ` · ${(c.export_share * 100).toFixed(1)}%` : ""}</option>`).join("");
        const main = countries.find((c) => c.name === (entry.main_country || doc.common.main_country));
        if (main) ctry.value = main.iso2;
      }
    }
  }
  function restoreDefaults() { if (defaultCountries != null) $("#sx-country").innerHTML = defaultCountries; resetHsOptions(); }

  // ---- 5) 도구 막대(위젯 편집 모드 · 배치 초기화)를 머리글의 세계 시간 오른쪽으로 ----
  function moveToolbar() {
    const tb = $("#sx-toolbar"), header = $(".desktop-header"), clocks = $("#sx-clocks");
    if (!tb || !header) return;
    let center = $(".jd-header-center", header);
    if (!center) { center = document.createElement("div"); center.className = "jd-header-center"; header.insertBefore(center, (clocks && clocks.parentElement === header) ? clocks : $(".header-right", header)); }
    if (clocks && clocks.parentElement !== center) center.append(clocks);
    if (tb.parentElement !== center) center.append(tb);
    tb.classList.add("jd-in-header");
    toolbarTexts();
  }
  // (junhee) 2026-09-27 머리글 가운데 묶음(세계 시간·도구 막대)은 가운데 고정이라 오른쪽(언어 선택·날짜)과 서로를 모른다.
  // 영어·일본어처럼 글자가 길어져 겹치면 도구 막대 버튼을 아이콘만 보이게 한다(글자는 title·aria-label 로 남김). 스타일은 바꾸지 않는다.
  function fitHeader() {
    const center = $(".desktop-header .jd-header-center"), right = $(".desktop-header .header-right"), tb = $("#sx-toolbar");
    if (!right || !tb) return;
    const spans = [...tb.querySelectorAll("button span")];
    spans.forEach((sp) => (sp.hidden = false));
    const leftOfRight = () => Math.min(...[...right.children].filter((el) => el.offsetParent).map((el) => el.getBoundingClientRect().left));
    const rightEdge = () => Math.max(tb.getBoundingClientRect().right, center ? center.getBoundingClientRect().right : 0); // 도구 막대가 가운데 묶음 밖에 있을 수도 있다
    if (rightEdge() > leftOfRight() - 8) spans.forEach((sp) => (sp.hidden = true));
  }
  function toolbarTexts() {
    const e = $("#sx-edit"), r = $("#sx-reset");
    if (e) { e.title = own("edit"); e.setAttribute("aria-label", own("edit")); }
    if (r) { r.title = own("reset"); r.setAttribute("aria-label", own("reset")); }
  }

  // ---- 6) 위젯을 옮길 때 다른 위젯 크기 유지: 기본 배치 → 자유 배치로 바뀌는 순간 각 카드 높이를 기억해 자유 배치에서도 같은 높이로 ----
  const HKEY = "jd.widgets.heights.v1"; // widgets.js 의 저장 키(axsx.team.widgets.v1)와 별도
  const readHeights = () => { try { return JSON.parse(localStorage.getItem(HKEY) || "null") || {}; } catch { return {}; } };
  function rememberHeights() {
    const canvas = $("#sx-canvas");
    if (!canvas || canvas.classList.contains("sx-free")) return;
    const out = {};
    $$("[data-sx-widget]", canvas).forEach((w) => { if (!w.hidden && w.dataset.sxWidget !== "fx") out[w.dataset.sxWidget] = Math.round(w.offsetHeight); });
    try { localStorage.setItem(HKEY, JSON.stringify(out)); } catch {}
  }
  const forgetHeights = () => { try { localStorage.removeItem(HKEY); } catch {} };

  // ---- 7) 위젯 크기 조절: 편집 모드에서 카드 오른쪽 아래 모서리를 끌어 너비·높이를 바꾼다 ----
  // 너비는 widgets.js 가 저장하는 positions.w 에 남기려고 끝난 뒤 방향키 이동(±10px)을 한 번 보내 widgets.js 가 스스로 저장하게 한다.
  // 높이는 브리지 저장소(jd.widgets.heights.v1)에 남기고 clampFree 가 적용한다. 배치 초기화하면 둘 다 기본으로 돌아간다.
  const MIN_W = 280, MIN_H = 140;
  function nudge(w) {
    const h = $(".sx-handle", w);
    if (!h) return;
    const send = (key) => h.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    if (w.offsetLeft >= 10) { send("ArrowLeft"); send("ArrowRight"); } else { send("ArrowRight"); send("ArrowLeft"); }
  }
  function addResizers() {
    $$("[data-sx-widget]").forEach((w) => {
      if ($(".jd-resize", w)) return;
      const grip = document.createElement("span");
      grip.className = "jd-resize";
      grip.setAttribute("role", "separator");
      grip.setAttribute("aria-label", "위젯 크기 조절");
      grip.title = "끌어서 위젯 크기 조절";
      grip.innerHTML = '<i class="ph ph-arrows-out-simple"></i>';
      w.append(grip);
      grip.addEventListener("pointerdown", (ev) => {
        if (ev.button !== 0 || !board()?.classList.contains("sx-editing")) return;
        ev.preventDefault(); ev.stopPropagation();
        const canvas = $("#sx-canvas");
        if (!canvas.classList.contains("sx-free")) nudge(w); // 기본 배치면 먼저 자유 배치로 (widgets.js freeze)
        const b = board(), start = { x: ev.clientX, y: ev.clientY, w: w.offsetWidth, h: w.offsetHeight };
        grip.setPointerCapture(ev.pointerId);
        w.classList.add("jd-resizing");
        const move = (e) => {
          const maxW = canvas.clientWidth - w.offsetLeft, maxH = b.clientHeight - 8 - w.offsetTop;
          w.style.width = Math.round(Math.max(MIN_W, Math.min(maxW, start.w + e.clientX - start.x))) + "px";
          const hh = Math.round(Math.max(MIN_H, Math.min(maxH, start.h + e.clientY - start.y)));
          w.style.maxHeight = maxH + "px";
          w.style.height = hh + "px";
        };
        const end = () => {
          grip.removeEventListener("pointermove", move);
          grip.removeEventListener("pointerup", end);
          grip.removeEventListener("pointercancel", end);
          w.classList.remove("jd-resizing");
          const heights = readHeights();
          heights[w.dataset.sxWidget] = w.offsetHeight;
          try { localStorage.setItem(HKEY, JSON.stringify(heights)); } catch {}
          nudge(w); // widgets.js 가 현재 너비(offsetWidth)를 positions.w 로 저장
          fitSoon();
        };
        grip.addEventListener("pointermove", move);
        grip.addEventListener("pointerup", end);
        grip.addEventListener("pointercancel", end);
      });
      // 키보드: 모서리에 초점을 두고 Shift+방향키로 크기 조절
      grip.tabIndex = 0;
      grip.addEventListener("keydown", (ev) => {
        const d = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }[ev.key];
        if (!d || !board()?.classList.contains("sx-editing")) return;
        ev.preventDefault(); ev.stopPropagation();
        const canvas = $("#sx-canvas");
        if (!canvas.classList.contains("sx-free")) nudge(w);
        const step = ev.shiftKey ? 40 : 10, b = board();
        w.style.width = Math.max(MIN_W, Math.min(canvas.clientWidth - w.offsetLeft, w.offsetWidth + d[0] * step)) + "px";
        w.style.height = Math.max(MIN_H, Math.min(b.clientHeight - 8 - w.offsetTop, w.offsetHeight + d[1] * step)) + "px";
        const heights = readHeights(); heights[w.dataset.sxWidget] = w.offsetHeight;
        try { localStorage.setItem(HKEY, JSON.stringify(heights)); } catch {}
        nudge(w);
      });
    });
  }

  // ---- 8) 위젯 공식 자료: static/data/widgets/widgets.json (fetch_widget_data.py 결과) 을 위젯 칸에 넣는다 ----
  // minjung widgets.js 는 키가 없어 예시 데이터를 그리므로, 같은 DOM 모양으로 공식 자료를 다시 그린다.
  // widgets.js 가 언어 변경·2시간 새로고침 때 다시 그리면(표시 없는 행) 관찰자가 알아채고 다시 넣는다. 자료 파일이 없으면 아무것도 바꾸지 않는다.
  const WIDGET_URL = "/static/data/widgets/widgets.json";
  let wdata = null, applying = false;
  const WT = (k) => { const L = window.AXSX_TEXT || {}; return (L[lang()] || L.ko || {})[k] || (L.ko || {})[k] || k; };
  const nf = (v, d) => new Intl.NumberFormat((window.AXPI18n && AXPI18n.locale) || "ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; n.dataset.jdLive = "1"; return n; };
  const OWN_SRC = {
    officialFx: { ko: "공식 환율", en: "Official rate", zh: "官方汇率", ja: "公式レート" },
    officialStat: { ko: "공식 통계", en: "Official data", zh: "官方统计", ja: "公式統計" },
    rss: { ko: "뉴스 RSS", en: "News RSS", zh: "新闻 RSS", ja: "ニュースRSS" },
    prevDay: { ko: "전 영업일 대비", en: "vs previous business day", zh: "较前一营业日", ja: "前営業日比" },
  };
  const own2 = (k) => OWN_SRC[k][lang()] || OWN_SRC[k].ko;
  function badge(kind, text) {
    const b = $(`#sx-${kind}-badge`);
    if (!b) return;
    b.textContent = text;
    b.classList.add("live");
    b.hidden = false;
  }
  function footer(kind, text) {
    const s = $(`#sx-${kind}-source`);
    if (!s) return;
    s.textContent = text;
    const f = s.closest("footer");
    if (f) f.hidden = false;
  }
  function applyFx() {
    const d = wdata && wdata.fx, box = $("#sx-fx-rows");
    if (!d || !box || !(d.rows || []).length) return;
    box.replaceChildren(...d.rows.map((r) => {
      const row = el("div", "sx-rate");
      const up = r.change != null && r.change >= 0;
      row.append(el("span", "", r.pair), el("strong", "", nf(r.value, r.pair.endsWith("CNY") ? 4 : 2)),
        el("small", r.change == null ? "" : up ? "sx-up" : "sx-down", r.change == null ? WT("noPrevious") : `${up ? "↑" : "↓"} ${nf(Math.abs(r.change), 2)}%`));
      return row;
    }));
    box.dataset.jdLive = "1";
    decorateFx();
    badge("fx", own2("officialFx"));
    footer("fx", `${lang() === "ko" ? d.source : d.source_en || d.source} · ${d.as_of} · ${own2("prevDay")}`);
  }
  function applyNews() {
    const all = wdata && wdata.news, box = $("#sx-news-rows");
    const d = all && (all[lang()] && all[lang()].rows && all[lang()].rows.length ? all[lang()] : all.ko);
    if (!d || !box || !(d.rows || []).length) return;
    box.replaceChildren(...d.rows.map((r) => {
      const it = el("article", "sx-news-item");
      let title = el("strong", "", r.title);
      try { const u = new URL(r.url); if (["https:", "http:"].includes(u.protocol)) { title = el("a", "", r.title); title.href = u.href; title.target = "_blank"; title.rel = "noopener noreferrer"; } } catch {}
      it.append(title, el("small", "", [r.source, r.published_at ? r.published_at.slice(0, 10) : ""].filter(Boolean).join(" · ")));
      return it;
    }));
    box.dataset.jdLive = "1";
    badge("news", own2("rss"));
    footer("news", `${d.source || ""} · ${(all.fetched_at || "").slice(0, 10)}`);
  }
  function applyWeather() {
    const d = wdata && wdata.weather, body = $("#sx-weather-rows");
    if (!d || !body || !(d.rows || []).length) return;
    body.replaceChildren(...d.rows.map((r) => {
      const v = r.yoy, icon = v == null ? "—" : v >= 30 ? "☀️" : v >= 0 ? "⛅" : v >= -10 ? "☁️" : v >= -20 ? "🌧️" : "⛈️";
      const tr = el("tr", "");
      const name = el("td", "", `${icon} ${WT(r.id)}`);
      name.title = `HS ${r.hs.join(", ")}`;
      tr.append(name, el("td", "", nf(r.exports_million_usd, 0)), el("td", v >= 0 ? "sx-up" : "sx-down", v == null ? WT("noComparison") : `${v >= 0 ? "↑" : "↓"} ${nf(Math.abs(v), 1)}%`));
      return tr;
    }));
    body.dataset.jdLive = "1";
    badge("weather", own2("officialStat"));
    const p = $("#sx-weather-period");
    if (p) p.textContent = `${WT("base")}: ${d.period}, ${WT("cumulative")}`;
    footer("weather", `${lang() === "ko" ? d.source : d.source_en || d.source} · ${d.compare} ${lang() === "ko" ? "대비" : "vs"}`);
  }
  function applyWidgets() {
    if (!wdata || applying) return;
    applying = true;
    try { applyFx(); applyNews(); applyWeather(); } finally { applying = false; }
  }
  // widgets.js 가 다시 그린 경우(첫 자식에 표시 없음)에만 다시 넣는다 → 자기 자신이 바꾼 변경에는 반응하지 않음
  function watchWidget(sel) {
    const box = $(sel);
    if (!box) return;
    new MutationObserver(() => {
      if (applying || !wdata) return;
      const first = box.firstElementChild;
      if (first && first.dataset.jdLive === "1") return;
      setTimeout(applyWidgets, 0);
    }).observe(box, { childList: true });
  }
  async function loadWidgetData() {
    try {
      const r = await fetch(WIDGET_URL, { cache: "no-store" });
      if (r.ok) wdata = await r.json();
    } catch { wdata = null; }
    applyWidgets();
  }

  function init() {
    if (!ready()) { window.JunheeWidgetBridge = Object.freeze({ ready: () => false, dropAt: () => null, loadDesktopFile: async () => false, fit: () => {} }); return; }
    const icons = $("#desktop-icons");
    icons.addEventListener("pointermove", markDrag);
    ["pointerup", "pointercancel", "lostpointercapture"].forEach((t) => icons.addEventListener(t, clearMark, true));
    document.addEventListener("submit", (e) => { if (e.target && e.target.id === "analysis-form") mapCountry(); }, true);
    // 위젯 머리를 끌기 시작하거나 방향키로 옮기기 직전(widgets.js 가 자유 배치로 바꾸기 전)에 높이를 기억
    document.addEventListener("pointerdown", (e) => { if (e.button === 0 && e.target.closest && e.target.closest("#sx-board .sx-handle") && !e.target.closest("button")) rememberHeights(); }, true);
    document.addEventListener("keydown", (e) => { if (e.key.startsWith("Arrow") && e.target.closest && e.target.closest("#sx-board .sx-handle")) rememberHeights(); }, true);
    $("#sx-reset")?.addEventListener("click", forgetHeights);
    window.addEventListener("resize", fitSoon);
    window.addEventListener("axp:window-layout", fitSoon); // workspace.js: 전체 화면 진입·해제
    document.addEventListener("fullscreenchange", fitSoon);
    const win = $("#analysis-window");
    if (win) new MutationObserver(fitSoon).observe(win, { attributes: true, attributeFilter: ["hidden", "class"] }); // 분석 창 열기·닫기·최대화
    new MutationObserver(fitSoon).observe(icons, { childList: true }); // 아이콘 다시 그림(열 수 변화)
    // 자유 배치 전환·위젯 이동(style 변경) 뒤 카드 높이 다시 제한 (같은 값이면 style 을 건드리지 않아 반복되지 않음)
    const cv = $("#sx-canvas");
    if (cv) new MutationObserver(fitSoon).observe(cv, { attributes: true, attributeFilter: ["class", "style"], subtree: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitSoon);
    decorateHeads();
    decorateFx();
    buildUploadForm();
    moveToolbar();
    fitHeader(); // (junhee)
    window.addEventListener("resize", fitHeader); // (junhee)
    { // (junhee) 번역은 비동기로 늦게 적용되므로, 도구 막대·세계 시간·날짜 글자가 실제로 바뀔 때마다 다시 잰다(버튼 글자 숨김은 속성 변경이라 감시 대상 아님)
      let raf = 0;
      const again = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(fitHeader); };
      const mo = new MutationObserver(again);
      ["#sx-toolbar", "#sx-clocks", "#desktop-date"].forEach((sel) => { const el = $(sel); if (el) mo.observe(el, { childList: true, characterData: true, subtree: true }); });
    }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitHeader); // (junhee)
    addResizers();
    ["#sx-fx-rows", "#sx-news-rows", "#sx-weather-rows"].forEach(watchWidget);
    loadWidgetData();
    setInterval(loadWidgetData, 30 * 60 * 1000); // 30분마다 자료 파일 다시 읽기 (run_live.py 가 파일을 새로 만든다)
    window.addEventListener("axp:language-changed", () => setTimeout(applyWidgets, 0));
    if ($("#sx-fx-rows")) new MutationObserver(decorateFx).observe($("#sx-fx-rows"), { childList: true });
    // 언어 변경: widgets.js 가 칩·옵션 문구를 먼저 바꾼 뒤 우리 문구·HS 선택지를 다시 쓴다
    window.addEventListener("axp:language-changed", () => setTimeout(() => { uploadTexts(); toolbarTexts(); if (!lastDoc) resetHsOptions(); fitHeader(); /* (junhee) 언어별 글자 길이로 겹침 재확인 */ }, 0));
    window.JunheeWidgetBridge = Object.freeze({ ready, dropAt, loadDesktopFile, fit, uploadVisible, focusUpload, loadOsFile }); // (junhee) 2026-09-27 업로드 아이콘 연동
    fit();
    setTimeout(fit, 400); // widgets.js 의 첫 배치(글꼴 로드 후 layout) 뒤 한 번 더
  }
  // defer 스크립트 실행 중에는 readyState 가 이미 "interactive" 라서 바로 init 하면 뒤따르는 widgets.js 보다 먼저 돈다.
  // → DOMContentLoaded(모든 defer 스크립트 실행 뒤) 에서 한 번만 시작한다. 이미 지났으면 load 에서.
  let started = false;
  const start = () => { if (started) return; started = true; init(); };
  if (document.readyState === "complete") start();
  else { document.addEventListener("DOMContentLoaded", start, { once: true }); window.addEventListener("load", start, { once: true }); }
})();
