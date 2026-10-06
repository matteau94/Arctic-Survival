import { hudHint } from './cold.js';
import * as THREE from 'three';
import { createTentDoor, animateTentDoor } from './tent-door.js';

export function createTentInterior({world,player,camera,camping,keys,getYaw,setYaw,companions,onTransition=()=>{}}){
  const room=new THREE.Scene();room.background=new THREE.Color('#241e18');
  room.add(new THREE.HemisphereLight(0xffe6b0,0x42342a,2));
  const light=new THREE.PointLight(0xffc477,35,15);light.position.set(0,3,0);room.add(light);
  const canvas=new THREE.MeshStandardMaterial({color:0xb99868,roughness:1,side:THREE.DoubleSide});
  const floor=new THREE.MeshStandardMaterial({color:0x514c3c,roughness:1});
  function box(w,h,d,x,y,z,material){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);m.position.set(x,y,z);room.add(m);return m;}
  box(7,.1,8,0,-.05,0,floor);
  box(.08,3.8,8,-3.5,1.9,0,canvas);box(.08,3.8,8,3.5,1.9,0,canvas);
  box(7,3.8,.08,0,1.9,-4,canvas);
  box(2.24,3.8,.08,-2.38,1.9,4,canvas);box(2.24,3.8,.08,2.38,1.9,4,canvas);
  box(2.52,1.3,.08,0,3.15,4,canvas);
  box(7,.08,8,0,3.8,0,canvas);
  const interiorDoor=createTentDoor();
  const interiorDoorMount=new THREE.Group();interiorDoorMount.scale.set(.75,.83,.75);
  interiorDoorMount.position.z=2.5;interiorDoorMount.add(interiorDoor);room.add(interiorDoorMount);
  box(2,.015,1.3,0,.01,2.6,new THREE.MeshStandardMaterial({color:0x876b43}));
  const lantern=box(.22,.35,.22,0,3.1,0,new THREE.MeshStandardMaterial({color:0xffd084,emissive:0xffac40,emissiveIntensity:1.5}));
  const prompt=document.createElement('div');prompt.className='context-hint';prompt.hidden=true;document.body.append(prompt);
  const fade=document.createElement('div');fade.style.cssText='position:fixed;inset:0;background:#100e0b;opacity:0;pointer-events:none;z-index:5';document.body.append(fade);
  let inside=false,transition=null,nearby=null,home=null,activeTent=null;
  let activeTentIndex=null;
  const local=new THREE.Vector3(),forward=new THREE.Vector3(),right=new THREE.Vector3(),move=new THREE.Vector3();
  function pose(name){const clip=player.clips.find(c=>c.name===`Human_${name}`);if(!clip||player.clip===clip.name)return;player.action?.fadeOut(.15);player.action=player.mixer.clipAction(clip);player.action.reset().setEffectiveTimeScale(1).fadeIn(.15).play();player.clip=clip.name;}
  function door(progress,closing=false){
    if(activeTent){
      const mesh=activeTent.mesh.getObjectByName('BlenderTentDoor');
      if(mesh)animateTentDoor(mesh,progress,closing);
      activeTent.mesh.updateMatrixWorld(true);
    }
    animateTentDoor(interiorDoor,progress,closing);
  }
  function interiorCamera(){
    const p=player.root.position;
    camera.position.set(THREE.MathUtils.clamp(p.x-Math.sin(getYaw())*2.6,-3.2,3.2),2.8,THREE.MathUtils.clamp(p.z-Math.cos(getYaw())*2.6,-3.7,3.7));
    camera.lookAt(p.x,1.2,p.z);camera.updateMatrixWorld();
  }
  function refreshPrompt(){
    if(transition){prompt.hidden=true;return;}
    if(inside){nearby=Math.abs(player.root.position.x)<1.5&&player.root.position.z>2.2;hudHint(prompt,'enter','F · Exit tent','F · Unzip and step outside');}
    else{
      nearby=null;
      if(!camping.active()&&!camping.busy())for(const tent of camping.tents()){
        local.copy(player.root.position);tent.mesh.worldToLocal(local);
        if(Math.abs(local.x)<.75&&local.z>1.25&&local.z<2.6&&Math.abs(local.y)<1){nearby=tent;break;}
      }
      hudHint(prompt,'tent','F · Enter tent','F · Unzip and enter tent. Exposure continues until inside.');
    }
    prompt.hidden=!nearby;
  }
  return {
    inside:()=>inside,active:()=>inside||Boolean(transition),scene:()=>inside?room:world,
    transitioning:()=>Boolean(transition),
    spectatorOrigin:()=>inside?home.position.clone():null,
    hide(){prompt.hidden=true;},
    canInteract(){refreshPrompt();return !!nearby||!!transition;},
    occupiedTentIndex:()=>inside?activeTentIndex:null,
    placementContext:()=>inside&&!transition?{scene:room,tentIndex:camping.tentIndex(activeTent),companionOverlap:bounds=>companions.overlaps(bounds)}:null,
    canSee(from,to){
      // Room coordinates never go through the outdoor terrain/obstacle sampler.
      if(!inside||transition||Math.abs(from.x)>3.4||Math.abs(to.x)>3.4||Math.abs(from.z)>3.9||Math.abs(to.z)>3.9)return false;
      const start=from.clone();start.y+=.35;
      const end=to.clone();end.y+=.35;
      const direction=end.clone().sub(start),length=direction.length();
      const ray=new THREE.Ray(start,direction.normalize()),hit=new THREE.Vector3();
      return !camping.indoorBounds(activeTentIndex).some(box=>box.containsPoint(start)||(ray.intersectBox(box,hit)&&start.distanceTo(hit)<length));
    },
    interact(){refreshPrompt();if(!nearby||transition)return;
      onTransition();
      camping.cancel();
      if(!inside){activeTent=nearby;activeTentIndex=camping.tentIndex(activeTent);home={position:player.root.position.clone(),rotation:player.root.rotation.y,yaw:getYaw()};}
      keys.clear();pose('Idle');transition={time:0,switched:false};prompt.hidden=true;
    },
    blocks(x,z,worldY=player.root.position.y){for(const tent of camping.tents()){
      local.set(x,worldY,z);tent.mesh.worldToLocal(local);
      if(Math.abs(local.x)<1.13&&Math.abs(local.z)<1.43)return true;
    }return false;},
    update(dt,running){
      if(transition){
        if(!running)return;
        transition.time+=dt;const t=transition.time;
        if(t<2.65)door(Math.min(1,t/2.3));else door(Math.min(1,(t-2.65)/2.3),true);
        fade.style.opacity=String(t<2.3?0:t<2.65?(t-2.3)/.35:t<2.8?1:Math.max(0,1-(t-2.8)/.35));
        if(t>=2.65&&!transition.switched){
          transition.switched=true;inside=!inside;
          if(inside){camping.showInterior(room,camping.tentIndex(activeTent));room.add(player.root);player.root.position.set(0,0,2.7);player.root.rotation.y=Math.PI;setYaw(Math.PI);companions.enter(room,activeTentIndex,home.position);}
          else{companions.leave();world.add(player.root);player.root.position.copy(home.position);player.root.rotation.y=home.rotation;setYaw(home.yaw);}
          player.root.updateMatrixWorld(true);keys.clear();
        }
        if(inside)interiorCamera();
        if(t>=4.95){door(1,true);fade.style.opacity='0';transition=null;}
      }else if(inside){
        if(running&&!player.petting){
          forward.set(Math.sin(getYaw()),0,Math.cos(getYaw()));right.set(-forward.z,0,forward.x);move.set(0,0,0);
          if(keys.has('KeyW')||keys.has('ArrowUp'))move.add(forward);
          if(keys.has('KeyS')||keys.has('ArrowDown'))move.sub(forward);
          if(keys.has('KeyD')||keys.has('ArrowRight'))move.add(right);
          if(keys.has('KeyA')||keys.has('ArrowLeft'))move.sub(right);
          const moving=move.lengthSq()>0;move.normalize().multiplyScalar(dt*1.3);
          const x=THREE.MathUtils.clamp(player.root.position.x+move.x,-3.1,3.1),z=THREE.MathUtils.clamp(player.root.position.z+move.z,-3.6,3.3);
          if(!companions.blocksPlayer(x,z)){player.root.position.x=x;player.root.position.z=z;}
          if(moving)player.root.rotation.y=Math.atan2(move.x,move.z);
          pose(moving?'Walk':'Idle');
        }
        if(running){player.mixer.update(dt);player.root.updateMatrixWorld(true);}
        interiorCamera();
      }
      if(inside)companions.update(dt,running&&!transition);
      refreshPrompt();if(!running)prompt.hidden=true;
    },
  };
}
