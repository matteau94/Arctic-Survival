// Shared UI helpers. SVG nodes are created once; only changed values are painted.
const paths={cold:'M10 3v10a4 4 0 1 0 4 0V3a2 2 0 0 0-4 0ZM12 8v9',tent:'M2 20 12 4l10 16ZM8 20l4-9 4 9',warm:'M2 20 12 4l10 16ZM8 19v-5h8v5M8 17h8',den:'M3 20v-7a9 9 0 0 1 18 0v7h-6v-7a3 3 0 0 0-6 0v7Z',eye:'M2 12q10-14 20 0-10 14-20 0ZM15 12a3 3 0 1 0-6 0 3 3 0 0 0 6 0',pause:'M8 5v14M16 5v14',pack:'M8 6V4h8v2M6 7h12l2 14H4ZM8 13h8v5H8Z',move:'M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4',run:'m4 8 6 4-6 4m10-8 6 4-6 4',crouch:'M14 4h1M7 10h7l3 5M14 10l-4 6h7v5M10 16H5',mouse:'M7 3h10a3 3 0 0 1 3 3v10a8 8 0 0 1-16 0V6a3 3 0 0 1 3-3ZM12 3v7',map:'m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16',enter:'M14 3h7v18h-7M2 12h14m-5-5 5 5-5 5'};
const hints=new WeakMap();
export function hudHint(node,icon,caption,detail=caption){
 let parts=hints.get(node);
 if(!parts || parts.text.parentNode!==node){
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.classList.add('hud-icon');
  const path=document.createElementNS(svg.namespaceURI,'path');svg.append(path);
  const text=document.createElement('span'),tip=document.createElement('span');tip.className='hud-tooltip';
  node.replaceChildren(svg,text,tip);parts={path,text,tip};hints.set(node,parts);node.classList.add('hud-tip');node.tabIndex=0;
 }
 if(parts.icon!==icon){parts.path.setAttribute('d',paths[icon]||paths.cold);parts.icon=icon;}
 if(parts.caption!==caption){parts.text.textContent=caption;parts.caption=caption;}
 if(parts.detail!==detail){parts.tip.textContent=detail;node.setAttribute('aria-label',detail);parts.detail=detail;}
}
export function renderControls(node,spectator=false){
 if(node.dataset.mode===String(spectator))return;node.dataset.mode=String(spectator);node.replaceChildren();
 for(const [icon,key,detail] of [['move','WASD','WASD or arrows: move'],['run','Shift',spectator?'Hold Shift: fly faster':'Hold Shift: run'],[spectator?'move':'crouch',spectator?'Space/C':'C',spectator?'Space rises; C descends':'Hold C: crouch'],['mouse','','Mouse: look and turn'],[spectator?'map':'pack',spectator?'T':'E',spectator?'T: teleport destinations':'E: inventory'],['pause','Esc','Esc: pause and release cursor']]){
  const hint=document.createElement('span');hudHint(hint,icon,key,detail);node.append(hint);
 }
}

// One exposure accumulator; no scene objects or background timers.
export function createCold({ onDeath }) {
  const limit = 360;
  let exposure = 0, dead = false, previousActive = false;
  let lastPaint = -Infinity, lastState = '', lastAnnouncement = '';
  const hud = document.createElement('div');hud.id='cold-status';hud.className='cold-widget';
  const reading=document.createElement('div'),condition=document.createElement('div');
  const unit=document.createElement('small');unit.textContent='outdoor seconds left';
  const gauge=document.createElement('meter');gauge.min=0;gauge.max=limit;gauge.low=120;gauge.high=240;gauge.optimum=0;gauge.setAttribute('aria-label','Cold exposure in active game seconds');
  const announcement=document.createElement('span');announcement.className='hud-sr';announcement.setAttribute('role','status');announcement.setAttribute('aria-live','polite');
  hud.append(reading,unit,gauge,condition,announcement);document.body.append(hud);
  const end = document.createElement('dialog');
  end.setAttribute('aria-label', 'Expedition ended from cold');
  const reason = document.createElement('p');
  reason.textContent = 'Expedition ended: cold exposure reached 360 active game seconds. Enter a tent or fox den before exposure reaches the limit.';
  const restart = document.createElement('button');
  restart.textContent = 'Restart fresh expedition';
  restart.addEventListener('click', () => { if (dead) window.location.reload(); });
  end.addEventListener('cancel', event => event.preventDefault());
  end.append(reason, restart);document.body.append(end);
  function paint(now, active, shelter, suspended) {
    const stateKey = `${active}:${shelter}:${active ? '' : suspended}`;
    if (stateKey === lastState && now - lastPaint < 1000) return;
    lastState = stateKey;lastPaint = now;
    const warning = exposure >= 240 ? 'URGENT' : exposure >= 120 ? 'WARNING' : 'COLD';
    const state = !active ? `${suspended}: exposure frozen.`
      : shelter === 'tent' ? 'Bare tent: protected, not warming. Exposure holds steady. E → Sleeping bag → Place inside this tent to restore warmth.'
      : shelter ? `${shelter === 'equipped-tent' ? 'Tent with indoor sleeping bag: recovering 3' : 'Fox den: recovering 1'} exposure seconds per active game second${exposure === 0 ? ' · fully recovered' : ''}.`
      : 'Outdoors: +1 exposure second per active game second.';
    const remaining = Math.ceil((limit - exposure) * 10) / 10;
    const detail=`${warning}. Exposure ${exposure.toFixed(1)} / 360 game seconds. Approximately ${remaining.toFixed(1)} active outdoor game seconds until death. ${state} Warning at 120; urgent at 240; death at 360 seconds. Setup, positioning and entry take time: remain exposed until inside.`;
    hud.dataset.severity=warning.toLowerCase();
    const needsShelter=active&&!shelter;
    const readingState=!active?'Frozen':shelter==='tent'?'Protected':shelter?'Warming':warning==='URGENT'?'Shelter now':warning==='WARNING'?'Warning':'Cold';
    hudHint(reading,'cold',`~${remaining.toFixed(1)}s · ${readingState}`,detail);
    gauge.value=exposure;gauge.setAttribute('aria-valuetext',`${exposure.toFixed(1)} of 360 exposure seconds`);
    const icon=!active?(/spectat/i.test(suspended)?'eye':'pause'):shelter==='equipped-tent'?'warm':shelter==='tent'?'tent':shelter==='den'?'den':'cold';
    const caption=!active?`${suspended} · frozen`:shelter==='equipped-tent'?'Equipped · −3/s':shelter==='tent'?'Bare tent · 0/s':shelter==='den'?'Den · −1/s':'Outdoors · +1/s';
    hudHint(condition,icon,caption,state);
    const stage=`${warning}:${active}:${shelter}:${active?'':suspended}`;
    if(stage!==lastAnnouncement){announcement.textContent=`${warning==='URGENT'?(needsShelter?'Shelter now.':'Critical exposure.'):warning+'.'} ${state}`;lastAnnouncement=stage;}
  }
  return {
    dead: () => dead,
    // Input transitions discard inactive wall time, including tab suspension.
    resetClock() { previousActive = false; },
    update(now, dt, active, shelter, suspended = 'Paused') {
      if (dead) return;
      // Match movement's bounded game time; never charge a resume frame.
      const elapsed = !previousActive || !active ? 0 : Math.max(0, Math.min(dt, .05));
      previousActive = active;
      exposure = Math.max(0, Math.min(limit, exposure + elapsed * (shelter === 'equipped-tent' ? -3 : shelter === 'tent' ? 0 : shelter === 'den' ? -1 : 1)));
      if (exposure >= limit) {
        dead = true;
        hud.textContent = 'Expedition ended from cold · Exposure 360 / 360 sec · 0 seconds remaining.';
        onDeath(); // Explicit, one-shot terminal event; bypass HUD throttling.
        end.showModal();restart.focus();return;
      }
      paint(now, active, shelter, suspended);
    },
  };
}
