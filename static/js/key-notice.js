"use strict";
// (2026-10-06 공개 데모) 외부 API 키 미적용 안내 버튼 → 안내 창. 닫기 버튼은 workspace.js 의 .modal-close 처리 사용.
(() => {
  const btn = document.getElementById("key-notice-btn");
  const dialog = document.getElementById("key-notice-dialog");
  if (!btn || !dialog || typeof dialog.showModal !== "function") return;
  btn.addEventListener("click", () => dialog.showModal());
  dialog.addEventListener("close", () => btn.focus());
})();
