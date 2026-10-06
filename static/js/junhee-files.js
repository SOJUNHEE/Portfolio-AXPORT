"use strict";
// (junhee) 2026-09-27 계정별 작업 저장 + 폴더 + 우클릭 메뉴 + 이름 바꾸기 + 삭제 확인.
// sanghyeob/static/js/workspace-files.js 의 기능을 junhee 바탕화면(workspace.js 의 cell 격자)에 맞춰 다시 작성했다.
// 새 스타일 없음: 창은 기존 .modal.small · .modal-title · .field · .button · .file-row · .small-button · .empty-state 를 쓴다.
// 서버: junhee/server/workspace_store.py (GET/PUT /api/workspace)
(() => {
  const W = window.AXWorkspace;
  if (!W) return;
  const auth = window.JunheeAuth || null; // 로그인하지 않았으면(로그인 필수라 보통 없음) 저장 없이 폴더만 동작
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = W.esc;
  const icons = $("#desktop-icons"), desk = $("#desktop");
  const uid = () =>
    window.crypto && crypto.randomUUID ? crypto.randomUUID() : "id-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);

  let folders = []; // {id, kind:'folder', name, cell, trash, trash_batch}
  let revision = 0, loaded = !auth, saving = false, dirty = false, timer = null, suppress = false, disabled = !auth;

  // ---------- 이름 규칙 (서버 clean_name 과 같음) ----------
  function nameError(raw) {
    const v = String(raw || "").normalize("NFC").trim();
    if (!v) return "이름을 입력해 주세요.";
    if (v.length > 120) return "이름은 120자 이하로 입력해 주세요.";
    if (/[<>:"/\\|?*\x00-\x1f\x7f]/.test(v)) return '다음 문자는 쓸 수 없습니다: < > : " / \\ | ? *';
    if (v === "." || v === ".." || v.endsWith(".")) return "이름은 마침표(.)로 끝날 수 없습니다.";
    if (/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$/i.test(v)) return "시스템 예약어는 이름으로 쓸 수 없습니다.";
    return null;
  }
  const siblings = (parentId) => [...W.files(), ...folders].filter((x) => !x.trash && (x.parent_id || null) === (parentId || null));
  const taken = (name, parentId, exceptId) =>
    siblings(parentId).some((x) => x.id !== exceptId && x.name.normalize("NFC").toLowerCase() === name.normalize("NFC").trim().toLowerCase());
  function freeName(base, parentId) {
    if (!taken(base, parentId)) return base;
    for (let n = 2; ; n++) if (!taken(`${base} (${n})`, parentId)) return `${base} (${n})`;
  }
  const childrenOf = (folder) => W.files().filter((f) => f.parent_id === folder.id);
  const isCurrent = (f) => W.context().fileId === f.id;

  // ---------- workspace.js 가 부르는 함수 ----------
  function normalize() {
    // 휴지통에 있거나 지워진 폴더를 가리키는 (휴지통 밖) 파일은 바탕화면으로 꺼낸다
    W.files().forEach((f) => {
      if (!f.parent_id) return;
      const d = folders.find((x) => x.id === f.parent_id);
      if (!d || (d.trash && !f.trash)) {
        delete f.parent_id;
        if (!f.trash) f.cell = W.emptyCell(Number.isInteger(f.cell) ? f.cell : 1, f.id) ?? 0;
      }
    });
  }
  function folderAt(x, y, exceptId) {
    const el = $$(".desktop-icon", icons).find((b) => {
      if (b.dataset.id === exceptId) return false;
      const r = b.getBoundingClientRect();
      return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
    });
    return el ? folders.find((d) => d.id === el.dataset.id && !d.trash) || null : null;
  }
  function moveInto(file, folder) {
    if (taken(file.name, folder.id, file.id)) {
      W.drawIcons();
      return W.toast(`'${folder.name}' 폴더에 같은 이름의 파일이 있습니다. 이름을 바꾼 뒤 옮겨 주세요.`);
    }
    file.parent_id = folder.id;
    W.drawIcons();
    W.toast(`'${folder.name}' 폴더로 옮겼습니다.`);
  }
  function moveOut(file) {
    if (taken(file.name, null, file.id)) return W.toast("바탕화면에 같은 이름의 파일이 있습니다. 이름을 바꾼 뒤 꺼내 주세요.");
    const cell = W.emptyCell(1, file.id);
    if (cell === null) return W.toast("바탕화면에 빈 공간이 없습니다.");
    delete file.parent_id;
    file.cell = cell;
    W.drawIcons();
    W.toast("바탕화면으로 꺼냈습니다.");
  }

  // ---------- 엑셀 파일 열기 (2026-09-27) ----------
  // 브라우저는 PC 의 엑셀 프로그램을 직접 실행할 수 없어, 원본 파일을 내려받아 엑셀로 열리게 한다(브라우저 설정 '다운로드 후 자동 열기'면 바로 열림).
  async function openExcel(f) {
    let href = null, revoke = null;
    if (typeof File !== "undefined" && f.raw instanceof File) { href = URL.createObjectURL(f.raw); revoke = href; } // 이번 창에서 올린 파일
    else if (f.sample) href = "/static/samples/" + encodeURIComponent(f.source_name || f.name); // 샘플 파일
    else if (f.source_id) href = "/api/analysis/sources/" + encodeURIComponent(f.source_id) + "/file"; // 계정에 올린 원본
    if (!href) return W.toast("원본 파일이 없습니다. 파일을 다시 올려 주세요.");
    if (!revoke) { // (2026-09-27 배포 QA) 서버 재시작 등으로 원본이 없으면 실패한 다운로드 대신 안내한다
      const ok = await fetch(href, { method: "HEAD", credentials: "same-origin", cache: "no-store" }).then((r) => r.ok, () => false);
      if (!ok) return W.toast("서버에 원본 파일이 없습니다(서버 재시작 등). 파일을 다시 올려 주세요.");
    }
    const a = document.createElement("a");
    a.href = href;
    a.download = f.name;
    document.body.append(a);
    a.click();
    a.remove();
    if (revoke) setTimeout(() => URL.revokeObjectURL(revoke), 4000);
    W.toast(`${f.name} 을(를) 엑셀로 엽니다. 분석은 우클릭 → 분석하기`);
  }

  // ---------- 기업 파일 업로드 (2026-09-27) ----------
  // 올린 엑셀을 서버가 양식 검사 후 작업 데이터 폴더(junhee/data/samples/uploads)에 저장하고 계정 분석 원본으로 등록 → 바탕화면 회사 파일로 추가
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = ".xlsx,.xls";
  picker.hidden = true;
  document.body.append(picker);
  picker.addEventListener("change", () => { const f = picker.files && picker.files[0]; picker.value = ""; if (f) uploadCompanyFile(f); });
  function pickCompanyFile() { picker.click(); }
  async function uploadCompanyFile(file) {
    if (!file) return;
    if (!/\.(xlsx|xls)$/i.test(file.name)) return W.toast("엑셀 파일(.xlsx, .xls)을 선택해 주세요.");
    if (file.size <= 0 || file.size > 20 * 1024 * 1024) return W.toast("0바이트보다 크고 20 MB 이하인 파일을 선택해 주세요.");
    if (!auth) return W.toast("로그인한 뒤 올릴 수 있습니다.");
    W.toast(`${file.name} 을(를) 올리는 중입니다…`);
    const fd = new FormData();
    fd.append("file", file, file.name);
    let data = null, res;
    try {
      res = await fetch("/api/analysis/company-files", { method: "POST", body: fd, credentials: "same-origin", headers: { "X-CSRF-Token": auth.csrf, Accept: "application/json" } });
      try { data = await res.json(); } catch { data = null; }
    } catch { return W.toast("파일을 올리지 못했습니다. 잠시 후 다시 시도해 주세요."); }
    if (res.status === 401) { location.href = "/app?auth=expired"; return; }
    if (!res.ok) return W.toast((data && data.message) || "파일을 올리지 못했습니다.");
    const stem = data.name.replace(/\.(xlsx|xls)$/i, "");
    const added = W.addFile({ id: "file-" + Date.now(), name: data.name, source_name: data.name, size: data.size, source_id: data.company_id.slice(7),
      conditions: { company: stem, hs: "854232", country: "US" } }); // 기본 조건(기업명은 파일 이름) — 우클릭 '분석하기'에서 바꿀 수 있음
    if (!added) { // 바탕화면이 가득 차 아이콘을 못 만들었으면 방금 올린 원본·저장 파일도 지운다
      if (window.JunheeAnalysis && JunheeAnalysis.forgetSource) JunheeAnalysis.forgetSource(data.company_id.slice(7));
      return;
    }
    const miss = data.missing && data.missing.fields ? data.missing.fields.filter((x) => x.scored).length : 0;
    W.toast(`저장했습니다 · ${data.saved_path}${miss ? ` · 점수에 영향 있는 빈 칸 ${miss}건` : ""}`);
  }

  // ---------- 삭제(휴지통) · 복원 · 영구 삭제 ----------
  function askTrash(id) {
    const d = folders.find((x) => x.id === id);
    const f = d ? null : W.files().find((x) => x.id === id);
    if (!d && !f) return;
    const kids = d ? childrenOf(d).filter((x) => !x.trash) : [];
    const message = d
      ? `'${d.name}' 폴더${kids.length ? `와 안의 파일 ${kids.length}개` : ""}를 휴지통으로 옮깁니다. 휴지통에서 함께 복원할 수 있습니다.`
      : `'${f.name}' 을(를) 휴지통으로 옮깁니다. 휴지통에서 복원할 수 있습니다.`;
    JunheeDashboard.confirm({ eyebrow: "DELETE", title: "삭제하시겠습니까?", message, ok: "삭제", danger: true }).then((ok) => {
      if (!ok) return;
      if (f) return W.trashFile(f.id);
      const batch = uid();
      d.trash = true;
      d.trash_batch = batch;
      kids.forEach((k) => {
        k.trash = true;
        k.trash_batch = batch;
        if (isCurrent(k)) W.clearAnalysis();
      });
      W.drawIcons();
      W.toast("휴지통으로 옮겼습니다. 휴지통에서 복원할 수 있습니다.");
    });
  }
  function restoreFolder(d) {
    if (taken(d.name, null, d.id)) return W.toast("바탕화면에 같은 이름이 있어 복원할 수 없습니다. 먼저 이름을 바꿔 주세요.");
    const cell = W.emptyCell(Number.isInteger(d.cell) ? d.cell : 1, d.id);
    if (cell === null) return W.toast("바탕화면에 빈 공간이 없습니다.");
    W.files().forEach((f) => {
      if (f.parent_id === d.id && f.trash && f.trash_batch === d.trash_batch) {
        f.trash = false;
        delete f.trash_batch;
      }
    });
    d.trash = false;
    delete d.trash_batch;
    d.cell = cell;
    W.drawIcons();
  }
  function purgeFolders(list) {
    list.forEach((d) => {
      const gone = W.files().filter((f) => f.parent_id === d.id && f.trash && f.trash_batch === d.trash_batch);
      if (gone.length) W.setFiles(W.files().filter((f) => !gone.includes(f)));
      W.files().forEach((f) => {
        if (f.parent_id === d.id) delete f.parent_id; // 먼저 따로 지운 파일은 휴지통에 남는다
      });
      folders = folders.filter((x) => x !== d);
    });
    W.drawIcons();
  }

  // ---------- 목록 창(#files-dialog) ----------
  const fileRow = (f, actions) =>
    `<div class="file-row"><i class="ph ph-microsoft-excel-logo"></i><div class="file-info"><strong>${esc(f.name)}</strong><small>${f.sample ? "샘플 파일" : ((f.size || 0) / 1024).toFixed(1) + " KB"} · ${f.analyzed ? "분석 완료" : "내용 미분석"}</small></div>${actions}</div>`;
  function decorateList(trash) {
    const list = $("#files-list");
    if (trash) {
      const rows = folders.filter((d) => d.trash);
      if (!rows.length) return;
      $(".empty-state", list)?.remove();
      list.insertAdjacentHTML(
        "beforeend",
        rows
          .map((d) => {
            const n = childrenOf(d).filter((f) => f.trash && f.trash_batch === d.trash_batch).length;
            return `<div class="file-row"><i class="ph ph-folder-simple"></i><div class="file-info"><strong>${esc(d.name)}</strong><small>폴더 · 함께 삭제한 파일 ${n}개</small></div><button class="small-button" data-folder-action="restore" data-folder-id="${esc(d.id)}">복원</button><button class="small-button jd-purge" data-folder-action="purge" data-folder-id="${esc(d.id)}" aria-label="${esc(d.name)} 영구 삭제">영구 삭제</button></div>`;
          })
          .join(""),
      );
    } else {
      if (auth) $("#files-description").textContent = auth.visitor
        ? "이 브라우저의 작업공간에 저장된 파일입니다. 공개 데모 서버라 마지막 사용 후 7일이 지나거나 서버가 다시 시작되면 지워질 수 있습니다." // (2026-10-06) 로그인 없는 방문자
        : "이 계정에 저장된 파일입니다. 다시 로그인해도 그대로 남습니다.";
      W.files().forEach((f) => {
        const d = f.parent_id && folders.find((x) => x.id === f.parent_id);
        const small = d && $$("[data-file-id]", list).find((b) => b.dataset.fileId === f.id)?.closest(".file-row")?.querySelector("small");
        if (small) small.textContent += ` · 폴더: ${d.name}`;
      });
    }
  }
  function openFolder(id) {
    const d = folders.find((x) => x.id === id && !x.trash);
    if (!d) return;
    $("#files-title").textContent = d.name;
    $("#files-title").dataset.trash = "false";
    $("#files-description").textContent = "폴더 안의 파일입니다. 바탕화면의 파일 아이콘을 이 폴더 아이콘 위에 끌어 놓으면 넣을 수 있습니다.";
    const kids = childrenOf(d).filter((f) => !f.trash);
    $("#files-list").innerHTML = kids.length
      ? kids
          .map((f) =>
            fileRow(
              f,
              `<button class="small-button" data-folder-action="open-file" data-file-ref="${esc(f.id)}">열기</button><button class="small-button" data-folder-action="analyze-file" data-file-ref="${esc(f.id)}">분석</button><button class="small-button" data-folder-action="move-out" data-file-ref="${esc(f.id)}">꺼내기</button><button class="icon-btn" data-folder-action="rename-file" data-file-ref="${esc(f.id)}" aria-label="${esc(f.name)} 이름 바꾸기"><i class="ph ph-pencil-simple"></i></button><button class="icon-btn" data-folder-action="trash-file" data-file-ref="${esc(f.id)}" aria-label="${esc(f.name)} 삭제"><i class="ph ph-trash"></i></button>`,
            ),
          )
          .join("")
      : `<div class="empty-state"><i class="ph ph-folder-simple"></i>빈 폴더입니다.</div>`;
    $("#files-list").dataset.folderId = d.id;
    W.openDialog("#files-dialog");
  }
  $("#files-list").addEventListener("click", (e) => {
    const b = e.target.closest("[data-folder-action]");
    if (!b) return;
    const action = b.dataset.folderAction;
    const d = folders.find((x) => x.id === b.dataset.folderId);
    const f = W.files().find((x) => x.id === b.dataset.fileRef);
    if (action === "restore" && d) {
      restoreFolder(d);
      W.showFiles(true);
      W.toast("폴더를 복원했습니다.");
    } else if (action === "purge" && d) {
      JunheeDashboard.confirm({ eyebrow: "TRASH", title: "영구 삭제", message: `'${d.name}' 폴더와 함께 삭제한 파일을 이 계정에서 영구 삭제합니다. 원본 파일은 변경되지 않습니다.`, ok: "영구 삭제", danger: true }).then((ok) => {
        if (!ok) return;
        purgeFolders([d]);
        W.showFiles(true);
        W.toast("영구 삭제했습니다.");
      });
    } else if (f) {
      const folderId = $("#files-list").dataset.folderId;
      const back = () => folderId && $("#files-dialog").open && openFolder(folderId);
      if (action === "open-file") openExcel(f);
      else if (action === "analyze-file") {
        $("#files-dialog").close();
        W.analyzeFile(f.id);
      } else if (action === "move-out") {
        moveOut(f);
        back();
      } else if (action === "rename-file") rename(f, back);
      else if (action === "trash-file") {
        JunheeDashboard.confirm({ eyebrow: "DELETE", title: "삭제하시겠습니까?", message: `'${f.name}' 을(를) 휴지통으로 옮깁니다. 휴지통에서 복원할 수 있습니다.`, ok: "삭제", danger: true }).then((ok) => {
          if (!ok) return;
          W.trashFile(f.id);
          back();
        });
      }
    }
  });
  $("#files-dialog").addEventListener("close", () => delete $("#files-list").dataset.folderId);

  // ---------- 창 만들기 (기존 클래스만 사용) ----------
  document.body.insertAdjacentHTML(
    "beforeend",
    `<dialog id="junhee-menu" class="modal small" aria-labelledby="junhee-menu-title">
      <div class="modal-title"><div><span class="eyebrow" id="junhee-menu-eyebrow">MENU</span><h2 id="junhee-menu-title"></h2></div><button class="icon-btn modal-close" type="button" aria-label="닫기"><i class="ph ph-x"></i></button></div>
      <p class="modal-description" id="junhee-menu-desc"></p>
      <div class="modal-actions" id="junhee-menu-actions"></div>
    </dialog>
    <dialog id="junhee-rename" class="modal small" aria-labelledby="junhee-rename-title">
      <div class="modal-title"><div><span class="eyebrow" id="junhee-rename-eyebrow">RENAME</span><h2 id="junhee-rename-title">이름 바꾸기</h2></div><button class="icon-btn modal-close" type="button" aria-label="닫기"><i class="ph ph-x"></i></button></div>
      <form id="junhee-rename-form" novalidate>
        <label class="field">이름<input id="junhee-rename-input" maxlength="120" autocomplete="off" required /></label>
        <p class="form-error" id="junhee-rename-error" role="alert"></p>
        <div class="modal-actions"><button type="button" class="button secondary" data-dialog-close>취소</button><button type="submit" class="button primary">확인</button></div>
      </form>
    </dialog>`,
  );
  const menu = $("#junhee-menu"), renameDlg = $("#junhee-rename");
  [menu, renameDlg].forEach((dlg) => {
    $$(".modal-close, [data-dialog-close]", dlg).forEach((b) => b.addEventListener("click", () => dlg.close()));
    dlg.addEventListener("click", (e) => {
      if (e.target !== dlg) return;
      const r = dlg.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dlg.close();
    });
  });

  let renameDone = null;
  function askName({ eyebrow, title, value, parentId, exceptId }) {
    return new Promise((resolve) => {
      $("#junhee-rename-eyebrow").textContent = eyebrow;
      $("#junhee-rename-title").textContent = title;
      const input = $("#junhee-rename-input");
      input.value = value;
      $("#junhee-rename-error").textContent = "";
      renameDone = { resolve, parentId, exceptId };
      renameDlg.showModal();
      input.focus();
      const dot = value.lastIndexOf(".");
      input.setSelectionRange(0, dot > 0 ? dot : value.length); // 확장자 앞까지 선택
    });
  }
  $("#junhee-rename-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!renameDone) return;
    const value = $("#junhee-rename-input").value.normalize("NFC").trim();
    const err = nameError(value) || (taken(value, renameDone.parentId, renameDone.exceptId) ? "같은 위치에 같은 이름이 있습니다." : null);
    if (err) {
      $("#junhee-rename-error").textContent = err;
      return;
    }
    const done = renameDone;
    renameDone = null;
    renameDlg.close();
    done.resolve(value);
  });
  renameDlg.addEventListener("close", () => {
    if (renameDone) renameDone.resolve(null);
    renameDone = null;
  });

  function rename(item, after) {
    askName({ eyebrow: "RENAME", title: "이름 바꾸기", value: item.name, parentId: item.parent_id, exceptId: item.id }).then((name) => {
      if (!name || name === item.name) return after && after();
      if (item.kind !== "folder" && !item.source_name) item.source_name = item.name; // 분석 연결용 원본 파일명 유지
      item.name = name;
      W.drawIcons();
      W.toast("이름을 바꿨습니다.");
      if (after) after();
    });
  }
  function newFolder(cellHint) {
    askName({ eyebrow: "NEW FOLDER", title: "새 폴더", value: freeName("새 폴더", null), parentId: null }).then((name) => {
      if (!name) return;
      const cell = W.emptyCell(Number.isInteger(cellHint) ? cellHint : 1, null);
      if (cell === null) return W.toast("바탕화면에 빈 공간이 없습니다.");
      folders.push({ id: uid(), kind: "folder", name, cell, trash: false });
      W.drawIcons();
      W.toast(`'${name}' 폴더를 만들었습니다.`);
    });
  }

  // ---------- 우클릭 메뉴 ----------
  function openMenu(title, desc, actions) {
    $("#junhee-menu-title").textContent = title;
    $("#junhee-menu-desc").textContent = desc;
    $("#junhee-menu-actions").innerHTML = actions
      .map((a) => `<button type="button" class="button ${a.danger ? "secondary jd-danger" : a.primary ? "primary" : "secondary"}" data-menu="${a.key}"><i class="ph ph-${a.icon}"></i>${a.label}</button>`)
      .join("");
    menuHandlers = Object.fromEntries(actions.map((a) => [a.key, a.run]));
    menu.showModal();
    $("#junhee-menu-actions button")?.focus();
  }
  let menuHandlers = {};
  $("#junhee-menu-actions").addEventListener("click", (e) => {
    const b = e.target.closest("[data-menu]");
    if (!b) return;
    const run = menuHandlers[b.dataset.menu];
    menu.close();
    if (run) run();
  });
  const SYSTEM = new Set(W.systemIcons.map((s) => s.id));
  function itemMenu(id) {
    const d = folders.find((x) => x.id === id && !x.trash);
    const f = W.files().find((x) => x.id === id && !x.trash);
    const open = { key: "open", label: "열기", icon: "arrow-square-out", primary: true, run: () => W.openIcon(id) };
    if (SYSTEM.has(id)) {
      const s = W.systemIcons.find((x) => x.id === id);
      return openMenu(s.name, "바탕화면 기본 아이콘은 이름을 바꾸거나 삭제할 수 없습니다.", [open]);
    }
    const item = d || f;
    if (!item) return;
    if (d)
      return openMenu(item.name, `폴더 · 파일 ${childrenOf(d).filter((x) => !x.trash).length}개`, [
        { key: "rename", label: "이름 바꾸기", icon: "pencil-simple", run: () => rename(item) },
        { key: "delete", label: "삭제", icon: "trash", danger: true, run: () => askTrash(id) },
        open,
      ]);
    openMenu(item.name, "기업 데이터 파일 · 열기는 엑셀 파일, 분석하기는 업로드 창", [
      { key: "rename", label: "이름 바꾸기", icon: "pencil-simple", run: () => rename(item) },
      { key: "delete", label: "삭제", icon: "trash", danger: true, run: () => askTrash(id) },
      { key: "analyze", label: "분석하기", icon: "chart-pie-slice", run: () => W.analyzeFile(id) },
      { key: "open", label: "엑셀 열기", icon: "microsoft-excel-logo", primary: true, run: () => openExcel(item) },
    ]);
  }
  desk.addEventListener("contextmenu", (e) => {
    // 바탕화면 빈 곳·아이콘에서만 우리 메뉴를 연다. 분석 창·위젯·입력칸은 브라우저 기본 메뉴 그대로.
    const icon = e.target.closest("#desktop-icons .desktop-icon");
    // #sx-canvas: minjung 위젯이 바탕화면 전체에 까는 투명 판. 판 자체(빈 곳)는 바탕화면으로, 위젯 카드 안은 제외
    const blank = !icon && (e.target === desk || e.target === icons || e.target.id === "sx-canvas" || e.target.closest(".desktop-heading, .desktop-note"));
    if (!icon && !blank) return;
    e.preventDefault();
    if (icon) return itemMenu(icon.dataset.id);
    const r = icons.getBoundingClientRect();
    const hint = W.nearestCell(e.clientX - r.left - 40, e.clientY - r.top - 40, null);
    openMenu("바탕화면", "새 폴더를 만들거나 아이콘을 이름순으로 정렬합니다.", [
      { key: "arrange", label: "아이콘 정렬", icon: "squares-four", run: () => { W.arrangeIcons(); W.toast("아이콘을 정렬했습니다."); } },
      { key: "new-folder", label: "새 폴더", icon: "folder-simple-plus", primary: true, run: () => newFolder(hint) },
    ]);
  });
  // 파일 아이콘을 끄는 동안 아래에 있는 폴더를 휴지통과 같은 방식(.drop-hover)으로 강조
  const clearHover = () => $$(".desktop-icon.drop-hover", icons).forEach((b) => folders.some((d) => d.id === b.dataset.id) && b.classList.remove("drop-hover"));
  icons.addEventListener("pointermove", (e) => {
    if (!(e.buttons & 1)) return;
    const src = e.target.closest(".desktop-icon");
    if (!src || !W.files().some((f) => f.id === src.dataset.id)) return;
    const over = folderAt(e.clientX, e.clientY, src.dataset.id);
    $$(".desktop-icon", icons).forEach((b) => {
      if (folders.some((d) => d.id === b.dataset.id)) b.classList.toggle("drop-hover", !!over && b.dataset.id === over.id);
    });
  });
  icons.addEventListener("pointerup", clearHover);
  icons.addEventListener("pointercancel", clearHover);
  icons.addEventListener("keydown", (e) => {
    const el = e.target.closest("[data-id]");
    if (!el) return;
    if (e.key === "F2") {
      const item = folders.find((x) => x.id === el.dataset.id) || W.files().find((x) => x.id === el.dataset.id);
      if (item) {
        e.preventDefault();
        rename(item);
      }
    }
  });

  // ---------- 계정 저장 · 불러오기 ----------
  const CONDITION_KEYS = ["company", "hs", "country", "file", "fileId", "period"];
  // (2026-09-27 검토 반영) 서버 이름 규칙(workspace_store.clean_name)에 안 맞는 이름 하나 때문에 바탕화면 저장 전체가 막히지 않게 저장 전에 정리
  const safeName = (v) => { let n = String(v || "").normalize("NFC").replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, "_").slice(0, 120).replace(/[.\s]+$/, "").trim(); if (!n || /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$/i.test(n)) n = "_" + (n || "파일"); return n; };
  function snapshot() {
    const items = folders.map((d) => ({ id: d.id, kind: "folder", name: d.name, cell: Number.isInteger(d.cell) ? d.cell : null, trash: !!d.trash, trash_batch: d.trash_batch || null }));
    W.files().forEach((f) => {
      const cond = f.conditions ? Object.fromEntries(CONDITION_KEYS.filter((k) => f.conditions[k] != null).map((k) => [k, String(f.conditions[k])])) : null;
      items.push({
        id: f.id, kind: "file", name: safeName(f.name), source_name: safeName(f.source_name || f.name), parent_id: f.parent_id || null,
        cell: Number.isInteger(f.cell) ? f.cell : null, trash: !!f.trash, trash_batch: f.trash_batch || null,
        sample: !!f.sample, size: Number.isInteger(f.size) ? f.size : 0, analyzed: !!f.analyzed,
        company_id: f.company_id || null, assessment_id: f.assessment_id || null, source_id: f.source_id || null, conditions: cond,
      });
    });
    const system = Object.fromEntries(W.systemIcons.map((s) => [s.id, s.cell]));
    const c = W.context();
    return { v: 1, items, system, last: c.fileId ? { fileId: String(c.fileId), country: String(c.country || ""), hs: String(c.hs || "") } : null };
  }
  function apply(state) {
    suppress = true;
    try {
      folders = state.items.filter((i) => i.kind === "folder").map((i) => ({ ...i }));
      const list = state.items
        .filter((i) => i.kind === "file")
        .map((i) => {
          const f = { ...i };
          ["parent_id", "trash_batch", "company_id", "assessment_id", "source_id", "conditions"].forEach((k) => f[k] == null && delete f[k]);
          return f;
        });
      W.setFiles(list);
      knownAssessments = new Set(list.map((f) => f.assessment_id).filter(Boolean));
      knownSources = new Set(list.map((f) => f.source_id).filter(Boolean));
      W.systemIcons.forEach((s) => {
        if (state.system && Number.isInteger(state.system[s.id])) s.cell = state.system[s.id];
      });
      // 저장한 화면과 지금 화면의 크기가 달라 칸이 넘치거나 겹치면 빈칸으로 옮긴다
      const { rows, cols } = W.grid(), limit = rows * cols, used = new Set();
      [...W.systemIcons, ...list.filter((f) => !f.trash && !f.parent_id), ...folders.filter((d) => !d.trash)].forEach((e) => {
        if (!Number.isInteger(e.cell) || e.cell >= limit || used.has(e.cell)) {
          let c = 0;
          while (used.has(c)) c++;
          e.cell = c;
        }
        used.add(e.cell);
      });
      W.drawIcons();
    } finally {
      suppress = false;
    }
  }
  // 영구 삭제·다시 분석 등으로 더 이상 어떤 파일도 가리키지 않는 분석 결과는 계정 저장소에서도 지운다
  let knownAssessments = new Set(), knownSources = new Set();
  function trackAssessments() {
    const now = new Set(W.files().map((f) => f.assessment_id).filter(Boolean));
    if (window.JunheeAnalysis) knownAssessments.forEach((id) => now.has(id) || JunheeAnalysis.forget(id));
    knownAssessments = now;
    // (2026-09-27 검토 반영) 어떤 파일(휴지통 포함)도 가리키지 않게 된 업로드 원본은 서버에서도 지운다 → 계정별 보관 한도 30개가 다시 빈다.
    // 바로 지우지 않고 바탕화면 저장이 성공한 뒤에 지운다(저장 실패·다른 창 충돌로 파일이 되살아나면 원본이 남아 있어야 함). 실패한 것은 다음 저장 때 다시 시도.
    const srcNow = new Set(W.files().map((f) => f.source_id).filter(Boolean));
    knownSources.forEach((id) => srcNow.has(id) || sourceDeletes.add(id));
    knownSources = srcNow;
    if (disabled) flushSourceDeletes(); // 계정 저장소가 없으면 서버에 바탕화면 기록이 없으므로 바로 지운다
  }
  const sourceDeletes = new Set();
  function flushSourceDeletes() {
    if (!window.JunheeAnalysis || !JunheeAnalysis.forgetSource) return;
    const live = new Set(W.files().map((f) => f.source_id).filter(Boolean));
    [...sourceDeletes].forEach((id) => {
      if (live.has(id)) return sourceDeletes.delete(id); // 되살아난 파일(복원·충돌로 불러옴)이 다시 가리키면 지우지 않는다
      JunheeAnalysis.forgetSource(id).then((ok) => ok && sourceDeletes.delete(id));
    });
  }
  function changed() {
    if (suppress || disabled || !loaded) return;
    trackAssessments();
    clearTimeout(timer);
    timer = setTimeout(save, 700);
  }
  async function save() {
    timer = null;
    if (disabled) return;
    if (saving) {
      dirty = true;
      return;
    }
    saving = true;
    dirty = false;
    try {
      const r = await auth.api("/api/workspace", { method: "PUT", json: { revision, state: snapshot() } });
      revision = r.revision;
      pendingClear();
      flushSourceDeletes(); // 저장이 확정된 뒤에만 원본 삭제
    } catch (e) {
      const code = e.data && e.data.error;
      if (code === "conflict" && e.data.state) {
        revision = e.data.revision;
        apply(e.data.state);
        W.toast("다른 창에서 저장한 바탕화면을 불러왔습니다.");
      } else if (code === "conflict") {
        // (2026-10-06) 서버 기록이 없어진 경우(재시작·보관기간 정리): 이 창의 상태로 다시 저장한다
        revision = e.data.revision || 0;
        dirty = true;
      } else if (code === "csrf_failed" || e.status === 403) {
        // (2026-10-06) 세션이 바뀌면 같은 요청을 계속 반복하지 않는다
        disabled = true;
        W.toast("작업 저장 연결이 끊겼습니다. 페이지를 새로고침해 주세요.");
      } else if (code === "rate_limited") {
        dirty = true;
      } else if (code === "setup_required") {
        disabled = true;
        W.toast("계정 저장소 설정(Supabase SQL)이 아직 없어 이 창에서만 유지됩니다.");
      } else if (code === "duplicate_name" || code === "invalid_name") {
        W.toast("같은 위치에 같은 이름이 있거나 쓸 수 없는 이름이라 저장하지 못했습니다.");
      } else if (e.message !== "authentication_required") {
        W.toast("작업 내용을 저장하지 못했습니다. 잠시 후 다시 저장합니다.");
        dirty = true;
      }
    } finally {
      saving = false;
      if (dirty && !disabled) timer = setTimeout(save, 3000);
    }
  }
  // 창을 닫는 순간 아직 못 보낸 변경은 이 브라우저에 잠시 보관했다가, 다음에 열 때 서버 revision 이 그대로면 이어서 저장한다.
  // (닫힐 때 keepalive 로 보내면 새로고침한 새 화면의 첫 저장과 순서가 엇갈려 거짓 충돌이 난다)
  const PENDING_KEY = auth ? "axport-pending-workspace:" + auth.userId : null;
  const pendingRead = () => { try { return JSON.parse(localStorage.getItem(PENDING_KEY) || "null"); } catch { return null; } };
  const pendingClear = () => { try { localStorage.removeItem(PENDING_KEY); } catch {} };
  window.addEventListener("pagehide", () => {
    if (!timer || disabled || !auth) return;
    clearTimeout(timer);
    try { localStorage.setItem(PENDING_KEY, JSON.stringify({ revision, state: snapshot(), at: Date.now() })); } catch {}
  });

  window.JunheeFiles = {
    folders: () => folders,
    folder: (id) => folders.find((d) => d.id === id) || undefined,
    trashedFolders: () => folders.filter((d) => d.trash),
    normalize, changed, folderAt, moveInto, askTrash, openFolder, decorateList, purgeFolders, openExcel, pickCompanyFile, uploadCompanyFile,
    rename: (id) => {
      const item = folders.find((x) => x.id === id) || W.files().find((x) => x.id === id);
      if (item) rename(item);
    },
    snapshot, // 점검용
  };
  W.files().forEach((f) => f.source_name || (f.source_name = f.name));
  W.drawIcons();

  if (auth) {
    auth
      .api("/api/workspace")
      .then(async (data) => {
        revision = data.revision || 0;
        const pending = pendingRead();
        pendingClear();
        if (pending && pending.revision === revision && pending.state && Date.now() - (pending.at || 0) < 7 * 864e5) {
          data.state = pending.state; // 지난번에 못 보낸 변경(서버가 그 뒤로 바뀌지 않았을 때만)
          setTimeout(() => changed(), 0);
        }
        if (data.state) {
          apply(data.state);
          loaded = true;
          const last = data.state.last;
          const f = last && W.files().find((x) => x.id === last.fileId && !x.trash);
          if (f) {
            // 복원은 서버 상태를 그대로 보여 주는 것이라 저장하지 않는다(새로고침 직후 이전 화면의 저장과 엇갈리는 거짓 충돌 방지)
            const wasSuppressed = suppress;
            suppress = !pending;
            const ok = await W.restoreAnalysis(f, last).catch(() => false);
            suppress = wasSuppressed;
            if (ok) W.toast(`지난 작업을 불러왔습니다 · ${f.name}`);
          }
        } else {
          loaded = true;
          changed(); // 처음 로그인: 기본 바탕화면을 계정에 만든다
        }
      })
      .catch((e) => {
        loaded = true;
        if (e.data && e.data.error === "setup_required") {
          disabled = true;
          W.toast("계정 저장소 설정(Supabase SQL)이 아직 없어 이 창에서만 유지됩니다.");
        } else if (e.message !== "authentication_required") {
          disabled = true;
          W.toast("저장된 작업을 불러오지 못했습니다. 이 창의 변경은 저장되지 않습니다.");
        }
      });
  }
})();
