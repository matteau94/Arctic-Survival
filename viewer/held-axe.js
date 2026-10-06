import * as THREE from 'three';
import { animate, choppingLineOfSight } from './gameplay.js';

// Human_Attack: anticipation 0–.40, strike .40–.54, recovery to 1.30.
const IMPACT = .54;
const normalized=name=>String(name??'').replace(/[._]/g,'').toLowerCase();

/** One runtime prop; the existing player mixer exclusively owns the swing pose. */
export function createHeldAxe({inventory,getPlayer,getTrees,camera,canEquip,allowed}){
  let prop=null,session=null,cooldown=0,message='',messageTime=0,promptTime=0;
  const from=new THREE.Vector3(),to=new THREE.Vector3();
  const view=new THREE.Frustum(),viewProjection=new THREE.Matrix4();
  const prompt=document.createElement('div');
  prompt.className='context-hint';prompt.style.bottom='164px';prompt.hidden=true;
  prompt.setAttribute('role','status');prompt.setAttribute('aria-live','polite');
  document.body.append(prompt);
  const holding=()=>inventory.heldId()==='handaxe';
  function say(text){message=text;messageTime=3;paint(text);}
  function paint(text){if(prompt.textContent!==text)prompt.textContent=text;}
  function attackClip(player){
    return player?.clips.find(clip=>clip.name==='Human_Attack'&&Number.isFinite(clip.duration)&&clip.duration>IMPACT&&clip.duration<=2);
  }
  function cancel(){
    if(session){
      const s=session;session=null;s.player.chopping=false;
      // A paused frame will not tick the mixer. Resolve a full-weight idle now,
      // without advancing time or leaving another locomotion fade underneath it.
      s.player.mixer.stopAllAction();s.player.clip=null;
      animate(s.player,'idle');
      s.player.action?.stopFading().setEffectiveWeight(1);
      s.player.mixer.update(0);s.player.root.updateMatrixWorld(true);
      s.player.root.traverse(node=>{if(node.isSkinnedMesh)node.skeleton.update();});
      s.player.state='Idle';
    }
    prompt.hidden=true;
  }
  inventory.subscribe(()=>{if(!holding()){cancel();if(prop)prop.visible=false;}});
  function target(){
    const p=getPlayer(),trees=getTrees();if(!p||!trees)return null;
    const t=trees.chopTarget(p.root.position,p.root.rotation.y);if(!t)return null;
    from.copy(p.root.position);from.y+=1;
    to.set(t.x,t.y+1,t.z);
    camera.updateMatrixWorld();
    view.setFromProjectionMatrix(viewProjection.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse));
    if(!view.containsPoint(to))return null;
    if(!choppingLineOfSight(from,to,t.id))return null;
    return choppingLineOfSight(camera.position,to,t.id,7.5)?t:null;
  }
  function toggle(){
    if(holding()){cancel();return inventory.putAway();}
    if(!canEquip())return {ok:false,message:'Equip the handaxe outdoors when not placing shelter or petting.'};
    const player=getPlayer();
    if(!attackClip(player))return {ok:false,message:'The loaded character has no usable Human_Attack swing animation.'};
    let socket=null,hand=null;
    player.root.traverse(node=>{
      if(!node.isBone)return;
      const names=[normalized(node.userData?.name),normalized(node.name)];
      if(names.includes('propr'))socket=node;
      if(names.includes('handr'))hand=node;
    });
    if(!socket&&!hand)return {ok:false,message:'The character has no available hand attachment.'};
    if(!prop){
      prop=new THREE.Group();prop.name='HeldHandaxe';
      const shaft=new THREE.Mesh(new THREE.CylinderGeometry(.018,.024,.48,7),new THREE.MeshStandardMaterial({color:0x805232,roughness:.9}));
      shaft.position.y=.12;
      const head=new THREE.Mesh(new THREE.BoxGeometry(.22,.11,.045),new THREE.MeshStandardMaterial({color:0x8096a1,metalness:.7,roughness:.38}));
      head.position.set(.055,.32,0);head.rotation.z=-.12;
      prop.add(shaft,head);
    }
    // Socket Y is the authored tool shaft. Use the food attachment's fallback
    // only if the prop socket is absent; never modify an authored bone or mesh.
    prop.position.set(0,socket?0:.07,socket?0:.035);
    prop.rotation.set(0,0,socket?0:Math.PI/2);
    (socket||hand).add(prop);
    const result=inventory.hold('handaxe');prop.visible=result.ok;
    prop.updateWorldMatrix(true,true);promptTime=0;return result;
  }
  function swing(){
    if(!holding()||!allowed()||session||cooldown>0)return;
    const player=getPlayer(),clip=attackClip(player);
    if(!clip){say('The loaded character has no usable swing animation.');return;}
    const t=target();
    if(!t){say('Face a clear conifer trunk within 1.65 m to chop.');return;}
    const action=player.mixer.clipAction(clip);
    if(player.action&&player.action!==action)player.action.fadeOut(.08);
    action.reset().setLoop(THREE.LoopOnce,1).setEffectiveTimeScale(1).setEffectiveWeight(1);
    action.clampWhenFinished=true;action.fadeIn(.08).play();
    player.action=action;player.clip=clip.name;player.chopping=true;player.state='Chopping';
    session={player,action,id:t.id,impact:false,duration:clip.duration};
    cooldown=clip.duration;say('Swinging…');
  }
  return {
    toggle,canEquip,swing,cancel,
    beforeFrame(dt){
      if(!holding()||!allowed())cancel();
      else cooldown=Math.max(0,cooldown-dt);
      if(prop){prop.visible=holding()&&canEquip();if(prop.visible)prop.updateWorldMatrix(true,true);}
    },
    // Call after the sole player mixer update and foot placement, before render.
    update(dt){
      if(!holding()||!allowed()){cancel();return;}
      if(prop)prop.updateWorldMatrix(true,true);
      prompt.hidden=false;
      if(session){
        const s=session;
        if(!s.impact&&s.action.time>=IMPACT){
          s.impact=true; // Consume the impact before synchronous inventory listeners.
          const t=target();
          if(!t||t.id!==s.id)say('Swing missed. Keep facing the nearby trunk.');
          else say(getTrees().chop(t.id,s.player.root.position,s.player.root.rotation.y,
            ()=>inventory.add('wood',3)).message);
        }
        if(session===s&&s.action.time>=s.duration-.001){cancel();prompt.hidden=false;}
      }
      messageTime=Math.max(0,messageTime-dt);promptTime-=dt;
      if(promptTime<=0){
        promptTime=.15;prompt.hidden=false;
        if(messageTime>0)paint(message);
        else {
          const t=target();
          paint(t?`Left click · Chop conifer (${t.hits}/4) · 3 Wood · E to put away`:
            'Handaxe held · Face a nearby conifer · Left click to chop · E to put away');
        }
      }
    },
  };
}
