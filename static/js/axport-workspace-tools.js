"use strict";
/* AXPORT dashboard controls: world clocks, the single widget menu, themes, and UI-language labels.
   All clocks use the browser's Intl timezone database; no external time API/key is needed. */
(() => {
  // (junhee) 2026-09-28 juyeon 원본의 1회 위젯 배치 초기화(v0.8.6 새 배치용)는 기존 배치를 지우므로 가져오지 않음.
  const $ = (s, r=document) => r.querySelector(s);
  const LANG = {
    ko: { widget:'위젯', edit:'위젯 편집', finish:'편집 완료', reset:'배치 초기화', theme:'테마', clock:'세계 시간', add:'지역 시계 추가', remove:'시계 삭제', select:'지역 선택', blue:'블루', pink:'핑크', green:'그린', yellow:'옐로우', purple:'퍼플', dark:'다크', neutral:'라이트', seoul:'서울', newYork:'뉴욕', london:'런던', shanghai:'상하이', tokyo:'도쿄', taipei:'타이베이', singapore:'싱가포르', hongKong:'홍콩', dubai:'두바이', delhi:'델리', paris:'파리', berlin:'베를린', sydney:'시드니', losAngeles:'로스앤젤레스', chicago:'시카고', toronto:'토론토', mexicoCity:'멕시코시티', saoPaulo:'상파울루', jakarta:'자카르타', bangkok:'방콕', auckland:'오클랜드', removeClock:'우클릭하여 시계 삭제'},
    en: { widget:'Widgets', edit:'Edit widgets', finish:'Finish editing', reset:'Reset layout', theme:'Theme', clock:'World clocks', add:'Add world clock', remove:'Remove clock', select:'Choose region', blue:'Blue', pink:'Pink', green:'Green', yellow:'Yellow', purple:'Purple', dark:'Dark', neutral:'Light', seoul:'Seoul', newYork:'New York', london:'London', shanghai:'Shanghai', tokyo:'Tokyo', taipei:'Taipei', singapore:'Singapore', hongKong:'Hong Kong', dubai:'Dubai', delhi:'New Delhi', paris:'Paris', berlin:'Berlin', sydney:'Sydney', losAngeles:'Los Angeles', chicago:'Chicago', toronto:'Toronto', mexicoCity:'Mexico City', saoPaulo:'São Paulo', jakarta:'Jakarta', bangkok:'Bangkok', auckland:'Auckland', removeClock:'Right-click to remove'},
    zh: { widget:'组件', edit:'编辑组件', finish:'完成编辑', reset:'重置布局', theme:'主题', clock:'世界时间', add:'添加地区时钟', remove:'删除时钟', select:'选择地区', blue:'蓝色', pink:'粉色', green:'绿色', yellow:'黄色', purple:'紫色', dark:'深色', neutral:'浅色', seoul:'首尔', newYork:'纽约', london:'伦敦', shanghai:'上海', tokyo:'东京', taipei:'台北', singapore:'新加坡', hongKong:'香港', dubai:'迪拜', delhi:'新德里', paris:'巴黎', berlin:'柏林', sydney:'悉尼', losAngeles:'洛杉矶', chicago:'芝加哥', toronto:'多伦多', mexicoCity:'墨西哥城', saoPaulo:'圣保罗', jakarta:'雅加达', bangkok:'曼谷', auckland:'奥克兰', removeClock:'右键删除时钟'},
    ja: { widget:'ウィジェット', edit:'ウィジェット編集', finish:'編集を終了', reset:'配置をリセット', theme:'テーマ', clock:'世界時計', add:'都市を追加', remove:'時計を削除', select:'都市を選択', blue:'ブルー', pink:'ピンク', green:'グリーン', yellow:'イエロー', purple:'パープル', dark:'ダーク', neutral:'ライト', seoul:'ソウル', newYork:'ニューヨーク', london:'ロンドン', shanghai:'上海', tokyo:'東京', taipei:'台北', singapore:'シンガポール', hongKong:'香港', dubai:'ドバイ', delhi:'ニューデリー', paris:'パリ', berlin:'ベルリン', sydney:'シドニー', losAngeles:'ロサンゼルス', chicago:'シカゴ', toronto:'トロント', mexicoCity:'メキシコシティ', saoPaulo:'サンパウロ', jakarta:'ジャカルタ', bangkok:'バンコク', auckland:'オークランド', removeClock:'右クリックで削除'}
  };
  const ZONES=[
    ['Asia/Seoul','seoul'],['America/New_York','newYork'],['Europe/London','london'],['Asia/Shanghai','shanghai'],
    ['Asia/Tokyo','tokyo'],['Asia/Taipei','taipei'],['Asia/Singapore','singapore'],['Asia/Hong_Kong','hongKong'],
    ['Asia/Dubai','dubai'],['Asia/Kolkata','delhi'],['Europe/Paris','paris'],['Europe/Berlin','berlin'],
    ['Australia/Sydney','sydney'],['America/Los_Angeles','losAngeles'],['America/Chicago','chicago'],['America/Toronto','toronto'],
    ['America/Mexico_City','mexicoCity'],['America/Sao_Paulo','saoPaulo'],['Asia/Jakarta','jakarta'],['Asia/Bangkok','bangkok'],['Pacific/Auckland','auckland']
  ];
  const DEFAULT=['Asia/Seoul','America/New_York','Europe/London','Asia/Shanghai'];
  const CLOCK_LIMIT=6;
  const KEY='axport.world-clocks.v2', THEME_KEY='axport.dashboard.theme.v1';
  const currentLang=()=>window.AXPI18n?.language||'ko';
  const L=(k)=>(LANG[currentLang()]||LANG.ko)[k]||k;
  const safeStore=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch{}};
  const restore=(k,fallback)=>{try{const d=JSON.parse(localStorage.getItem(k));return d==null?fallback:d;}catch{return fallback;}};
  let zones=restore(KEY,DEFAULT);
  if(!Array.isArray(zones)) zones=[...DEFAULT];
  zones=[...new Set(zones.filter(z=>ZONES.some(v=>v[0]===z)))].slice(0,CLOCK_LIMIT);
  // An intentionally empty clock list stays empty until a region is added.
  const themes=['neutral','blue','pink','green','yellow','purple'];
  let theme=restore(THEME_KEY,'neutral');if(!themes.includes(theme))theme='neutral'; // (junhee) 2026-09-28 기본값은 라이트(기존 화면 그대로)
  let clocks,widgetMenu,clockMenu,widgetButton,themeSelect;
  const timeLabel=(zone)=>{const key=ZONES.find(v=>v[0]===zone)?.[1];return L(key||zone);};
  function renderClocks(){
    if(!clocks)return;
    clocks.querySelectorAll('[data-sx-zone]').forEach(n=>n.remove());
    const plus=$('#axp-clock-add');
    zones.forEach(zone=>{
      const el=document.createElement('div');el.className='axp-clock';el.dataset.sxZone=zone;
      const label=document.createElement('span');label.textContent=timeLabel(zone);
      const tz=document.createElement('small');tz.textContent=new Intl.DateTimeFormat('en',{timeZone:zone,timeZoneName:'short'}).formatToParts(new Date()).find(v=>v.type==='timeZoneName')?.value||'';
      const time=document.createElement('time');time.textContent='--:--:--';
      el.append(label,tz,time);el.title=L('removeClock');el.tabIndex=0;
      el.addEventListener('contextmenu',ev=>{ev.preventDefault();openClockMenu(ev.clientX,ev.clientY,zone);});
      el.addEventListener('keydown',ev=>{if(ev.key==='Delete'||ev.key==='Backspace'){ev.preventDefault();removeClock(zone);} });
      clocks.insertBefore(el,plus);
    });
    // The team's widgets.js clock timer reads [data-sx-zone] and updates all user-added clocks every second.
    if(plus){ plus.disabled=zones.length>=CLOCK_LIMIT;plus.setAttribute('aria-disabled',String(plus.disabled));plus.hidden=plus.disabled;}
    fitClocks();
    if(clocks.scrollWidth>clocks.clientWidth && plus && !plus.disabled) plus.scrollIntoView({block:'nearest',inline:'nearest'});
  }
  // (junhee) 2026-09-28 세계 시계를 늘려도 머리글 왼쪽(로고·워크스페이스 이름)·오른쪽(위젯·언어·날짜·도움말) 버튼과 겹치지 않게 맞춘다.
  // 1) 빈 칸에 들어가면 기존처럼 가운데  2) 가운데서 겹치면 빈 칸 안으로 옆으로 이동  3) 그래도 넓으면 작은 시계(시간대 표시 숨김)
  // 4) 그래도 넓으면 빈 칸 폭만큼만 보이고 가로 스크롤(마우스 휠로 넘김). 기본 4개가 들어가는 화면은 바뀌지 않는다.
  function fitClocks(){
    const header=$('.desktop-header');if(!header||!clocks)return;
    const group=clocks.parentElement&&clocks.parentElement.classList.contains('jd-header-center')?clocks.parentElement:null;
    const centered=!!group&&getComputedStyle(group).position==='absolute';
    clocks.classList.remove('axp-clocks-compact','axp-clocks-scroll');clocks.style.maxWidth='';if(group)group.style.transform='';
    header.classList.remove('axp-clock-fit');
    const shown=(el)=>el&&el.getClientRects().length>0&&getComputedStyle(el).visibility!=='hidden';
    const right=header.querySelector('.header-right'),GAP=14,cs=getComputedStyle(header);
    const hr=header.getBoundingClientRect(),padL=parseFloat(cs.paddingLeft)||0,padR=parseFloat(cs.paddingRight)||0,mid=hr.left+hr.width/2;
    let L,R;
    if(matchMedia('(max-width:600px)').matches){ // 모바일: 시계가 머리글 한 줄 전체를 쓴다
      L=hr.left+padL;R=hr.right-padR;
    }else{
      // 흐름 배치(1280px 미만)에서는 다른 머리글 요소가 찌그러지지 않게 원래 폭으로 재고, 시계만 줄인다
      if(!centered)header.classList.add('axp-clock-fit');
      L=hr.left+padL;
      [...header.children].forEach(el=>{if(el===right||el===group||el===clocks||el.id==='sx-toolbar'||!shown(el))return;const r=el.getBoundingClientRect();if(r.width&&r.right<=mid)L=Math.max(L,r.right);});
      const kids=right?[...right.children].filter(shown):[];
      if(centered)R=kids.length?Math.min(...kids.map(k=>k.getBoundingClientRect().left)):hr.right-padR;
      else R=hr.right-padR-(right&&shown(right)?right.getBoundingClientRect().width:0);
      L+=GAP;R-=GAP;
    }
    const avail=Math.max(0,R-L),w=()=>clocks.scrollWidth;
    if(w()>avail)clocks.classList.add('axp-clocks-compact');
    if(w()>avail){clocks.classList.add('axp-clocks-scroll');clocks.style.maxWidth=Math.floor(avail)+'px';}
    else if(!centered&&!clocks.classList.contains('axp-clocks-compact'))header.classList.remove('axp-clock-fit'); // 들어가면 기존 배치 그대로
    markEnd();
    if(centered){
      const gw=group.getBoundingClientRect().width,natural=mid-gw/2,left=Math.min(Math.max(natural,L),Math.max(L,R-gw)),dx=Math.round(left-natural);
      if(dx)group.style.transform=`translate(calc(-50% + ${dx}px), -50%)`;
    }
  }
  const markEnd=()=>clocks&&clocks.classList.toggle('axp-clocks-end',clocks.scrollLeft+clocks.clientWidth>=clocks.scrollWidth-2);
  // (junhee) 2026-09-28 분석 창 탭(종합·규제·시장성·가격·물류·안정성) 이름이 번역으로 길어져도 버튼 안에 한 줄로: 넘치는 탭만 글자를 0.5px씩 줄인다(최소 8px)
  function fitTabs(){
    document.querySelectorAll('#analysis-window .bookmark-tabs button').forEach(btn=>{
      const label=btn.querySelector('span');if(!label)return;
      label.style.fontSize='';label.style.letterSpacing='';
      if(!btn.clientWidth)return; // 창이 닫혀 있으면 열릴 때 다시 맞춘다
      const room=btn.clientWidth-6;let size=parseFloat(getComputedStyle(label).fontSize)||11;
      while(label.scrollWidth>room&&size>8){size-=.5;label.style.fontSize=size+'px';}
      if(label.scrollWidth>room)label.style.letterSpacing='-.03em';
    });
  }
  let tabFrame=0;
  const scheduleTabs=()=>{cancelAnimationFrame(tabFrame);tabFrame=requestAnimationFrame(fitTabs);};
  let fitFrame=0;
  const scheduleFit=()=>{cancelAnimationFrame(fitFrame);fitFrame=requestAnimationFrame(fitClocks);};
  function removeClock(zone){zones=zones.filter(z=>z!==zone);safeStore(KEY,zones);renderClocks();clockMenu.hidden=true;}
  function openClockMenu(x,y,zone){
    clockMenu.replaceChildren();const b=document.createElement('button');b.type='button';b.textContent=L('remove');
    b.addEventListener('click',()=>removeClock(zone));clockMenu.append(b);clockMenu.hidden=false;
    clockMenu.style.left=Math.max(8,Math.min(x,innerWidth-175))+'px';clockMenu.style.top=Math.max(8,Math.min(y,innerHeight-46))+'px';
  }
  function updateText(){
    if(!clocks)return;
    widgetButton.querySelector('span').textContent=L('widget');widgetButton.setAttribute('aria-label',L('widget'));
    const langSelect=$('#axp-language'), langLabel=$('#axp-language-current');
    if(langSelect && langLabel) langLabel.textContent=langSelect.selectedOptions[0]?.textContent||'한국어';
    $('#axp-language-trigger')?.setAttribute('aria-label',({'ko':'언어 선택 열기','en':'Choose language','zh':'选择语言','ja':'言語を選択'})[currentLang()]||'Choose language');
    document.querySelectorAll('.analysis-window .bookmark-tabs button').forEach(b=>{b.title=b.querySelector('span')?.textContent?.trim()||b.textContent?.trim()||'';});
    $('#axp-widget-edit').textContent=$('#sx-edit').getAttribute('aria-pressed')==='true'?L('finish'):L('edit');
    $('#axp-widget-reset').textContent=L('reset');$('#axp-widget-theme-label').textContent=L('theme');
    themeSelect.replaceChildren(...themes.map(k=>new Option(L(k),k)));themeSelect.value=theme;
    $('#axp-clock-add').setAttribute('aria-label',L('add'));$('#axp-clock-add').title=L('add');
    $('#axp-clock-select').replaceChildren(new Option(L('select'),'',true,true),...ZONES.filter(([z])=>!zones.includes(z)).map(([z,key])=>new Option(L(key),z)));
    $('#axp-clock-add').disabled=zones.length>=CLOCK_LIMIT;
    clockMenu.hidden=true;
    renderClocks();
  }
  // Synchronize the brand image with the active palette (the original asset is restored in light modes).
  function setTheme(next){
    if(!themes.includes(next))return;
    theme=next;if(theme==='neutral')delete document.body.dataset.axpTheme;else document.body.dataset.axpTheme=theme;safeStore(THEME_KEY,theme); // (junhee) 라이트 = 테마 속성 없음 = 기존 화면
    if(themeSelect)themeSelect.value=theme;
    const logo=$('.desktop-header .brand img');
    if(logo){
      if(!logo.dataset.axpLightLogo)logo.dataset.axpLightLogo=logo.getAttribute('src')||'/static/assets/axport-logo.png';
      const src=logo.dataset.axpLightLogo; // Only light/readable themes remain.
      if(logo.getAttribute('src')!==src)logo.setAttribute('src',src);
    }
  }
  function init(){
    clocks=$('#sx-clocks');const toolbar=$('#sx-toolbar');if(!clocks||!toolbar)return;
    // Keep the team's edit/reset handlers untouched. The original buttons remain accessible by JS, not visible twice.
    const widgetDropdown=document.createElement('div');widgetDropdown.className='axp-widget-dropdown';
    widgetDropdown.innerHTML=`<button type="button" id="axp-widget-toggle" aria-haspopup="true" aria-expanded="false"><i class="ph ph-gear-six" aria-hidden="true"></i><span></span><i class="ph ph-caret-down" aria-hidden="true"></i></button><div id="axp-widget-menu" class="axp-widget-menu" hidden><button type="button" id="axp-widget-edit"></button><button type="button" id="axp-widget-reset"></button><label id="axp-widget-theme-label" for="axp-theme-select"></label><select id="axp-theme-select"></select></div>`;
    // Pin the widget selector beside the language selector; never attach it to the resizing clock strip.
    const controls=$('.desktop-header .header-right');
    const languageControl=controls?.querySelector('.workspace-language-control');
    if(controls&&languageControl) controls.insertBefore(widgetDropdown,languageControl);
    else toolbar.append(widgetDropdown);
    widgetMenu=$('#axp-widget-menu');widgetButton=$('#axp-widget-toggle');themeSelect=$('#axp-theme-select');
    // Only the right-hand arrow opens the language dropdown. The original #axp-language
    // select remains in the DOM so AXPI18n's existing change listener continues to work.
    const langTrigger=$('#axp-language-trigger'),langMenu=$('#axp-language-menu'),langSelect=$('#axp-language');
    if(langTrigger && langMenu && langSelect){
      const options=[...langSelect.options];
      langMenu.replaceChildren(...options.map(option=>{
        const item=document.createElement('button');item.type='button';item.setAttribute('role','menuitemradio');
        item.dataset.lang=option.value;item.textContent=option.textContent;
        item.addEventListener('click',()=>{
          langSelect.value=item.dataset.lang;langSelect.dispatchEvent(new Event('change',{bubbles:true}));
          langMenu.hidden=true;langTrigger.setAttribute('aria-expanded','false');langTrigger.focus();
        });return item;
      }));
      const syncLanguageMenu=()=>{
        langMenu.querySelectorAll('[data-lang]').forEach(b=>b.setAttribute('aria-checked',String(b.dataset.lang===langSelect.value)));
        $('#axp-language-current').textContent=langSelect.selectedOptions[0]?.textContent||'한국어';
      };
      langTrigger.addEventListener('click',()=>{
        langMenu.hidden=!langMenu.hidden;langTrigger.setAttribute('aria-expanded',String(!langMenu.hidden));
        if(!langMenu.hidden){syncLanguageMenu();widgetMenu.hidden=true;widgetButton.setAttribute('aria-expanded','false');langMenu.querySelector('[aria-checked="true"]')?.focus();}
      });
      langMenu.addEventListener('keydown',e=>{
        if(e.key==='Escape'){langMenu.hidden=true;langTrigger.setAttribute('aria-expanded','false');langTrigger.focus();}
        if(e.key==='ArrowDown'||e.key==='ArrowUp'){
          e.preventDefault();const items=[...langMenu.querySelectorAll('button')];const i=items.indexOf(document.activeElement);
          items[(i+(e.key==='ArrowDown'?1:items.length-1))%items.length]?.focus();
        }
      });
      document.addEventListener('pointerdown',e=>{
        if(!e.target.closest('.workspace-language-control')){langMenu.hidden=true;langTrigger.setAttribute('aria-expanded','false');}
      },true);
      document.addEventListener('keydown',e=>{if(e.key==='Escape'){langMenu.hidden=true;langTrigger.setAttribute('aria-expanded','false');}});
      window.addEventListener('axp:language-changed',syncLanguageMenu);
      syncLanguageMenu();
    }

    clocks.classList.add('axp-editable-clocks');
    const add=document.createElement('button');add.id='axp-clock-add';add.type='button';add.className='axp-clock-plus';add.textContent='+';
    const select=document.createElement('select');select.id='axp-clock-select';select.setAttribute('aria-label',L('select'));select.className='axp-clock-select';
    // Keep the dropdown outside the horizontally scrollable clock rail to prevent clipping.
    clocks.append(add);document.body.append(select);
    clockMenu=document.createElement('div');clockMenu.id='axp-clock-menu';clockMenu.className='axp-clock-menu';clockMenu.hidden=true;document.body.append(clockMenu);
    const pick=()=>{
      if(zones.length>=CLOCK_LIMIT)return;
      select.classList.toggle('open');
      if(select.classList.contains('open')){
        const r=add.getBoundingClientRect();
        select.style.left=Math.max(8,Math.min(r.right-200,innerWidth-210))+'px';
        select.style.top=Math.min(r.bottom+8,innerHeight-280)+'px';
        select.focus();
      }
    };
    add.addEventListener('click',pick);
    select.addEventListener('change',()=>{const zone=select.value;if(zone&&!zones.includes(zone)&&zones.length<CLOCK_LIMIT){zones.push(zone);safeStore(KEY,zones);}select.classList.remove('open');updateText();});
    select.addEventListener('blur',()=>{select.classList.remove('open');});
    widgetButton.addEventListener('click',()=>{widgetMenu.hidden=!widgetMenu.hidden;widgetButton.setAttribute('aria-expanded',String(!widgetMenu.hidden));});
    $('#axp-widget-edit').addEventListener('click',()=>{$('#sx-edit').click();widgetMenu.hidden=true;widgetButton.setAttribute('aria-expanded','false');updateText();});
    $('#axp-widget-reset').addEventListener('click',()=>{$('#sx-reset').click();widgetMenu.hidden=true;widgetButton.setAttribute('aria-expanded','false');});
    themeSelect.addEventListener('change',()=>setTheme(themeSelect.value));
    document.addEventListener('pointerdown',e=>{
      if(!e.target.closest('.axp-widget-dropdown')){widgetMenu.hidden=true;widgetButton.setAttribute('aria-expanded','false');}
      if(!e.target.closest('#axp-clock-menu'))clockMenu.hidden=true;
    },true);
    document.addEventListener('keydown',e=>{if(e.key==='Escape'){widgetMenu.hidden=true;clockMenu.hidden=true;select.classList.remove('open');widgetButton.setAttribute('aria-expanded','false');}});
    window.addEventListener('axp:language-changed',updateText);
    // (junhee) 머리글 폭·오른쪽 버튼 폭(언어·날짜 글자)이 바뀌면 시계 자리를 다시 맞춘다
    window.addEventListener('resize',scheduleFit);
    if(window.ResizeObserver){const ro=new ResizeObserver(scheduleFit);[$('.desktop-header'),$('.desktop-header .header-right')].forEach(el=>el&&ro.observe(el));}
    document.fonts?.ready?.then(scheduleFit);
    // 탭 글자가 바뀌거나(번역) 분석 창이 열리거나 크기가 바뀌면 탭 글자를 다시 맞춘다
    const tabs=document.querySelector('#analysis-window .bookmark-tabs'),win=document.getElementById('analysis-window');
    if(tabs)new MutationObserver(scheduleTabs).observe(tabs,{subtree:true,childList:true,characterData:true});
    if(win)new MutationObserver(scheduleTabs).observe(win,{attributes:true,attributeFilter:['hidden','class','style']});
    if(tabs&&window.ResizeObserver)new ResizeObserver(scheduleTabs).observe(tabs);
    window.addEventListener('axp:language-changed',scheduleTabs);
    document.fonts?.ready?.then(scheduleTabs);scheduleTabs();
    clocks.addEventListener('scroll',markEnd,{passive:true});
    clocks.addEventListener('wheel',e=>{if(!clocks.classList.contains('axp-clocks-scroll')||Math.abs(e.deltaY)<=Math.abs(e.deltaX))return;clocks.scrollLeft+=e.deltaY;e.preventDefault();},{passive:false});
    window.AXPI18n?.register({
      '위젯':{en:'Widgets',zh:'组件',ja:'ウィジェット'}, '폴더로 이동: ':{en:'Move to: ',zh:'移至文件夹：',ja:'フォルダへ移動：'},
      '새 폴더':{en:'New folder',zh:'新建文件夹',ja:'新しいフォルダ'},'폴더 이름':{en:'Folder name',zh:'文件夹名称',ja:'フォルダ名'},
      '새 이름':{en:'New name',zh:'新名称',ja:'新しい名前'}, '이름 변경':{en:'Rename',zh:'重命名',ja:'名前を変更'},
      '삭제':{en:'Delete',zh:'删除',ja:'削除'},'바탕화면으로 이동':{en:'Move to desktop',zh:'移至桌面',ja:'デスクトップに移動'},
      '폴더가 비어 있습니다.':{en:'This folder is empty.',zh:'文件夹为空。',ja:'フォルダは空です。'},
      '파일을 폴더로 이동했습니다.':{en:'File moved to folder.',zh:'文件已移至文件夹。',ja:'ファイルをフォルダへ移動しました。'},
      '폴더를 휴지통으로 이동했습니다.':{en:'Folder moved to Trash.',zh:'文件夹已移至回收站。',ja:'フォルダをゴミ箱へ移動しました。'},
      '폴더에 넣은 파일을 관리합니다. 원본 파일은 변경되지 않습니다.':{en:'Manage files in this folder. Original files are unchanged.',zh:'管理文件夹内的文件。原始文件不受影响。',ja:'フォルダ内のファイルを管理します。元のファイルは変更されません。'},
      '폴더를 영구 삭제할까요? 폴더 안의 파일은 휴지통으로 이동합니다.':{en:'Delete this folder permanently? Its files will go to Trash.',zh:'永久删除文件夹吗？里面的文件将移至回收站。',ja:'このフォルダを完全に削除しますか？中のファイルはゴミ箱へ移動します。'},
      '개 파일':{en:'files',zh:'个文件',ja:'ファイル'},'세계 시간':{en:'World clocks',zh:'世界时间',ja:'世界時計'},
      '분석 대시보드':{en:'Analysis dashboard',zh:'分析仪表盘',ja:'分析ダッシュボード'},'휴지통':{en:'Trash',zh:'回收站',ja:'ゴミ箱'},'기업 데이터 업로드':{en:'Upload company data',zh:'上传企业数据',ja:'企業データのアップロード'},'더블클릭으로 열기':{en:'Double-click to open',zh:'双击打开',ja:'ダブルクリックで開く'}
    });
    setTheme(theme);updateText();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
