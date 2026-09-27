import * as THREE from 'three';
import { TerrainSurface } from './terrain.mjs';
export const surface = new TerrainSurface();
let player;
const wildlife = [], obstacles = [];
const forward = new THREE.Vector3(), right = new THREE.Vector3(), move = new THREE.Vector3();
const profiles = {
  fox: {speed:3, radius:70, alert:35}, penguin:{speed:1.1,radius:35,alert:22},
  bear:{speed:2,radius:100,alert:55}, fish:{speed:3,radius:100,aquatic:true},
  orca:{speed:7,radius:400,aquatic:true}
};
function animate(a, names) {
  const clip = names.map(name=>a.clips.find(c=>c.name.toLowerCase()===name.toLowerCase()||c.name.toLowerCase().endsWith('_'+name.toLowerCase()))).find(Boolean);
  if (!clip || a.clip===clip.name) return;
  const old = a.action;
  a.action=a.mixer.clipAction(clip); a.action.reset().fadeIn(.2).play();
  if (old) old.fadeOut(.2);
  a.clip=clip.name;
}
export function register(a) {
  if (a.type==='human') player=a;
  else if (!profiles[a.type]) {
    obstacles.push(new THREE.Box3().setFromObject(a.root)); return;
  } else wildlife.push(a);
  a.home=a.root.position.clone(); a.destination=a.home.clone(); a.think=0;
  a.action=a.clips.length ? a.mixer.clipAction(a.clips.find(c=>c.name===a.clip)||a.clips[0]) : null;
  const ground=surface.height(a.root.position.x,a.root.position.z);
  a.footOffset=a.type==='human'||profiles[a.type]?.aquatic||ground===null?0:Math.max(0,a.root.position.y-ground);
  a.state='Roaming';
}
function step(a, dx, dz) {
  const p=a.root.position, x=p.x+dx,z=p.z+dz;
  const h=surface.height(x,z), aquatic=profiles[a.type]?.aquatic;
  if (h===null) return false;
  if (aquatic) {
    if (h>p.y-2) return false;
  } else {
    if (h<0 || Math.abs(h-p.y+a.footOffset)>Math.hypot(dx,dz)*1.2+1) return false;
    if (obstacles.some(b=>x>b.min.x-.5&&x<b.max.x+.5&&z>b.min.z-.5&&z<b.max.z+.5&&p.y<b.max.y)) return false;
    p.y=h+a.footOffset;
  }
  p.x=x;p.z=z;
  a.root.rotation.y=Math.atan2(dx,dz);
  return true;
}
export function updateGame(dt, keys, camera) {
  if (!player) return;
  camera.getWorldDirection(forward);forward.y=0;
  if (forward.lengthSq()<.001) forward.set(0,0,-1);
  forward.normalize();right.crossVectors(forward,camera.up).normalize();move.set(0,0,0);
  if (keys.has('KeyW')||keys.has('ArrowUp')) move.add(forward);
  if (keys.has('KeyS')||keys.has('ArrowDown')) move.sub(forward);
  if (keys.has('KeyD')||keys.has('ArrowRight')) move.add(right);
  if (keys.has('KeyA')||keys.has('ArrowLeft')) move.sub(right);
  const crouch=keys.has('KeyC'), run=!crouch&&(keys.has('ShiftLeft')||keys.has('ShiftRight'));
  const moving=move.lengthSq()>0;
  move.normalize().multiplyScalar(dt*(crouch?.7:run?4.5:1.5));
  const moved=moving&&step(player,move.x,move.z);
  animate(player,[crouch?(moved?'CrouchWalk':'CrouchIdle'):moved?(run?'Run':'Walk'):'Idle']);
  player.state=moved?(run?'Running':crouch?'Crouching':'Walking'):'Idle';
  for (const a of wildlife) {
    const profile=profiles[a.type], p=a.root.position;
    a.think-=dt;
    const distance=p.distanceTo(player.root.position);
    let fast=false;
    if (!profile.aquatic && distance<profile.alert) {
      const away=p.clone().sub(player.root.position);away.y=0;
      if (away.lengthSq()<.001) away.set(1,0,0);
      a.destination.copy(p).addScaledVector(away.normalize(),a.type==='bear'?-10:20);
      a.state=a.type==='bear'?'Approaching':'Fleeing';fast=true;
      if(a.type==='bear'&&distance<3) a.destination.copy(p);
    } else if(a.think<=0) {
      a.think=3+Math.random()*5;a.state='Roaming';
      const prey=a.type==='orca'?wildlife.filter(b=>b.type==='fish').sort((b,c)=>p.distanceToSquared(b.root.position)-p.distanceToSquared(c.root.position))[0]:null;
      if(prey && p.distanceTo(prey.root.position)<1500){a.destination.copy(prey.root.position);a.state='Following fish';}
      else {const angle=Math.random()*Math.PI*2,r=Math.random()*profile.radius;a.destination.copy(a.home).add(new THREE.Vector3(Math.sin(angle)*r,0,Math.cos(angle)*r));}
    }
    move.copy(a.destination).sub(p);move.y=0;
    const travel=Math.min(move.length(),profile.speed*(fast?2:1)*dt);
    move.normalize().multiplyScalar(travel);
    const moved=travel>.001&&step(a,move.x,move.z);
    if(!moved){a.think=0;a.state='Resting';}
    animate(a,profile.aquatic?['SwimCalm','Swim']:moved?(fast?['Run','Walk']:['Walk']):['Idle']);
  }
}
