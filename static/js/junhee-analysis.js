"use strict";
// (junhee) 2026-09-27 등록 샘플이 아닌 기업 파일 → 서버 분석 엔진(sanghyeob suitability-reference-v1) → 대시보드 문서(handoff-v1).
// 스타일 없음. 서버: junhee/server/analysis.py · 변환: junhee/server/engine_adapter.py
(() => {
  const auth = window.JunheeAuth;
  if (!auth) return;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const message = (e, fallback) => (e && e.data && e.data.message) || fallback;
  // (2026-09-27 배포 QA) 서버 오류 코드를 사용자 문구로 (코드를 그대로 보여 주지 않는다)
  const CODE_TEXT = {
    auth_unavailable: "로그인 확인 서버에 잠시 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    analysis_storage_unavailable: "분석 저장소를 잠시 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    assessment_not_found: "분석 기록을 찾지 못했습니다(서버 재시작 등). 다시 분석해 주세요.",
    not_found: "저장된 분석 결과를 찾지 못했습니다. 다시 분석해 주세요.",
    request_failed: "서버와 통신하지 못했습니다. 잠시 후 다시 시도해 주세요.",
  };
  const readable = (e, fallback) => message(e, CODE_TEXT[e && e.message] || fallback);

  async function upload(raw, name) {
    const fd = new FormData();
    fd.append("file", raw, name);
    const res = await fetch("/api/analysis/sources", { method: "POST", body: fd, credentials: "same-origin", headers: { "X-CSRF-Token": auth.csrf, Accept: "application/json" } });
    let data = null;
    try { data = await res.json(); } catch { data = null; }
    if (res.status === 401) { location.href = "/app?auth=expired"; throw new Error("authentication_required"); }
    if (!res.ok) throw new Error((data && data.message) || "파일을 올리지 못했습니다.");
    return data;
  }

  // file: 바탕화면 파일(raw = 브라우저 File, source_id = 서버에 올린 원본 id) · cond: {company, hs, country(ISO2)}
  async function run(file, cond, progress = () => {}) {
    let companyId = file.source_id ? "upload:" + file.source_id : file.sample && file.company_id ? file.company_id : null; // 샘플은 서버의 샘플 파일(static/samples)로
    if (file.raw) {
      progress("파일을 분석 서버로 올리는 중입니다…");
      const up = await upload(file.raw, file.name);
      companyId = up.company_id;
      file.source_id = companyId.slice(7);
    }
    if (!companyId) throw new Error("원본 파일이 서버에 없습니다. 파일을 다시 올려 주세요.");
    // (2026-09-27) 결측 확인: 빈 칸·빠진 시트가 있으면 어느 셀인지와 점수 영향을 보여 주고 진행 여부를 묻는다(값을 채우지 않음)
    progress("파일의 빈 칸을 확인합니다…");
    const chk = await auth.api("/api/analysis/inspect?company_id=" + encodeURIComponent(companyId)).catch(() => null);
    if (chk && (chk.fields.length || chk.missing_sheets.length || chk.issues.length) && window.JunheeDashboard && !(await confirmMissing(chk))) {
      const e = new Error("결측 확인 후 분석을 취소했습니다. 파일을 보완해 다시 올리거나 '그래도 진행'을 선택하세요.");
      e.cancelled = true;
      throw e;
    }
    progress("분석을 시작합니다…");
    let st;
    try {
      st = await auth.api("/api/analysis/assessments", { method: "POST", json: { company_id: companyId, company: cond.company, hs: cond.hs, country: cond.country } });
    } catch (e) {
      if (e.status === 404) { delete file.source_id; throw new Error("서버에 원본 파일이 없습니다(서버 재시작 등). 파일을 다시 올려 주세요."); }
      throw new Error(message(e, "분석을 시작하지 못했습니다."));
    }
    const started = Date.now();
    let fails = 0; // (2026-09-27 배포 QA) 일시 오류(5xx·429·네트워크)는 간격을 늘려 다시 묻는다. 404 등은 바로 중단
    while (st.status === "QUEUED" || st.status === "RUNNING") {
      progress(st.progress || "분석 중입니다…");
      if (Date.now() - started > 6 * 60 * 1000) throw new Error("분석이 너무 오래 걸립니다. 서버에서는 계속 진행될 수 있으니 잠시 후 같은 조건으로 다시 분석하면 이어서 확인합니다.");
      await sleep(fails ? Math.min(1500 * 2 ** fails, 12000) : 1500);
      try {
        st = await auth.api(`/api/analysis/assessments/${st.assessment_id}`);
        fails = 0;
      } catch (e) {
        const transient = !e.status || e.status >= 500 || e.status === 429;
        if (!transient || ++fails > 5) throw new Error(readable(e, "분석 진행 상태를 확인하지 못했습니다."));
      }
    }
    if (st.status !== "COMPLETED") throw new Error(st.progress || "분석을 완료하지 못했습니다.");
    progress("대시보드에 결과를 여는 중입니다…");
    try {
      return await load(st.assessment_id);
    } catch (e) {
      throw new Error(readable(e, "분석 결과를 불러오지 못했습니다."));
    }
  }
  function confirmMissing(chk) {
    const esc = (v) => String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
    const scored = chk.fields.filter((f) => f.scored).length;
    const rows = chk.fields.map((f) => `<tr><td>${esc(f.label)}</td><td>${esc(f.cell)}</td><td>${f.scored ? "<b>점수 영향</b>" : "참고"}</td><td>${esc(f.impact)}</td></tr>`).join("")
      + chk.missing_sheets.map((m) => `<tr><td>${esc(m)} 시트</td><td>—</td><td><b>빠짐</b></td><td>이 시트로 계산하는 항목은 자료 부족</td></tr>`).join("")
      + chk.issues.slice(0, 20).map((m) => `<tr><td colspan="2">검증</td><td>오류</td><td>${esc(m)}</td></tr>`).join("");
    const html = `<div class="jd-table-wrap"><table class="jd-data-table"><thead><tr><th>항목</th><th>셀</th><th>구분</th><th>영향</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    const n = chk.fields.length + chk.missing_sheets.length + chk.issues.length;
    return JunheeDashboard.confirm({ eyebrow: "DATA CHECK", title: "결측치가 있는 파일입니다", wide: true, html,
      message: `${chk.file_name} 에서 빈 칸·누락 ${n}건을 찾았습니다${scored ? ` (점수에 영향 ${scored}건)` : ""}. 빈 칸은 값을 채우지 않고 '자료 부족'으로 두며, 해당 점수 항목은 정책 기준 50점으로 계산합니다. 그래도 진행하시겠습니까?`,
      ok: "그래도 진행", cancel: "취소" });
  }
  const load = (id) => auth.api(`/api/analysis/assessments/${encodeURIComponent(id)}/handoff`);
  const forget = (id) => auth.api(`/api/analysis/assessments/${encodeURIComponent(id)}`, { method: "DELETE" }).catch(() => null);

  // (2026-09-27) 영구 삭제한 업로드 원본. 성공(이미 없음 404 포함)이면 true, 진행 중(409)·네트워크 오류면 false → 다음 저장 때 다시 시도
  const forgetSource = (id) => auth.api(`/api/analysis/sources/${encodeURIComponent(id)}`, { method: "DELETE" }).then(() => true, (e) => e && e.status === 404);
  window.JunheeAnalysis = { run, load, forget, forgetSource };
})();
