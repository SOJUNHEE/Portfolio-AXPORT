/* Additive adapter. Reuses the team's original form handlers and analysis window. */
(() => {
 'use strict';
 const $=(q,r=document)=>r.querySelector(q), $$=(q,r=document)=>[...r.querySelectorAll(q)];
 const desk=$('#desktop'), board=$('#sx-board'),canvas=$('#sx-canvas');
 if(!desk || !$('#analysis-window') || !window.JunheeDashboard) return;
 desk.append($('#sx-toolbar'),board);
 $('.desktop-header').insertBefore($('#sx-clocks'),$('.header-right'));
 $('#analysis-window').hidden=true;
 const ids=['upload','fx','news','weather'],key='axsx.team.widgets.v1',mobile=matchMedia('(max-width:900px)');
 let state={hidden:[],positions:null},editing=false,selection=null,drag=null,z=2,requestId=0;
 const data={};
 const language=()=>window.AXPI18n?.language || 'ko';
 const t=k=>(window.AXSX_TEXT[language()] || window.AXSX_TEXT.ko)[k] || k;
 const titles={upload:'uploadTitle',fx:'fxTitle',news:'newsTitle',weather:'weatherTitle'};
 const extra={
  ko:{company:'기업명',fileLimit:'최대 20 MB · CSV는 선택 미리보기만 지원',sample:'팀 샘플 불러오기',teamNote:'기존 팀 분석기에 연결됩니다. 현재 등록된 기업 샘플만 분석하며, 샘플의 HS·대상국 기준으로 결과가 표시됩니다.',widgetTrash:'숨긴 위젯',teamTrash:'기존 파일 휴지통 열기',csv:'CSV는 선택 미리보기만 지원합니다. 기존 분석기는 등록된 XLSX/XLS 샘플만 처리합니다.',privacy:'파일 전송 없음 · 등록된 샘플 여부는 기존 분석기가 SHA-256으로 확인합니다.'},
  en:{company:'Company',fileLimit:'Max. 20 MB · CSV selection preview only',sample:'Load team sample',teamNote:'Connected to the existing team analyzer. Only registered samples can be analyzed; results use the sample’s HS code and destination.',widgetTrash:'Hidden widgets',teamTrash:'Open existing file trash',csv:'CSV is preview-only. The existing analyzer processes registered XLSX/XLS samples.',privacy:'No file upload · the existing analyzer checks registered files using SHA-256.'},
  ja:{company:'企業名',fileLimit:'最大20 MB・CSVは選択プレビューのみ',sample:'チームのサンプル',teamNote:'既存の分析機能に接続します。登録済みサンプルのみ分析でき、サンプルのHS・輸出先に基づく結果が表示されます。',widgetTrash:'非表示のウィジェット',teamTrash:'既存ファイルのゴミ箱',csv:'CSVは選択プレビューのみです。既存の分析機能は登録済みXLSX/XLSに対応します。',privacy:'ファイル送信なし・既存機能でSHA-256照合を行います。'},
  zh:{company:'企业名称',fileLimit:'最大20 MB · CSV仅支持选择预览',sample:'加载团队示例',teamNote:'连接现有团队分析功能。仅分析已注册的示例，结果采用示例的HS编码和目的地。',widgetTrash:'隐藏的组件',teamTrash:'打开现有文件回收站',csv:'CSV仅支持选择预览。现有分析器仅处理已注册的XLSX/XLS示例。',privacy:'不会上传文件 · 现有分析器通过SHA-256匹配注册文件。'}
 };
 const e=k=>(extra[language()]||extra.ko)[k];
 const node=(tag,cls,txt)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(txt!=null)n.textContent=txt;return n;};
 const fmt=(v,d=0)=>new Intl.NumberFormat(window.AXPI18n?.locale||'ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
 try{const old=JSON.parse(localStorage.getItem(key));if(old){editing=false;state.hidden=Array.isArray(old.hidden)?[...new Set(old.hidden.filter(id=>ids.includes(id)))]:[];if(old.positions&&typeof old.positions==='object'){state.positions={};for(const id of ids){const p=old.positions[id];if(p&&['x','y','w','base'].every(k=>Number.isFinite(p[k]))&&p.w>0&&p.base>0)state.positions[id]={...p,y:Math.max(0,Math.min(3000,p.y))};}}}}catch{}
 function save(){state.editing=editing;try{localStorage.setItem(key,JSON.stringify(state));}catch{}}
 function clock(){const now=new Date();$$('[data-sx-zone]').forEach(el=>{const zone=el.dataset.sxZone;const parts=new Intl.DateTimeFormat('en-GB',{timeZone:zone,hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZoneName:'shortOffset'}).formatToParts(now);const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));$('time',el).textContent=`${p.hour}:${p.minute}:${p.second}`;const offset=p.timeZoneName;$('small',el).textContent=parts.find(x=>x.type==='timeZoneName')?.value||offset||'';});}
 function translate(){
  $$('[data-sx-t]').forEach(el=>el.textContent=t(el.dataset.sxT));$$('[data-sx-extra]').forEach(el=>el.textContent=e(el.dataset.sxExtra));
  $$('[data-sx-delete]').forEach(b=>b.setAttribute('aria-label',`${t(titles[b.dataset.sxDelete])} · ${t('hide')}`));
  for(const kind of ['fx','news','weather'])if(data[kind])render(kind,data[kind]);
  renderTrash();clock();layout();
 }
 function source(result){return result.mode==='demo'?t('demo'):result.source;}
 function render(kind,result){
  const badge=$(`#sx-${kind}-badge`);badge.textContent=t(result.status==='error'?'error':result.mode==='demo'?'demo':'live');badge.classList.toggle('live',result.mode==='live');badge.hidden=false;
  const target=$(`#sx-${kind}-rows`);target.replaceChildren();$(`#sx-${kind}-source`).textContent=result.status==='error'?'':source(result);const footer=$(`#sx-${kind}-source`).closest('footer');footer.hidden=kind==='news'&&!$(`#sx-${kind}-source`).textContent;
  if(kind==='weather')$('#sx-weather-period').textContent=result.period?`${t('base')}: ${result.period}, ${t('cumulative')}`:'';
  if(result.status==='error'){const msg=t(({missing_key:'missingKey',weather_not_configured:'weatherPending'})[result.code]||'connectionError');if(kind==='weather'){const row=node('tr'),cell=node('td','sx-empty',msg);cell.colSpan=3;row.append(cell);target.append(row);}else target.append(node('p','sx-empty',msg));return;}
  if(kind==='fx')for(const r of result.rows){const row=node('div','sx-rate');row.append(node('span','',r.pair),node('strong','',fmt(r.value,r.pair.endsWith('CNY')?4:2)),node('small',r.change>=0?'sx-up':'sx-down',r.change==null?t('noPrevious'):`${r.change>=0?'↑':'↓'} ${fmt(Math.abs(r.change),2)}%`));target.append(row);}
  if(kind==='news'){
   if(!result.rows.length)target.append(node('p','sx-empty',t('emptyNews')));
   for(const r of result.rows){const item=node('article','sx-news-item');let title=node('strong','',r.title);try{const url=new URL(r.url);if(!['https:','http:'].includes(url.protocol))throw Error();title=node('a','',r.title);title.href=url.href;title.target='_blank';title.rel='noopener noreferrer';}catch{}item.append(title,node('small','',[result.mode==='demo'?'':r.source,r.published_at?.slice(0,10)].filter(Boolean).join(' · ')));target.append(item);}
  }
  if(kind==='weather')for(const r of result.rows){const v=r.yoy,icon=v==null?'—':v>=30?'☀️':v>=0?'⛅':v>=-10?'☁️':v>=-20?'🌧️':'⛈️';const row=node('tr'),name=node('td','',`${icon} ${t(r.id)}`);name.title=`HS ${r.hs.join(', ')}`;row.append(name,node('td','',Number.isFinite(r.exports_million_usd)?fmt(r.exports_million_usd):'—'),node('td',v>=0?'sx-up':'sx-down',v==null?t('noComparison'):`${v>=0?'↑':'↓'} ${fmt(Math.abs(v),1)}%`));target.append(row);}
  requestAnimationFrame(height);
 }
 async function load(){const current=++requestId,lang=language();await Promise.allSettled(['fx','news','weather'].map(async kind=>{let value;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),25000);try{const response=await fetch(`/_axp_semiconductor/data/${kind}?language=${lang}`,{signal:controller.signal});value=await response.json();if(!response.ok&&value.status!=='error')throw Error();}catch{value={status:'error'};}finally{clearTimeout(timeout);}if(current!==requestId)return;data[kind]=value;render(kind,value);}));}
 function height(){if(!state.positions){canvas.style.height='';return;}let bottom=board.clientHeight-10;$$('[data-sx-widget]').forEach(w=>{if(!w.hidden)bottom=Math.max(bottom,w.offsetTop+w.offsetHeight+8);});canvas.style.height=`${bottom}px`;}
 function badgeTrash(){const trash=$('#desktop-icons [data-id="trash"]');if(!trash)return;let badge=$('.sx-trash-count',trash);if(!badge){badge=node('span','sx-trash-count');badge.dataset.noTranslate='';trash.append(badge);}const count=String(state.hidden.length);if(badge.textContent!==count)badge.textContent=count;badge.hidden=!state.hidden.length;}
 function layout(){
  const width=canvas.clientWidth;canvas.classList.toggle('sx-free',Boolean(state.positions));
  $$('[data-sx-widget]').forEach(w=>{const id=w.dataset.sxWidget;w.hidden=state.hidden.includes(id);if(!state.positions){w.removeAttribute('style');return;}const p=state.positions[id]||{x:0,y:0,w:width*.55,base:width};const ww=Math.min(width,Math.max(280,p.w*width/p.base));Object.assign(w.style,{left:`${Math.max(0,Math.min(width-ww,p.x*width/p.base))}px`,top:`${p.y}px`,width:`${ww}px`});});height();badgeTrash();
 }
 function freeze(){if(state.positions)return;const bounds=canvas.getBoundingClientRect(),positions={};$$('[data-sx-widget]').forEach(w=>{if(!w.hidden){const r=w.getBoundingClientRect();positions[w.dataset.sxWidget]={x:r.left-bounds.left,y:r.top-bounds.top,w:r.width,base:bounds.width};}});state.positions=positions;layout();}
 function place(w,x,y){x=Math.max(0,Math.min(canvas.clientWidth-w.offsetWidth,x));y=Math.max(0,Math.min(3000,y));state.positions[w.dataset.sxWidget]={x,y,w:w.offsetWidth,base:canvas.clientWidth};Object.assign(w.style,{left:`${x}px`,top:`${y}px`,zIndex:String(++z)});height();}
 function onTrash(x,y){const el=$('#desktop-icons [data-id="trash"]');if(!el)return false;const r=el.getBoundingClientRect();return x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom;}
 function hide(id){if(!state.hidden.includes(id))state.hidden.push(id);layout();save();renderTrash();}
 function restore(id){state.hidden=state.hidden.filter(x=>x!==id);layout();save();renderTrash();}
 function renderTrash(){const list=$('#sx-trash-list');list.replaceChildren();for(const id of state.hidden){const row=node('div','sx-trash-row'),button=node('button','',t('restore'));button.type='button';button.addEventListener('click',()=>restore(id));row.append(node('span','',t(titles[id])),button);list.append(row);}if(!state.hidden.length)list.append(node('p','sx-empty',t('emptyTrash')));$('#sx-restore-all').disabled=!state.hidden.length;}
 $$('[data-sx-delete]').forEach(b=>b.addEventListener('click',()=>hide(b.dataset.sxDelete)));
 $$('[data-sx-widget]').forEach(w=>{
  const handle=$('.sx-handle',w);handle.tabIndex=-1;
  handle.addEventListener('pointerdown',ev=>{if(!editing||ev.button!==0||ev.target.closest('button'))return;ev.preventDefault();freeze();drag={id:ev.pointerId,w,handle,x:ev.clientX,y:ev.clientY,left:w.offsetLeft,top:w.offsetTop,scroll:board.scrollTop};handle.setPointerCapture(ev.pointerId);w.classList.add('sx-dragging');});
  handle.addEventListener('pointermove',ev=>{if(!drag||drag.id!==ev.pointerId)return;place(w,drag.left+ev.clientX-drag.x,drag.top+ev.clientY-drag.y+board.scrollTop-drag.scroll);$('#desktop-icons [data-id="trash"]')?.classList.toggle('sx-trash-target',onTrash(ev.clientX,ev.clientY));});
  const end=ev=>{if(!drag||drag.id!==ev.pointerId)return;const remove=ev.type==='pointerup'&&onTrash(ev.clientX,ev.clientY);if(handle.hasPointerCapture(ev.pointerId))handle.releasePointerCapture(ev.pointerId);drag=null;w.classList.remove('sx-dragging');$('#desktop-icons [data-id="trash"]')?.classList.remove('sx-trash-target');if(remove)hide(w.dataset.sxWidget);save();};
  handle.addEventListener('pointerup',end);handle.addEventListener('pointercancel',end);
  handle.addEventListener('keydown',ev=>{if(!editing||ev.target!==handle)return;if(ev.key==='Delete'){ev.preventDefault();hide(w.dataset.sxWidget);return;}const directions={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};if(directions[ev.key]){ev.preventDefault();freeze();const [x,y]=directions[ev.key],step=ev.shiftKey?40:10;place(w,w.offsetLeft+x*step,w.offsetTop+y*step);save();}});
 });
 function syncEditing(){board.classList.toggle('sx-editing',editing);$('#sx-edit').setAttribute('aria-pressed',String(editing));$$('.sx-handle').forEach(h=>h.tabIndex=editing?0:-1);}
 $('#sx-edit').addEventListener('click',()=>{editing=!editing;syncEditing();save();});
 $('#sx-reset').addEventListener('click',()=>{state.positions=null;layout();save();});
 $('#sx-restore-all').addEventListener('click',()=>{state.hidden=[];layout();save();renderTrash();});
 $('#sx-trash-close').addEventListener('click',()=>$('#sx-trash-dialog').close());
 $('#sx-original-trash').addEventListener('click',()=>{$('#sx-trash-dialog').close();$('#desktop-icons [data-id="trash"]')?.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));});
 // Original icons, files and their drag handlers remain owned by workspace.js.
 $('#desktop-icons').addEventListener('click',ev=>{const icon=ev.target.closest('[data-id]');if(icon?.dataset.id==='analysis')$('.side-link[data-action="overview"]').click();if(icon?.dataset.id==='trash'&&ev.detail<=1){renderTrash();$('#sx-trash-dialog').showModal();}});
 $('#desktop-icons').addEventListener('dblclick',ev=>{if(ev.target.closest('[data-id="trash"]')&&$('#sx-trash-dialog').open)$('#sx-trash-dialog').close();});
 new MutationObserver(badgeTrash).observe($('#desktop-icons'),{childList:true});
 // Bridge into existing controls rather than duplicating the team's analyzer.
 function formError(message){$('#sx-error').textContent=message;}
 function mirrorLabel(){if(selection?.csv)return;const value=$('#file-label').textContent;if(selection)$('#sx-file-label').textContent=value;}
 new MutationObserver(mirrorLabel).observe($('#file-label'),{childList:true,characterData:true,subtree:true});
 new MutationObserver(()=>formError($('#upload-error').textContent)).observe($('#upload-error'),{childList:true,characterData:true,subtree:true});
 $('#sx-sample').addEventListener('click',()=>{$('#use-sample').click();selection={sample:true};$('#sx-hs').value='8542.32';$('#sx-company').value='AX 반도체';mirrorLabel();formError('');chips();});
 function accept(file){
  formError('');if(!file)return;
  if(!/\.(xlsx|xls|csv)$/i.test(file.name)){formError(t('fileType'));return;}
  if(file.size<=0||file.size>20*1024*1024){formError(language()==='ko'?'0바이트보다 크고 20 MB 이하인 파일을 선택해 주세요.':'Select a non-empty file up to 20 MB.');return;}
  selection={name:file.name,csv:/\.csv$/i.test(file.name)};
  if(selection.csv){$('#sx-file-label').textContent=file.name;formError(e('csv'));return;}
  const transfer=new DataTransfer();transfer.items.add(file);$('#excel-input').files=transfer.files;$('#excel-input').dispatchEvent(new Event('change',{bubbles:true}));mirrorLabel();
 }
 $('#sx-file-button').addEventListener('click',()=>$('#sx-file').click());$('#sx-file').addEventListener('change',ev=>{accept(ev.target.files[0]);ev.target.value='';});
 $('#sx-drop').addEventListener('dragover',ev=>{ev.preventDefault();ev.stopPropagation();$('#sx-drop').classList.add('sx-over');});
 $('#sx-drop').addEventListener('dragleave',()=>$('#sx-drop').classList.remove('sx-over'));
 $('#sx-drop').addEventListener('drop',ev=>{ev.preventDefault();ev.stopPropagation();$('#sx-drop').classList.remove('sx-over');if(ev.dataTransfer.files.length!==1){formError(t('fileSingle'));return;}accept(ev.dataTransfer.files[0]);});
 function chips(){$$('[data-sx-hs]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.sxHs.replaceAll('.','')===$('#sx-hs').value.replaceAll('.',''))));}
 $$('[data-sx-hs]').forEach(b=>b.addEventListener('click',()=>{$('#sx-hs').value=b.dataset.sxHs;chips();}));$('#sx-hs').addEventListener('input',chips);
 $('#sx-form').addEventListener('submit',ev=>{
  ev.preventDefault();formError('');if(!selection){formError(t('fileNeeded'));return;}if(selection.csv){formError(e('csv'));return;}
  const hs=$('#sx-hs').value.replace(/[.\s]/g,'');if(!/^(\d{6}|\d{8}|\d{10})$/.test(hs)){formError(t('hsInvalid'));return;}
  const hsInput=$('#hs-input');
  if(hsInput.tagName==='SELECT' && ![...hsInput.options].some(o=>o.value===hs))hsInput.add(new Option(hs,hs));
  hsInput.value=hs;$('#company-input').value=$('#sx-company').value;
  const country=$('#sx-country').value;if(![...$('#country-input').options].some(o=>o.value===country))$('#country-input').add(new Option($('#sx-country').selectedOptions[0].textContent,country));$('#country-input').value=country;
  $('#analysis-form').requestSubmit();formError($('#upload-error').textContent);
 });
 window.addEventListener('axp:language-changed',()=>{delete data.news;$('#sx-news-rows').replaceChildren(node('p','sx-empty',t('loading')));translate();load();});
 let width=canvas.clientWidth;new ResizeObserver(()=>{if(width!==canvas.clientWidth){width=canvas.clientWidth;layout();}}).observe(board);
 const observer=new ResizeObserver(()=>{if(!drag)height();});$$('[data-sx-widget]').forEach(w=>observer.observe(w));
 mobile.addEventListener('change',layout);translate();chips();layout();syncEditing();load();document.fonts.ready.then(layout);setInterval(clock,1000);setInterval(()=>{if(!document.hidden)load();},7200000);
})();
