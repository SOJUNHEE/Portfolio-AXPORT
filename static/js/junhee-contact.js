/* junhee-contact.js — 홈 Contact Us 폼: 입력 검증, 글자 수 표시, POST /api/contact 전송, aria-live 안내.
   home.js 는 수정하지 않는다. alert 를 쓰지 않는다. 접수 내용은 화면에 다시 표시하지 않는다. */
(() => {
  "use strict";
  const form = document.getElementById("contact-form");
  if (!form) return;
  const $ = (sel) => form.querySelector(sel);
  const status = document.getElementById("contact-status");
  const counter = document.getElementById("contact-count");
  const message = $('[name="message"]');
  const email = $('[name="email"]');
  const consent = $('[name="consent"]');
  const button = form.querySelector('button[type="submit"]');
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  const MIN = 10, MAX = 1000;
  const t = (s) => (window.AXPI18n && typeof AXPI18n.t === "function" ? AXPI18n.t(s) : s);

  function say(text, kind) {
    status.textContent = t(text);
    status.classList.remove("ok", "error");
    if (kind) status.classList.add(kind);
    if (window.AXPI18n && typeof AXPI18n.translateDOM === "function") AXPI18n.translateDOM(status);
  }
  function mark(el, bad) {
    const field = el.closest(".contact-field, .contact-consent");
    if (field) field.classList.toggle("invalid", !!bad);
  }
  function updateCount() {
    const n = (message.value || "").length;
    counter.textContent = `${n} / ${MAX}`;
    counter.classList.toggle("over", n > MAX || (n > 0 && n < MIN));
  }
  message.addEventListener("input", updateCount);
  updateCount();
  email.addEventListener("input", () => {
    if (!email.value.trim()) { consent.checked = false; mark(consent, false); }
  });
  form.querySelectorAll("input, select, textarea").forEach((el) => el.addEventListener("input", () => mark(el, false)));

  function validate() {
    const type = $('[name="type"]').value.trim();
    const name = $('[name="name"]').value.trim();
    const mail = email.value.trim();
    const body = message.value.trim();
    const errors = [];
    mark($('[name="type"]'), !type);
    if (!type) errors.push("의견 유형을 선택해 주세요.");
    mark($('[name="name"]'), name.length > 40);
    if (name.length > 40) errors.push("이름 또는 닉네임은 40자 이내로 적어 주세요.");
    const badMail = !!mail && !EMAIL_RE.test(mail);
    mark(email, badMail);
    if (badMail) errors.push("이메일 형식을 확인해 주세요.");
    const badBody = body.length < MIN || body.length > MAX;
    mark(message, badBody);
    if (badBody) errors.push("내용은 10자 이상 1000자 이하로 적어 주세요.");
    const needConsent = !!mail && !consent.checked;
    mark(consent, needConsent);
    if (needConsent) errors.push("이메일을 적으셨다면 개인정보 수집·이용 동의가 필요합니다.");
    return { errors, payload: { type, field: $('[name="field"]').value.trim(), name, email: mail, message: body, consent: consent.checked, website: $('[name="website"]').value } };
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const { errors, payload } = validate();
    if (errors.length) {
      say(errors[0], "error");
      const first = form.querySelector(".invalid input, .invalid select, .invalid textarea");
      if (first) first.focus();
      return;
    }
    button.disabled = true;
    say("보내는 중입니다…", "");
    try {
      const res = await fetch("/api/contact", { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) });
      let data = null;
      try { data = await res.json(); } catch { data = null; }
      if (res.ok && data && data.ok) {
        say("보내 주셔서 감사합니다. 접수되었습니다.", "ok");
        form.reset();
        updateCount();
        form.querySelectorAll(".invalid").forEach((el) => el.classList.remove("invalid"));
      } else if (res.status === 429) {
        say("잠시 후 다시 시도해 주세요. 같은 곳에서 1분에 3회까지만 보낼 수 있습니다.", "error");
      } else if (res.status === 400 && data && data.message) {
        say(data.message, "error");
      } else {
        say("보내지 못했습니다. 잠시 후 다시 시도해 주세요.", "error");
      }
    } catch {
      say("네트워크 오류로 보내지 못했습니다. 연결을 확인한 뒤 다시 시도해 주세요.", "error");
    } finally {
      button.disabled = false;
    }
  });
})();
