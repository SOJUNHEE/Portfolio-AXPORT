"use strict";
// (junhee) 2026-09-27 로그인 화면(탭 전환·재발송 대기 시간)과 워크스페이스의 계정 창·세션 확인.
// 스타일은 추가하지 않는다. 서버 쪽: junhee/server/accounts.py
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  // ---------- 로그인 화면 (templates/junhee_login.html) ----------
  const login = $("#login-dialog");
  if (login) {
    if (login.open && typeof login.showModal === "function") {
      login.close();
      login.showModal(); // 가운데 정렬·배경 흐림(.modal::backdrop)
    }
    login.addEventListener("cancel", (e) => e.preventDefault()); // 로그인 필수: Esc 로 닫지 않음
    const panels = $$("[data-auth-panel]", login);
    const select = (name) => {
      if (login.dataset.authTab !== name) $$('input[type="password"]', login).forEach((i) => (i.value = ""));
      login.dataset.authTab = name;
      panels.forEach((p) => (p.hidden = p.dataset.authPanel !== name));
      const p = panels.find((x) => !x.hidden);
      (p && (p.querySelector('[role="alert"]') || p.querySelector('input:not([type="hidden"])')))?.focus();
    };
    $$("[data-auth-tab-link]", login).forEach((a) =>
      a.addEventListener("click", (e) => {
        const target = a.dataset.authTabLink;
        // 인증 메일 대기 화면에서 '로그인으로' 는 그냥 이동, 가입 폼이 없는 상태의 '회원가입' 도 서버 화면으로
        if (!panels.some((p) => p.dataset.authPanel === target)) return;
        if (target === "signup" && !$("#signup-form") && !$("#resend-form")) return;
        e.preventDefault();
        select(target);
      }),
    );
    const pw = $("#signup-password"), pw2 = $("#signup-password-confirm");
    if (pw && pw2) {
      const check = () => pw2.setCustomValidity(pw2.value && pw.value !== pw2.value ? "비밀번호와 비밀번호 확인이 일치하지 않습니다." : "");
      pw.addEventListener("input", check);
      pw2.addEventListener("input", check);
    }
    const resend = $("#resend-form");
    if (resend) {
      const btn = $("#resend-button"), status = $("#resend-cooldown-status");
      const readyAt = Date.now() + Math.max(0, Number(resend.dataset.resendCooldown) || 0) * 1000;
      const tick = () => {
        const left = Math.ceil((readyAt - Date.now()) / 1000);
        btn.disabled = left > 0;
        status.textContent = left > 0 ? `${left}초 후 인증 메일을 다시 요청할 수 있습니다.` : "";
        if (left > 0) setTimeout(tick, 1000);
      };
      tick();
    }
    $$("form[data-auth-form]", login).forEach((f) =>
      f.addEventListener("submit", () => {
        const b = f.querySelector('button[type="submit"]');
        if (b) setTimeout(() => (b.disabled = true), 0); // 두 번 누름 방지
      }),
    );
    return;
  }

  // ---------- 워크스페이스 (templates/junhee_account.html) ----------
  const account = $("#junhee-account");
  if (!account) return;
  // (2026-10-05) visitor: 로그인 없이 쓰는 방문자(서버가 세션 방문자 id 로 파일·분석·바탕화면을 구분)
  const info = { userId: account.dataset.userId, email: account.dataset.email, csrf: account.dataset.csrf, visitor: account.dataset.visitor === "1" };
  // 다른 junhee 모듈(폴더·분석)이 쓰는 공통 요청 도우미: CSRF 헤더를 붙이고, 로그인이 풀렸으면 로그인 화면으로 보낸다.
  async function api(url, opts = {}) {
    const headers = { Accept: "application/json", ...(opts.headers || {}) };
    if (opts.method && opts.method !== "GET") headers["X-CSRF-Token"] = info.csrf;
    if (opts.json !== undefined) {
      headers["Content-Type"] = "application/json";
      opts = { ...opts, body: JSON.stringify(opts.json) };
    }
    const res = await fetch(url, { credentials: "same-origin", cache: "no-store", ...opts, headers });
    if (res.status === 401) {
      location.href = "/app?auth=expired";
      throw new Error("authentication_required");
    }
    let data = null;
    try { data = await res.json(); } catch { data = null; }
    if (!res.ok) {
      const err = new Error((data && data.error) || "request_failed");
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }
  window.JunheeAuth = { ...info, api };

  const avatar = $("#profile-btn");
  if (info.visitor) {
    if (avatar) {
      const note = "로그인 없이 사용 중입니다. 올린 파일·분석·바탕화면은 이 브라우저에 연결되어 서버에 저장되며, 마지막 사용 후 7일이 지나거나 서버가 다시 시작되면 지워질 수 있습니다.";
      avatar.setAttribute("aria-label", "작업공간 안내");
      avatar.title = note;
      avatar.onclick = () => (window.AXWorkspace && AXWorkspace.toast ? AXWorkspace.toast(note) : null);
    }
    return; // 계정 창·비밀번호 변경·세션 확인은 로그인 사용자만
  }
  if (avatar) {
    const name = (info.email || "").split("@")[0];
    if (name) avatar.textContent = name.slice(0, 2).toUpperCase();
    avatar.setAttribute("aria-label", `내 계정 (${info.email})`);
    avatar.title = info.email;
  }
  // workspace.js 가 붙인 '계정 연결 없는 미리보기' 안내 대신 계정 창을 연다 (workspace.js 다음에 로드됨)
  const openAccount = () => $("#account-dialog")?.showModal();
  if (avatar) avatar.onclick = openAccount;

  // (2026-09-29) 계정 창의 비밀번호 변경: 메일 인증 없이 바로 바뀌고 지금 로그인은 유지된다.
  const pwForm = $("#password-form");
  if (pwForm) {
    const pw = $("#new-password"), pw2 = $("#new-password-confirm"), status = $("#password-status"), btn = $("#password-submit");
    const show = (text, ok) => {
      status.hidden = !text;
      status.textContent = text || "";
      status.className = ok ? "demo-notice" : "form-error"; // 기존 클래스만 사용(성공=안내 상자, 실패=오류 글자)
    };
    const reset = () => { pw.value = ""; pw2.value = ""; show(""); };
    $("#account-dialog")?.addEventListener("close", reset);
    pwForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (pw.value.length < 8 || pw.value.length > 128) return show("비밀번호는 8자 이상 128자 이하로 입력해 주세요.");
      if (pw.value !== pw2.value) return show("새 비밀번호와 비밀번호 확인이 일치하지 않습니다.");
      btn.disabled = true;
      show("");
      try {
        const data = await api("/api/auth/password", { method: "POST", json: { password: pw.value, password_confirm: pw2.value } });
        pw.value = ""; pw2.value = "";
        show((data && data.message) || "비밀번호를 바꿨습니다.", true);
      } catch (err) {
        show((err.data && err.data.message) || "비밀번호를 바꾸지 못했습니다. 잠시 후 다시 시도해 주세요.");
      } finally {
        btn.disabled = false;
      }
    });
  }
  // 다른 탭에서 로그아웃했거나 세션이 만료되면 알아챈다
  setInterval(() => {
    if (document.visibilityState === "visible") api("/api/auth/session").catch(() => {});
  }, 60000);
})();
