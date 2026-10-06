import * as THREE from 'three';

// Metres and active game seconds. Bounds only select candidates; rays confirm contact.
const NOTICE=55, ESCAPE=65, WARNING=3, CONTACT=.5;
const ATTACK_REACH=2.2, WINDUP=.8, ATTACK=.4, RECOVERY=1.2;
const HIT_START=.12, HIT_END=.32, CHARGE_SPEED=7;
const SAMPLE=.1, LOST_SIGHT=10, COOLDOWN=10;
const bears=new Set(), blockers=[];
let treeOverlap=()=>false, treeRayDistance=(_ray,length)=>length;
let surface, cancelSetup=()=>{}, onDeath=()=>{}, isActive=()=>false, hud=null, caption=null, sampleTime=0, contactTurn=0;
const box=new THREE.Box3(), inverse=new THREE.Matrix4(), matrix=new THREE.Matrix4();
const point=new THREE.Vector3(), target=new THREE.Vector3(), direction=new THREE.Vector3();
const scale=new THREE.Vector3(), rotation=new THREE.Quaternion(), axis=new THREE.Vector3(0,1,0);
const ray=new THREE.Raycaster(), hits=[];

export function configureBears(options){
  treeOverlap=options.treeOverlap??treeOverlap;
  treeRayDistance=options.treeRayDistance??treeRayDistance;
  surface=options.surface;cancelSetup=options.cancelSetup;onDeath=options.onDeath;isActive=options.isActive;
  blockers.push(...options.obstacles);
  for(const tent of options.camping.tents())addTent(tent);
  options.camping.subscribeTentPlaced(addTent);
  hud=document.createElement('div');hud.id='bear-status';hud.hidden=true;
  hud.setAttribute('role','status');hud.setAttribute('aria-live','polite');
  // DOM only: no scene objects, materials, or changes to the animal asset.
  hud.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 8 3 4l5 1m8 0 5-1-2 4M5 8l-2 6 4 6h10l4-6-2-6-7-3ZM7 12h2m6 0h2m-7 4h4l-2 2Z"/></svg><span></span>';
  caption=hud.lastElementChild;document.body.append(hud);
}
function addTent(tent){blockers.push(new THREE.Box3().setFromObject(tent.mesh));}
function finiteBounds(bounds){return !bounds.isEmpty()&&[bounds.min.x,bounds.min.y,bounds.min.z,bounds.max.x,bounds.max.y,bounds.max.z].every(Number.isFinite);}
function clear(a){Object.assign(a.bear,{phase:'roam',warning:0,age:0,attackYaw:0,advanced:false,strike:false,recoveryCarry:0,checked:0,escape:0,lost:0,cooldown:0,sense:0,gap:Infinity,los:false});}
export function registerBear(a){
  if(a.type!=='bear')return;
  a.root.updateMatrixWorld(true);inverse.copy(a.root.matrixWorld).invert();
  const meshes=[],bounds=new THREE.Box3();
  a.root.traverseVisible(mesh=>{
    if(!mesh.isMesh||!visible(mesh))return;
    if(mesh.isSkinnedMesh){mesh.skeleton.update();mesh.computeBoundingBox();}
    else if(!mesh.geometry.boundingBox)mesh.geometry.computeBoundingBox();
    const local=mesh.isSkinnedMesh?mesh.boundingBox:mesh.geometry.boundingBox;
    if(!local||!finiteBounds(local))return;
    matrix.multiplyMatrices(inverse,mesh.matrixWorld);
    bounds.union(box.copy(local).applyMatrix4(matrix));meshes.push(mesh);
  });
  a.bear={meshes,bounds,world:new THREE.Box3()};clear(a);bears.add(a);
}
export function unregisterBear(a){if(a.bear)clear(a);bears.delete(a);}
export function resetBearThreats(){
  for(const a of bears){if(a.bear.phase!=='roam')a.think=0;clear(a);}
  sampleTime=0;contactTurn=0;if(hud)hud.hidden=true;
}
function visible(mesh){
  for(let node=mesh;node;node=node.parent)if(!node.visible)return false;
  const materials=Array.isArray(mesh.material)?mesh.material:[mesh.material];
  return materials.some(material=>material&&material.visible);
}
function boundsAt(a,x=a.root.position.x,z=a.root.position.z,yaw=a.root.rotation.y,y=a.root.position.y){
  const b=a.bear;
  scale.copy(a.root.scale);rotation.setFromAxisAngle(axis,yaw);
  point.set(x,y,z);matrix.compose(point,rotation,scale);
  return b.world.copy(b.bounds).applyMatrix4(matrix);
}
function gapTo(bounds,p){return Math.hypot(Math.max(bounds.min.x-p.x,0,p.x-bounds.max.x),Math.max(bounds.min.z-p.z,0,p.z-bounds.max.z));}
function clearLine(from,to){
  direction.copy(to).sub(from);const length=direction.length();
  ray.set(from,direction.multiplyScalar(length>.001?1/length:0));ray.near=0;ray.far=length;
  if(treeRayDistance(ray.ray,length)<length)return false;
  for(const obstacle of blockers){
    if(obstacle.containsPoint(from)||obstacle.containsPoint(to))return false;
    const hit=length>.001?ray.ray.intersectBox(obstacle,point):null;
    if(hit&&hit.distanceTo(from)<=length)return false;
  }
  // Containment is checked even for coincident endpoints; a zero-length segment
  // cannot establish a clear sightline or confirm contact.
  if(length<=.001)return false;
  // At most 64 terrain samples per sightline, including unusually large actors.
  const count=Math.min(64,Math.max(1,Math.ceil(length/2)));
  for(let i=1;i<=count;i++){
    point.lerpVectors(from,to,i/count);const ground=surface.height(point.x,point.z);
    if(!Number.isFinite(ground)||ground>point.y-.05)return false;
  }
  return true;
}
const from=new THREE.Vector3(),to=new THREE.Vector3();
function sense(a,p){
  const b=a.bear;
  boundsAt(a);
  // Distance to the oriented loaded footprint, not its origin or world-AABB corners.
  inverse.copy(matrix).invert();to.copy(p).applyMatrix4(inverse);
  to.x=THREE.MathUtils.clamp(to.x,b.bounds.min.x,b.bounds.max.x);
  to.z=THREE.MathUtils.clamp(to.z,b.bounds.min.z,b.bounds.max.z);
  to.applyMatrix4(matrix);b.gap=Math.hypot(to.x-p.x,to.z-p.z);
  from.copy(p);from.y+=1;
  // Use the bear's body centre for sight, independently of footprint distance.
  // Clamping the player into the footprint can produce an empty-corner endpoint.
  b.bounds.getCenter(to).applyMatrix4(matrix);
  b.los=b.gap<=ESCAPE&&clearLine(from,to);
}
export function bearIntent(a,dt,threat){
  const b=a.bear;
  if(!b||!surface||b.bounds.isEmpty())return null;
  if(!threat||!isActive()){clear(a);return null;}
  b.advanced=false;b.strike=false;
  b.sense-=dt;if(b.sense<=0){b.sense=SAMPLE;sense(a,threat);}
  if(b.cooldown>0){b.cooldown=Math.max(0,b.cooldown-dt);return null;}
  if(b.phase==='roam'&&b.gap<=NOTICE&&b.los){
    b.phase='warning';b.warning=WARNING;cancelSetup();
    if(hud){hud.hidden=false;caption.textContent='Bear · Shift: run / shelter · 3.0s';}
    return {stop:true,state:'Warning'};
  }
  if(b.phase==='roam')return null;
  // Also cancel setup begun after the initial warning; nothing was consumed yet.
  cancelSetup();
  b.escape=b.gap>ESCAPE?b.escape+dt:0;b.lost=b.los?0:b.lost+dt;
  if(b.escape>=3||b.lost>=LOST_SIGHT){clear(a);b.cooldown=COOLDOWN;a.think=0;return null;}
  if(b.phase==='warning'){
    b.warning=Math.max(0,b.warning-dt);
    if(b.warning===0)b.phase='pursuit';
    return {stop:true,state:'Warning'};
  }
  if(b.phase==='pursuit'&&b.gap<=ATTACK_REACH){
    // Recheck before committing; sampled pursuit sight is not attack authority.
    sense(a,threat);
    const yaw=Math.atan2(threat.x-a.root.position.x,threat.z-a.root.position.z);
    if(b.gap<=ATTACK_REACH&&b.los&&bearCanStep(a,a.root.position.x,a.root.position.z,yaw)){
      b.phase='windup';b.age=0;b.attackYaw=yaw;a.root.rotation.y=yaw;
      return {stop:true,state:'Attack windup'};
    }
  }
  if(b.phase==='windup'){
    const used=Math.min(dt,WINDUP-b.age);b.age+=used;dt-=used;
    if(b.age<WINDUP)return {stop:true,state:'Attack windup'};
    b.phase='attack';b.age=0;
  }
  if(b.phase==='attack'){
    const start=b.age,chargeDt=Math.min(dt,ATTACK-start);
    b.age=start+chargeDt;b.recoveryCarry=dt-chargeDt;
    // This frame's interval may cross a strike boundary. Never queue its hit.
    b.strike=chargeDt>0&&start<HIT_END&&b.age>=HIT_START;
    // Keep attack phase until current movement, pose and contact are evaluated.
    return {stop:chargeDt<=0,state:'Charging',charge:true,chargeDt,yaw:b.attackYaw,speed:CHARGE_SPEED};
  }
  if(b.phase==='recovery'){
    b.age+=dt;
    if(b.age>=RECOVERY){b.phase='pursuit';b.age=0;}
    return {stop:true,state:'Recovering'};
  }
  return {stop:false,state:'Pursuing'};
}
export function bearCanStep(a,x,z,yaw){
  if(!a.bear||!surface)return true;
  const center=surface.height(x,z);
  if(!Number.isFinite(center)||center<0)return false;
  const bounds=boundsAt(a,x,z,yaw,center+a.footOffset);
  if(!finiteBounds(bounds))return false;
  if(treeOverlap(bounds))return false;
  for(const obstacle of blockers)if(bounds.intersectsBox(obstacle))return false;
  for(const u of [0,.5,1])for(const v of [0,.5,1]){
    const px=THREE.MathUtils.lerp(bounds.min.x,bounds.max.x,u),pz=THREE.MathUtils.lerp(bounds.min.z,bounds.max.z,v);
    const height=surface.height(px,pz);
    if(!Number.isFinite(height)||height<0||Math.abs(height-center)>1+Math.hypot(px-x,pz-z)*.35)return false;
  }
  return true;
}
function contact(a,p){
  const b=a.bear;
  // Flush deferred animation before evaluating contact, even for large scaled actors.
  if(a.animationElapsed>0){a.mixer.update(a.animationElapsed);a.animationElapsed=0;}
  a.root.updateMatrixWorld(true);
  // At most two fairly scheduled candidates reach this posed-geometry work.
  for(const mesh of b.meshes)if(visible(mesh)&&mesh.isSkinnedMesh){
    mesh.skeleton.update();mesh.computeBoundingBox();
    if(!mesh.boundingSphere)mesh.boundingSphere=new THREE.Sphere();
    mesh.boundingBox.getBoundingSphere(mesh.boundingSphere);
  }
  // Short rays from three body heights. Misses are safe; bounding boxes never kill.
  for(const height of [.35,.9,1.45]){
    from.copy(p);from.y+=height;
    let nearest=Infinity;
    for(const mesh of b.meshes)if(visible(mesh)){
      box.copy(mesh.isSkinnedMesh?mesh.boundingBox:mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
      if(from.y<box.min.y||from.y>box.max.y)continue;
      box.clampPoint(from,point);
      const distance=point.distanceToSquared(from);
      if(distance<nearest){nearest=distance;target.copy(point);if(distance<1e-8)box.getCenter(target);}
    }
    if(nearest>CONTACT*CONTACT)continue;
    const angle=Math.atan2(target.x-from.x,target.z-from.z);
    // Two short directions per height; at most six rays per candidate per sample.
    for(const offset of [0,Math.PI]){
      direction.set(Math.sin(angle+offset),0,Math.cos(angle+offset));
      ray.set(from,direction);ray.near=0;ray.far=CONTACT;hits.length=0;
      for(const mesh of b.meshes)if(visible(mesh))ray.intersectObject(mesh,false,hits);
      const hit=hits.find(hit=>{
        const material=Array.isArray(hit.object.material)?hit.object.material[hit.face?.materialIndex??0]:hit.object.material;
        if(!material?.visible||hit.distance>CONTACT)return false;
        // Filter each intersection so an earlier flank cannot mask a front hit.
        to.copy(hit.point).applyMatrix4(inverse.copy(a.root.matrixWorld).invert());
        return to.z>=b.bounds.min.z+(b.bounds.max.z-b.bounds.min.z)*.75;
      });
      if(!hit)continue;
      target.copy(hit.point);
      if(clearLine(from,target))return true;
    }
  }
  return false;
}
export function updateBearContact(dt,p,yaw){
  if(!isActive()){resetBearThreats();return;}
  sampleTime+=dt;
  let shown=null;const eligible=[];
  for(const a of bears){
    const b=a.bear,advanced=b.advanced,strike=b.strike;b.advanced=false;b.strike=false;
    if(b.phase==='roam')continue;
    // Only this frame's moving charge can hit, never warning/pursuit/recovery.
    const bounds=boundsAt(a);
    b.contactGap=gapTo(bounds,p);
    if(!shown||b.gap<shown.bear.gap)shown=a;
    if(b.phase!=='attack'||!advanced||!strike||!finiteBounds(bounds)||b.contactGap>CONTACT||bounds.max.y<p.y+.35||bounds.min.y>p.y+1.45||!a.root.visible)continue;
    const dx=p.x-a.root.position.x,dz=p.z-a.root.position.z;
    if(dx*Math.sin(b.attackYaw)+dz*Math.cos(b.attackYaw)<=Math.hypot(dx,dz)*.75)continue;
    eligible.push(a);
  }
  // Least recently checked first: persistent misses cannot monopolize the budget.
  // Eligibility is rebuilt from current movement/contact bounds every frame.
  eligible.sort((a,b)=>a.bear.checked-b.bear.checked);
  for(const a of eligible.slice(0,2)){
    const b=a.bear;b.checked=++contactTurn;
    sense(a,p);
    if(b.los&&contact(a,p)&&isActive()){
      resetBearThreats();onDeath('bear');return;
    }
  }
  for(const a of bears){
    const b=a.bear;
    if(b.phase==='attack'&&b.age>=ATTACK){
      b.phase='recovery';b.age=b.recoveryCarry;b.recoveryCarry=0;
    }
  }
  if(sampleTime<SAMPLE)return;sampleTime=0;
  if(!hud)return;hud.hidden=!shown;if(!shown)return;
  const b=shown.bear,angle=yaw-Math.atan2(shown.root.position.x-p.x,shown.root.position.z-p.z);
  const arrows=['↑','↗','→','↘','↓','↙','←','↖'];
  const arrow=arrows[((Math.round(angle/(Math.PI/4))%8)+8)%8];
  const label=b.phase==='windup'?`Charging soon · move aside · ${Math.max(0,WINDUP-b.age).toFixed(1)}s`:b.phase==='attack'?'Charging · dodge sideways':b.phase==='recovery'?'Recovering · escape':b.phase==='warning'?`Shift: run / shelter · ${b.warning.toFixed(1)}s`:'Pursuing · Shift / shelter';
  caption.textContent=`${arrow} Bear · ${label}`;
}
