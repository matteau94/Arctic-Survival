// In-game commands: strict tokens, bounded text, and no executable input.
export function createSurvivalCommands({menu,available,pause,onClose,execute}){
  let enabled=false,opened=false;
  const setting=document.createElement('label');
  setting.style.cssText='display:block;margin:16px 0;line-height:1.6';
  const toggle=document.createElement('input');toggle.type='checkbox';toggle.checked=false;
  setting.append(toggle,' Enable survival commands · / opens console');menu.append(setting);
  const panel=document.createElement('section');panel.hidden=true;
  panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-label','Survival commands');
  panel.style.cssText='position:fixed;inset:15% auto auto 50%;transform:translateX(-50%);width:min(640px,94vw);max-height:75vh;overflow:auto;padding:20px;background:#0d202b;color:#eef5f5;border:1px solid #9cbdc6;border-radius:8px;z-index:10010';
  const title=document.createElement('h2');title.textContent='Survival commands · paused';
  const log=document.createElement('div');log.setAttribute('role','log');log.setAttribute('aria-live','polite');
  log.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;max-height:38vh;overflow:auto;margin:12px 0';
  const form=document.createElement('form');
  const input=document.createElement('input');input.type='text';input.maxLength=160;input.autocomplete='off';input.spellcheck=false;
  input.setAttribute('aria-label','Command');input.placeholder='/help';input.style.cssText='width:100%;padding:12px;font:16px monospace';
  const submit=document.createElement('button');submit.type='submit';submit.textContent='Run command';
  const closeButton=document.createElement('button');closeButton.type='button';closeButton.textContent='Close · Esc (return to pause menu)';
  form.append(input,submit);panel.append(title,log,form,closeButton);document.body.append(panel);
  function say(message){const line=document.createElement('div');line.textContent=message;log.append(line);while(log.children.length>16)log.firstChild.remove();log.scrollTop=log.scrollHeight;}
  function close(){if(!opened)return;opened=false;panel.hidden=true;input.blur();onClose();}
  toggle.addEventListener('change',()=>{enabled=toggle.checked;if(!enabled)close();});
  closeButton.onclick=close;
  form.onsubmit=event=>{
    event.preventDefault();
    if(!enabled||!opened||!available())return;
    const text=input.value.trim();input.value='';
    if(!text)return;
    say(`> ${text}`);
    const parts=text.split(/\s+/),name=parts.shift().toLowerCase();
    if(name==='/help'&&parts.length===0){
      say('/help\n/summon fox|penguin|bear — one nearby animal; maximum 8 pending or live summons. Fish and orca are unsupported.\n/tp x z — auto-ground at dry, clear world coordinates; no y argument.\nUse finite decimal metres (negative values allowed). Commands require outdoor survival, no placement or shelter transition. Summons disappear beyond 1100 m. Esc returns to pause; Resume captures the mouse.');
    }else if(name==='/summon'&&parts.length===1){
      const type=parts[0].toLowerCase();
      say(['fox','penguin','bear'].includes(type)?execute('summon',type):'Unsupported animal. Syntax: /summon fox|penguin|bear');
    }else if(name==='/tp'&&parts.length===2){
      const decimal=/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
      say(parts.every(p=>decimal.test(p)&&Number.isFinite(Number(p)))?execute('tp',parts.map(Number)):'Coordinates must be finite decimal numbers. Syntax: /tp x z');
    }else say('Unknown command or incorrect arguments. Type /help for exact syntax.');
    input.focus();
  };
  window.addEventListener('keydown',event=>{
    if(opened){
      event.stopImmediatePropagation();
      if(event.code==='Escape'){event.preventDefault();close();}
      if(event.code==='Tab'){event.preventDefault();const fields=[input,submit,closeButton],i=fields.indexOf(document.activeElement);fields[(i+(event.shiftKey?2:1))%3].focus();}
      return;
    }
    if(event.key!=='/'||event.repeat||event.ctrlKey||event.altKey||event.metaKey||!enabled||!available())return;
    if(event.target.closest?.('input,textarea,select,[contenteditable="true"]'))return;
    event.preventDefault();event.stopImmediatePropagation();opened=true;panel.hidden=false;
    pause();say('Expedition paused. Type /help for commands.');input.value='/';input.focus();
  },true);
  window.addEventListener('keyup',event=>{if(opened)event.stopImmediatePropagation();},true);
  return {isOpen:()=>opened,isEnabled:()=>enabled,focus:()=>{if(opened&&document.hasFocus())input.focus();},setSurvival:value=>{setting.hidden=!value;if(!value)close();}};
}
