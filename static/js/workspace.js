"use strict";
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const t = (source) => window.AXPI18n?.t(source) || source;
  const countryCodes = {US:"미국",JP:"일본",DE:"독일",VN:"베트남",CN:"중국"}; // (junhee) 2026-09-27 CN: 분석 엔진 후보국
  const countryLabel = (code) => t(countryCodes[code] || code);
  const displayDate = () => {const loc = window.AXPI18n?.locale || "ko-KR"; $("#desktop-date").textContent = new Date().toLocaleDateString(loc, {month: /^ko/.test(loc) ? "long" : "short",day:"numeric",weekday:"short"});}; // (junhee) 2026-09-27 외국어는 짧은 월(Sep) — 머리글 겹침 방지
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const esc = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
  const icons = $("#desktop-icons"),
    desk = $("#desktop"),
    win = $("#analysis-window"),
    sidebar = $("#window-sidebar"),
    sidebarToggle = $("#sidebar-toggle");
  const defaults = { market: 35, price: 30, logistics: 20, stability: 15 };
  let weights = { ...defaults },
    draft = { ...defaults },
    customWeights = false;
  // (junhee) 처음에는 아무 회사도 선택되지 않은 상태. 점수는 등록된 더미 파일을 열었을 때만 채워진다.
  let context = {
    company: "미선택",
    hs: "854231",
    country: "US",
    file: "",
    fileId: null,
  };
  let pendingFile = null,
    activeTab = "overview",
    chart = null,
    selected = null,
    maximized = false;
  // (junhee) 2026-09-27 바탕화면 샘플을 sanghyeob 샘플로 교체 (junhee/data/engine_samples.json · 파일은 static/samples/). 모두 가상 기업이며 분석 엔진으로 계산한다.
  const SAMPLE_DEFAULTS = {
    gaon: { company: "가온반도체", hs: "854232", country: "US" },
    nuri: { company: "누리하이테크", hs: "854232", country: "US" },
    mirinae: { company: "미리내전자", hs: "854232", country: "US" },
    hanbit: { company: "한빛반도체", hs: "854232", country: "US" },
    daesung: { company: "대성일렉트로닉스", hs: "854232", country: "CN" },
    hanul: { company: "한울메모리", hs: "854232", country: "US" },
    daon: { company: "다온메모리웍스", hs: "854232", country: "US" },
  };
  let files = [
    // (junhee) 2026-09-27 바탕화면에는 쓰는 회사 파일 3개만 둔다(간편입력 v2 · 가상 기업). 한빛·대성 v0.1 은 static/samples 에만 남음. 칸은 arrangeIcons() 가 정렬
    { id: "sample-gaon", name: "기업데이터_가상_가온반도체.xlsx", size: 0, sample: true, trash: false, cell: 3, company_id: "gaon" }, // 대형 종합 메모리 제조사형
    { id: "sample-nuri", name: "기업데이터_가상_누리하이테크.xlsx", size: 0, sample: true, trash: false, cell: 4, company_id: "nuri" }, // HBM 특화 제조사형
    { id: "sample-mirinae", name: "기업데이터_가상_미리내전자_결측.xlsx", size: 0, sample: true, trash: false, cell: 5, company_id: "mirinae" }, // 결측 예시
  ];
  const ENGINE_ONLY = true; // (junhee) 2026-09-27 모든 파일을 sanghyeob 분석 엔진으로 계산 (기존 등록 샘플 점수표 경로는 쓰지 않음)
  const systemIcons = [
    {
      id: "analysis",
      name: "분석 대시보드",
      icon: "chart-pie-slice",
      cell: 0,
    },
    { id: "trash", name: "휴지통", icon: "trash", cell: 2 },
    // (junhee) 바탕화면 고정 아이콘: 더블클릭/Enter → 위젯 '기업 분석 데이터 업로드'(닫혀 있으면 업로드 창), 파일을 끌어 놓으면 그 파일로 분석
    { id: "upload", name: "기업 분석 데이터 업로드", icon: "upload-simple", cell: 5 }, // (junhee) 2026-09-27 이름 변경(기업 데이터 업로드 → 기업 분석 데이터 업로드)
    // (junhee) 2026-09-27 기업 파일 업로드: 올린 엑셀을 작업 데이터 폴더(junhee/data/samples/uploads)에 저장하고 바탕화면 회사 파일로 등록
    { id: "company-file", name: "기업 파일 업로드", icon: "file-arrow-up", cell: 3 },
  ];
  const names = {
    overview: "종합",
    regulation: "규제",
    market: "시장성",
    price: "가격",
    logistics: "물류",
    stability: "안정성",
  };
  const colors = {
    regulation: "#e94c98",
    market: "#9565d8",
    price: "#32b5d2",
    logistics: "#efa44d",
    stability: "#39ad96",
  };
  // ---- 요약 카드 실제 데이터 연결 (junhee) ------------------------------
  // static/data/dashboard_summary.json 을 읽어 종합 탭 5개 카드에 넣는다.
  // 상태는 loading / ok / insufficient / error 를 문구로 구분한다 (색상만으로 구분하지 않음).
  const SUMMARY_SRC =
    ($("#tab-content") && $("#tab-content").dataset.summarySrc) ||
    "/static/data/dashboard_summary.json";
  let summary = { status: "loading", items: {}, context: null, error: "" };
  function loadSummary() {
    summary = { status: "loading", items: {}, context: null, error: "" };
    fetch(SUMMARY_SRC, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then((doc) => {
        if (!doc || !Array.isArray(doc.items)) throw new Error("형식 오류");
        const items = {};
        doc.items.forEach((it) => {
          if (it && it.key) items[it.key] = it;
        });
        summary = {
          status: "ok",
          items,
          context: doc.context || null,
          error: "",
          generatedAt: doc.generated_at || "",
        };
      })
      .catch((e) => {
        console.error("AXPORT summary:", e);
        summary = {
          status: "error",
          items: {},
          context: null,
          error: String((e && e.message) || e),
        };
      })
      .finally(() => {
        if (activeTab === "overview") setTab("overview");
      });
  }
  function summaryCard(key) {
    let item = summary.items[key];
    // 안정성은 목적국(결제통화)별 결과가 detail.per_country 에 있으면 현재 화면 조건의 나라 것을 쓴다
    if (item && item.detail && item.detail.per_country && item.detail.per_country[context.country]) {
      const pc = item.detail.per_country[context.country];
      item = {
        ...item,
        headline: pc.headline,
        note: pc.note,
        state: pc.state,
        as_of: pc.as_of !== undefined ? pc.as_of : item.as_of,
        source: pc.source || item.source,
      };
    }
    if (summary.status === "loading")
      return {
        state: "loading",
        value: "불러오는 중",
        desc: "실제 자료 요약을 불러오고 있습니다.",
        meta: "",
        foot: "상태: 로딩 중",
      };
    if (summary.status === "error")
      return {
        state: "error",
        value: "조회 실패",
        desc: "요약 자료를 불러오지 못했습니다. 파일 경로와 서버 상태를 확인하세요.",
        meta: summary.error ? "오류: " + summary.error : "",
        foot: "상태: 조회 실패 · 값 미표시",
      };
    if (!item)
      return {
        state: "error",
        value: "조회 실패",
        desc: "요약 자료에 이 항목이 없습니다.",
        meta: "",
        foot: "상태: 조회 실패 · 값 미표시",
      };
    const asOf = item.as_of
      ? "기준일 " + item.as_of
      : item.checked_on
        ? "기준일 없음 (확인일 " + item.checked_on + ")"
        : "기준일 없음";
    const meta = "출처 " + (item.source || "-") + " · " + asOf;
    const cls = item.data_class ? " · " + item.data_class : "";
    if (item.state === "insufficient")
      return {
        state: "insufficient",
        value: "자료 부족",
        desc: item.note || "필요한 자료가 없습니다.",
        meta,
        foot: "상태: 자료 부족" + cls,
      };
    return {
      state: "ok",
      value: item.headline || "-",
      desc: item.note || "",
      meta,
      foot: "상태: 정상" + cls,
    };
  }
  let toastTimer;
  const toast = (message) => {
    $("#toast").textContent = message;
    $("#toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("#toast").classList.remove("show"), 3500);
  };
  const openDialog = (id) => {
    const dlg = $(id);
    if (dlg.open) return;
    // (junhee) 2026-09-28 업로드 창은 비모달로 연다: 모달은 창 밖(바탕화면)을 조작할 수 없게 만들어 파일 아이콘을 끌어 넣을 수 없었다.
    // 반투명 배경은 클릭을 막지 않는 막(CSS body.jd-upload-open)으로 대신하고, 파일 아이콘은 그 위에 둔다.
    if (dlg.id === "upload-dialog") { dlg.classList.add("jd-nonmodal"); document.body.classList.add("jd-upload-open"); dlg.show(); dlg.focus(); return; }
    dlg.showModal();
  };
  $("#upload-dialog").addEventListener("close", () => { document.body.classList.remove("jd-upload-open"); $("#drop-zone").classList.remove("drag-over"); });
  document.addEventListener("keydown", (e) => { // (junhee) 비모달 창은 Esc 로 닫히지 않으므로 직접 닫는다(다른 모달 창이 위에 있으면 그 창이 먼저)
    const up = $("#upload-dialog");
    if (e.key === "Escape" && up.open && up.classList.contains("jd-nonmodal") && !document.querySelector("dialog:modal")) up.close();
  });
  const readUI = () => {
    try {
      return JSON.parse(localStorage.getItem("axport-ui-layout-v1") || "null");
    } catch {
      return null;
    }
  };
  const saveUI = () => {
    try {
      localStorage.setItem(
        "axport-ui-layout-v1",
        JSON.stringify({
          x: win.offsetLeft,
          y: win.offsetTop,
          w: win.offsetWidth,
          h: win.offsetHeight,
        }),
      );
    } catch {
      /* UI storage is optional. */
    }
  };
  // UI geometry only is persisted. User filenames, file contents and conditions stay in memory.
  function fitWindow() {
    // (junhee) 숨긴 창은 크기가 0 이라 좌표 계산이 틀어지므로 건너뛴다. showWindow() 가 다시 맞춘다.
    if (win.hidden || maximized || innerWidth <= 850) return;
    const bottomGap = 13,
      availableHeight = desk.clientHeight - 26;
    win.style.minHeight = Math.min(455, Math.max(220, availableHeight)) + "px";
    const width = Math.min(win.offsetWidth, desk.clientWidth - 83),
      height = Math.min(win.offsetHeight, availableHeight);
    win.style.width =
      Math.max(Math.min(690, desk.clientWidth - 83), width) + "px";
    win.style.height = Math.max(Math.min(455, availableHeight), height) + "px";
    win.style.left =
      Math.max(
        8,
        Math.min(win.offsetLeft, desk.clientWidth - win.offsetWidth - 72),
      ) + "px";
    win.style.top =
      Math.max(
        8,
        Math.min(
          win.offsetTop,
          desk.clientHeight - win.offsetHeight - bottomGap,
        ),
      ) + "px";
  }
  function resetWindow() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); // (junhee) 전체 화면이면 먼저 끝낸다
    win.style.cssText = "";
    maximized = false;
    win.classList.remove("maximized");
    $("#maximize-btn").setAttribute("aria-label", "창 최대화");
    try {
      localStorage.removeItem("axport-ui-layout-v1");
    } catch {}
    fitWindow();
  }
  // (junhee) 창이 숨겨진 동안 탭을 그렸으면 true. 숨긴 채로 그린 차트·점수 애니메이션은 보이지 않으므로
  // 창이 다시 나타날 때 한 번만 다시 그린다 (단순 최소화→복원은 스크롤·차트를 그대로 둔다).
  let staleWhileHidden = false;
  function showWindow() {
    win.hidden = false;
    fitWindow();
    if (staleWhileHidden) {
      staleWhileHidden = false;
      setTab(activeTab);
    }
  }
  function hideWindow() {
    win.hidden = true;
  }
  function setSidebarOpen(open) {
    sidebar.hidden = !open;
    win.classList.toggle("sidebar-collapsed", !open);
    const label = open ? "사이드바 접기" : "사이드바 펼치기";
    sidebarToggle.setAttribute("aria-expanded", String(open));
    sidebarToggle.setAttribute("aria-label", label);
    sidebarToggle.title = label;
    // (junhee) WORKSPACE 줄의 접기 버튼·접힌 막대의 열기 버튼도 같은 상태로 맞춘다
    $$("#sidebar-collapse, #sidebar-open").forEach((b) => b.setAttribute("aria-expanded", String(open)));
    const rail = $("#sidebar-rail");
    if (rail) rail.hidden = open;
  }
  // (junhee) 사이드바 맨 위 'WORKSPACE' 오른쪽 끝 접기 버튼 + 접혔을 때 남는 44px 막대의 열기 버튼 (둘 다 setSidebarOpen 사용)
  $(".sidebar-caption", sidebar)?.insertAdjacentHTML("beforeend", `<button type="button" class="icon-btn jd-side-toggle" id="sidebar-collapse" aria-label="사이드바 접기" title="사이드바 접기" aria-controls="window-sidebar" aria-expanded="true"><i class="ph ph-sidebar-simple" aria-hidden="true"></i></button>`);
  sidebar.insertAdjacentHTML("afterend", `<div class="jd-side-rail" id="sidebar-rail" hidden><button type="button" class="icon-btn jd-side-toggle" id="sidebar-open" aria-label="사이드바 열기" title="사이드바 열기" aria-controls="window-sidebar" aria-expanded="false"><i class="ph ph-sidebar-simple" aria-hidden="true"></i></button></div>`);
  $("#sidebar-collapse").onclick = () => setSidebarOpen(false);
  $("#sidebar-open").onclick = () => { setSidebarOpen(true); $("#sidebar-collapse")?.focus(); };
  function grid() {
    return {
      rows: Math.max(3, Math.floor((desk.clientHeight - 95) / 106)),
      cols: Math.max(1, Math.floor((desk.clientWidth - 18) / 112)),
    };
  }
  function point(cell) {
    const { rows } = grid();
    return {
      x: 18 + Math.floor(cell / rows) * 112,
      y: 19 + (cell % rows) * 106,
    };
  }
  function occupied(except) {
    return new Set(
      [...systemIcons, ...files.filter((f) => !f.parent_id), ...(window.JunheeFiles ? JunheeFiles.folders() : [])] // (junhee) 폴더 안 파일은 칸을 차지하지 않고, 폴더 아이콘은 차지한다
        .filter((f) => !f.trash && f.id !== except)
        .map((f) => f.cell),
    );
  }
  function desktopIcon(id) {
    return (
      systemIcons.find((f) => f.id === id) || files.find((f) => f.id === id) ||
      (window.JunheeFiles ? JunheeFiles.folder(id) : undefined) // (junhee) 폴더 아이콘도 끌어서 옮긴다
    );
  }
  function emptyCell(want, id) {
    const { rows, cols } = grid(),
      used = occupied(id),
      limit = rows * cols;
    want = Math.max(0, Math.min(limit - 1, want));
    if (!used.has(want)) return want;
    for (let i = 0; i < limit; i++) if (!used.has(i)) return i;
    return null;
  }
  function nearestCell(x, y, id) {
    const { rows, cols } = grid();
    return emptyCell(
      Math.max(0, Math.min(cols - 1, Math.round((x - 18) / 112))) * rows +
        Math.max(0, Math.min(rows - 1, Math.round((y - 19) / 106))),
      id,
    );
  }
  function drawIcons() {
    if (window.JunheeFiles) JunheeFiles.normalize(); // (junhee) 휴지통·삭제된 폴더를 가리키는 파일은 바탕화면으로
    const entries = [
      systemIcons[0],
      ...files
        .filter((f) => !f.trash && !f.parent_id) // (junhee) 폴더 안 파일은 바탕화면에 그리지 않는다
        .map((f) => ({ ...f, icon: "microsoft-excel-logo" })),
      ...(window.JunheeFiles ? JunheeFiles.folders().filter((d) => !d.trash).map((d) => ({ ...d, icon: "folder-simple" })) : []), // (junhee) 폴더 아이콘
      ...systemIcons.slice(1), // (junhee) 휴지통 + 업로드 아이콘
    ];
    icons.innerHTML = entries
      .map((f) => {
        const p = point(f.cell);
        const nm = systemIcons.some((x) => x.id === f.id) ? t(f.name) : f.name; // (junhee) 2026-09-27 기본 아이콘 이름은 언어에 맞게(파일 이름은 그대로)
        return `<button class="desktop-icon ${selected === f.id ? "selected" : ""}" data-id="${esc(f.id)}" style="left:${p.x}px;top:${p.y}px" aria-label="${esc(nm)}" title="${esc(nm)} · 더블클릭으로 열기"><span class="file-image"><i class="ph ph-${f.icon}"></i></span><span class="file-name">${esc(nm)}</span></button>`;
      })
      .join("");
    $("#file-count").textContent = files.filter((f) => !f.trash).length;
    if (window.JunheeFiles) JunheeFiles.changed(); // (junhee) 바탕화면이 바뀌면 계정에 저장(잠시 모아서)
  }
  function selectIcon(id) {
    selected = id;
    $$(".desktop-icon").forEach((el) =>
      el.classList.toggle("selected", el.dataset.id === id),
    );
  }
  function trashFile(id) {
    const f = files.find((f) => f.id === id);
    if (!f && window.JunheeFiles && JunheeFiles.folder(id)) return JunheeFiles.askTrash(id); // (junhee) 폴더는 확인 후 안의 파일과 함께 휴지통으로
    if (!f) return; // 시스템 아이콘(분석 대시보드·업로드·휴지통)은 휴지통에 들어가지 않는다
    f.trash = true;
    selected = null;
    // (junhee) 삭제한 파일이 지금 대시보드에 열린 회사면 빈 상태로 되돌린다
    if (context.fileId === f.id || (window.JunheeDashboard && JunheeDashboard.isAnalyzed(f.source_name || f.name))) clearAnalysis(); // (junhee) 이름을 바꿔도 원본 파일명으로 비교
    if (pendingFile === f) pendingFile = null;
    drawIcons();
    toast("휴지통으로 삭제했습니다. 휴지통에서 복원할 수 있습니다.");
  }
  // (junhee) 불러온 회사 분석 결과를 비운다: 모듈 clear, 조건 '미선택', 파일 analyzed/conditions 해제, 종합 탭. 창 위치는 건드리지 않는다.
  function clearAnalysis() {
    if (window.JunheeDashboard) JunheeDashboard.clear();
    files.forEach((f) => { f.analyzed = false; delete f.conditions; });
    context = { company: "미선택", hs: "854231", country: "US", file: "", fileId: null };
    contextUI();
    setTab("overview");
  }
  // (junhee) 사이드바 '데이터 초기화': 분석 결과 비움 + 내가 올린(샘플 아닌) 파일 제거. 샘플 파일은 남는다.
  function resetData() {
    clearAnalysis();
    files = files.filter((f) => f.sample);
    pendingFile = null;
    selected = null;
    drawIcons();
    if ($("#files-dialog").open) $("#files-dialog").close();
    toast("데이터를 초기화했습니다.");
  }
  function openIcon(id) {
    if (id === "analysis") showWindow();
    else if (id === "trash") showFiles(true);
    else if (window.JunheeFiles && JunheeFiles.folder(id)) JunheeFiles.openFolder(id); // (junhee) 폴더 열기
    else if (id === "company-file") { if (window.JunheeFiles) JunheeFiles.pickCompanyFile(); } // (junhee) 2026-09-27 기업 파일 업로드
    else if (id === "upload") {
      // (junhee) 2026-09-27 업로드 아이콘 = 위젯 '기업 데이터 업로드'와 연동 (위젯을 닫아 두었으면 업로드 창)
      if (window.JunheeWidgetBridge && JunheeWidgetBridge.uploadVisible && JunheeWidgetBridge.uploadVisible()) return JunheeWidgetBridge.focusUpload();
      pendingFile = null;
      openUpload();
    } else {
      const f = files.find((f) => f.id === id);
      if (f && !f.trash && window.JunheeFiles) JunheeFiles.openExcel(f); // (junhee) 2026-09-27 회사 파일 열기 = 엑셀 파일 열기
      else analyzeFile(id);
    }
  }
  // (junhee) 2026-09-27 파일 분석(업로드 창): 우클릭 '분석하기' · 업로드 아이콘에 끌어 놓기
  function analyzeFile(id) {
    const f = files.find((f) => f.id === id);
    if (!f || f.trash) return;
    pendingFile = f;
    updateUploadLabel();
    openUpload();
  }
  // (junhee) 2026-09-27 대시보드 '기업 데이터' → 바로 종합 수출적합도. 저장된 조건(없으면 샘플 기본값)으로 분석하고 종합 탭을 연다.
  // 같은 조건으로 이미 분석한 파일은 저장된 결과를 다시 연다. 기업명·HS·대상국을 모르면 업로드 창에서 입력받는다.
  function showSuitability(id) {
    const f = files.find((x) => x.id === id && !x.trash);
    if (!f) return;
    if (engineBusy) return toast("분석이 진행 중입니다. 끝난 뒤 다시 선택해 주세요."); // (검토 반영) 진행 중인 분석 결과를 버리지 않게
    const own = f.conditions && f.conditions.company && f.conditions.company !== "미선택" ? f.conditions : null;
    const d = own || SAMPLE_DEFAULTS[f.company_id] || null;
    if (!d || !/^(\d{6}|\d{8}|\d{10})$/.test(String(d.hs || ""))) return analyzeFile(id);
    pendingFile = f;
    updateUploadLabel();
    $("#company-input").value = d.company;
    const hsSel = $("#hs-input");
    if (hsSel.tagName === "SELECT" && ![...hsSel.options].some((o) => o.value === d.hs)) hsSel.add(new Option(d.hs, d.hs));
    hsSel.value = d.hs;
    const cSel = $("#country-input");
    if (![...cSel.options].some((o) => o.value === d.country)) cSel.add(new Option(d.country, d.country));
    cSel.value = d.country;
    setTab("overview");
    showWindow();
    toast(`${f.name} · 종합 수출적합도를 계산합니다…`);
    runEngine(d.company, d.hs);
  }
  // (junhee) 2026-09-27 사이드바 'ANALYSIS · 분석 조건'에서 대상국·HS 를 바꾸면 지금 보는 파일을 그 조건으로 다시 계산한다(실패하면 알림만, 화면은 그대로)
  async function rerunConditions(next) {
    const f = files.find((x) => x.id === context.fileId && !x.trash);
    if (!f) return toast("분석한 파일을 바탕화면에서 찾을 수 없습니다. 파일을 휴지통에서 복원하거나 다시 올려 주세요.");
    if (engineBusy) return toast("분석이 진행 중입니다. 끝난 뒤 다시 선택해 주세요.");
    const cur = f.conditions || context;
    const d = { company: cur.company || context.company, hs: next.hs || cur.hs, country: next.country || cur.country };
    if (!/^(\d{6}|\d{8}|\d{10})$/.test(String(d.hs || ""))) return toast("분석할 HS 코드를 하나 선택해 주세요.");
    pendingFile = f;
    updateUploadLabel();
    $("#company-input").value = d.company;
    const hsSel = $("#hs-input");
    if (hsSel.tagName === "SELECT" && ![...hsSel.options].some((o) => o.value === d.hs)) hsSel.add(new Option(d.hs, d.hs));
    hsSel.value = d.hs;
    const cSel = $("#country-input");
    if (![...cSel.options].some((o) => o.value === d.country)) cSel.add(new Option(d.country, d.country));
    cSel.value = d.country;
    toast(`${f.name} · 조건을 바꿔 다시 계산합니다…`);
    await runEngine(d.company, d.hs);
  }
  // (junhee) 2026-09-27 바탕화면 정렬: 첫 줄(세로)에 분석 대시보드·기업 데이터 업로드·휴지통, 다음 줄부터 파일·폴더를 이름순으로
  function arrangeIcons() {
    const { rows } = grid();
    const order = ["analysis", "upload", "company-file", "trash"].map((sid) => systemIcons.find((x) => x.id === sid)).filter(Boolean);
    order.forEach((ic, i) => (ic.cell = i));
    const items = [...files.filter((f) => !f.trash && !f.parent_id), ...(window.JunheeFiles ? JunheeFiles.folders().filter((d) => !d.trash) : [])]
      .sort((a, b) => (a.kind === "folder") - (b.kind === "folder") || a.name.localeCompare(b.name, "ko"));
    const start = Math.max(order.length, rows); // 다음 열의 맨 위부터
    items.forEach((it, i) => (it.cell = start + i));
    drawIcons();
  }
  icons.addEventListener("click", (e) => {
    const el = e.target.closest("[data-id]");
    if (el) selectIcon(el.dataset.id);
  });
  icons.addEventListener("dblclick", (e) => {
    const el = e.target.closest("[data-id]");
    if (el) openIcon(el.dataset.id);
  });
  icons.addEventListener("keydown", (e) => {
    const el = e.target.closest("[data-id]");
    if (!el) return;
    const id = el.dataset.id;
    selectIcon(id);
    if (e.key === "Enter") {
      e.preventDefault();
      openIcon(id);
    } else if (e.key === "Delete") {
      e.preventDefault();
      trashFile(id);
    } else if (e.key.startsWith("Arrow")) {
      const f = desktopIcon(id);
      if (!f) return;
      e.preventDefault();
      const { rows } = grid();
      const delta = {
          ArrowDown: 1,
          ArrowUp: -1,
          ArrowLeft: -rows,
          ArrowRight: rows,
        }[e.key],
        cell = emptyCell(f.cell + delta, id);
      if (cell !== null) f.cell = cell;
      drawIcons();
      $(`[data-id="${id}"]`, icons)?.focus();
    }
  });
  icons.addEventListener("pointerdown", (e) => {
    const el = e.target.closest("[data-id]");
    if (!el || e.button !== 0) return;
    const id = el.dataset.id,
      f = desktopIcon(id);
    selectIcon(id);
    if (!f) return;
    const start = {
      x: e.clientX,
      y: e.clientY,
      left: el.offsetLeft,
      top: el.offsetTop,
    };
    let moved = false;
    el.setPointerCapture(e.pointerId);
    // (junhee) 파일 아이콘을 끌 때 휴지통·업로드 아이콘 위에 있으면 테두리로 강조
    const overTarget = (ev, target) => {
      if (!target || target === el) return false;
      const r = target.getBoundingClientRect();
      return ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom;
    };
    const markTargets = (ev) => {
      ["trash", "upload"].forEach((t) => {
        const target = $(`[data-id="${t}"]`, icons);
        if (target) target.classList.toggle("drop-hover", !!ev && files.includes(f) && overTarget(ev, target));
      });
    };
    const move = (ev) => {
      if (
        Math.abs(ev.clientX - start.x) + Math.abs(ev.clientY - start.y) < 5 &&
        !moved
      )
        return;
      moved = true;
      markTargets(ev);
      const up = $("#upload-dialog"); // (junhee) 2026-09-28 파일 아이콘을 열린 업로드 창 위로 끌면 끌어 놓기 칸을 강조
      if (up.open) { $("#drop-zone").classList.toggle("drag-over", files.includes(f) && overTarget(ev, up)); icons.style.zIndex = "1001"; } // 끄는 동안만 아이콘 층을 업로드 창 위로
      el.style.zIndex = "6";
      el.style.left =
        Math.max(
          0,
          Math.min(desk.clientWidth - 100, start.left + ev.clientX - start.x),
        ) + "px";
      el.style.top =
        Math.max(
          0,
          Math.min(desk.clientHeight - 100, start.top + ev.clientY - start.y),
        ) + "px";
    };
    const cleanup = () => {
      icons.style.zIndex = ""; // (junhee) 2026-09-28 끄는 동안 올린 아이콘 층을 원래대로
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerup", end);
      el.removeEventListener("pointercancel", cancel);
      el.removeEventListener("lostpointercapture", cancel);
      if (el.hasPointerCapture(e.pointerId))
        el.releasePointerCapture(e.pointerId);
    };
    const end = (ev) => {
      cleanup();
      if (!moved) return;
      const inRect = (target) => {
        if (!target || target.closest("[hidden]")) return false;
        const r = target.getBoundingClientRect();
        return (
          ev.clientX >= r.left &&
          ev.clientX <= r.right &&
          ev.clientY >= r.top &&
          ev.clientY <= r.bottom
        );
      };
      markTargets(null);
      $("#drop-zone").classList.remove("drag-over");
      if (files.includes(f) && $("#upload-dialog").open && inRect($("#upload-dialog"))) {
        drawIcons(); // (junhee) 2026-09-28 열린 업로드 창에 놓으면: 아이콘은 제자리로, 그 파일(과 저장된 조건)을 업로드 창에 넣는다
        analyzeFile(id);
        return;
      }
      const dropFolder = window.JunheeFiles ? JunheeFiles.folderAt(ev.clientX, ev.clientY, id) : null; // (junhee) 파일을 폴더 아이콘 위에 놓으면 폴더 안으로
      if (window.JunheeFiles && JunheeFiles.folder(id) && inRect($('[data-id="trash"]', icons))) {
        drawIcons(); // (junhee) 폴더를 휴지통에 놓으면 확인 후 이동
        JunheeFiles.askTrash(id);
      } else if (files.includes(f) && dropFolder) {
        JunheeFiles.moveInto(f, dropFolder);
      } else if (files.includes(f) && inRect($('[data-id="trash"]', icons)))
        trashFile(id);
      else if (files.includes(f) && inRect($('[data-id="upload"]', icons))) {
        // (junhee) 파일 아이콘을 업로드 아이콘 위에 놓으면 그 파일로 업로드 창을 연다
        drawIcons();
        if (window.JunheeWidgetBridge && JunheeWidgetBridge.uploadVisible && JunheeWidgetBridge.uploadVisible()) JunheeWidgetBridge.loadDesktopFile(f); // (junhee) 2026-09-27 업로드 아이콘 = 위젯과 연동
        else analyzeFile(id); // (junhee) 2026-09-27 열기(엑셀)와 분리
      } else if (files.includes(f) && window.JunheeWidgetBridge && JunheeWidgetBridge.dropAt(ev.clientX, ev.clientY)) {
        // (junhee) 바탕화면 위젯 위에 놓으면 아이콘은 원래 칸으로. '반도체 수출 데이터' 위젯이면 그 파일을 위젯에 넣는다(처리는 브리지)
        drawIcons();
        if (JunheeWidgetBridge.dropAt(ev.clientX, ev.clientY) === "upload") JunheeWidgetBridge.loadDesktopFile(f);
      } else {
        const cell = nearestCell(el.offsetLeft, el.offsetTop, id);
        if (cell !== null) f.cell = cell;
        drawIcons();
      }
    };
    const cancel = () => {
      cleanup();
      $("#drop-zone").classList.remove("drag-over"); // (junhee) 2026-09-28
      drawIcons();
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerup", end);
    el.addEventListener("pointercancel", cancel);
    el.addEventListener("lostpointercapture", cancel);
  });
  function bindWindowMove(handle, resize) {
    handle.addEventListener("pointerdown", (e) => {
      if (
        maximized ||
        e.button !== 0 ||
        innerWidth <= 850 ||
        e.target.closest("button")
      )
        return;
      e.preventDefault();
      const start = {
        x: e.clientX,
        y: e.clientY,
        left: win.offsetLeft,
        top: win.offsetTop,
        w: win.offsetWidth,
        h: win.offsetHeight,
      };
      handle.setPointerCapture(e.pointerId);
      const move = (ev) => {
        const dx = ev.clientX - start.x,
          dy = ev.clientY - start.y,
          bottomGap = 13;
        if (resize) {
          win.style.width =
            Math.max(
              690,
              Math.min(desk.clientWidth - start.left - 72, start.w + dx),
            ) + "px";
          win.style.height =
            Math.max(
              Math.min(455, desk.clientHeight - start.top - bottomGap),
              Math.min(desk.clientHeight - start.top - bottomGap, start.h + dy),
            ) + "px";
        } else {
          win.style.left =
            Math.max(
              8,
              Math.min(desk.clientWidth - start.w - 72, start.left + dx),
            ) + "px";
          win.style.top =
            Math.max(
              8,
              Math.min(desk.clientHeight - start.h - bottomGap, start.top + dy),
            ) + "px";
        }
      };
      const end = () => {
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", end);
        handle.removeEventListener("pointercancel", end);
        saveUI();
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", end);
      handle.addEventListener("pointercancel", end);
    });
  }
  bindWindowMove($("#window-handle"), false);
  bindWindowMove($("#resize-handle"), true);
  $("#resize-handle").addEventListener("keydown", (e) => {
    if (maximized || !e.key.startsWith("Arrow")) return;
    e.preventDefault();
    if (e.key === "ArrowRight") win.style.width = win.offsetWidth + 20 + "px";
    if (e.key === "ArrowLeft")
      win.style.width = Math.max(690, win.offsetWidth - 20) + "px";
    if (e.key === "ArrowDown") win.style.height = win.offsetHeight + 20 + "px";
    if (e.key === "ArrowUp")
      win.style.height = Math.max(455, win.offsetHeight - 20) + "px";
    fitWindow();
    saveUI();
  });
  $("#minimize-btn").onclick = hideWindow;
  $("#close-window-btn").onclick = hideWindow;
  sidebarToggle.onclick = () => setSidebarOpen(sidebar.hidden);
  const toggleMaximized = () => { // (junhee) 기존 '창 최대화' 동작 (전체 화면이 막힌 브라우저용 대체)
    maximized = !maximized;
    win.classList.toggle("maximized", maximized);
    $("#maximize-btn").setAttribute(
      "aria-label",
      maximized ? "이전 창 크기로 복원" : "창 최대화",
    );
    fitWindow();
  };
  // (junhee) □ 버튼 → 브라우저 전체 화면(Fullscreen API) + 분석 창이 화면 전체를 채움. Esc 는 브라우저가 전체 화면을 끝내고
  // fullscreenchange 에서 창을 이전 크기·위치로 되돌린다(인라인 위치 style 은 건드리지 않으므로 그대로 복원됨).
  const setFullUI = (on) => {
    win.classList.toggle("jd-fullscreen", on);
    const btn = $("#maximize-btn");
    btn.innerHTML = `<i class="ph ${on ? "ph-corners-in" : "ph-corners-out"}"></i>`;
    btn.setAttribute("aria-label", on ? "전체 화면 끝내기 (Esc)" : "전체 화면");
    btn.title = on ? "전체 화면 끝내기 (Esc)" : "전체 화면";
  };
  $("#maximize-btn").onclick = () => {
    if (document.fullscreenElement) return void document.exitFullscreen().catch(() => {});
    if (maximized) return toggleMaximized(); // 대체 모드(창 최대화)에서 복원
    const fallback = () => { toggleMaximized(); toast("브라우저가 전체 화면을 허용하지 않아 창 최대화로 표시합니다."); };
    if (!document.documentElement.requestFullscreen || document.fullscreenEnabled === false) return fallback();
    document.documentElement.requestFullscreen().then(() => {
      maximized = true;
      win.classList.add("maximized");
      setFullUI(true);
      window.dispatchEvent(new Event("axp:window-layout")); // (junhee) 위젯 브리지 등 배치 재조정 알림
    }).catch(fallback);
  };
  document.addEventListener("fullscreenchange", () => {
    if (document.fullscreenElement || !win.classList.contains("jd-fullscreen")) return;
    maximized = false;
    win.classList.remove("maximized");
    setFullUI(false);
    fitWindow();
    window.dispatchEvent(new Event("axp:window-layout")); // (junhee)
  });
  const formatHS = (hs) => hs.slice(0, 4) + "." + hs.slice(4);
  function contextUI() {
    $("#company-context").textContent = context.company;
    $("#hs-context").textContent = context.hs === "all" ? "전체" : formatHS(context.hs); // (junhee) 전체 HS
    $("#country-context").textContent = countryLabel(context.country);
    // (junhee) 기준일: 점수 JSON 의 as_of
    const asof = $("#asof-context");
    if (asof) {
      const cur = window.JunheeDashboard && JunheeDashboard.current();
      const per = cur && JunheeDashboard.period ? JunheeDashboard.period() : null; // (junhee) 기간 필터가 있으면 적용 기간
      asof.textContent = per ? (per.isDefault ? "자료기간 " : per.label + " ") + per.from + "~" + per.to : cur && cur.common && cur.common.period ? "자료기간 " + cur.common.period.from + "~" + cur.common.period.to : "";
    }
    if (window.JunheeFiles) JunheeFiles.changed(); // (junhee) 마지막 분석 조건을 계정에 저장
  }
  function heading(title, sub, kicker = "EXPORT INTELLIGENCE") {
    return `<div class="content-heading"><div><span class="eyebrow">${kicker}</span><h2>${title}</h2><p>${sub}</p></div><div class="heading-actions"><button class="small-button" aria-label="가중치 설정" data-action="weights"><i class="ph ph-sliders-horizontal"></i><span>가중치 설정</span></button><button class="small-button" aria-label="보고서 다운로드" data-action="report"><i class="ph ph-download-simple"></i><span>보고서</span></button></div></div>`;
  }
  function overview() {
    // (junhee) 점수형 종합 화면 모듈이 있으면 그것을 쓴다 (업로드 전 빈 상태 / 회사 선택 후 점수).
    // index3 종합 화면은 제목 없이 패널로 시작하고, 가중치·보고서 버튼은 모듈이 컨텍스트 바 오른쪽에 넣는다.
    if (window.JunheeDashboard) return JunheeDashboard.panelHTML();
    const cards = [
      {
        key: "regulation",
        icon: "shield-check",
        label: "규제",
        hint: "GATE",
        value: "검토 전",
        unit: "",
        desc: "필수 조건 확인이 필요한 단계",
        foot: "실제 판정 미실행",
        status: true,
      },
      {
        key: "market",
        icon: "trend-up",
        label: "시장성",
        hint: "MARKET",
        value: "82",
        unit: "/ 100",
        desc: "시장규모와 성장 흐름의 예시",
        foot: "성장 추세 예시",
      },
      {
        key: "price",
        icon: "currency-circle-dollar",
        label: "가격",
        hint: "PRICE",
        value: "76",
        unit: "/ 100",
        desc: "관세·환율 조건의 예시",
        foot: "가격 조건 예시",
      },
      {
        key: "logistics",
        icon: "airplane-tilt",
        label: "물류",
        hint: "LOGISTICS",
        value: "88",
        unit: "/ 100",
        desc: "운송 기간·비용의 예시",
        foot: "운송 시나리오 예시",
      },
      {
        key: "stability",
        icon: "wave-sine",
        label: "안정성",
        hint: "STABILITY",
        value: "71",
        unit: "/ 100",
        desc: "변동률 표시를 위한 예시",
        foot: "대상·산식 미확정",
      },
    ];
    return (
      heading(
        "한눈에 보는 수출 가능성",
        "기업의 다음 선택을 위한 다섯 가지 관점",
      ) +
      summaryBanner() +
      `<div class="score-grid">${cards
        .map((c) => {
          const s = summaryCard(c.key);
          return `<article class="score-card" style="--card-color:${colors[c.key]}" data-state="${s.state}"><div class="card-title"><i class="ph ph-${c.icon}"></i>${c.label}<small>${c.hint}</small></div><div class="metric status" style="white-space:normal;font-size:19px;line-height:1.3" title="${esc(s.value)}">${esc(s.value)}</div><p>${esc(s.desc)}</p>${s.meta ? `<p>${esc(s.meta)}</p>` : ""}<div class="card-foot"><span>${esc(s.foot)}</span><span>${c.key === "regulation" ? "관문 고정" : `비중 ${weights[c.key]}%`}</span></div></article>`;
        })
        .join("")}</div><div class="summary-foot"><span><i class="ph ph-info"></i>오른쪽 책갈피에서 상세 지표와 근거를 확인하세요.</span><span>${customWeights ? "사용자 가중치 · 시연" : "기본 가중치 · 시연"} · ${summaryFootNote()}</span></div>`
    );
  }
  function summaryBanner() {
    let strong = "가능성을 살펴보고, 근거를 확인하세요.";
    let p = "요약 자료를 불러오는 중입니다. 실제 규제 검토와 수출 판정은 진행되지 않았습니다.";
    let badge = "LOADING";
    if (summary.status === "ok") {
      const ctx = summary.context || {};
      const hsList = Array.isArray(ctx.hs) ? ctx.hs : ctx.hs ? [ctx.hs] : [];
      const basis = [
        hsList.length ? "HS " + hsList.map((h) => formatHS(String(h))).join("·") : "",
        ctx.country || "",
      ]
        .filter(Boolean)
        .join(" · ");
      strong = "공개 자료에서 추출한 요약값입니다.";
      p = `요약 카드는 실제 자료 기준${basis ? "(" + esc(basis) + ")" : ""}이며, 규제 판정·적합도 채점은 진행되지 않았습니다. 상세 탭은 예시입니다.`;
      badge = "DATA";
    } else if (summary.status === "error") {
      strong = "요약 자료를 불러오지 못했습니다.";
      p = "카드에 값을 표시하지 않습니다. 파일 경로와 서버 상태를 확인한 뒤 새로고침하세요.";
      badge = "ERROR";
    }
    return `<div class="analysis-banner"><span class="banner-icon"><i class="ph ph-magnifying-glass"></i></span><div><strong>${strong}</strong><p>${p}</p></div><span class="example-badge">${badge}</span></div>`;
  }
  function summaryFootNote() {
    if (summary.status === "ok") {
      const ctx = summary.context || {};
      const hsList = Array.isArray(ctx.hs) ? ctx.hs : ctx.hs ? [ctx.hs] : [];
      const mismatch = ctx.country && ctx.country !== context.country;
      const hsMismatch = hsList.length && !hsList.some((h) => String(context.hs).startsWith(String(h)));
      return (
        "요약 카드 실제 자료 연결" +
        (summary.generatedAt ? " (생성 " + esc(summary.generatedAt.slice(0, 10)) + ")" : "") +
        (mismatch ? ` · 주의: 요약 자료는 ${esc(ctx.country)} 기준` : "") +
        (hsMismatch ? ` · 주의: 요약 자료는 HS ${esc(hsList.join("·"))} 기준` : "")
      );
    }
    if (summary.status === "error") return "요약 자료 조회 실패";
    return "요약 자료 불러오는 중";
  }
  const detailData = {
    market: {
      title: "시장의 흐름을 읽다",
      sub: "시장규모와 성장률을 같은 시선으로 살펴보세요.",
      metrics: [
        ["수입시장 규모", "$128.4B"],
        ["전년 대비 성장률", "+12.8%"],
        ["시장성 예시 점수", "82 / 100"],
      ],
      chart: "수입시장 추이",
      labels: ["2021", "2022", "2023", "2024", "2025", "2026"],
      data: [76, 83, 91, 97, 114, 128.4],
      unit: "B USD",
      rows: [
        ["시장규모", "128.4B USD", "연간 합계 · 예시"],
        ["성장률", "12.8%", "전년 대비 · 예시"],
        ["수출입실적", "상세 조회 예정", "실제 데이터 미연결"],
      ],
      note: "실제 연결 시 목적국·HS 버전·조회 기간을 함께 표시합니다. 현재 숫자는 추이 차트 디자인을 위한 가상 값입니다.",
    },
    price: {
      title: "가격에 영향을 주는 조건",
      sub: "관세와 환율을 분리해서 살펴보세요.",
      metrics: [
        ["관세율 예시", "3.5%"],
        ["환율 예시", "1,340 KRW"],
        ["가격 예시 점수", "76 / 100"],
      ],
      chart: "환율 흐름 예시",
      labels: ["4월", "5월", "6월", "7월", "8월", "9월"],
      data: [1330, 1375, 1362, 1325, 1348, 1340],
      unit: "KRW / USD",
      rows: [
        ["관세", "3.5%", "적용 조건 검증 전"],
        ["환율", "1,340 KRW/USD", "기준일 미연결"],
        ["원산지·세번", "확인 필요", "실제 판정 미실행"],
      ],
      note: "예시 세율은 실제 목적국 관세율이 아닙니다. 원산지·세번·적용일과 결제 통화를 확인한 뒤 계산하도록 연동할 예정입니다.",
    },
    logistics: {
      title: "목적지까지의 계획",
      sub: "운송 경로와 기간, 비용을 함께 확인하세요.",
      metrics: [
        ["운송 기간 예시", "8일"],
        ["운송비 예시", "$2,400"],
        ["물류 예시 점수", "88 / 100"],
      ],
      chart: "구간별 소요 기간",
      labels: ["출고 준비", "내륙 운송", "국제 운송", "통관·배송"],
      data: [2, 1, 3, 2],
      unit: "일",
      bar: true,
      rows: [
        ["운송 수단", "항공 · 예시", "실제 견적 없음"],
        ["경로", "인천 → 목적국", "시연 시나리오"],
        ["납기", "확인 필요", "기업 조건 미분석"],
      ],
      note: "실제 운송 조회·견적·예약을 제공하지 않는 화면 시연입니다. 구간별 일정과 비용 근거가 이 영역에 연결됩니다.",
    },
    stability: {
      title: "변화를 살피는 또 하나의 관점",
      sub: "변동률의 크기와 흐름을 시각화합니다.",
      metrics: [
        ["변동률 예시", "4.2%"],
        ["관측 구간 예시", "6개월"],
        ["안정성 예시 점수", "71 / 100"],
      ],
      chart: "변동률 표시 예시",
      labels: ["4월", "5월", "6월", "7월", "8월", "9월"],
      data: [3.1, 5.2, 3.8, 4.7, 2.9, 4.2],
      unit: "%",
      rows: [
        ["대상 지표", "미확정", "PM 결정 필요"],
        ["계산 방식", "미확정", "표시는 가상 값"],
        ["분석 기간", "6개월 · 예시", "확정 기준 아님"],
      ],
      note: "변동률의 대상과 산식은 아직 정해지지 않았습니다. 이 화면은 UI 시연이며 국가위험 또는 신용등급을 의미하지 않습니다.",
    },
  };
  function detail(key) {
    if (key === "regulation")
      return (
        heading(
          "판정에 앞서, 반드시 확인할 조건",
          "규제 관문은 사업성 점수와 별도로 확인합니다.",
          "REGULATION CHECK",
        ) +
        `<div class="analysis-banner"><span class="banner-icon"><i class="ph ph-shield-check"></i></span><div><strong>규제 검토 전 · 실제 판정 미실행</strong><p>가중치를 변경해도 이 상태는 바뀌지 않습니다.</p></div><span class="example-badge">GATE</span></div><section class="detail-panel"><div class="panel-heading"><h3>필수 확인 항목</h3><span>화면 구성 예시</span></div><div class="table-wrap"><table><thead><tr><th>검토 항목</th><th>현재 상태</th><th>확인할 내용</th></tr></thead><tbody>${[
          ["전략물자 해당 여부", "제품 사양·분류"],
          ["거래 상대·최종사용자", "대상 목록·최종용도"],
          ["수출 허가 조건", "목적국·적용 규정"],
          ["원산지 및 증빙", "기업 증빙자료"],
        ]
          .map(
            (r) =>
              `<tr><td>${r[0]}</td><td><span class="tag">미검토</span></td><td>${r[1]}</td></tr>`,
          )
          .join(
            "",
          )}</tbody></table></div><p class="detail-help">규정·거래 제한 목록이 연결되지 않았습니다. 목록 불일치나 자료 누락을 ‘통과’로 표시하지 않습니다.</p></section>`
      );
    const d = detailData[key];
    return (
      heading(d.title, d.sub, key.toUpperCase() + " INSIGHT") +
      `<div class="detail-metrics">${d.metrics.map((m) => `<div class="detail-metric"><span>${m[0]}</span><strong style="color:${colors[key]}">${m[1]}</strong></div>`).join("")}</div><section class="chart-panel"><div class="panel-heading"><h3>${d.chart}</h3><span>${d.unit} · 예시 데이터</span></div><div class="chart-wrap"><canvas id="detail-chart" role="img" aria-label="${d.chart}, ${d.labels.map((l, i) => l + " " + d.data[i]).join(", ")}"></canvas></div></section><section class="detail-panel"><div class="panel-heading"><h3>지표와 판단 근거</h3><span>실제 자료 미연결</span></div><div class="table-wrap"><table><thead><tr><th>지표</th><th>표시값</th><th>근거 상태</th></tr></thead><tbody>${d.rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div><p class="detail-help">${d.note}</p></section>`
    );
  }
  function drawChart(key) {
    const d = detailData[key];
    if (!d || !$("#detail-chart") || !window.Chart) return;
    chart = new Chart($("#detail-chart"), {
      type: d.bar ? "bar" : "line",
      data: {
        labels: d.labels.map(t),
        datasets: [
          {
            data: d.data,
            borderColor: colors[key],
            backgroundColor: colors[key] + (d.bar ? "bb" : "15"),
            fill: true,
            borderWidth: 2,
            tension: 0.38,
            pointRadius: 3,
            pointBackgroundColor: "#fff",
            pointBorderWidth: 2,
            borderRadius: 5,
            barThickness: 32,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 400 },
        plugins: {
          legend: { display: false },
          tooltip: {
            displayColors: false,
            callbacks: { label: (ctx) => `${ctx.parsed.y} ${d.unit} · ${t("예시")}` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { font: { size: 10 }, color: "#a1aabc" },
          },
          y: {
            beginAtZero: d.bar,
            border: { display: false },
            grid: { color: "#f1f3f8" },
            ticks: { maxTicksLimit: 5, font: { size: 9 }, color: "#b1b9c7" },
          },
        },
      },
    });
  }
  function setTab(key) {
    if (key === "items" && window.JunheeDashboard) return showAllItems(); // (junhee) 2026-09-27 사이드바 '세부사항 (항목 전체 보기)'
    if (!names[key]) return;
    activeTab = key;
    sideActive(key !== "overview" && window.JunheeDashboard && JunheeDashboard.itemsOn() ? "items" : "overview", key);
    if (win.hidden) staleWhileHidden = true;
    chart?.destroy();
    chart = null;
    $$("[data-tab]").forEach((b) => {
      const on = b.dataset.tab === key;
      b.classList.toggle("selected", on);
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
    });
    // (junhee) 종합 탭과 상세 탭 5개는 점수형 모듈이 회사 점수·공개자료로 그린다 (모듈이 없으면 기존 예시 화면)
    const jdMeta = window.JunheeDashboard && key !== "overview" ? JunheeDashboard.detailMeta(key) : null;
    $("#tab-content").innerHTML =
      key === "overview" ? overview() : jdMeta ? JunheeDashboard.detailHTML(key) : detail(key);
    if (window.JunheeDashboard && (key === "overview" || jdMeta)) JunheeDashboard.mount($("#tab-content"), key);
    $("#tab-content").setAttribute("role", "tabpanel");
    $("#tab-content").setAttribute("aria-labelledby", "tab-" + key);
    $(".window-main").scrollTop = 0;
    drawChart(key);
    window.AXPI18n?.translateDOM($("#tab-content"));
  }
  // (junhee) 2026-09-27 '세부사항 (항목 전체 보기)': 다섯 영역의 모든 항목. 북마크 탭은 선택 해제, 영역 버튼(data-open-tab)으로 상세 탭 이동
  // 사이드바 '분석 대시보드'·'세부사항' 중 지금 화면 표시(기존 .active)
  function sideActive(action, key) {
    $$('.side-link[data-action="overview"], .side-link[data-action="items"]').forEach((b) => b.classList.toggle("active", b.dataset.action === action));
    const btn = $('.side-link[data-action="items"]');
    if (!btn) return;
    btn.setAttribute("aria-pressed", String(action === "items"));
    const c = window.JunheeDashboard && JunheeDashboard.current() ? JunheeDashboard.itemCount(key) : null; // 확인 건수는 툴팁으로(사이드바 폭 때문에 배지 없음)
    btn.title = c ? `확인됨 ${c.ok}/${c.total}` : "";
  }
  function showAllItems() {
    activeTab = "items";
    sideActive("items", "items");
    if (win.hidden) staleWhileHidden = true;
    chart?.destroy();
    chart = null;
    $$("[data-tab]").forEach((b) => {
      b.classList.remove("selected");
      b.setAttribute("aria-selected", "false");
      b.tabIndex = b.dataset.tab === "overview" ? 0 : -1;
    });
    $("#tab-content").innerHTML = JunheeDashboard.allItemsHTML();
    JunheeDashboard.mount($("#tab-content"), "items");
    $("#tab-content").removeAttribute("role");
    $("#tab-content").removeAttribute("aria-labelledby");
    $(".window-main").scrollTop = 0;
    window.AXPI18n?.translateDOM($("#tab-content"));
  }
  $$(".bookmark-tabs button").forEach((b) => {
    b.onclick = () => setTab(b.dataset.tab);
    b.onkeydown = (e) => {
      if (
        ![
          "ArrowDown",
          "ArrowUp",
          "ArrowLeft",
          "ArrowRight",
          "Home",
          "End",
        ].includes(e.key)
      )
        return;
      e.preventDefault();
      const all = $$(".bookmark-tabs button"),
        i = all.indexOf(b),
        next =
          e.key === "Home"
            ? 0
            : e.key === "End"
              ? all.length - 1
              : (i +
                  (["ArrowDown", "ArrowRight"].includes(e.key) ? 1 : -1) +
                  all.length) %
                all.length;
      all[next].focus();
      setTab(all[next].dataset.tab);
    };
  });
  // (junhee) 등록 샘플이면 회사 JSON(handoff-v1)의 main_hs6·main_country 로 채우고, 대상국 선택지를 그 회사의 countries 로 바꾼다.
  // 회사가 없으면 기존 고정 목록(US/JP/DE/VN)으로 되돌린다.
  const defaultCountryOptions = $("#country-input").innerHTML;
  const escAttr = (v) => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  if (window.JunheeDashboard && JunheeDashboard.engineHsOptions) $("#hs-input").innerHTML = JunheeDashboard.engineHsOptions("854232"); // (junhee) 2026-09-27 분석 엔진 지원 HS6 전체
  const defaultHsOptions = $("#hs-input").innerHTML;
  function fillHsOptions(list, selected) {
    const sel = $("#hs-input");
    if (!list || !list.length) { sel.innerHTML = defaultHsOptions; if (selected != null) sel.value = String(selected); return; }
    sel.innerHTML = `<option value="all">전체 HS (회사 제품 전체)</option>` + list.map((h) => `<option value="${escAttr(h)}">${escAttr(String(h).replace(/^(\d{4})(\d+)$/, "$1.$2"))}</option>`).join("");
    sel.value = list.includes(String(selected)) ? String(selected) : "all";
  }
  function fillCountryOptions(names, selected) {
    const sel = $("#country-input");
    if (!names || !names.length) {
      sel.innerHTML = defaultCountryOptions;
      if (selected != null) sel.value = selected;
      return;
    }
    sel.innerHTML = names.map((n) => `<option value="${escAttr(n)}">${escAttr(n)}</option>`).join("");
    sel.value = names.includes(selected) ? selected : names[0];
  }
  function syncUploadConditions(preferredCountry) {
    const reg = pendingFile && window.JunheeDashboard ? (pendingFile.raw ? pendingFile.match : JunheeDashboard.findByFileName(pendingFile.source_name || pendingFile.name)) : null; // (junhee) 이름을 바꿔도 원본 파일명
    if (!reg) {
      fillCountryOptions(null, preferredCountry);
      fillHsOptions(null, $("#hs-input").value);
      return;
    }
    const mine = pendingFile;
    JunheeDashboard.peek(reg.company_id)
      .then((doc) => {
        if (pendingFile !== mine) return;
        $("#company-input").value = doc.company_name;
        fillHsOptions(doc.common.analysis_hs6 || [], (pendingFile.conditions && pendingFile.conditions.hs) || "all"); // (junhee) 전체 HS + 회사 HS6 목록 드롭다운
        fillCountryOptions(doc.common.countries.map((c) => c.name), preferredCountry || doc.common.main_country);
      })
      .catch(() => fillCountryOptions(null, preferredCountry));
  }
  function updateUploadLabel() {
    $("#file-label").textContent = pendingFile
      ? pendingFile.name
      : "엑셀 파일을 끌어 놓거나 선택하세요";
    $("#upload-error").textContent = "";
  }
  function openUpload() {
    const own = pendingFile?.conditions && pendingFile.conditions.company !== "미선택" ? pendingFile.conditions : null; // (junhee) 초기값('미선택')은 조건으로 보지 않는다
    const saved = own || (pendingFile && SAMPLE_DEFAULTS[pendingFile.company_id]) || context; // (junhee) 샘플 기본 조건(기업명·HS·대상국)
    $("#excel-input").value = "";
    $("#company-input").value = saved.company;
    $("#hs-input").value = saved.hs;
    $("#country-input").value = saved.country;
    updateUploadLabel();
    syncUploadConditions(saved.country); // (junhee) 연필 버튼으로 열었을 때 현재 회사의 목적국 목록·선택값
    openDialog("#upload-dialog");
  }
  function acceptFile(file) {
    if (!file) return;
    if (!/\.(xlsx|xls)$/i.test(file.name)) {
      $("#upload-error").textContent =
        "엑셀 파일(.xlsx, .xls)을 선택해 주세요.";
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      $("#upload-error").textContent = "20 MB 이하의 파일을 선택해 주세요.";
      return;
    }
    pendingFile = { name: file.name, size: file.size, sample: false, raw: file, hashing: !ENGINE_ONLY, match: null };
    updateUploadLabel();
    // (junhee) 브라우저에서 SHA-256 을 계산해 등록된 샘플인지 확인한다 (내용은 전송하지 않음). 엔진 전용이면 생략
    if (window.JunheeDashboard && !ENGINE_ONLY) {
      const mine = pendingFile;
      JunheeDashboard.identifyFile(file).then((res) => {
        if (pendingFile !== mine) return;
        mine.hashing = false;
        mine.match = res.status === "matched" ? res.entry : null;
        mine.identifyError = res.status === "error" ? res.message : "";
        if (res.status === "matched") $("#file-label").textContent = `${mine.name} · 등록된 샘플 (${res.entry.company_name})`;
        syncUploadConditions(); // (junhee) 등록 샘플이면 HS·대상국 선택지를 회사 값으로
      });
    }
  }
  $("#excel-input").onchange = (e) => acceptFile(e.target.files[0]);
  $("#drop-zone").ondragover = (e) => {
    e.preventDefault();
    $("#drop-zone").classList.add("drag-over");
  };
  $("#drop-zone").ondragleave = () =>
    $("#drop-zone").classList.remove("drag-over");
  $("#drop-zone").ondrop = (e) => {
    e.preventDefault();
    $("#drop-zone").classList.remove("drag-over");
    acceptFile(e.dataTransfer.files[0]);
  };
  desk.addEventListener("dragover", (e) => {
    if ([...e.dataTransfer.types].includes("Files")) e.preventDefault();
  });
  // (junhee) 컴퓨터의 엑셀 파일을 업로드 아이콘 위로 끌면 아이콘을 강조한다 (놓으면 아래 desk drop 이 업로드 창을 연다)
  const uploadIconHover = (on) => $('[data-id="upload"]', icons)?.classList.toggle("drop-hover", on);
  icons.addEventListener("dragover", (e) => {
    if (![...e.dataTransfer.types].includes("Files")) return;
    uploadIconHover(!!e.target.closest('[data-id="upload"]'));
    $('[data-id="company-file"]', icons)?.classList.toggle("drop-hover", !!e.target.closest('[data-id="company-file"]')); // (junhee)
  });
  icons.addEventListener("dragleave", (e) => {
    if (!icons.contains(e.relatedTarget)) uploadIconHover(false);
  });
  desk.addEventListener("drop", () => { uploadIconHover(false); $('[data-id="company-file"]', icons)?.classList.remove("drop-hover"); }); // (junhee)
  desk.addEventListener("drop", (e) => {
    if (!e.dataTransfer.files.length) return;
    e.preventDefault();
    if (e.target.closest && e.target.closest('[data-id="company-file"]') && window.JunheeFiles) return JunheeFiles.uploadCompanyFile(e.dataTransfer.files[0]); // (junhee) 기업 파일 업로드
    if (window.JunheeWidgetBridge && JunheeWidgetBridge.uploadVisible && JunheeWidgetBridge.uploadVisible()) return JunheeWidgetBridge.loadOsFile(e.dataTransfer.files[0]); // (junhee) 2026-09-27 위젯으로
    openUpload();
    acceptFile(e.dataTransfer.files[0]);
  });
  $("#use-sample").onclick = () => {
    pendingFile = files.find((f) => f.sample && !f.trash) || { name: "기업데이터_가상_가온반도체.xlsx", size: 0, sample: true, company_id: "gaon" }; // (junhee) 2026-09-27 sanghyeob 샘플
    updateUploadLabel();
    const d = SAMPLE_DEFAULTS[pendingFile.company_id]; // (junhee) 샘플의 기업명·HS·대상국
    if (d) { $("#company-input").value = d.company; $("#hs-input").value = d.hs; $("#country-input").value = d.country; }
    syncUploadConditions(d ? d.country : undefined); // (junhee)
  };
  let qualityChecking = false; // (junhee) 중복 제출로 확인 창의 Promise가 덮어써지는 것 방지
  $("#analysis-form").onsubmit = (e) => {
    e.preventDefault();
    if (qualityChecking) return; // (junhee)
    const hs = $("#hs-input").value.replace(/[.\s]/g, ""),
      company = $("#company-input").value.trim();
    if (!pendingFile) {
      $("#upload-error").textContent =
        "파일을 선택하거나 샘플 파일을 사용해 주세요.";
      return;
    }
    if (hs !== "all" && !/^(\d{6}|\d{8}|\d{10})$/.test(hs)) { // (junhee) 드롭다운의 '전체 HS' 허용
      $("#upload-error").textContent =
        "HS 코드는 숫자 6·8·10자리로 입력해 주세요.";
      return;
    }
    if (!company) {
      $("#upload-error").textContent = "기업명을 입력해 주세요.";
      return;
    }
    // (junhee) 시연 환경에서는 등록된 샘플 파일만 분석한다. 그 외 파일은 안내만 하고 대시보드를 바꾸지 않는다.
    let reg = null;
    // (junhee) 2026-09-27 엔진 전용: 샘플·업로드 파일 모두 서버 분석 엔진으로
    if (ENGINE_ONLY && window.JunheeAnalysis && (pendingFile.raw || pendingFile.source_id || pendingFile.assessment_id || (pendingFile.sample && pendingFile.company_id))) {
      runEngine(company, hs);
      return;
    }
    if (window.JunheeDashboard) {
      if (pendingFile.raw && pendingFile.hashing) {
        $("#upload-error").textContent = "파일을 확인하는 중입니다. 잠시 후 다시 시도해 주세요.";
        return;
      }
      reg = pendingFile.raw ? pendingFile.match : JunheeDashboard.findByFileName(pendingFile.source_name || pendingFile.name) || (pendingFile.company_id ? JunheeDashboard.findById(pendingFile.company_id) : null); // (junhee) 이름을 바꿨거나 다시 로그인해 원본 File 이 없어도 원본 파일명·저장된 회사 ID 로 찾는다
      // (junhee) 2026-09-27 등록 샘플이 아니면 서버 분석 엔진으로 분석 (새 간편입력 양식·상세 양식)
      if (!reg && window.JunheeAnalysis && (pendingFile.raw || pendingFile.source_id || pendingFile.assessment_id)) {
        runEngine(company, hs);
        return;
      }
      if (!reg) {
        $("#upload-error").textContent = pendingFile.identifyError
          ? "파일을 확인하지 못했습니다: " + pendingFile.identifyError
          : "시연 환경에서는 등록된 샘플 파일만 분석됩니다.";
        return;
      }
    }
    // (junhee) 결측치·오류가 있는 파일이면 어느 시트·항목인지 보여주고 "그래도 진행하시겠습니까?" 확인을 받는다 (값을 채우지 않음)
    qualityChecking = true; // (junhee) 업로드 제출마다 결측 확인
    const submittedFile = pendingFile; // (junhee) 확인 중 다른 파일로 변경되면 중단
    const gate = reg && window.JunheeDashboard ? JunheeDashboard.qualityGate(reg.company_id) : Promise.resolve(true);
    gate.then((ok) => {
      if (!ok) {
        $("#upload-error").textContent = "결측·오류 확인 후 분석을 취소했습니다. 파일을 보완해 다시 올리거나 '그래도 진행'을 선택하세요.";
        return;
      }
      if (pendingFile !== submittedFile) return; // (junhee)
      runAnalysis(reg, company, hs);
    }).catch(() => { // (junhee) 검증 실패를 정상 분석으로 취급하지 않음
      $("#upload-error").textContent = "파일 검증 중 오류가 발생했습니다. 다시 시도해 주세요.";
    }).finally(() => { qualityChecking = false; }); // (junhee)
  };
  // (junhee) 2026-09-27 서버 분석 엔진 실행 → 결과 문서를 대시보드에 연다. 같은 조건으로 이미 분석한 파일은 저장된 결과를 다시 연다.
  let engineBusy = false;
  async function runEngine(company, hs) {
    if (engineBusy) return;
    if (!/^(\d{6}|\d{8}|\d{10})$/.test(hs)) {
      $("#upload-error").textContent = "분석할 HS 코드를 하나 선택해 주세요.";
      return;
    }
    const submitted = pendingFile, country = $("#country-input").value;
    const note = $("#upload-dialog .demo-notice"), noteText = note ? note.textContent : "", btn = $('#analysis-form button[type="submit"]');
    const same = submitted.assessment_id && submitted.conditions && submitted.conditions.company === company && submitted.conditions.hs === hs && submitted.conditions.country === country;
    engineBusy = true;
    if (btn) btn.disabled = true;
    $("#upload-error").textContent = "";
    try {
      const progress = (m) => { if (note) note.textContent = m; window.dispatchEvent(new CustomEvent("axp:analysis-progress", { detail: { message: m, busy: true } })); }; // (junhee) 위젯에도 진행 표시
      const doc = same && !submitted.raw ? await JunheeAnalysis.load(submitted.assessment_id) : await JunheeAnalysis.run(submitted, { company, hs, country }, progress);
      if (pendingFile !== submitted) return;
      let file = files.find((f) => f.id === submitted.id && !f.trash);
      if (!file) {
        const cell = emptyCell(1);
        if (cell === null) {
          $("#upload-error").textContent = "바탕화면이 가득 찼습니다. 파일을 휴지통으로 이동해 주세요.";
          return;
        }
        file = { ...submitted, id: "file-" + Date.now(), trash: false, cell };
        delete file.raw; // 브라우저 File 객체는 저장하지 않는다(원본은 서버에 source_id 로 보관)
        files.push(file);
      }
      file.source_id = submitted.source_id;
      file.assessment_id = doc.engine.assessment_id;
      if (!file.source_name) file.source_name = file.name;
      JunheeDashboard.selectDoc(doc);
      context = { company: doc.company_name, hs, country, file: file.name, fileId: file.id };
      files.forEach((f) => (f.analyzed = f === file));
      file.conditions = { ...context };
      contextUI();
      drawIcons();
      setTab("overview");
      showWindow();
      $("#upload-dialog").close();
      toast(`${doc.company_name} 분석 완료 · ${doc.engine.grade}`);
    } catch (e) {
      $("#upload-error").textContent = (e && e.message) || "분석하지 못했습니다. 잠시 후 다시 시도해 주세요.";
      if (!$("#upload-dialog").open) toast($("#upload-error").textContent); // (junhee) 대시보드에서 바로 분석할 때
    } finally {
      engineBusy = false;
      if (btn) btn.disabled = false;
      if (note) note.textContent = noteText;
      window.dispatchEvent(new CustomEvent("axp:analysis-progress", { detail: { message: "", busy: false } })); // (junhee)
    }
  }
  function runAnalysis(reg, company, hs) { // (junhee) 결측 확인을 통과한 뒤의 분석 실행 (기존 흐름 그대로)
    let file = files.find((f) => f.id === pendingFile.id && !f.trash);
    if (!file) {
      const cell = emptyCell(1);
      if (cell === null) {
        $("#upload-error").textContent =
          "바탕화면이 가득 찼습니다. 파일을 휴지통으로 이동해 주세요.";
        return;
      }
      file = { ...pendingFile, id: "file-" + Date.now(), trash: false, cell };
      files.push(file);
    }
    context = {
      company,
      hs,
      country: $("#country-input").value,
      file: file.name,
      fileId: file.id,
    };
    if (reg) {
      // (junhee) 등록된 샘플이면 기업명·HS 는 회사 JSON(handoff-v1) 값을 쓰고, 목적국은 선택한 나라가 회사 목적국 목록에 있으면 그것을, 아니면 주요 목적국을 쓴다
      const list = JunheeDashboard.countriesOf(reg.company_id);
      const picked = $("#country-input").value;
      context = {
        ...context,
        company: reg.company_name,
        hs: hs === "all" || (JunheeDashboard.hsListOf(reg.company_id) || []).includes(hs) ? hs : "all", // (junhee) 드롭다운에서 고른 HS(전체 또는 회사 HS6)
        country: list && list.includes(picked) ? picked : reg.main_country || picked,
      };
    }
    file.conditions = { ...context };
    if (reg) file.company_id = reg.company_id; // (junhee) 다시 로그인했을 때 이 파일의 분석을 불러오기 위한 회사 ID
    if (!file.source_name) file.source_name = file.name; // (junhee) 이름을 바꿔도 원본 파일명은 유지
    contextUI();
    drawIcons();
    setTab("overview");
    showWindow();
    $("#upload-dialog").close();
    if (reg) {
      JunheeDashboard.select(reg.company_id, context.country) // (junhee) 목적국별 항목(per_country)
        .then(() => {
          // (junhee) 업로드 창에서 고른 HS 를 대시보드 HS 필터로 적용 (회사 HS6 목록에 있을 때만)
          const hsList = JunheeDashboard.hsListOf(reg.company_id) || [];
          JunheeDashboard.setFilters({ hs: hsList.includes(context.hs) ? context.hs : "all" });
          files.forEach((f) => (f.analyzed = f === file || (f.source_name || f.name) === reg.file_name)); // (junhee) 이름을 바꾼 파일·다른 이름으로 올린 같은 파일도 표시
          contextUI();
          drawIcons(); // (junhee) 분석 완료 상태를 계정에 저장
          if (activeTab === "overview") setTab("overview");
          const vd = JunheeDashboard.calc()?.overall?.verdict; // (junhee) 분석 완료 + 종합 판정
          toast(`${reg.company_name} 분석 완료${vd ? " · 종합 판정 " + vd.label : ""}`); // (junhee)
        })
        .catch((err) => {
          console.error("JunheeDashboard select:", err);
          toast("점수 파일을 불러오지 못했습니다. 대시보드는 바뀌지 않았습니다.");
        });
    } else {
      toast("예시 분석 화면을 열었습니다. 파일 내용은 분석하지 않았습니다.");
    }
  }
  function showFiles(trash = false) {
    $("#files-title").textContent = trash ? "휴지통" : "기업 데이터";
    $("#files-title").dataset.trash = String(trash);
    $("#files-description").textContent = trash
      ? "휴지통의 파일을 바탕화면으로 복원할 수 있습니다. 원본 파일은 변경되지 않습니다."
      : "현재 화면에서 추가한 파일입니다. 새로고침하면 파일 목록이 초기화됩니다.";
    const list = files.filter((f) => f.trash === trash);
    $("#files-list").innerHTML = list.length
      ? list
          .map(
            (f) =>
              `<div class="file-row"><i class="ph ph-microsoft-excel-logo"></i><div class="file-info"><strong>${esc(f.name)}</strong><small>${f.sample ? "샘플 파일" : (f.size / 1024).toFixed(1) + " KB"} · ${f.analyzed ? "분석 완료 · 대시보드에 표시 중" : "내용 미분석"}</small></div><button class="small-button" data-file-action="${trash ? "restore" : "open"}" data-file-id="${f.id}">${trash ? "복원" : "종합 적합도"}</button>${trash ? `<button class="small-button jd-purge" data-file-action="purge" data-file-id="${f.id}" aria-label="${esc(f.name)} 영구 삭제">영구 삭제</button>` : `<button class="icon-btn" aria-label="${esc(f.name)} 휴지통으로 이동" data-file-action="trash" data-file-id="${f.id}"><i class="ph ph-trash"></i></button>`}</div>`,
          )
          .join("")
      : `<div class="empty-state"><i class="ph ph-${trash ? "trash" : "folder-simple"}"></i>${trash ? "휴지통이 비어 있습니다." : "추가된 파일이 없습니다."}</div>`;
    // (junhee) 휴지통 창 맨 아래 '휴지통 비우기' (영구 삭제·비우기는 이 화면의 목록에서만 지우며 원본 파일은 건드리지 않는다)
    if (window.JunheeFiles) JunheeFiles.decorateList(trash); // (junhee) 휴지통의 폴더 행 추가 · 폴더 위치 표시
    if (trash && (list.length || (window.JunheeFiles && JunheeFiles.trashedFolders().length))) // (junhee) 폴더만 있어도 비우기 표시
      $("#files-list").insertAdjacentHTML("beforeend", `<div class="jd-trash-foot"><small>영구 삭제·비우기를 하면 서버에 저장된 원본과 분석 결과도 함께 삭제됩니다. PC에 있는 원본 파일은 변경되지 않습니다.</small><button class="button secondary jd-danger" data-file-action="empty-trash">휴지통 비우기</button></div>`);
    openDialog("#files-dialog");
  }
  // (junhee) 휴지통 영구 삭제 · 비우기: 확인 창을 거친 뒤 메모리에서 지운다
  const purgeFiles = (list) => {
    files = files.filter((f) => !list.includes(f));
    if (list.includes(pendingFile)) pendingFile = null;
    drawIcons();
    showFiles(true);
  };
  $("#files-list").onclick = (e) => {
    const b = e.target.closest("[data-file-action]");
    if (!b) return;
    if (b.dataset.fileAction === "empty-trash") {
      const list = files.filter((f) => f.trash);
      const trashedFolders = window.JunheeFiles ? JunheeFiles.trashedFolders() : []; // (junhee) 휴지통의 폴더도 함께 비운다
      if (!list.length && !trashedFolders.length) return;
      JunheeDashboard.confirm({ eyebrow: "TRASH", title: "휴지통 비우기", message: `휴지통의 파일 ${list.length}개${trashedFolders.length ? `·폴더 ${trashedFolders.length}개` : ""}를 영구 삭제합니다. 서버에 저장된 원본과 분석 결과도 함께 삭제되며, PC에 있는 원본 파일은 변경되지 않습니다.`, ok: "비우기", danger: true }).then((ok) => {
        if (!ok) return;
        if (window.JunheeFiles) JunheeFiles.purgeFolders(trashedFolders); // (junhee)
        purgeFiles(list);
        toast("휴지통을 비웠습니다. 원본 파일은 변경되지 않습니다.");
      });
      return;
    }
    const f = files.find((f) => f.id === b.dataset.fileId);
    if (!f) return;
    if (b.dataset.fileAction === "purge") {
      JunheeDashboard.confirm({ eyebrow: "TRASH", title: "영구 삭제", message: `${f.name} 을(를) 영구 삭제합니다. 서버에 저장된 원본과 분석 결과도 함께 삭제되며, PC에 있는 원본 파일은 변경되지 않습니다.`, ok: "영구 삭제", danger: true }).then((ok) => {
        if (!ok) return;
        purgeFiles([f]);
        toast("영구 삭제했습니다. 원본 파일은 변경되지 않습니다.");
      });
      return;
    }
    if (b.dataset.fileAction === "restore") {
      const cell = emptyCell(1, f.id);
      if (cell === null) {
        toast("바탕화면에 빈 공간이 없습니다.");
        return;
      }
      f.trash = false;
      f.cell = cell;
      drawIcons();
      showFiles(true);
      toast("바탕화면으로 복원했습니다.");
    } else if (b.dataset.fileAction === "trash") {
      trashFile(f.id);
      showFiles(false);
    } else {
      $("#files-dialog").close();
      showSuitability(f.id); // (junhee) 2026-09-27 대시보드 '기업 데이터': 내려받기 대신 바로 종합 수출적합도
    }
  };
  function drawWeights() {
    $("#weight-fields").innerHTML = Object.keys(defaults)
      .map(
        (key) =>
          `<div class="weight-row"><label for="weight-${key}">${names[key]}</label><input type="range" id="weight-${key}" data-weight="${key}" min="0" max="100" value="${draft[key]}" aria-label="${names[key]} 가중치 슬라이더"><input type="number" data-weight="${key}" min="0" max="100" step="1" value="${draft[key]}" aria-label="${names[key]} 가중치 퍼센트"></div>`,
      )
      .join("");
    weightTotal();
  }
  function weightTotal() {
    const total = Object.values(draft).reduce((a, b) => a + b, 0);
    $("#weight-total").textContent = total + "%";
    $("#weight-total").style.color = total === 100 ? "#6788d6" : "#ce5870";
    return total;
  }
  function openWeights() {
    draft = { ...weights };
    drawWeights();
    $("#weight-error").textContent = "";
    openDialog("#weights-dialog");
  }
  $("#weight-fields").oninput = (e) => {
    const key = e.target.dataset.weight;
    if (!key) return;
    const raw = e.target.value,
      v = Number(raw);
    if (raw === "" || !Number.isInteger(v) || v < 0 || v > 100) {
      $("#weight-error").textContent = "0~100 사이의 정수를 입력해 주세요.";
      draft[key] = NaN;
      weightTotal();
      return;
    }
    draft[key] = v;
    $$(`[data-weight="${key}"]`).forEach((el) => {
      if (el !== e.target) el.value = v;
    });
    $("#weight-error").textContent = "";
    weightTotal();
  };
  $("#restore-weights").onclick = () => {
    draft = { ...defaults };
    drawWeights();
    $("#weight-error").textContent = "";
  };
  $("#weights-form").onsubmit = (e) => {
    e.preventDefault();
    if (
      Object.values(draft).some(
        (v) => !Number.isInteger(v) || v < 0 || v > 100,
      ) ||
      weightTotal() !== 100
    ) {
      $("#weight-error").textContent =
        "네 항목의 가중치 합계를 100%로 맞춰 주세요.";
      return;
    }
    weights = { ...draft };
    customWeights = Object.keys(defaults).some(
      (k) => weights[k] !== defaults[k],
    );
    $("#weights-dialog").close();
    setTab(activeTab);
    toast(window.JunheeDashboard && JunheeDashboard.current() ? "가중치를 적용했습니다. 종합 점수와 판정을 다시 계산했습니다." : "가중치를 적용했습니다."); // (junhee)
  };
  function report() {
    const button = $('[data-action="report"]', $("#tab-content"));
    if (button) button.disabled = true;
    try {
      // (junhee) 회사가 선택돼 있으면 화면과 같은 회사 점수를, 아니면 공개자료 요약값을 쓴다
      const reportRows = window.JunheeDashboard && JunheeDashboard.current() ? JunheeDashboard.reportRows() : ["regulation", "market", "price", "logistics", "stability"].map((k) => {
        const s = summaryCard(k);
        return [
          names[k],
          esc(s.value) + " — " + esc(s.foot) + (s.meta ? "<br><small>" + esc(s.meta) + "</small>" : ""),
          k === "regulation" ? "관문 고정" : weights[k] + "%",
        ];
      });
      const details = Object.entries(detailData)
        .map(
          ([k, d]) =>
            `<h2>${names[k]}</h2><p>${d.note}</p><table><tr><th>지표</th><th>표시값</th><th>상태</th></tr>${d.rows.map((r) => `<tr>${r.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table>`,
        )
        .join("");
      let html = `<!doctype html><html lang="${window.AXPI18n?.language || "ko"}"><meta charset="utf-8"><title>AXPORT 예시 분석 보고서</title><style>body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:850px;margin:50px auto;padding:24px;color:#24344f;line-height:1.8}h1{font-size:30px}h2{margin-top:35px;font-size:20px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:12px;text-align:left;border-bottom:1px solid #e5e9f1}th{background:#f5f7fb}.note{background:#eef2ff;padding:18px;border-radius:8px;color:#526a9c}@media print{body{margin:0;padding:10px}h2{break-after:avoid}table{break-inside:avoid}}</style><body><p>AXPORT / EXPORT INTELLIGENCE</p><h1>수출 분석 보고서</h1><div class="note">화면 검토용 예시 데이터 · 실제 수출 판정 미실행<br>파일 내용·외부 API·규정 데이터는 연결되지 않았습니다.</div><p>기업: ${esc(context.company)}<br>HS: ${esc(formatHS(context.hs))} · 대상국: ${esc(countryLabel(context.country))}<br>파일: ${esc(context.file)}<br>생성일: ${new Date().toLocaleString(window.AXPI18n?.locale || "ko-KR")}<br>가중치: ${customWeights ? "사용자 설정" : "기본값"} · UI 예시 v1</p><h2>5개 영역 요약</h2><table><tr><th>영역</th><th>표시 결과</th><th>적용 비중</th></tr>${reportRows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table><h2>규제 관문</h2><p>전략물자·최종사용자·수출허가·원산지 증빙은 모두 미검토입니다. 가중치로 규제 관문을 해제하지 않습니다.</p>${details}<p>출처: AXPORT 프론트엔드 시연 데이터. 실제 근거·시행일·규칙 버전은 미연결입니다.</p></body></html>`;
      // (junhee) handoff-v1: 항목·status 표 보고서 (점수 행 없음, 예시 수치 없음). 회사 선택 전에는 안내만 담는다.
      if (window.JunheeDashboard) html = JunheeDashboard.reportHTML({ generated: new Date().toLocaleString(window.AXPI18n?.locale || "ko-KR") }) || html;
      // (junhee) 2026-09-28 엔진 문서는 juyeon 보고서 틀(junhee-report.js)로 만든다. 틀이 스스로 번역하므로 AXPI18n 번역은 건너뛴다.
      const scenario = Object.fromEntries(["sale", "cost", "extras", "tax"].map((key) => [key, document.getElementById("report-" + key)?.value?.trim() ?? ""]));
      const framed = window.JunheeReport ? JunheeReport.render({ generated: new Date().toLocaleString(window.AXPI18n?.locale || "ko-KR"), scenario }) : null;
      html = framed || window.AXPI18n?.translateHTML(html) || html;
      const link = $("#report-download");
      if (link.dataset.blobUrl) URL.revokeObjectURL(link.dataset.blobUrl);
      const blob = new Blob([html], { type: "text/html;charset=utf-8" }),
        url = URL.createObjectURL(blob);
      link.href = url;
      link.dataset.blobUrl = url;
      // (junhee) 2026-09-28 미리보기(iframe sandbox, 스크립트 불가)에는 보고서 안 계산 스크립트·onclick 을 빼고 넣는다. 다운로드 HTML 에는 그대로 있다.
      $("#report-preview").srcdoc = framed ? html.replace(/<script>[\s\S]*?<\/script>/g, "").replace(/ onclick="[^"]*"/g, "") : html;
      openDialog("#report-dialog");
      window.AXPORTReportL10n?.localizeDialog(); // (junhee) 2026-09-28 보고서 창(시나리오·인쇄 버튼) 번역
    } catch {
      toast("보고서를 만들지 못했습니다. 다시 시도해 주세요.");
    } finally {
      if (button) button.disabled = false;
    }
  }
  // (junhee) 2026-09-28 juyeon 보고서 창: 시나리오를 보고서에 반영 · 인쇄 창(PDF 저장). juyeon/static/js/workspace.js 그대로
  document.getElementById("report-scenario-apply")?.addEventListener("click", () => {
    const get = (name) => document.getElementById("report-" + name)?.value?.trim() ?? "";
    const vals = [get("sale"),get("extras"),get("tax")];
    if (vals.some(x => x === "") || vals.some(x => !Number.isFinite(Number(x)) || Number(x)<0) || Number(vals[0])<=0) {
      return toast(window.AXPORTReportL10n?.translate("판매단가(0 초과), 부대비용, 관세 가정값을 올바르게 입력해 주세요. 원가는 선택 사항입니다.",window.AXPI18n?.language||"ko") || "판매단가(0 초과), 부대비용, 관세 가정값을 올바르게 입력해 주세요. 원가는 선택 사항입니다.");
    }
    const cost=get("cost");
    if (cost!=="" && (!Number.isFinite(Number(cost)) || Number(cost)<0)) return toast(window.AXPORTReportL10n?.translate("제품 원가는 0 이상의 숫자로 입력해 주세요.",window.AXPI18n?.language||"ko") || "제품 원가는 0 이상의 숫자로 입력해 주세요.");
    report();
    toast(window.AXPORTReportL10n?.translate("시나리오를 반영했습니다. 지금 PDF로 저장하면 결과가 포함됩니다.",window.AXPI18n?.language||"ko") || "시나리오를 반영했습니다. 지금 PDF로 저장하면 결과가 포함됩니다.");
  });
  // 다운로드한 HTML은 독립 실행되며, 이 버튼은 내장 미리보기를 브라우저 PDF 인쇄로 연결한다.
  document.getElementById("report-print")?.addEventListener("click", () => {
    const frame = document.getElementById("report-preview");
    if (!frame || !frame.contentWindow) return toast(window.AXPORTReportL10n?.translate("보고서 미리보기를 먼저 생성해 주세요.",window.AXPI18n?.language||"ko") || "보고서 미리보기를 먼저 생성해 주세요.");
    frame.contentWindow.focus();
    frame.contentWindow.print();
  });
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-action]");
    if (!b) return;
    const action = b.dataset.action;
    if (action === "overview") {
      setTab("overview");
      showWindow();
    }
    if (action === "items") {
      // (junhee) 2026-09-27 '세부사항': 규제~안정성 탭에서는 그 파트의 항목 전체를 켜고 끈다(예전 오른쪽 아래 '항목 전체 보기' 버튼 자리),
      // 종합 탭에서는 다섯 영역 전체 화면을 열고, 전체 화면에서 다시 누르면 종합으로 돌아간다
      if (names[activeTab] && activeTab !== "overview" && window.JunheeDashboard) {
        const on = JunheeDashboard.setItems(!JunheeDashboard.itemsOn());
        setTab(activeTab);
        if (on) $("#tab-content .jd-items-head")?.scrollIntoView({ block: "start", behavior: "smooth" });
      } else setTab(activeTab === "items" ? "overview" : "items");
      showWindow();
    }
    if (action === "upload") {
      pendingFile = null;
      openUpload();
    }
    if (action === "files") showFiles();
    if (action === "report") report();
    if (action === "weights") openWeights();
    if (action === "reset-data") {
      // (junhee) 확인 창(dialog) 후 분석 결과 초기화. 창 위치(localStorage 레이아웃)는 건드리지 않는다.
      JunheeDashboard.confirm({ eyebrow: "RESET", title: "데이터 초기화", message: "불러온 회사 분석 결과를 모두 지우고 처음 빈 화면으로 돌아갑니다. 바탕화면의 샘플 파일은 남습니다.", ok: "초기화", danger: true }).then((ok) => { if (ok) resetData(); });
    }
    if (action === "reset-layout") {
      resetWindow();
      // (junhee) index3 의 '창 배치 초기화': 종합 탭으로 돌아가고 게이지·점수 애니메이션을 다시 재생
      if (window.JunheeDashboard) {
        JunheeDashboard.replay();
        setTab("overview");
      }
      toast("창 배치를 초기화했습니다.");
    }
  });
  $$(".modal-close").forEach(
    (b) => (b.onclick = () => b.closest("dialog").close()),
  );
  $$("dialog").forEach((d) =>
    d.addEventListener("click", (e) => {
      if (e.target === d) {
        const r = d.getBoundingClientRect();
        if (
          e.clientX < r.left ||
          e.clientX > r.right ||
          e.clientY < r.top ||
          e.clientY > r.bottom
        )
          d.close();
      }
    }),
  );
  $("#edit-context").onclick = () => {
    pendingFile =
      files.find((f) => f.id === context.fileId && !f.trash) || null;
    openUpload();
  };
  $("#help-btn").onclick = () => openDialog("#help-dialog");
  $("#profile-btn").onclick = () =>
    toast("계정 연결 없는 디자인 미리보기입니다.");
  displayDate();
  window.addEventListener("axp:language-changed", () => {
    displayDate();
    contextUI();
    drawIcons();
    setTab(activeTab);
    if ($("#weights-dialog")?.open) drawWeights();
    if ($("#files-dialog")?.open) showFiles($("#files-title").dataset.trash === "true");
    if ($("#report-dialog")?.open) report();
  });
  window.addEventListener("resize", () => {
    fitWindow();
    const { rows, cols } = grid(),
      used = new Set();
    [...systemIcons, ...files.filter((f) => !f.trash)].forEach((f) => {
      if (f.cell >= rows * cols || used.has(f.cell)) {
        let cell = 0;
        while (used.has(cell)) cell++;
        f.cell = cell;
      }
      used.add(f.cell);
    });
    drawIcons();
  });
  const layout = readUI();
  if (
    layout &&
    [layout.x, layout.y, layout.w, layout.h].every(Number.isFinite) &&
    innerWidth > 850
  ) {
    Object.assign(win.style, {
      left: layout.x + "px",
      top: layout.y + "px",
      width: layout.w + "px",
      height: layout.h + "px",
    });
  }
  files[0].conditions = { ...context };
  setSidebarOpen(innerWidth > 560);
  // (junhee) 점수형 종합 화면 모듈 연결: 색·가중치 전달, '더보기 →' 탭 이동, 등록 샘플 목록 미리 읽기
  if (window.JunheeDashboard) {
    JunheeDashboard.configure({
      esc,
      defaults,
      getWeights: () => weights, // 사용자 가중치 설정을 그대로 읽어 종합 점수를 재계산
      isCustom: () => customWeights,
      // (junhee) 정보 막대의 기간·HS 필터나 '항목 전체 보기' 토글이 바뀌면 컨텍스트 바를 맞추고 현재 탭을 다시 그린다
      onEngineConditions: (next) => rerunConditions(next), // (junhee) 2026-09-27 사이드바에서 대상국·HS 변경 → 같은 파일 다시 계산
      onFilter: (f) => {
        const cur = JunheeDashboard.current();
        if (cur && f && f.hs) context.hs = f.hs; // "all" 은 전체 HS
        if (cur && f && f.country) context.country = f.country; // (junhee) 사이드바 'ANALYSIS · 분석 조건' 의 목적국
        contextUI();
        setTab(activeTab);
      },
    });
    $("#tab-content").addEventListener("click", (e) => {
      const b = e.target.closest("[data-open-tab]");
      if (b) setTab(b.dataset.openTab);
    });
    JunheeDashboard.load().then(() => {
      if (activeTab === "overview") setTab("overview");
    });
  }
  contextUI();
  arrangeIcons(); // (junhee) 2026-09-27 기본 바탕화면을 정렬된 형태로 (저장된 계정 배치가 있으면 junhee-files.js 가 그 배치로 바꾼다)
  setTab("overview");
  loadSummary();
  fitWindow();
  // (junhee) 입장 시에는 바탕화면만 보인다. 분석 창은 '분석 대시보드' 아이콘이나 기업 파일을 열 때 띄운다.
  // 검토용 URL 파라미터: ?window=open (창을 연 채 시작) &tab=market (탭) &company=hanbit (등록 샘플 선택) &country=독일 (목적국) &dialog=weights|report. 시연 흐름에는 영향 없음.
  const debugQ = new URLSearchParams(location.search);
  if (debugQ.get("window") === "open") {
    const openTab = names[debugQ.get("tab")] ? debugQ.get("tab") : "overview";
    const pick = window.JunheeDashboard && debugQ.get("company") ? JunheeDashboard.select(debugQ.get("company")).catch(() => null) : Promise.resolve(null);
    pick.then((c) => {
      if (c) {
        if (debugQ.get("country")) JunheeDashboard.setCountry(debugQ.get("country"));
        const sampleFile = files.find((f) => f.name === c.file_name && !f.trash) || null;
        context = { ...context, company: c.company_name, hs: "all", country: JunheeDashboard.country() || c.common.main_country, file: c.file_name, fileId: sampleFile ? sampleFile.id : null };
        if (sampleFile) sampleFile.conditions = { ...context };
        files.forEach((f) => (f.analyzed = f.name === c.file_name));
        contextUI();
        drawIcons();
      }
      setTab(openTab);
      showWindow();
      if (debugQ.get("dialog") === "weights") openWeights();
      else if (debugQ.get("dialog") === "report") report();
    });
  } else hideWindow();
  // (junhee) 2026-09-27 계정 저장·폴더 모듈(static/js/junhee-files.js) 연결부. 이 파일의 상태를 읽고 쓰는 창구만 연다.
  window.AXWorkspace = {
    files: () => files,
    setFiles: (list) => { files = list; pendingFile = null; selected = null; },
    systemIcons,
    context: () => context,
    drawIcons, emptyCell, nearestCell, grid, toast, openDialog, esc, openIcon, trashFile, clearAnalysis, showFiles, analyzeFile, arrangeIcons,
    showSuitability,
    // 기업 파일 업로드로 저장한 파일을 바탕화면 회사 파일로 등록(빈 칸에)
    addFile(file) {
      const cell = emptyCell(Math.max(4, grid().rows), null);
      if (cell === null) { toast("바탕화면이 가득 찼습니다. 파일을 휴지통으로 이동해 주세요."); return null; }
      const f = { trash: false, sample: false, ...file, cell };
      files.push(f);
      drawIcons();
      return f;
    },
    // 위젯에 넣은 바탕화면 파일: 새 업로드 복사본 대신 그 파일(샘플 id·서버 원본)을 분석 대상으로. 기업명·HS·대상국 기본값을 돌려준다
    bindPending(id) {
      const f = files.find((x) => x.id === id && !x.trash);
      if (!f) return null;
      pendingFile = f;
      updateUploadLabel();
      const own = f.conditions && f.conditions.company !== "미선택" ? f.conditions : null;
      const d = own || SAMPLE_DEFAULTS[f.company_id] || null;
      if (d) { $("#company-input").value = d.company; }
      return d;
    },
    // 저장된 파일의 분석(회사·목적국·HS)을 다시 연다. 창은 열지 않고 대시보드 내용만 채운다.
    async restoreAnalysis(file, last) {
      if (!window.JunheeDashboard || !file) return false;
      if (file.assessment_id && window.JunheeAnalysis) { // 서버 엔진으로 분석한 파일: 계정에 저장된 결과 문서를 다시 연다
        const doc = await JunheeAnalysis.load(file.assessment_id).catch(() => null);
        if (!doc || !JunheeDashboard.selectDoc(doc)) return false;
        const cond = file.conditions || {};
        context = { company: doc.company_name, hs: cond.hs || (doc.engine && doc.engine.hs) || doc.common.main_hs6, country: cond.country || (last && last.country) || "US", file: file.name, fileId: file.id };
        files.forEach((f) => (f.analyzed = f === file));
        contextUI();
        drawIcons();
        setTab(activeTab);
        return true;
      }
      if (ENGINE_ONLY) return false; // 엔진 전용: 기존 등록 샘플 점수표로 열지 않는다
      await JunheeDashboard.load();
      const reg = (file.company_id && JunheeDashboard.findById(file.company_id)) || JunheeDashboard.findByFileName(file.source_name || file.name);
      if (!reg) return false;
      const cond = file.conditions || {};
      const c = await JunheeDashboard.select(reg.company_id, (last && last.country) || cond.country);
      if (!c) return false;
      const hs = (last && last.hs) || cond.hs || "all";
      context = { company: c.company_name, hs, country: JunheeDashboard.country() || c.common.main_country, file: file.name, fileId: file.id };
      const hsList = JunheeDashboard.hsListOf(reg.company_id) || [];
      JunheeDashboard.setFilters({ hs: hsList.includes(hs) ? hs : "all" });
      files.forEach((f) => (f.analyzed = f === file));
      file.conditions = { ...context };
      contextUI();
      drawIcons();
      setTab(activeTab);
      return true;
    },
  };
  $("#workspace-loading").hidden = true;
})();
