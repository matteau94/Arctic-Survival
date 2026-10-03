import * as THREE from 'three';
import { worldSeed, transformWorldPoint, reshapeTerrain, reshapeManifest } from './world-seed.js';
import { createTerrainTiles, createTerrainMaterial } from './terrain-render.js';
import { surface, register, updateGame, updateWildlife, updateFootContact, setCampCollision } from './gameplay.js';
import { createFootprints } from './footprints.js';
import { createInventory } from './inventory.js';
import { createInventoryUI } from './inventory-ui.js';
import { createCamping } from './camping.js';
import { createTentInterior } from './tent-interior.js';
import { loadTentDoor } from './tent-door.js';
import { createWaypoints } from './waypoints.js';
import { createWildlifeStream } from './wildlife-stream.js';
import { createFoxDens } from './fox-dens.js';
import { createHabitatDensity } from './habitat-density.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';
const $ = id => document.getElementById(id);
const scene = new THREE.Scene(); scene.background = new THREE.Color('#8aa9ba');scene.fog=new THREE.Fog('#8aa9ba',12000,55000);
const camera = new THREE.PerspectiveCamera(65, innerWidth / innerHeight, .1, 60000);
const renderer = new THREE.WebGLRenderer({antialias:false, powerPreference:'high-performance'});
renderer.setSize(innerWidth,innerHeight); renderer.setPixelRatio(Math.min(devicePixelRatio,1)); renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.15; document.body.prepend(renderer.domElement);
// Low polar sunlight makes ridge faces distinct while sky fill keeps shaded snow readable.
scene.add(new THREE.HemisphereLight(0xdff5ff,0x485263,1.05));
const sun = new THREE.DirectionalLight(0xfff4df,2.5);sun.position.set(-8000,4500,6000);scene.add(sun);
const ocean=new THREE.Mesh(new THREE.PlaneGeometry(1000000,1000000),new THREE.MeshStandardMaterial({color:0x247993,transparent:true,opacity:.4,roughness:.3,depthWrite:false,side:THREE.DoubleSide}));ocean.rotation.x=-Math.PI/2;scene.add(ocean);
const actors=[],terrainMeshes=[],cameraObstacles=[],keys=new Set();
let player=null,ready=false,locked=false,yaw=0,pitch=-.18,updateFootprints=null,camping=null,tentInterior=null,waypointHUD=null;
let foxDens=null,wildlifeStream=null;
let spectating=false;
const spectatorPosition=new THREE.Vector3();
const spectatorForward=new THREE.Vector3(),spectatorRight=new THREE.Vector3(),spectatorMove=new THREE.Vector3();
let survivalView=null,teleportLocations=[];
const survivalHelp=$('help').textContent;
function refreshModeMenu(){
  $('play').textContent=spectating?'Return to survival':'Resume expedition';
  $('spectate').textContent=spectating?'Resume spectator mode':'Enter spectator mode';
  $('spectator-tools').hidden=!spectating;
  $('spectate').disabled=!ready||!!tentInterior?.active()||!!foxDens?.active()||!!camping?.busy();
  $('help').textContent=spectating?'SPECTATOR · WASD / Arrows · Fly · Space / C · Up / Down · Shift · Faster · T · Teleport · Esc · Menu':survivalHelp;
}
function enterSpectator(){
  if(!ready||tentInterior?.active()||foxDens?.active()||camping?.busy())return;
  if(!spectating){
    camping?.cancel();
    survivalView={yaw,pitch};
    spectatorPosition.copy(camera.position);
    const direction=camera.getWorldDirection(new THREE.Vector3());
    yaw=Math.atan2(direction.x,direction.z);pitch=Math.asin(direction.y);
    spectating=true;inventoryUI.setEnabled(false);
  }
  refreshModeMenu();lockPointer();
}
function leaveSpectator(){
  if(spectating){spectating=false;yaw=survivalView.yaw;pitch=survivalView.pitch;player.root.visible=true;inventoryUI.setEnabled(true);updateCamera();}
  refreshModeMenu();lockPointer();
}
function updateSpectator(dt){
  spectatorForward.set(Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),Math.cos(yaw)*Math.cos(pitch));
  spectatorRight.crossVectors(spectatorForward,camera.up).normalize();
  spectatorMove.set(0,0,0);
  if(keys.has('KeyW')||keys.has('ArrowUp'))spectatorMove.add(spectatorForward);
  if(keys.has('KeyS')||keys.has('ArrowDown'))spectatorMove.sub(spectatorForward);
  if(keys.has('KeyD')||keys.has('ArrowRight'))spectatorMove.add(spectatorRight);
  if(keys.has('KeyA')||keys.has('ArrowLeft'))spectatorMove.sub(spectatorRight);
  if(keys.has('Space'))spectatorMove.y+=1;
  if(keys.has('KeyC'))spectatorMove.y-=1;
  if(locked&&spectatorMove.lengthSq())spectatorPosition.addScaledVector(spectatorMove.normalize(),dt*(keys.has('ShiftLeft')||keys.has('ShiftRight')?250:35));
  camera.position.copy(spectatorPosition);camera.lookAt(look.copy(spectatorPosition).add(spectatorForward));camera.updateMatrixWorld();
}
$('spectate').onclick=enterSpectator;
$('teleport').onclick=()=>{
  if(!spectating)return;
  const destination=teleportLocations[Number($('destination').value)];
  if(!destination)return;
  const [x,y,z]=destination.position;
  spectatorPosition.set(x,Math.max(y,surface.height(x,z+18)??y)+12,z+18);
  yaw=Math.PI;pitch=-.5;keys.clear();updateSpectator(0);lockPointer();
};
const inventory=createInventory({storage:null});
const inventoryUI=createInventoryUI({inventory,canPlace:()=>!tentInterior?.active()&&!foxDens?.active(),onOpen:()=>{
  camping?.cancel();
  release();$('start').hidden=true;
},onClose:()=>{
  release();$('play').focus();
},onPlace:id=>{
  camping?.begin(id);lockPointer();
}});
inventoryUI.setEnabled(false);
const aim=new THREE.Vector3(),look=new THREE.Vector3(),offset=new THREE.Vector3(),cameraProbe=new THREE.Vector3();
const cameraRay=new THREE.Raycaster();
function updateCamera(){
  if(!player)return;
  aim.copy(player.root.position);aim.y+=keys.has('KeyC')?1.05:1.5;
  look.set(Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),Math.cos(yaw)*Math.cos(pitch));
  offset.copy(look).multiplyScalar(-1);
  cameraRay.set(aim,offset);cameraRay.far=4.5;
  let distance=4.5;
  const probe=cameraProbe;
  for(const box of cameraObstacles){
    const hit=cameraRay.ray.intersectBox(box,probe);
    if(hit)distance=Math.min(distance,Math.max(.15,aim.distanceTo(hit)-.2));
  }
  for(let d=.15;d<=distance;d+=.15){
    probe.copy(aim).addScaledVector(offset,d);
    const ground=surface.height(probe.x,probe.z);
    if(ground!==null&&probe.y<ground+.2){distance=Math.max(.15,d-.15);break;}
  }
  camera.position.copy(aim).addScaledVector(offset,distance);
  camera.lookAt(aim);camera.updateMatrixWorld();
}
function captureFailed(){
  $('status').textContent='Mouse capture was blocked. Try again, or open the game in desktop Chrome or Edge if this embedded preview blocks capture.';
  $('play').textContent='Retry mouse capture';
}
async function lockPointer(){
  if(!ready||inventoryUI.isOpen())return;
  try{await renderer.domElement.requestPointerLock();}
  catch{captureFailed();}
}
$('play').onclick=leaveSpectator;
renderer.domElement.addEventListener('click',()=>{
  if(camping?.busy())return;
  if(locked&&camping?.active())camping.place();else lockPointer();
});
document.addEventListener('pointerlockchange',()=>{
  locked=document.pointerLockElement===renderer.domElement;keys.clear();
  if(inventoryUI.isOpen()&&locked){document.exitPointerLock();locked=false;}
  $('start').hidden=locked||inventoryUI.isOpen();$('crosshair').hidden=!locked;
  if(!locked&&ready){$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';refreshModeMenu();}
});
document.addEventListener('pointerlockerror',captureFailed);
document.addEventListener('mousemove',event=>{
  if(!locked)return;
  yaw-=event.movementX*.002;pitch=THREE.MathUtils.clamp(pitch-event.movementY*.002,-1.2,1.2);
});
window.addEventListener('keydown',event=>{
  if(event.code==='KeyE'&&ready&&!spectating&&!event.repeat){
    event.preventDefault();
    if(inventoryUI.isOpen())inventoryUI.close();
    else inventoryUI.open();
    return;
  }
  if(inventoryUI.isOpen()){
    if(event.code==='Escape'){event.preventDefault();inventoryUI.close();}
    return;
  }
  if(event.code==='Escape'){camping?.cancel();release();return;}
  if(!locked)return;
  if(spectating&&event.code==='KeyT'){event.preventDefault();release();$('destination').focus();return;}
  if(!spectating&&event.code==='KeyF'&&!event.repeat){event.preventDefault();if(!tentInterior?.active()&&!camping?.active()&&!camping?.busy()&&foxDens?.interact())return;tentInterior?.interact();return;}
  if(event.code==='KeyR'&&camping?.active()&&!event.repeat){event.preventDefault();camping.rotate();return;}
  if(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','ShiftLeft','ShiftRight','KeyC',...(spectating?['Space']:[])].includes(event.code)){event.preventDefault();keys.add(event.code);}
});
window.addEventListener('keyup',event=>keys.delete(event.code));
function release(){
  keys.clear();locked=false;
  if(ready){$('start').hidden=inventoryUI.isOpen();$('crosshair').hidden=true;$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';refreshModeMenu();}
  if(document.pointerLockElement===renderer.domElement)document.exitPointerLock();
}
window.addEventListener('blur',release);
document.addEventListener('visibilitychange',()=>{if(document.hidden)release();});
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
const footPoint=new THREE.Vector3();
function groundAnimal(a){
  if(!a.ground||!['penguin','fox','bear'].includes(a.type))return;
  a.root.updateMatrixWorld(true);
  if(!a.groundResolved){const ray=new THREE.Raycaster(new THREE.Vector3(a.position[0],100000,a.position[2]),new THREE.Vector3(0,-1,0));const hit=ray.intersectObjects(terrainMeshes,false)[0];if(hit){a.ground={height:hit.point.y,normal:hit.face.normal.toArray()};}a.groundResolved=true;} const n=a.ground.normal;
  if(n[1]<.1)return;
  let lift=-Infinity;
  // Use the posed skin vertices, not the GLB origin or a stale rest-pose box.
  // The terrain is planar at animal scale; its hit normal also handles slopes.
  a.root.traverseVisible(mesh=>{
    if(!mesh.isMesh||/icosphere/i.test(mesh.name))return;
    if(mesh.isSkinnedMesh)mesh.skeleton.update();
    for(let i=0;i<mesh.geometry.attributes.position.count;i++){
      mesh.getVertexPosition(i,footPoint).applyMatrix4(mesh.matrixWorld);
      const ground=a.ground.height-(n[0]*(footPoint.x-a.position[0])+n[2]*(footPoint.z-a.position[2]))/n[1];
      lift=Math.max(lift,ground+.015-footPoint.y);
    }
  });
  if(Number.isFinite(lift)&&lift>0){a.root.position.y+=lift;a.root.updateMatrixWorld(true);}
}

async function loadTerrain(entry){const response=await fetch('/viewer/data/'+entry.file);if(!response.ok)throw new Error(`Terrain ${entry.file}: HTTP ${response.status}`);const buffer=await response.arrayBuffer(),n=entry.vertexCount*3;const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,0,n),3));geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(buffer,n*4,n),3));geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(buffer,n*8,n),3));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,n*12,entry.indexCount),1));reshapeTerrain(geometry);surface.add(geometry.attributes.position.array, geometry.index.array);geometry.computeBoundingBox();const material=createTerrainMaterial(THREE);for(const mesh of createTerrainTiles(THREE,geometry,material)){scene.add(mesh);mesh.updateMatrixWorld(true);terrainMeshes.push(mesh);}}

async function init(){await loadTentDoor();const response=await fetch('/viewer/data/world.json');if(!response.ok)throw new Error(`World manifest: HTTP ${response.status}`);const world=await response.json();reshapeManifest(world);const terrains=Array.isArray(world.terrain)?world.terrain:[world.terrain];for(let i=0;i<terrains.length;i++){if(!terrains[i])continue;$('status').textContent=`Loading terrain ${i+1} / ${terrains.length}…`;await loadTerrain(terrains[i]);} const anchor=world.actors.find(a=>a.type==='penguin'); const spawn=world.spawn??(anchor?[anchor.position[0]+8,anchor.position[1],anchor.position[2]+8]:[0,100,0]); if(Number.isFinite(world.viewYaw))yaw=world.viewYaw; if(Number.isFinite(world.viewPitch))pitch=THREE.MathUtils.clamp(world.viewPitch,-1.2,1.2); world.actors.unshift({id:'player',type:'human',asset:'/Human_Animated.glb',position:spawn,rotation:yaw,scale:1,clip:'Human_Idle'});const loader=new GLTFLoader(),assets=new Map();for(const [i,data] of world.actors.entries()){$('status').textContent=`Loading wildlife ${i+1} / ${world.actors.length}…`;if(!assets.has(data.asset))assets.set(data.asset,await loader.loadAsync(data.asset));const gltf=assets.get(data.asset),model=clone(gltf.scene);model.traverse(o=>{if(/icosphere/i.test(o.name))o.visible=false;});const root=new THREE.Group();root.add(model);root.position.fromArray(data.position);root.rotation.y=data.rotation||0;root.scale.setScalar(data.scale??1);scene.add(root);const a={...data,age:0,root,clips:gltf.animations,mixer:new THREE.AnimationMixer(model),origin:new THREE.Vector3().fromArray(data.position),target:data.target?new THREE.Vector3().fromArray(data.target):null};actors.push(a);const clip=THREE.AnimationClip.findByName(a.clips,data.clip)||a.clips[0];if(clip){a.mixer.clipAction(clip).play();a.clip=clip.name;a.mixer.update(0);}if(a.ground)groundAnimal(a);if(['cabin','village'].includes(a.type))cameraObstacles.push(new THREE.Box3().setFromObject(root));register(a);if(a.type==='human'){player=a;const h=surface.height(a.root.position.x,a.root.position.z);if(h!==null)a.root.position.y=h;}}
scene.updateMatrixWorld(true);
scene.matrixWorldAutoUpdate=false;
for(const a of actors){
  const box=new THREE.Box3().setFromObject(a.root);
  a.renderRadius=box.getSize(new THREE.Vector3()).length()*.5+box.getCenter(new THREE.Vector3()).distanceTo(a.root.position);
  a.animationElapsed=0;
}
updateFootprints=createFootprints(scene,surface,player,terrainMeshes);
camping=createCamping({scene,surface,inventory,getPlayer:()=>player,getYaw:()=>yaw,obstacles:cameraObstacles});
tentInterior=createTentInterior({world:scene,player,camera,camping,keys,getYaw:()=>yaw,setYaw:value=>{yaw=value;}});
setCampCollision(tentInterior.blocks);
const habitatResponse=await fetch('/viewer/data/waypoints.json');
if(!habitatResponse.ok)throw new Error(`Habitat locations: HTTP ${habitatResponse.status}`);
const habitats=await habitatResponse.json();
for(const point of habitats.waypoints){point.position=transformWorldPoint(point.position);point.id=`${worldSeed}:${point.id}`;const h=surface.height(point.position[0],point.position[2]);if(h!==null)point.position[1]=h;}
const habitatLocations=createHabitatDensity({scene,surface,waypoints:habitats.waypoints,spawn,seed:worldSeed});
foxDens=createFoxDens({camera,player,keys,locations:habitatLocations,getYaw:()=>yaw,setYaw:value=>{yaw=value;},getPitch:()=>pitch,setPitch:value=>{pitch=value;}});
teleportLocations=[{name:'Starting area',position:spawn},...habitatLocations,
  ...world.actors.filter(a=>a.type==='cabin'||a.type==='village').map((a,i)=>({name:`${a.type==='cabin'?'Cabin':'Village'} ${i+1}`,position:a.position}))];
teleportLocations.forEach((location,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=location.name||`${location.type==='fox_den'?'Fox den':'Penguin nest'} ${i}`;$('destination').append(option);});
waypointHUD=createWaypoints({camera,getPlayer:()=>spectating?{root:{position:spectatorPosition}}:player,waypoints:habitatLocations});
wildlifeStream=createWildlifeStream({scene,surface,actors,assets,definitions:world.actors,obstacles:cameraObstacles,seed:worldSeed});
ready=true;
player.inventory=inventory;
inventoryUI.setEnabled(true);
$('status').textContent=`New expedition · World ${worldSeed.toString(16).toUpperCase()}`;
$('world-seed').textContent=`World ${worldSeed.toString(16).toUpperCase()} · Reload starts a fresh world and backpack.`;
$('play').disabled=false;
$('spectate').disabled=false;
$('play').textContent='Enter world';
updateCamera();
}

const perf=document.createElement('div');perf.id='performance';perf.style.cssText='position:fixed;top:12px;right:14px;color:white;background:#07141eaa;padding:6px 9px;font:12px monospace;pointer-events:none';document.body.append(perf);
let samples=[],lastFrame=performance.now(),quality=1,qualityFrames=0;
const clock=new THREE.Clock();
function frame(){
  requestAnimationFrame(frame);
  const now=performance.now();samples.push(now-lastFrame);lastFrame=now;
  if(samples.length>=60){
    const average=samples.reduce((a,b)=>a+b,0)/samples.length;
    perf.textContent=`${Math.round(1000/average)} FPS`;
    perf.dataset.draws=renderer.info.render.calls;perf.dataset.triangles=renderer.info.render.triangles;
    perf.dataset.frameMs=average.toFixed(2);perf.dataset.scale=quality;
    // Prefer smooth controls on slower GPUs, keeping full resolution as the ceiling.
    if(ready&&locked&&qualityFrames++>0){
      const next=average>30?Math.max(.55,quality-.15):average<17?Math.min(1,quality+.05):quality;
      if(next!==quality){quality=next;renderer.setPixelRatio(Math.min(devicePixelRatio,1)*quality);qualityFrames=0;}
    }
    samples=[];
  }
  const dt=Math.min(clock.getDelta(),.05);
  if(ready&&foxDens?.active()){
    waypointHUD?.setVisible(false);foxDens.update(dt,locked&&!inventoryUI.isOpen());renderer.render(foxDens.scene(),camera);return;
  }
  if(ready&&spectating){
    foxDens?.hide();
    updateSpectator(dt);
    if(locked){wildlifeStream?.update(dt,spectatorPosition);updateWildlife(dt,spectatorPosition);}
    for(const a of actors){
      const distance=a.root.position.distanceTo(spectatorPosition);
      a.root.visible=a!==player&&distance<((a.type==='cabin'||a.type==='village')?6000:1000)+a.renderRadius;
      if(a.root.visible&&locked){if(a.clips.length)a.mixer.update(dt);a.root.updateMatrixWorld(true);}
    }
    waypointHUD?.setVisible(true);waypointHUD?.update({visible:locked});
    ocean.visible=camera.position.y>=0;renderer.render(scene,camera);return;
  }
  if(ready&&tentInterior?.active()){
    foxDens?.hide();
    waypointHUD?.setVisible(false);
    tentInterior.update(dt,locked);
    if(!tentInterior.inside())updateCamera();
    renderer.render(tentInterior.scene(),camera);return;
  }
  if(ready){
    camera.rotation.set(pitch,yaw+Math.PI,0,'YXZ');camera.updateMatrixWorld();
    if(locked)wildlifeStream?.update(dt,player.root.position);
    if(locked&&!camping?.busy())updateGame(dt,keys,camera);
    if(locked)camping?.beforeFrame();
    for(const a of actors){
      const distance=a.root.position.distanceTo(player.root.position);
      const scenery=a.type==='cabin'||a.type==='village';
      a.root.visible=a===player||distance<(scenery?6000:1000)+a.renderRadius;
      if(!a.root.visible)continue;
      if(locked&&a.clips.length){
        a.animationElapsed+=dt;
        if(a===player||distance<80||a.animationElapsed>=(distance<300?1/20:1/8)){
          a.mixer.update(a.animationElapsed);a.animationElapsed=0;
        }
      }
      if(locked&&!scenery)a.root.updateMatrixWorld(true);
    }
    if(locked){camping?.tick(dt);updateFootContact(player,dt);updateFootprints();}
    updateCamera();
    if(locked)camping?.update();
    tentInterior?.update(dt,locked);
    foxDens?.update(dt,locked&&!camping?.active()&&!camping?.busy());
    waypointHUD?.setVisible(true);
    waypointHUD?.update({visible:!inventoryUI.isOpen()});
  }
  ocean.visible=camera.position.y>=0;
  renderer.render(scene,camera);
}
camera.position.set(100,100,100);frame();
init().catch(error=>{$('status').textContent='The world could not load. Reload to retry.';$('error').textContent=error.message;console.error(error);});
