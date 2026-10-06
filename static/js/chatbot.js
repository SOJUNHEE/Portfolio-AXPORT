(() => {
  const root = document.querySelector('.axchat');
  if (!root) return;
  const $ = (s) => root.querySelector(s);
  const panel = $('.axchat-panel'), launcher = $('.axchat-launcher');
  const body = $('.axchat-body'), messages = $('.axchat-messages');
  const welcome = $('.axchat-welcome'), suggestions = $('.axchat-suggestions');
  const form = $('.axchat-form'), input = $('textarea'), send = form.querySelector('button');
  const latest = $('.axchat-latest'), badge = $('.axchat-badge'), status = $('.axchat-status');
  const handle = $('.axchat-resize'), provider = window.AXPORTChatDemo;
  const i18n = window.AXPORTChatI18n;
  const live = root.dataset.chatMode === 'live';
  const liveText = {
    ko: {preview:'반도체 전문 어드바이저 · AI 연결 모드', replyLabel:'AXPORT AI · AI 분석', arrived:'답변이 도착했습니다.', hint:'반도체 경영·재무·SCM·무역을 물어보세요. 질문과 최근 대화가 AI에 전송됩니다.', notConfigured:'AI 연결 설정이 필요합니다. 서버의 API 키와 모델 설정을 확인해 주세요.'},
    en: {preview:'Semiconductor advisor · AI mode', replyLabel:'AXPORT AI · AI analysis', arrived:'Your answer has arrived.', hint:'Ask about semiconductor business, finance, SCM or trade. Your question and recent conversation are sent to AI.', notConfigured:'AI is not configured. Check the server API key and model settings.'},
    ja: {preview:'半導体専門アドバイザー · AIモード', replyLabel:'AXPORT AI · AI分析', arrived:'回答が届きました。', hint:'半導体の経営・財務・SCM・貿易についてご相談ください。質問と最近の会話はAIに送信されます。', notConfigured:'AIの接続設定が必要です。サーバーのAPIキーとモデル設定を確認してください。'},
    'zh-CN': {preview:'半导体专业顾问 · AI模式', replyLabel:'AXPORT AI · AI分析', arrived:'回答已送达。', hint:'欢迎咨询半导体经营、财务、供应链和贸易。问题和近期对话将发送给AI。', notConfigured:'请检查服务器的API密钥和模型设置。'},
  };
  let history = [], controller = null;
  let locale = i18n.normalize(document.documentElement.lang || navigator.language);
  let hasOpened = false, statusKey = '';
  const textFor = (key, language) => (live && liveText[language]?.[key]) || i18n.catalog[language].ui[key];
  const t = key => textFor(key, locale);
  function localized(node, key) {
    node.dataset.chatText = key; node.textContent = t(key); return node;
  }
  function announce(key) { statusKey = key; status.textContent = key ? t(key) : ''; }
  function setLanguage(value) {
    locale = i18n.normalize(value); root.lang = locale;
    root.querySelectorAll('[data-chat-text]').forEach(node => {
      node.textContent = t(node.dataset.chatText);
      // All interface states follow the current site language.
      node.closest('.axchat-answer')?.setAttribute('lang', locale);
    });
    [[$('.axchat-minimize'),'minimize'],[$('.axchat-close'),'close'],[handle,'resize'],[body,'body'],[suggestions,'suggestions'],[input,'input'],[send,'sendLabel']].forEach(([node,key]) => node.setAttribute('aria-label',t(key)));
    handle.title = t('resizeHint'); input.placeholder = t('placeholder');
    send.textContent = t('send'); latest.querySelector('button').textContent = t('latest'); badge.textContent = t('badge');
    launcher.setAttribute('aria-label', t(opened ? 'minimize' : hasOpened ? 'restore' : 'open'));
    announce(statusKey);
    suggestions.replaceChildren();
    const heading = document.createElement('div'); heading.className = 'axchat-question-heading';
    const sparkle = document.createElement('i'); sparkle.className = 'ph ph-sparkle'; sparkle.setAttribute('aria-hidden', 'true');
    const headingText = document.createElement('span'); headingText.textContent = t('suggestions');
    heading.append(sparkle, headingText); suggestions.append(heading);
    const icons = root.dataset.page === 'workspace' ? ['chart-pie-slice', 'sliders-horizontal', 'bookmarks-simple'] : ['info', 'compass', 'lightbulb'];
    i18n.catalog[locale].questions[root.dataset.page].forEach((question, index) => {
      const button = document.createElement('button'); button.type = 'button';
      const icon = document.createElement('i'); icon.className = `ph ph-${icons[index]} axchat-question-icon`; icon.setAttribute('aria-hidden', 'true');
      const label = document.createElement('span'); label.textContent = question; button.append(icon, label);
      button.addEventListener('click', () => submit(question)); suggestions.append(button);
    });
    messages.querySelectorAll('[data-demo-complete]').forEach(answer => renderAnswer(answer));
    layout();
  }
  function renderAnswer(answer) {
    answer.lang = locale;
    const label = document.createElement('small'); label.textContent = t('replyLabel');
    const content = document.createElement('div');
    content.textContent = provider.getResponse(answer.dataset.question, locale);
    answer.replaceChildren(label, content);
  }
  const safe = document.createElement('span'); safe.className = 'axchat-safe'; root.append(safe);
  let generation = 0, pending = false, composing = false, opened = false;
  let desired = { width:400, height:560 }, savedScroll = 0, following = true, unread = false, drag = null;
  const movable = root.dataset.page === 'workspace';
  const CHAT_POS_KEY = 'axport.workspace.chat.position.v1';
  let chatPosition = null;
  if (movable) {try {const saved=JSON.parse(localStorage.getItem(CHAT_POS_KEY));if(Number.isFinite(saved?.x)&&Number.isFinite(saved?.y))chatPosition=saved;}catch{}}
  let chatMove = null, skipLauncherClick = false, skipClickUntil = 0;
  let panelPosition = null;
  if(movable){try{const old=JSON.parse(localStorage.getItem(CHAT_POS_KEY));if(Number.isFinite(old?.panelX)&&Number.isFinite(old?.panelY))panelPosition={x:old.panelX,y:old.panelY};}catch{}}
  const saveChatPosition=()=>{if(movable&&chatPosition){try{localStorage.setItem(CHAT_POS_KEY,JSON.stringify({...chatPosition,...(panelPosition?{panelX:panelPosition.x,panelY:panelPosition.y}:{})}));}catch{}}};
  const mobile = () => matchMedia('(max-width:767px)').matches;
  const nearBottom = () => body.scrollHeight - body.scrollTop - body.clientHeight <= 40;
  function sync() {
    send.disabled = pending || !input.value.trim();
    root.querySelectorAll('.axchat-retry').forEach(b => { b.disabled = pending; });
    latest.hidden = !unread;
    badge.hidden = !unread || opened;
  }
  function bottom() {
    body.scrollTop = welcome.hidden ? body.scrollHeight : 0; savedScroll = body.scrollTop;
    following = true; unread = false; sync();
  }
  function layout() {
    const vv = window.visualViewport;
    const width = vv ? vv.width : document.documentElement.clientWidth;
    const height = vv ? vv.height : window.innerHeight;
    const left = vv ? vv.offsetLeft : 0, top = vv ? vv.offsetTop : 0;
    const s = getComputedStyle(safe), margin = mobile() ? 16 : 24, size = parseFloat(getComputedStyle(root).getPropertyValue('--axchat-launch-size'));
    const edgeRight = margin + parseFloat(s.paddingRight), edgeBottom = margin + parseFloat(s.paddingBottom);
    const edgeLeft = margin + parseFloat(s.paddingLeft), edgeTop = margin + parseFloat(s.paddingTop);
    const availableW = Math.max(1, width - edgeRight - edgeLeft);
    // Keep desktop home navigation accessible, including at browser zoom levels.
    const siteHeader = document.querySelector('#site-header');
    const headerBottom = !mobile() && siteHeader ? siteHeader.getBoundingClientRect().bottom : 0;
    const topClearance = Math.max(edgeTop, headerBottom > 0 ? headerBottom - top + 12 : 0);
    const availableH = Math.max(1, height - edgeBottom - size - 12 - topClearance);
    const w = Math.min(mobile() ? 400 : desired.width, availableW);
    const h = Math.min(mobile() ? 560 : desired.height, availableH);
    panel.classList.toggle('axchat-compact', h < 520);
    const launchX = movable && chatPosition ? Math.max(left+edgeLeft, Math.min(chatPosition.x, left+width-edgeRight-size)) : left+width-edgeRight-size;
    const launchY = movable && chatPosition ? Math.max(top+topClearance,Math.min(chatPosition.y,top+height-edgeBottom-size)) : top+height-edgeBottom-size;
    if(movable&&chatPosition)chatPosition={x:launchX,y:launchY};
    launcher.style.left = `${launchX}px`;
    launcher.style.top = `${launchY}px`;
    const defaultPanelLeft = movable ? Math.max(left+edgeLeft,Math.min(launchX+size-w, left+width-edgeRight-w)) : left+width-edgeRight-w;
    const defaultPanelTop = movable ? Math.max(top+topClearance,Math.min(launchY-h-12,top+height-edgeBottom-h)) : top+height-edgeBottom-size-12-h;
    const panelLeft = movable && panelPosition ? Math.max(left+edgeLeft,Math.min(panelPosition.x,left+width-edgeRight-w)) : defaultPanelLeft;
    const panelTop = movable && panelPosition ? Math.max(top+topClearance,Math.min(panelPosition.y,top+height-edgeBottom-h)) : defaultPanelTop;
    if(movable&&panelPosition)panelPosition={x:panelLeft,y:panelTop};
    Object.assign(panel.style, {left:`${panelLeft}px`, top:`${panelTop}px`, width:`${w}px`, height:`${h}px`});
    if (opened && following) bottom();
    return {availableW, availableH};
  }
  function open() {
    opened = true; hasOpened = true; panel.hidden = false; layout();
    body.scrollTop = following ? (welcome.hidden ? body.scrollHeight : 0) : savedScroll;
    if (following) unread = false;
    launcher.setAttribute('aria-expanded', 'true');
    launcher.setAttribute('aria-label', t('minimize')); sync();
    // Do not summon a mobile keyboard merely by opening the panel.
    $('.axchat-minimize').focus({preventScroll:true});
  }
  function minimize() {
    savedScroll = body.scrollTop; opened = false; panel.hidden = true;
    launcher.setAttribute('aria-expanded', 'false');
    launcher.setAttribute('aria-label', t('restore')); sync();
    launcher.focus({preventScroll:true});
  }
  function close() {
    generation++; pending = false; input.value = ''; composing = false;
    controller?.abort(); controller = null; history = [];
    messages.replaceChildren(); welcome.hidden = false; suggestions.hidden = false;
    desired = {width:400, height:560}; following = true; unread = false; announce('');
    minimize(); savedScroll = 0; layout();
    hasOpened = false; launcher.setAttribute('aria-label', t('open'));
  }
  function bubble(kind, text) {
    const node = document.createElement('div'); node.className = `axchat-message axchat-${kind}`;
    node.lang = locale;
    if (text) node.textContent = text;
    messages.append(node); return node;
  }
  // (2026-09-29) AI 답변을 한 번에 붙이지 않고 빠르게 타이핑하듯 보여 준다(최대 약 2초).
  // 움직임 줄이기 설정이면 바로 전체를 보여 주고, 탭이 숨겨지면 남은 글자를 한 번에 채운다.
  function typeOut(node, text, token) {
    const chars = Array.from(text);
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || chars.length < 2) { node.textContent = text; return Promise.resolve(); }
    const step = Math.max(2, Math.ceil(chars.length / 120)), textNode = document.createTextNode('');
    node.replaceChildren(textNode);
    let shown = 0;
    return new Promise(resolve => {
      const tick = () => {
        if (token !== generation) return resolve();
        const next = document.hidden ? chars.length : Math.min(chars.length, shown + step);
        textNode.appendData(chars.slice(shown, next).join('')); shown = next;
        if (opened && following) body.scrollTop = body.scrollHeight;
        if (shown < chars.length) setTimeout(tick, 16); else resolve();
      };
      tick();
    });
  }
  async function request(question, answer) {
    if (pending) return;
    pending = true; sync();
    const token = generation;
    const requestLocale = answer.dataset.requestLocale || locale;
    answer.dataset.requestLocale = requestLocale;
    answer.dataset.question = question;
    delete answer.dataset.demoComplete;
    answer.lang = requestLocale;
    answer.replaceChildren();
    const loading = document.createElement('div'); loading.className = 'axchat-loading';
    const spinner = document.createElement('span'); spinner.className = 'axchat-spinner'; spinner.setAttribute('aria-hidden','true');
    loading.append(spinner, localized(document.createElement('span'), 'loading')); answer.append(loading);
    announce('loading');
    if (opened && following) bottom();
    let failed = false;
    const activeController = new AbortController();
    controller = activeController;
    const timeout = live ? setTimeout(() => activeController.abort(), 55000) : null;
    try {
      let result;
      if (live) {
        const response = await fetch('/api/chat', {
          method:'POST', headers:{'Content-Type':'application/json'}, signal:activeController.signal,
          body:JSON.stringify({question, language:requestLocale, history}),
        });
        result = await response.json();
        if (!response.ok || result.mode !== 'live' || typeof result.answer !== 'string') {
          const error = new Error('Chat unavailable'); error.code = result.code; throw error;
        }
      } else await provider.respond(question, requestLocale);
      if (token !== generation) return;
      if (live) {
        answer.lang = requestLocale;
        const label = document.createElement('small'); label.textContent = textFor('replyLabel', requestLocale);
        const content = document.createElement('div');
        answer.replaceChildren(label, content);
        history.push({role:'user', content:question}, {role:'assistant', content:result.answer});
        while (history.length > 12 || history.reduce((sum, item) => sum + item.content.length, 0) > 24000) history.splice(0, 2);
        await typeOut(content, result.answer, token);
        if (token !== generation) return;
      } else {
        answer.dataset.demoComplete = 'true';
        renderAnswer(answer);
      }
    } catch (error) {
      if (token !== generation) return;
      failed = true; answer.replaceChildren(localized(document.createElement('span'), error.code === 'not_configured' ? 'notConfigured' : 'error'));
      const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'axchat-retry'; localized(retry, 'retry');
      retry.addEventListener('click', () => { if (!pending) request(question, answer); }); answer.append(retry);
    } finally {
      if (timeout !== null) clearTimeout(timeout);
      if (controller === activeController) controller = null;
    }
    if (token !== generation) return;
    pending = false; announce(failed ? 'failed' : 'arrived');
    if (opened && following) bottom();
    else { unread = true; sync(); }
    sync();
  }
  function submit(text) {
    const question = text.trim();
    if (!question || question.length > 4000 || pending) return;
    welcome.hidden = true; suggestions.hidden = true;
    bubble('user', question); input.value = '';
    const answer = bubble('answer');
    // request sets pending synchronously, before the first await.
    request(question, answer); bottom();
  }
  // Desktop: drag the launcher or the opened chat titlebar to move the *entire* widget.
  // Window-level listeners retain drag even when the pointer crosses cards and charts.
  if(movable){
    const head=$('.axchat-header');
    const startMove=(e,source)=>{
      if(mobile()||e.button!==0||(source==='header'&&e.target.closest('button,.axchat-resize')))return;
      const launchRect=launcher.getBoundingClientRect();
      const panelRect=panel.getBoundingClientRect();
      chatMove={id:e.pointerId,source,clientX:e.clientX,clientY:e.clientY,
        launchX:launchRect.left,launchY:launchRect.top,
        panelX:panelRect.left,panelY:panelRect.top,moved:false};
      root.classList.add('axchat-moving');
      try{e.currentTarget.setPointerCapture(e.pointerId);}catch{}
      e.preventDefault();
    };
    const move=e=>{
      if(!chatMove||e.pointerId!==chatMove.id)return;
      const dx=e.clientX-chatMove.clientX,dy=e.clientY-chatMove.clientY;
      if(!chatMove.moved&&Math.hypot(dx,dy)<5)return;
      chatMove.moved=true;
      e.preventDefault();
      chatPosition={x:chatMove.launchX+dx,y:chatMove.launchY+dy};
      if(opened)panelPosition={x:chatMove.panelX+dx,y:chatMove.panelY+dy};
      layout();
    };
    const finish=e=>{
      if(!chatMove||e.pointerId!==chatMove.id)return;
      const didMove=chatMove.moved;
      const origin=chatMove.source;
      chatMove=null;root.classList.remove('axchat-moving');
      if(didMove){
        saveChatPosition();
        if(origin==='launcher'){skipLauncherClick=true;skipClickUntil=performance.now()+500;}
      }
    };
    [[launcher,'launcher'],[head,'header']].forEach(([el,source])=>{
      if(!el)return;
      el.addEventListener('pointerdown',e=>startMove(e,source));
      el.addEventListener('pointermove',move);
      for(const name of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(name,finish);
    });
    window.addEventListener('pointermove',move,{capture:true});
    window.addEventListener('pointerup',finish,{capture:true});
    window.addEventListener('pointercancel',finish,{capture:true});
  }
  launcher.addEventListener('click', (e) => {if(skipLauncherClick){const wasRecent=performance.now()<skipClickUntil;skipLauncherClick=false;if(wasRecent){e.preventDefault();return;}}opened ? minimize() : open();});
  $('.axchat-minimize').addEventListener('click', minimize);
  $('.axchat-close').addEventListener('click', close);
  form.addEventListener('submit', e => { e.preventDefault(); submit(input.value); });
  input.addEventListener('input', sync);
  input.addEventListener('compositionstart', () => { composing = true; });
  input.addEventListener('compositionend', () => { composing = false; });
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey && !mobile() && !e.isComposing && !composing && e.keyCode !== 229) {
      // While waiting, keep Enter available for drafting multiline text.
      if (pending) return;
      e.preventDefault(); submit(input.value);
    }
  });
  root.addEventListener('keydown', e => e.stopPropagation());
  root.addEventListener('pointerdown', e => e.stopPropagation());
  body.addEventListener('scroll', () => {
    if (!opened) return;
    savedScroll = body.scrollTop; following = nearBottom();
    if (following) { unread = false; sync(); }
  });
  latest.querySelector('button').addEventListener('click', bottom);
  function resize(w, h) {
    const bounds = layout();
    desired = {width:Math.min(bounds.availableW, Math.max(360,w)), height:Math.min(bounds.availableH, Math.max(480,h))}; layout();
  }
  handle.addEventListener('pointerdown', e => {
    if (mobile() || e.button !== 0) return;
    e.preventDefault(); const r = panel.getBoundingClientRect();
    drag = {id:e.pointerId, x:e.clientX, y:e.clientY, w:r.width, h:r.height};
    handle.setPointerCapture(e.pointerId); root.classList.add('axchat-resizing');
  });
  handle.addEventListener('pointermove', e => {
    if (drag && e.pointerId === drag.id) resize(drag.w + drag.x - e.clientX, drag.h + drag.y - e.clientY);
  });
  function endDrag() { drag = null; root.classList.remove('axchat-resizing'); }
  ['pointerup','pointercancel','lostpointercapture'].forEach(event => handle.addEventListener(event, endDrag));
  handle.addEventListener('keydown', e => {
    const change = {ArrowLeft:[20,0],ArrowRight:[-20,0],ArrowUp:[0,20],ArrowDown:[0,-20]}[e.key];
    if (!change) return; e.preventDefault();
    const r = panel.getBoundingClientRect(); resize(r.width + change[0], r.height + change[1]);
  });
  window.addEventListener('resize', layout);
  window.addEventListener('scroll', layout, {passive:true});
  const siteHeader = document.querySelector('#site-header');
  if (siteHeader && typeof ResizeObserver !== 'undefined') new ResizeObserver(layout).observe(siteHeader);
  window.visualViewport?.addEventListener('resize', layout);
  window.visualViewport?.addEventListener('scroll', layout);
  // Site events update open/minimized chats; the observer also supports other switchers.
  window.addEventListener('axp:language-changed', event => {
    const next = event.detail?.language || document.documentElement.lang;
    if (i18n.normalize(next) !== locale) setLanguage(next);
  });
  new MutationObserver(() => {
    if (i18n.normalize(document.documentElement.lang) !== locale) setLanguage(document.documentElement.lang);
  }).observe(document.documentElement, {attributes:true, attributeFilter:['lang']});
  window.AXPORTChat = Object.freeze({ setLanguage, getLanguage: () => locale });
  setLanguage(locale);
})();
