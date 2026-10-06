import { hudHint } from './cold.js';

const FEEDS={fox:3,penguin:2},LIMIT=3,RANGE=3,COOLDOWN=1.2;
const ALERT={fox:35,penguin:22},NEAR=9.144,FOV_COS=.5,APPROACH_STOP=2,APPROACH_RESUME=2.3;

function approachPhase(id){
  let seed=2166136261;
  for(const character of String(id))seed=Math.imul(seed^character.charCodeAt(0),16777619);
  return (seed>>>0)/4294967296;
}

/** Expedition memory only. Identity belongs to stream records, never clone templates. */
export function createAnimalTaming({inventory,getPlayer,available,blocked,canSee,isCrouching=()=>false,sensing=available,sameSpace=()=>true,worldPosition=a=>a.root.position,pet=()=>false,isPetting=()=>false}){
  const records=new Map(),live=new Map();
  const sight=new Map();
  let time=0,sightTime=0,reserved=0,nextPrompt=0,sightCursor=0,shown=null;
  let frameBudget=0,interactionBudget=4;
  const TTL=.4,MAX_CANDIDATES=8;
  const prompt=document.createElement('div');
  prompt.className='context-hint';prompt.hidden=true;document.body.append(prompt);
  const count=()=>reserved;
  const food=()=>inventory.heldId()==='food';
  let wasHolding=food();
  function invalidate(){sight.clear();shown=null;nextPrompt=0;prompt.hidden=true;}
  inventory.subscribe(()=>{const holding=food();if(holding!==wasHolding){wasHolding=holding;invalidate();}});
  function inView(a){
    if(!sameSpace(a))return false;
    const p=getPlayer().root.position,q=a.root.position;
    if(!ALERT[a.type]||p.distanceToSquared(q)>=ALERT[a.type]**2)return false;
    if(p.distanceToSquared(q)<=NEAR**2)return true;
    const dx=p.x-q.x,dz=p.z-q.z,distance=Math.hypot(dx,dz);
    return distance>0&&(Math.sin(a.root.rotation.y)*dx+Math.cos(a.root.rotation.y)*dz)/distance>=FOV_COS;
  }
  function visible(a){
    // Reevaluate facing even while the geometric LOS result is cached.
    return live.get(a.id)===a&&inView(a)&&cached(a)?.visible===true;
  }
  function tempting(a){
    const r=records.get(a.id);
    return available()&&isCrouching()&&food()&&!r?.tamed&&(r?.feeds>0||count()<LIMIT)&&visible(a);
  }
  function candidates(){
    const p=getPlayer().root.position;
    const holding=food(),slotsFull=holding&&count()>=LIMIT;
    const result=[];
    for(const [id,a] of live){
      if(!sameSpace(a))continue;
      const r=records.get(id);
      // Held food targets wild animals only; stowed food targets companions.
      if(!r||(holding?r.tamed:!r.tamed))continue;
      const rank=holding&&(time<r.nextFeed||(!r.feeds&&slotsFull))?1:0;
      const d=p.distanceTo(a.root.position);
      if(d>=RANGE||(!r.tamed&&!inView(a)))continue;
      result.push({a,r,d,rank});
      result.sort((a,b)=>a.rank-b.rank||a.d-b.d);
      if(result.length>MAX_CANDIDATES)result.pop();
    }
    return result;
  }
  function cached(a){
    const entry=sight.get(a.id),p=getPlayer().root.position;
    if(entry&&entry.actor===a&&sightTime-entry.time<TTL&&
      p.distanceToSquared(entry.player)<=.75*.75&&
      a.root.position.distanceToSquared(entry.position)<=.75*.75)return entry;
    sight.delete(a.id);return null;
  }
  function check(a){
    const p=getPlayer().root.position;
    const entry={actor:a,time:sightTime,player:p.clone(),position:a.root.position.clone(),visible:canSee(p,a.root.position)};
    sight.set(a.id,entry);return entry.visible;
  }
  function target(fresh=false,companionCommand=false){
    if(fresh&&interactionBudget<=0)return null;
    if(!available()||(!companionCommand&&blocked())||isPetting())return null;
    let allowance=fresh?Math.min(4,interactionBudget):Math.min(2,frameBudget);
    for(const {a,r} of candidates()){
      const entry=fresh?null:cached(a);
      if(entry){if(entry.visible)return r;continue;}
      if(allowance<=0)return null; // Unknown visibility never authorizes an action.
      allowance--;if(fresh)interactionBudget--;else frameBudget--;
      if(check(a))return r;
    }
    return null;
  }
  function label(r){
    if(r.tamed)return `G · ${r.mode==='follow'?'Stay':'Follow'}${blocked()?'':inventory.heldId()?' · Put away held item to pet':' · P · Pet up close'} · ${r.type} (${count()}/${LIMIT})`;
    if(!r.feeds&&count()>=LIMIT)return `Companion slots reserved ${LIMIT}/${LIMIT}`;
    if(time<r.nextFeed)return `${r.type} · Eating (${r.feeds}/${FEEDS[r.type]})`;
    return `F · Feed ${r.type} (${r.feeds}/${FEEDS[r.type]}) · Costs 1 Trail food`;
  }
  return {
    invalidate,
    admit(a,data){
      if(!FEEDS[a.type])return;
      sight.delete(a.id);
      if(shown?.id===a.id){shown=null;prompt.hidden=true;}
      if(!records.has(a.id))records.set(a.id,{id:a.id,type:a.type,feeds:0,nextFeed:0,tamed:false,mode:'follow',phase:approachPhase(a.id),approachStart:null,data:{...data}});
      live.set(a.id,a);
    },
    detach(a){
      if(live.get(a.id)!==a)return;
      const r=records.get(a.id);
      if(r){r.data={...r.data,position:worldPosition(a).toArray(),rotation:a.companionRoom?r.data.rotation:a.root.rotation.y};}
      if(!r?.feeds)records.delete(a.id);
      live.delete(a.id);
      sight.delete(a.id);
      if(r){r.approachStart=null;r.waiting=false;}
      if(shown?.id===a.id){shown=null;prompt.hidden=true;}
    },
    retain(ids){for(const [id,r] of records)if(!r.feeds&&!ids.has(id)&&!live.has(id))records.delete(id);},
    liveTamed(){return [...live.values()].flatMap(a=>{const r=records.get(a.id);return r?.tamed?[{a,r}]:[];});},
    pet(){
      if(inventory.heldId())return false;
      const r=target(true),a=r&&live.get(r.id);
      return !!(r?.tamed&&a&&pet(a));
    },
    companions(){
      return [...records.values()].filter(r=>r.feeds>0).map(r=>{
        const a=live.get(r.id);
        return {...r.data,...(a?{position:worldPosition(a).toArray(),rotation:a.companionRoom?r.data.rotation:a.root.rotation.y}:{})};
      });
    },
    intent(a,threat){
      const r=live.get(a.id)===a?records.get(a.id):null;
      if(!r)return null;
      if(a.petting)return {stop:true,target:null,state:'Being petted'};
      if(!r.tamed){
        if(!threat||!isCrouching()||!tempting(a)){r.approachStart=null;r.waiting=false;return null;}
        if(r.approachStart===null)r.approachStart=time;
        const distance=a.root.position.distanceTo(threat),height=a.root.position.y-threat.y;
        const period=3.2+r.phase*.8,walking=(time-r.approachStart)%period<2.1+r.phase*.4;
        r.waiting=distance<=APPROACH_STOP+.001||(r.waiting&&distance<APPROACH_RESUME);
        const close=r.waiting;
        return {cautious:true,stop:close||!walking,target:threat,stopDistance:Math.sqrt(Math.max(0,APPROACH_STOP**2-height**2)),
          speedScale:a.type==='fox'?.55:.65,state:close?'Waiting for food':walking?'Cautiously approaching':'Watching food'};
      }
      const follow=available()&&threat&&r.mode==='follow';
      return {stop:!follow||a.root.position.distanceTo(threat)<=2.2,target:threat,state:follow?'Following':'Staying'};
    },
    tempting,
    detects(a){return sensing()&&visible(a);},
    toggleFollow(){
      if(food())return false;
      const r=target(true,true);if(!r?.tamed)return false;
      r.mode=r.mode==='follow'?'stay':'follow';
      return true;
    },
    interact(){
      if(!food())return false;
      const r=target(true);if(!r)return false;
      if(r.tamed)return false;
      if((!r.feeds&&count()>=LIMIT)||time<r.nextFeed)return true;
      // Synchronous inventory commit is the sole consumption point; it also stows the last ration.
      const result=inventory.remove('food',1);
      if(!result.ok)return true;
      if(!r.feeds)reserved++;
      r.feeds++;r.nextFeed=time+COOLDOWN;
      if(r.feeds===FEEDS[r.type]){r.tamed=true;r.mode='follow';}
      return true;
    },
    update(dt){
      frameBudget=4;interactionBudget=4;
      if(!sensing()){invalidate();return;}
      const elapsed=Math.min(Math.max(dt,0),.05);
      sightTime+=elapsed;
      // Feeding/cautious cadence pauses whenever taming is unavailable;
      // wildlife LOS can still expire while sensing remains active (e.g. camping).
      if(available())time+=elapsed;
      if(time>=nextPrompt){nextPrompt=time+.1;shown=target(false,!food());}
      const a=shown&&live.get(shown.id);
      if(!available()||!a||!sameSpace(a)||!cached(a)?.visible||(!shown.tamed&&!inView(a))||a.root.position.distanceTo(getPlayer().root.position)>=RANGE||(!shown.tamed&&blocked())||isPetting())shown=null;
      prompt.hidden=!shown;
      if(shown)hudHint(prompt,'pack',label(shown),label(shown));
      // Rotate across all live animals (stream cap 120), skipping fresh LOS.
      // Prompt candidates remain nearest-eight and share the four-call budget.
      const animals=[...live.values()];
      for(let scanned=0;frameBudget>0&&scanned<animals.length;scanned++){
        sightCursor%=animals.length;
        const animal=animals[sightCursor++];
        if(records.get(animal.id)?.tamed||!inView(animal)||cached(animal))continue;
        frameBudget--;check(animal);
      }
    },
  };
}
