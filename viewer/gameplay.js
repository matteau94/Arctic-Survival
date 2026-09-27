import * as THREE from 'three';
import { TerrainSurface } from './terrain.mjs';
export const surface = new TerrainSurface();
let player;
const wildlife = [], fish = [], obstacles = [];
export const WILDLIFE_SIMULATION_DISTANCE = 1000;
const forward = new THREE.Vector3(), right = new THREE.Vector3(), move = new THREE.Vector3(), away = new THREE.Vector3();
const animationChoices = {idle:['Idle'], walk:['Walk'], run:['Run','Walk'], crouchIdle:['CrouchIdle'], crouchWalk:['CrouchWalk'], swim:['SwimCalm','Swim']};
// World distances are metres; convert requested mph to metres per second.
const WALK_SPEED = 5 * 0.44704;
const SPRINT_SPEED = 14 * 0.44704;
// In-place clips were authored at these ground speeds (human_anim_locomotion.py).
const HUMAN_CLIP_SPEED = {walk:1.3, run:4.5, crouchWalk:.9};
const STANDING_TURN_RATE = 2.8;
const MOVING_TURN_RATE = 9;
const TURN_THRESHOLD = .025;
const solePoint = new THREE.Vector3();
const profiles = {
  fox: {speed:3, radius:70, alert:35}, penguin:{speed:1.1,radius:35,alert:22},
  bear:{speed:2,radius:100,alert:55}, fish:{speed:3,radius:100,aquatic:true},
  orca:{speed:7,radius:400,aquatic:true}
};
function animate(a, state, speed=0) {
  const clip = a.animationClips[state];
  if (!clip) return;
  if(a.type==='human') {
    const authoredSpeed=HUMAN_CLIP_SPEED[state];
    a.mixer.clipAction(clip).setEffectiveTimeScale(authoredSpeed&&speed>0?speed/authoredSpeed:1);
  }
  if(a.clip===clip.name) return;
  const old = a.action;
  a.action=a.mixer.clipAction(clip); a.action.reset().fadeIn(.2).play();
  if (old) old.fadeOut(.2);
  a.clip=clip.name;
}
export function register(a) {
  if (a.type==='human') player=a;
  else if (!profiles[a.type]) {
    obstacles.push(new THREE.Box3().setFromObject(a.root)); return;
  } else {wildlife.push(a);if(a.type==='fish') fish.push(a);}
  a.animationClips = {};
  for (const [state,names] of Object.entries(animationChoices)) {
    a.animationClips[state] = names.map(name=>a.clips.find(c=>c.name.toLowerCase()===name.toLowerCase()||c.name.toLowerCase().endsWith('_'+name.toLowerCase()))).find(Boolean);
  }
  a.home=a.root.position.clone(); a.destination=a.home.clone(); a.think=0;
  a.action=a.clips.length ? a.mixer.clipAction(a.clips.find(c=>c.name===a.clip)||a.clips[0]) : null;
  const ground=surface.height(a.root.position.x,a.root.position.z);
  a.footOffset=a.type==='human'||profiles[a.type]?.aquatic||ground===null?0:Math.max(0,a.root.position.y-ground);
  a.state='Roaming';
  if(a.type==='human') {a.turnStepTime=0;prepareFootContact(a);}
}
function prepareFootContact(a) {
  a.soleSamples=[];
  a.root.updateMatrixWorld(true);
  a.root.traverseVisible(mesh=>{
    if(!mesh.isSkinnedMesh) return;
    const indices=mesh.geometry.attributes.skinIndex, weights=mesh.geometry.attributes.skinWeight;
    if(!indices||!weights) return;
    mesh.skeleton.update();
    for(const side of ['L','R']) {
      const bones=new Set(mesh.skeleton.bones.map((bone,i)=>new RegExp(`^(foot|toe)[._]?${side}$`).test(bone.name)?i:-1));
      bones.delete(-1);
      const candidates=[];
      for(let i=0;i<indices.count;i++) {
        let influence=0;
        for(let j=0;j<4;j++) if(bones.has(indices.getComponent(i,j))) influence+=weights.getComponent(i,j);
        if(influence<.5) continue;
        mesh.getVertexPosition(i,solePoint).applyMatrix4(mesh.matrixWorld);
        candidates.push({mesh,index:i,side,height:solePoint.y,x:solePoint.x,z:solePoint.z});
      }
      candidates.sort((left,right)=>left.height-right.height);
      const bottom=candidates.filter(v=>v.height<(candidates[0]?.height??0)+.008);
      // Cover heel, midsole and toe evenly, rather than selecting arbitrary
      // vertices along the mesh's index order. Still at most 24 total samples.
      if(!bottom.length)continue;
      const minX=Math.min(...bottom.map(v=>v.x)),maxX=Math.max(...bottom.map(v=>v.x));
      const minZ=Math.min(...bottom.map(v=>v.z)),maxZ=Math.max(...bottom.map(v=>v.z));
      const chosen=new Set();
      for(let row=0;row<4;row++)for(let column=0;column<3;column++){
        const x=minX+(maxX-minX)*(column+.5)/3,z=minZ+(maxZ-minZ)*(row+.5)/4;
        let best=null,distance=Infinity;
        for(const vertex of bottom){const d=(vertex.x-x)**2+(vertex.z-z)**2;if(d<distance){best=vertex;distance=d;}}
        if(best&&!chosen.has(best.index)){chosen.add(best.index);a.soleSamples.push(best);}
      }
    }
  });
}
export function updateFootContact(a,dt) {
  if(!a.soleSamples?.length) return;
  const p=a.root.position, floor=surface.height(p.x,p.z);
  if(floor===null) return;
  p.y=floor+a.footOffset;
  a.root.updateMatrixWorld(true);
  let lowest=Infinity;
  let currentMesh=null;
  for(const sample of a.soleSamples) {
    if(sample.mesh!==currentMesh){sample.mesh.skeleton.update();currentMesh=sample.mesh;}
    sample.mesh.getVertexPosition(sample.index,solePoint).applyMatrix4(sample.mesh.matrixWorld);
    sample.x=solePoint.x;sample.y=solePoint.y;sample.z=solePoint.z;
    lowest=Math.min(lowest,sample.y);
  }
  let slope=0,count=0;
  for(const sample of a.soleSamples) if(sample.y<lowest+.025) {
    const height=surface.height(sample.x,sample.z);
    if(height!==null){slope+=height-floor;count++;}
  }
  // Move the ground reference to the planted boot. Preserve the clip's pelvis
  // bounce and airborne running frames instead of pinning both feet every frame.
  const target=THREE.MathUtils.clamp(count?slope/count:0,-.35,.35)-.008;
  a.groundCorrection=THREE.MathUtils.lerp(a.groundCorrection??target,target,1-Math.exp(-dt*22));
  p.y+=a.groundCorrection;
  a.root.updateMatrixWorld(true);
}
function step(a, dx, dz) {
  const p=a.root.position, x=p.x+dx,z=p.z+dz;
  const h=surface.height(x,z), aquatic=profiles[a.type]?.aquatic;
  if (h===null) return false;
  if (aquatic) {
    if (h>p.y-2) return false;
  } else {
    if (h<0 || Math.abs(h-p.y+a.footOffset)>Math.hypot(dx,dz)*1.2+1) return false;
    for (const b of obstacles) if(x>b.min.x-.5&&x<b.max.x+.5&&z>b.min.z-.5&&z<b.max.z+.5&&p.y<b.max.y) return false;
    p.y=h+a.footOffset;
  }
  p.x=x;p.z=z;
  if(a.type!=='human') a.root.rotation.y=Math.atan2(dx,dz);
  return true;
}
export function updateGame(dt, keys, camera) {
  if (!player) return;
  camera.getWorldDirection(forward);forward.y=0;
  if (forward.lengthSq()<.001) forward.set(0,0,-1);
  forward.normalize();right.crossVectors(forward,camera.up).normalize();move.set(0,0,0);
  const targetYaw=Math.atan2(forward.x,forward.z);
  if (keys.has('KeyW')||keys.has('ArrowUp')) move.add(forward);
  if (keys.has('KeyS')||keys.has('ArrowDown')) move.sub(forward);
  if (keys.has('KeyD')||keys.has('ArrowRight')) move.add(right);
  if (keys.has('KeyA')||keys.has('ArrowLeft')) move.sub(right);
  const crouch=keys.has('KeyC'), run=!crouch&&(keys.has('ShiftLeft')||keys.has('ShiftRight'));
  const moving=move.lengthSq()>0;
  move.normalize().multiplyScalar(dt*(crouch?.7:run?SPRINT_SPEED:WALK_SPEED));
  const moved=moving&&step(player,move.x,move.z);
  // Camera look leads the body. Follow the shortest arc with a visible step,
  // rather than spinning a frozen idle pose directly with the mouse.
  const yawDelta=Math.atan2(Math.sin(targetYaw-player.root.rotation.y),Math.cos(targetYaw-player.root.rotation.y));
  const needsTurn=Math.abs(yawDelta)>TURN_THRESHOLD;
  if(!moved&&needsTurn&&!(player.turnStepTime>0)) player.turnStepTime=.45;
  player.turnStepTime=Math.max(0,(player.turnStepTime??0)-dt);
  const turning=!moved&&(needsTurn||player.turnStepTime>0);
  if(moved||turning) {
    const maxTurn=(moved?MOVING_TURN_RATE:STANDING_TURN_RATE)*(crouch?.7:1)*dt;
    player.root.rotation.y+=THREE.MathUtils.clamp(yawDelta,-maxTurn,maxTurn);
  }
  if(moved) player.turnStepTime=0;
  const walking=moved||turning;
  const animationSpeed=moved?(crouch?.7:run?SPRINT_SPEED:WALK_SPEED):turning?(crouch?.75:1.3):0;
  animate(player,crouch?(walking?'crouchWalk':'crouchIdle'):moved&&run?'run':walking?'walk':'idle',animationSpeed);
  player.state=moved?(run?'Running':crouch?'Crouching':'Walking'):turning?'Turning':'Idle';
  for (const a of wildlife) {
    const profile=profiles[a.type], p=a.root.position;
    const distanceSquared=p.distanceToSquared(player.root.position);
    // Distant animals resume from their current state when the player returns.
    if(distanceSquared>WILDLIFE_SIMULATION_DISTANCE*WILDLIFE_SIMULATION_DISTANCE) continue;
    a.think-=dt;
    let fast=false;
    if (!profile.aquatic && distanceSquared<profile.alert*profile.alert) {
      away.copy(p).sub(player.root.position);away.y=0;
      if (away.lengthSq()<.001) away.set(1,0,0);
      a.destination.copy(p).addScaledVector(away.normalize(),a.type==='bear'?-10:20);
      a.state=a.type==='bear'?'Approaching':'Fleeing';fast=true;
      if(a.type==='bear'&&distanceSquared<9) a.destination.copy(p);
    } else if(a.think<=0) {
      a.think=3+Math.random()*5;a.state='Roaming';
      let prey=null,nearestSquared=1500*1500;
      if(a.type==='orca') for(const candidate of fish) {
        const d=p.distanceToSquared(candidate.root.position);
        if(d<nearestSquared){nearestSquared=d;prey=candidate;}
      }
      if(prey){a.destination.copy(prey.root.position);a.state='Following fish';}
      else {const angle=Math.random()*Math.PI*2,r=Math.random()*profile.radius;a.destination.set(a.home.x+Math.sin(angle)*r,a.home.y,a.home.z+Math.cos(angle)*r);}
    }
    move.copy(a.destination).sub(p);move.y=0;
    const travel=Math.min(move.length(),profile.speed*(fast?2:1)*dt);
    move.normalize().multiplyScalar(travel);
    const moved=travel>.001&&step(a,move.x,move.z);
    if(!moved){a.think=0;a.state='Resting';}
    animate(a,profile.aquatic?'swim':moved?(fast?'run':'walk'):'idle');
  }
}
