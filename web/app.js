'use strict';
const $ = s => document.querySelector(s);
const state={catalog:null,group:'全部',query:'',favoritesOnly:false,page:1,size:6,os:'windows',favorites:new Set(),trial:null,pixelMode:null};
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const pixelRevision='?v=20261019-all-pixel-v5';
let previewSize=96;
const expressionMoods=[['blink','眨眼','眨眨眼，陪你发呆。',0],['wink','wink','偷偷给你一个 wink。',2],['hop','小跳','开心到跳起来！',3],['think','歪头','嗯？你在想什么呀。',4],['shy','害羞','不要一直盯着看嘛。',5],['sleep','困困','抱着小枕头，休息一下。',6],['wave','挥手','嗨！今天也要开心。',7],['happy','开心','每一帧，都有小情绪。',1]];
const functionalMoods=[['Hand','点击','伸出小手，轻轻点一下。'],['Wait','等待','捧着沙漏，耐心等一会。'],['No','禁止','双手示停：这里不可以。'],['IBeam','文字','安静读书，轻轻翻一页。'],['NWPen','书写','拿起小笔，认真写几笔。'],['SizeWE','横向','拉开双箭头，调整宽度。'],['SizeNS','纵向','上下伸展，调整高度。'],['SizeAll','移动','抱稳小箱子，挪个位置。']];
let studioMode='functional',moods=functionalMoods,selectedMood=moods[0],spritePaused=reducedMotion.matches;
function renderMood(){
 const functional=studioMode==='functional';
 $('#stageSprite').src='/previews/diana/'+(functional?'Character-':'emoji-')+selectedMood[0]+(spritePaused?'.png':'.gif')+pixelRevision;
 $('#stageSprite').alt='嘉然像素动态：'+selectedMood[1];$('#moodTitle').textContent=selectedMood[2];
 $('#moodMeta').textContent=spritePaused?'动画已暂停 / 最近邻放大':functional?'角色专用动作 / 实际光标见下方':'休闲表情 / 8 帧循环';
 $('#pauseSprite').textContent=spritePaused?'播放动画':'暂停动画';$('#pauseSprite').setAttribute('aria-pressed',String(spritePaused));
 $('#moodButtons').replaceChildren(...moods.map(m=>{const b=el('button','mood-button');b.setAttribute('aria-label',(functional?'动作：':'表情：')+m[1]);b.setAttribute('aria-pressed',String(m[0]===selectedMood[0]));b.append(picture('/previews/diana/'+(functional?'Character-'+m[0]:'pose-'+m[3])+'.png',m[1],'pixel-art',40),el('span','',m[1]));b.onclick=()=>{selectedMood=m;renderMood();};return b;}));
 $('#studioFunctional').setAttribute('aria-pressed',String(functional));$('#studioExpressions').setAttribute('aria-pressed',String(!functional));
}
function switchStudio(mode){studioMode=mode;moods=mode==='functional'?functionalMoods:expressionMoods;selectedMood=moods[0];const sizes=[144,192,240];$('#pixelZoom').replaceChildren(...sizes.map(size=>{const option=el('option','',size/48+'×');option.value=size;return option;}));$('#pixelZoom').value='192';$('#stageSprite').style.setProperty('--sprite-size','192px');renderMood();}
$('#studioFunctional').onclick=()=>switchStudio('functional');$('#studioExpressions').onclick=()=>switchStudio('expressions');
$('#pauseSprite').onclick=()=>{spritePaused=!spritePaused;renderMood();};
$('#pixelZoom').onchange=e=>$('#stageSprite').style.setProperty('--sprite-size',e.target.value+'px');
renderMood();
reducedMotion.addEventListener('change',()=>{spritePaused=reducedMotion.matches;renderMood();if(reducedMotion.matches)endTrial();render();});
try{state.favorites=new Set(JSON.parse(localStorage.getItem('freecur-favorites')||'[]').filter(x=>typeof x==='string'));}catch{}
try{document.documentElement.dataset.theme=localStorage.getItem('freecur-color')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}catch{}
function themeButtonLabel(){$('#themeToggle').setAttribute('aria-label',document.documentElement.dataset.theme==='dark'?'切换白天主题':'切换深色主题');}
themeButtonLabel();
$('#themeToggle').onclick=()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=value;themeButtonLabel();try{localStorage.setItem('freecur-color',value);}catch{}};
const osLabel={windows:'Windows',linux:'Linux',macos:'macOS'};
function el(tag,cls,text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
function picture(src,alt,cls,size){const im=el('img',cls);im.src=src+(src.startsWith('/previews/')?pixelRevision:'');im.alt=alt;im.width=size;im.height=size;im.loading='lazy';return im;}
function toast(message){const t=$('#toast');t.textContent=message;t.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.hidden=true,3500);}
function favorite(id){state.favorites.has(id)?state.favorites.delete(id):state.favorites.add(id);try{localStorage.setItem('freecur-favorites',JSON.stringify([...state.favorites]));}catch{}render();}
function downloadPackage(item,platform){return platform==='windows'?state.catalog.managers.windows_exe:item.packages[platform];}
function download(item){const a=el('a','download-link',osLabel[state.os]+(state.os==='windows'?' EXE':'')+' ↓');a.href=downloadPackage(item,state.os).url;a.download='';a.setAttribute('aria-label','下载'+item.name+'的'+osLabel[state.os]+(state.os==='windows'?' EXE安装器':'主题'));if(state.os==='windows')a.title='安装包包含全部主题，安装后在切换器中选择'+item.name;return a;}
function render(){
 if(!state.catalog)return;
 const activeIds=new Set(state.catalog.themes.map(x=>x.id));
 const versionThemes=state.catalog.themes.filter(x=>state.pixelMode===null||Boolean(x.pixel)===state.pixelMode);
 $('#allTab').setAttribute('aria-pressed',String(state.pixelMode===null));
 $('#pixelTab').setAttribute('aria-pressed',String(state.pixelMode===true));$('#legacyTab').setAttribute('aria-pressed',String(state.pixelMode===false));
 $('#styleDescription').textContent=state.pixelMode===null?'逐角色像素重绘 · 圆角主题色箭头 · 可调大小':state.pixelMode?'角色自己动，不只是加载圈。':'头像伴随型 · 不是像素动态';
 $('#grid').classList.toggle('pixel-grid',state.pixelMode===true);
 $('#favoriteCount').textContent=[...state.favorites].filter(id=>activeIds.has(id)).length;
 $('#favoriteFilter').setAttribute('aria-pressed',String(state.favoritesOnly));
 const groups=['全部',...new Set(versionThemes.map(x=>x.group))];
 $('#groups').replaceChildren(...groups.map(group=>{const b=el('button',state.group===group?'active':'',group);b.type='button';b.setAttribute('aria-pressed',String(group===state.group));const count=group==='全部'?versionThemes.length:versionThemes.filter(x=>x.group===group).length;b.append(el('span','',count));b.onclick=()=>{state.group=group;state.page=1;render();};return b;}));
 const list=versionThemes.filter(x=>(state.group==='全部'||x.group===state.group)&&(!state.favoritesOnly||state.favorites.has(x.id))&&(x.name+x.group+x.id+(x.subtitle||'')).toLowerCase().includes(state.query.toLowerCase()));
 const pages=Math.max(1,Math.ceil(list.length/state.size));state.page=Math.min(state.page,pages);
 $('#resultCount').textContent=list.length+' 个角色'+(state.query?' · “'+state.query+'”':'')+' · 第 '+state.page+' / '+pages+' 页';
 if(document.body.dataset.view==='library')history.replaceState(null,'','#library'+(state.page>1?'?page='+state.page:''));
 $('#empty').hidden=!!list.length;
 $('#grid').replaceChildren(...list.slice((state.page-1)*state.size,state.page*state.size).map(item=>{
  const card=el('article','theme-card'+(item.pixel?' pixel-card':''));card.style.setProperty('--character',item.color);
  const art=el('button','theme-art');art.setAttribute('aria-label','查看'+item.name+'主题');
  if(item.pixel)art.append(picture('/previews/'+item.id+'/Character-Hand'+(reducedMotion.matches?'.png':'.gif'),item.name+'伸手点选','pixel-character',192),el('span','pixel-badge',item.animation.task_keyframes?'功能精修版':'像素动态'));
  else art.append(picture(item.preview,item.name,'portrait',116),picture('/previews/'+item.id+'/Arrow.png',item.name+'光标','card-arrow',65));art.onclick=()=>detail(item);
  const heart=el('button','heart',state.favorites.has(item.id)?'♥':'♡');heart.setAttribute('aria-label','收藏'+item.name);heart.setAttribute('aria-pressed',String(state.favorites.has(item.id)));heart.onclick=()=>favorite(item.id);
  const info=el('div','theme-info'),row=el('div','name-row');row.append(el('h3','',item.name),el('small','',item.group));info.append(row);
  const swatch=el('p','theme-swatch',item.color.toUpperCase()+' · 角色主题色');swatch.style.setProperty('--character',item.color);info.append(swatch);
  if(item.pixel)info.append(el('p','pixel-card-note',item.animation.task_keyframes?'48 张功能关键帧 · 15 种状态':'8 种小表情 · 15 种状态'));
  const states=el('div','cursor-states');for(const role of ['Arrow','Hand','IBeam','Wait'])states.append(picture('/previews/'+item.id+'/'+role+(item.pixel&&!reducedMotion.matches?'.gif':'.png'),role,item.pixel?'pixel-art':'',item.pixel?64:33));info.append(states);
  const bottom=el('div','card-bottom'),tryIt=el('button','','预览与试用 ↗');tryIt.onclick=()=>detail(item);bottom.append(tryIt,download(item));info.append(bottom);card.append(art,heart,info);return card;
 }));
 const buttons=[];function pageButton(label,page,disabled=false){const b=el('button','',label);b.disabled=disabled;b.setAttribute('aria-label',typeof label==='number'?'第 '+label+' 页':label==='←'?'上一页':'下一页');if(page===state.page&&typeof label==='number')b.setAttribute('aria-current','page');b.onclick=()=>{location.hash='library'+(page>1?'?page='+page:'');};return b;}
 buttons.push(pageButton('←',state.page-1,state.page===1));for(let p=1;p<=pages;p++)buttons.push(pageButton(p,p));buttons.push(pageButton('→',state.page+1,state.page===pages));$('#pagination').replaceChildren(...buttons);
}
let trialTimer=null,trialRaf=null,trialCursor=null,trialPoint=null,trialFrame=0,trialRole='Arrow',trialRenderedRole='Arrow',trialForcedRole=null,reactUntil=0;
function endTrial(){const style=$('#trialStyle');if(style)style.remove();clearTimeout(trialTimer);cancelAnimationFrame(trialRaf);trialTimer=null;trialRaf=null;trialCursor?.remove();trialCursor=null;trialPoint=null;trialForcedRole=null;trialRenderedRole='Arrow';document.body.classList.remove('pixel-trial-active');state.trial=null;$('#trialBar').hidden=true;$('#trialMode').hidden=true;}
function paintTrial(){
 trialRaf=null;if(!trialCursor||document.hidden)return;
 const react=!trialForcedRole&&trialRole==='Hand'&&Date.now()<reactUntil,role=trialForcedRole||trialRole;
 if(role!==trialRenderedRole){trialRenderedRole=role;trialFrame=0;}
 const frame=react?4:trialFrame;
 const item=state.catalog.themes.find(x=>x.id===state.trial);
 const hotspots={Arrow:[3,3],Help:[3,3],AppStarting:[3,3],Wait:[16,17],Crosshair:[20,20],IBeam:[20,21],NWPen:[3,45],No:[20,20],SizeNS:[20,20],SizeWE:[20,20],SizeNWSE:[20,20],SizeNESW:[20,20],SizeAll:[20,20],UpArrow:[20,3],Hand:[15,4]};
 const hotspot=(item.pixel?item.animation.hotspots:hotspots)[role];
 const src='/previews/'+state.trial+'/'+role+(item.pixel?'-'+(reducedMotion.matches?0:frame)+'.png':!reducedMotion.matches&&['Wait','AppStarting'].includes(role)?'.gif':'.png')+pixelRevision;if(trialCursor.getAttribute('src')!==src)trialCursor.src=src;
 trialCursor.style.width=previewSize+'px';trialCursor.style.height=previewSize+'px';
 trialCursor.style.imageRendering=item.pixel?'pixelated':'auto';
 if(!trialPoint)return;
 trialCursor.style.transform=`translate3d(${trialPoint.x-hotspot[0]*previewSize/64}px,${trialPoint.y-hotspot[1]*previewSize/64}px,0)`;
 trialCursor.hidden=false;document.body.classList.add('pixel-trial-active');
}
function cycleTrial(){if(!trialCursor||document.hidden)return;trialFrame=(trialFrame+1)%8;paintTrial();const item=state.catalog.themes.find(x=>x.id===state.trial),role=trialForcedRole||trialRole;if(item.pixel)trialTimer=setTimeout(cycleTrial,item.animation.durations_ms?.[role]||item.animation.duration_ms);}
document.addEventListener('pointermove',e=>{if(!trialCursor||e.pointerType==='touch')return;trialPoint={x:e.clientX,y:e.clientY};trialRole=e.target.closest('input,textarea,[contenteditable=true]')?'IBeam':e.target.closest('button,a,select,label')?'Hand':'Arrow';if(!trialRaf)trialRaf=requestAnimationFrame(paintTrial);},{passive:true});
document.addEventListener('pointerdown',e=>{if(!trialCursor||e.pointerType==='touch'||reducedMotion.matches)return;reactUntil=Date.now()+360;paintTrial();},{passive:true});
document.addEventListener('pointerout',e=>{if(!e.relatedTarget&&trialCursor){trialCursor.hidden=true;document.body.classList.remove('pixel-trial-active');trialPoint=null;}},{passive:true});
document.addEventListener('visibilitychange',()=>{if(!trialCursor)return;if(document.hidden){clearTimeout(trialTimer);trialCursor.hidden=true;document.body.classList.remove('pixel-trial-active');trialPoint=null;}else cycleTrial();});
function trial(item,forcedRole=null){
 endTrial();state.trial=item.id;const style=el('style');style.id='trialStyle';
 {
  if(!matchMedia('(any-pointer: fine)').matches){state.trial=null;toast('触屏设备可查看表情与动态预览；跟随试用需要鼠标。');return;}
  style.textContent='body.pixel-trial-active,body.pixel-trial-active *{cursor:none!important}';document.head.append(style);
  trialCursor=picture('/previews/'+item.id+(item.pixel?'/Arrow-0.png':'/Arrow.png'),'','trial-pixel-cursor',previewSize);trialCursor.setAttribute('aria-hidden','true');trialCursor.loading='eager';trialCursor.hidden=true;
  trialCursor.onerror=endTrial;document.body.append(trialCursor);trialFrame=0;
  trialForcedRole=forcedRole;
  trialRole='Arrow';paintTrial();
  const modes=$('#trialMode');modes.replaceChildren(el('option','','自动识别'));
  modes.options[0].value='';
  for(const role of state.catalog.roles){const option=el('option','',role.name);option.value=role.id;modes.append(option);}
  modes.value=forcedRole||'';modes.hidden=false;
  if(item.pixel)trialTimer=setTimeout(cycleTrial,item.animation.durations_ms?.[forcedRole||'Arrow']||item.animation.duration_ms);
  $('#trialName').textContent='正在本站试用：'+item.name+' · '+previewSize+'px';$('#trialBar').hidden=false;if($('#detail').open)$('#detail').close();toast(forcedRole?'仅固定预览光标外观，不会改变系统或网页控件的实际功能。':'角色会跟随鼠标；可调整网页试用大小，Esc 随时退出。');return;
 }
}
function detail(item){
 const body=$('#detailBody');body.replaceChildren();const identity=el('div','detail-identity'),text=el('div');text.append(el('h2','',item.name),el('p','',item.group+' · '+item.style+' · 15 个 Windows / Linux 状态'));identity.append(picture(item.preview,item.name,'',100),text);body.append(identity);
 const cursorFor=(role,fallback)=>{const hot=item.pixel?item.animation.hotspots[role]:({Arrow:[3,3],Hand:[15,4],IBeam:[20,21]})[role];return `url('/previews/${item.id}/${role}.png${item.pixel?pixelRevision:''}') ${hot[0]} ${hot[1]},${fallback}`;};
 const play=el('div','preview-play');const input=el('input');input.placeholder='在这里试试文字输入';input.setAttribute('aria-label','文本选择试验');input.style.cursor=cursorFor('IBeam','text');const link=el('a','','移到这里试试链接');link.href='#';link.onclick=e=>e.preventDefault();link.style.cursor=cursorFor('Hand','pointer');play.style.cursor=cursorFor('Arrow','auto');play.append(input,link);body.append(play);
 let selectedRole='Arrow';const cells=el('div','state-grid'+(item.pixel?' pixel-state-grid':''));
 const roleStage=el('section','role-stage'),roleImage=picture('/previews/'+item.id+'/Arrow.gif','常规选择大预览','pixel-art',128),roleText=el('div'),roleTitle=el('h3'),roleAction=el('p','role-action'),roleMeaning=el('p','role-meaning'),roleExample=el('small');
 function showRole(role){
  selectedRole=role.id;
  if(item.pixel){const info=item.animation.behaviors[role.id];roleImage.src='/previews/'+item.id+'/'+role.id+(reducedMotion.matches?'.png':'.gif')+pixelRevision;roleImage.alt=role.name+'大预览';roleTitle.textContent=role.name;roleAction.textContent=info.action;roleMeaning.textContent=info.meaning;roleExample.textContent='典型场景：'+info.example;
   play.style.cursor=`url('/previews/${item.id}/${role.id}.png${pixelRevision}') ${item.animation.hotspots[role.id].join(' ')},auto`;
   for(const button of cells.querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.role===role.id));}
 }
 if(item.pixel){roleStage.setAttribute('aria-label','按功能查看动作');roleText.append(roleTitle,roleAction,roleMeaning,roleExample);roleStage.append(roleImage,roleText);body.append(roleStage,el('p','role-hint','点击下面任意状态，查看它的动作和用途。文字、精确选择保持稳定，缩放动作与方向一致。'));}
 for(const role of state.catalog.roles){const c=el(item.pixel?'button':'div','state-cell');const extension=(item.pixel||role.id==='Wait')&&!reducedMotion.matches?'.gif':'.png';c.append(picture('/previews/'+item.id+'/'+role.id+extension,role.name,item.pixel?'pixel-art':'',item.pixel?64:42),el('span','',role.name));
  if(item.pixel){c.type='button';c.dataset.role=role.id;c.setAttribute('aria-label','查看状态：'+role.name);c.setAttribute('aria-pressed',String(role.id==='Arrow'));c.onclick=()=>showRole(role);}
  cells.append(c);}
 body.append(cells);if(item.pixel)showRole(state.catalog.roles[0]);
 const actions=el('div','detail-actions');for(const platform of ['windows','linux','macos']){const a=el('a','button '+(platform===state.os?'primary':'light'),osLabel[platform]+(platform==='windows'?' EXE':'')+' ↓');a.href=downloadPackage(item,platform).url;a.download='';actions.append(a);}const tryIt=el('button','button light','自动试用');tryIt.onclick=()=>trial(item);actions.append(tryIt);if(item.pixel){const fixed=el('button','button light','固定预览选中状态');fixed.onclick=()=>trial(item,selectedRole);actions.append(fixed);}body.append(actions,el('p','role-hint','Windows EXE 包含全部离线主题，安装后在切换器中选择「'+item.name+'」。仅当前用户安装，未签名，尚未进行 Windows 实机验收。'));
 const note=el('div','detail-source');note.append(el('p','',item.pixel?(item.animation.task_keyframes?'嘉然精修版：AI 辅助重绘12种功能专用动作、48张关键帧，另有8种休闲表情。':'基础像素版：按该角色形象单独生成8张姿势底稿，不是旧头像像素化、也不是嘉然换色。编排为15种状态，尚未做到嘉然48张功能专用关键帧的细节。')+' 系统按光标状态播放，非全局点击监听。Windows / macOS 仍待真机验收；Mac 需 Mousecape。':'这是保留的旧版头像主题，只有加载环转动，不是像素动态。Windows / macOS 仍待真机验收。'));
 const source=el('a','','查看角色与图片出处 ↗');source.href=item.source;source.target='_blank';source.rel='noopener noreferrer';note.append(source,el('p','',item.rights));const hash=el('p','','当前 '+osLabel[state.os]+' 包 SHA-256：'+downloadPackage(item,state.os).sha256);hash.style.overflowWrap='anywhere';note.append(hash);body.append(note);$('#detail').showModal();
}
$('#closeDetail').onclick=()=>$('#detail').close();$('#detail').addEventListener('click',e=>{if(e.target===$('#detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#endTrial').onclick=endTrial;
$('#trialMode').onchange=e=>{trialForcedRole=e.target.value||null;trialFrame=0;reactUntil=0;const item=state.catalog.themes.find(x=>x.id===state.trial);$('#trialName').textContent='正在本站试用：'+item.name+' · '+previewSize+'px';paintTrial();};
$('#previewSize').onchange=e=>{previewSize=Number(e.target.value);paintTrial();toast('网页试用大小：'+previewSize+'px；系统大小请在切换器中调整。');};
document.addEventListener('keydown',e=>{if(e.key==='Escape')endTrial();if(e.key==='/'&&!e.ctrlKey&&!e.metaKey&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();if(document.body.dataset.view!=='library')location.hash='library';requestAnimationFrame(()=>$('#search').focus());}});
$('#search').addEventListener('input',e=>{state.query=e.target.value;state.page=1;render();});
$('#favoriteFilter').onclick=()=>{state.favoritesOnly=!state.favoritesOnly;state.page=1;render();};
$('#os').onchange=e=>{state.os=e.target.value;render();};
for(const [id,pixelMode] of [['allTab',null],['pixelTab',true],['legacyTab',false]])$('#'+id).onclick=()=>{state.pixelMode=pixelMode;state.group='全部';state.page=1;render();};
$('#heroTry').onclick=()=>{const sample=state.catalog?.themes.find(x=>x.id===homeCharacterId)||state.catalog?.themes.find(x=>x.pixel);if(sample)trial(sample);else toast('正在载入像素主题，请稍后重试。');};
const platform=navigator.platform.toLowerCase();state.os=platform.includes('linux')?'linux':platform.includes('mac')?'macos':'windows';$('#os').value=state.os;
$('#copyLinuxCommand').onclick=async()=>{try{await navigator.clipboard.writeText($('#linuxCommand').textContent);toast('已复制。在桌面终端粘贴运行，不要加 sudo。');}catch{const selection=window.getSelection(),range=document.createRange();range.selectNodeContents($('#linuxCommand'));selection.removeAllRanges();selection.addRange(range);toast('命令已选中，请手动复制。');}};

// Hash routes keep the existing public links working without server rewrites.
const pageNames={home:'首页',library:'角色库',install:'下载使用'};
let homeCharacterId='diana',tiltFrame=null,tiltPoint=null;
function route(){
 const raw=location.hash.slice(1),[candidate,query='']=raw.split('?'),view=Object.prototype.hasOwnProperty.call(pageNames,candidate)?candidate:'home';
 const requested=Number(new URLSearchParams(query).get('page')||1);
 if(view==='library')state.page=Number.isInteger(requested)&&requested>0&&requested<=1000?requested:1;
 const old=document.body.dataset.view;
 if(old!==view){if(state.trial)endTrial();if($('#detail').open)$('#detail').close();}
 document.body.dataset.view=view;
 for(const id of Object.keys(pageNames))$('#'+id).hidden=id!==view;
 for(const link of document.querySelectorAll('[data-view-link]')){if(link.dataset.viewLink===view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');}
 $('#viewCounter').textContent='0'+(Object.keys(pageNames).indexOf(view)+1)+' / 03';
 document.title='Free Cur · '+(view==='home'?'喜欢，在指尖发生。':pageNames[view]);
 if(view==='library')render();
 if(view!=='home')resetTilt();
 window.scrollTo(0,0);
}
function availableCharacters(){return state.catalog?.themes||[];}
function activeHomeIndex(){return Math.max(0,availableCharacters().findIndex(item=>item.id===homeCharacterId));}
function setHomeCharacter(id){if(!availableCharacters().some(item=>item.id===id))return;homeCharacterId=id;renderHome();}
function stepHome(offset){const list=availableCharacters();if(!list.length)return;setHomeCharacter(list[(activeHomeIndex()+offset+list.length)%list.length].id);}
function renderHome(){
 const list=availableCharacters();if(!list.length){$('#homeCharacterName').textContent='目录暂不可用';$('#homeCharacterGroup').textContent='请稍后刷新';return;}
 const index=activeHomeIndex(),item=list[index],previous=list[(index-1+list.length)%list.length],next=list[(index+1)%list.length];
 homeCharacterId=item.id;
 $('#collectible').style.setProperty('--home-colour',item.color);
 $('#homeCharacterImage').src='/previews/'+item.id+'/Character-Hand'+(reducedMotion.matches?'.png':'.gif')+pixelRevision;
 $('#homeCharacterImage').alt=item.name+'像素角色';$('#homeCharacterName').textContent=item.name;$('#homeCharacterGroup').textContent=item.group;
 $('#homeShowpiece').setAttribute('aria-label','查看'+item.name+'主题');
 const tryArrow=el('span','','↖');tryArrow.setAttribute('aria-hidden','true');$('#heroTry').replaceChildren('先试试'+(item.id==='taffy'?'塔菲':item.name)+' ',tryArrow);
 $('#homeNumber').textContent=String(index+1).padStart(2,'0')+' / '+String(list.length).padStart(2,'0');
 for(const [prefix,character] of [['Previous',previous],['Next',next]]){
  $('#home'+prefix+'Image').src='/previews/'+character.id+'/Character-Hand.png'+pixelRevision;
  $('#home'+prefix+'Name').textContent=character.name;
  $('#home'+prefix+'Card').setAttribute('aria-label','切换到'+character.name);
 }
 const indices=[...new Set([-2,-1,0,1,2].map(offset=>(index+offset+list.length)%list.length))];
 $('#homeCharacters').replaceChildren(...indices.map(at=>{const character=list[at],button=el('button');button.type='button';button.setAttribute('aria-label','展示'+character.name);button.setAttribute('aria-pressed',String(at===index));button.title=character.name;button.append(picture('/previews/'+character.id+'/pose-0.png',character.name,'',24));button.onclick=()=>setHomeCharacter(character.id);return button;}));
}
function resetTilt(){if(tiltFrame)cancelAnimationFrame(tiltFrame);tiltFrame=null;tiltPoint=null;$('#sceneTurn').style.setProperty('--rx','0deg');$('#sceneTurn').style.setProperty('--ry','0deg');}
$('#collectible').addEventListener('pointermove',event=>{
 if(reducedMotion.matches||event.pointerType!=='mouse'||document.body.dataset.view!=='home')return;
 const rect=event.currentTarget.getBoundingClientRect();tiltPoint={x:Math.max(-1,Math.min(1,(event.clientX-rect.left)/rect.width*2-1)),y:Math.max(-1,Math.min(1,(event.clientY-rect.top)/rect.height*2-1))};
 if(!tiltFrame)tiltFrame=requestAnimationFrame(()=>{tiltFrame=null;if(!tiltPoint)return;$('#sceneTurn').style.setProperty('--rx',(-tiltPoint.y*3).toFixed(2)+'deg');$('#sceneTurn').style.setProperty('--ry',(tiltPoint.x*5).toFixed(2)+'deg');});
},{passive:true});
$('#collectible').addEventListener('pointerleave',resetTilt);
$('#homePrevious').onclick=()=>stepHome(-1);$('#homePreviousCard').onclick=()=>stepHome(-1);
$('#homeNext').onclick=()=>stepHome(1);$('#homeNextCard').onclick=()=>stepHome(1);
$('#homeShowpiece').onclick=()=>{const item=availableCharacters().find(item=>item.id===homeCharacterId);if(item)detail(item);};
window.addEventListener('hashchange',route);
reducedMotion.addEventListener('change',()=>{resetTilt();renderHome();});
route();
fetch('/catalog.json').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(async c=>{
 if(!Array.isArray(c.themes)||!c.themes.every(x=>/^[a-z0-9-]+$/.test(x.id)))throw Error('Invalid catalogue');state.catalog=c;
 try{const response=await fetch('/api/windows/catalog.xml',{cache:'no-store'});if(response.ok){const xml=new DOMParser().parseFromString(await response.text(),'application/xml');if(xml.documentElement.tagName==='free-cur'&&!xml.querySelector('parsererror')){const ids=new Set([...xml.querySelectorAll('free-cur>theme')].map(x=>x.getAttribute('id')));c.themes=c.themes.filter(x=>ids.has(x.id));}}}catch{}
 const count=c.themes.filter(x=>x.pixel).length;$('#totalCount').textContent=count;$('#pixelCount').textContent=count;$('#legacyCount').textContent=c.themes.length-count;
 $('#basicCount').textContent=c.themes.filter(x=>x.pixel&&!x.animation.task_keyframes).length;
 $('#legacyTab').hidden=count===c.themes.length;
 $('#allTab').textContent='全部角色 '+c.themes.length;
 for(const a of document.querySelectorAll('[data-manager]')){const p=c.managers[a.dataset.manager];a.href=p.url;a.download='';a.title='SHA-256: '+p.sha256;}
 render();renderHome();
}).catch(()=>{$('#resultCount').textContent='主题库暂时未能加载，请稍后刷新。';$('#empty').hidden=false;$('#empty').textContent='请检查网络后重新打开页面。主题文件不会因网页离线而自动安装或修改。';$('#homeCharacterName').textContent='目录暂不可用';$('#homeCharacterGroup').textContent='请稍后刷新';});
