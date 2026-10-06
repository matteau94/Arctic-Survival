import { placeNearbySettlements } from './nearby-settlements.js';
import { createTreeStream } from './tree-stream.js';
import { setVegetationCollision } from './gameplay.js';
import * as THREE from 'three';
import { worldSeed, transformWorldPoint, reshapeTerrain, reshapeManifest } from './world-seed.js';
import { createTerrainTiles, createTerrainMaterial } from './terrain-render.js';
import { surface, register, updateGame, updateWildlife, updateFootContact, setCampCollision, setAnimalTaming, animalLineOfSight, addAnimalObstacles, setAnimalCampBounds } from './gameplay.js';
import { createAnimalTaming } from './animal-taming.js';
import { createAnimalPetting } from './animal-petting.js';
import { createCompanionRoom } from './companion-room.js';
import { createFootprints } from './footprints.js';
import { createAnimalTracks } from './animal-tracks.js';
import { createInventory } from './inventory.js';
import { createHeldFood } from './held-food.js';
import { createHeldAxe } from './held-axe.js';
import { createCold, renderControls } from './cold.js';
import { configureBears, resetBearThreats, updateBearContact } from './bear-threat.js';
import { createInventoryUI } from './inventory-ui.js';
import { createCamping } from './camping.js';
import { createTentInterior } from './tent-interior.js';
import { loadTentDoor } from './tent-door.js';
import { createWaypoints } from './waypoints.js';
import { createWildlifeStream } from './wildlife-stream.js';
import { createSurvivalCommands } from './survival-commands.js';
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
let player=null,ready=false,locked=false,yaw=0,pitch=-.18,updateFootprints=null,updateAnimalTracks=null,camping=null,tentInterior=null,waypointHUD=null;
let foxDens=null,wildlifeStream=null,heldFood=null,animalTaming=null;
let treeStream=null,heldAxe=null;
let animalPetting=null,companionRoom=null;
const typing=()=>!!document.activeElement?.closest('input,textarea,select,[contenteditable="true"],[contenteditable=""]');
const canTame=()=>ready&&locked&&!cold.dead()&&!spectating&&!player?.chopping&&!document.hidden&&document.hasFocus()&&!typing()&&!inventoryUI.isOpen()&&!commands.isOpen()&&!tentInterior?.transitioning()&&!foxDens?.active()&&!camping?.active()&&!camping?.busy();
const companionSight=(from,to)=>tentInterior?.inside()?tentInterior.canSee(from,to):animalLineOfSight(from,to);
let spectating=false;
let captureWanted=false;
const spectatorPosition=new THREE.Vector3();
const spectatorForward=new THREE.Vector3(),spectatorRight=new THREE.Vector3(),spectatorMove=new THREE.Vector3();
let survivalView=null,teleportLocations=[];
renderControls($('help'));
const cold=createCold({onDeath:()=>{
  animalPetting?.cancel();companionRoom?.leave();
  heldAxe?.cancel();
  heldFood?.stow();
  resetBearThreats();
  keys.clear();locked=false;captureWanted=false;
  inventoryUI.setEnabled(false);
  $('start').hidden=true;$('crosshair').hidden=true;
  $('play').disabled=true;$('spectate').disabled=true;$('teleport').disabled=true;
  if(document.pointerLockElement===renderer.domElement)document.exitPointerLock();
}});
function spectatorBlockReason(){
  if(!ready)return 'Spectator mode is available once the world has loaded.';
  if(tentInterior?.transitioning())return 'Resume the expedition to finish entering or leaving the tent before spectating.';
  if(camping?.busy())return 'Resume the expedition to finish tent setup before spectating.';
  return '';
}
function refreshModeMenu(){
  if(cold.dead())return;
  commands.setSurvival(!spectating);
  $('play').textContent=spectating?'Return to survival':'Resume expedition';
  $('spectate').textContent=spectating?'Resume spectator mode':'Enter spectator mode';
  $('spectator-tools').hidden=!spectating;
  const blocked=spectatorBlockReason();
  $('spectate').disabled=!!blocked;
  $('spectate').textContent=blocked||$('spectate').textContent;
  renderControls($('help'),spectating);
}
function enterSpectator(){
  if(cold.dead())return;
  resetBearThreats();
  cold.resetClock();
  if(spectatorBlockReason()){refreshModeMenu();return;}
  if(!spectating){
    animalPetting?.cancel();
    heldFood.stow();
    camping?.cancel();
    survivalView={yaw,pitch,cameraPosition:camera.position.clone(),cameraQuaternion:camera.quaternion.clone(),playerVisible:player.root.visible};
    const tentOrigin=tentInterior?.spectatorOrigin();
    spectatorPosition.copy(tentOrigin??(foxDens?.active()?player.root.position:camera.position));
    if(tentOrigin||foxDens?.active())spectatorPosition.y+=12;
    const direction=camera.getWorldDirection(new THREE.Vector3());
    yaw=Math.atan2(direction.x,direction.z);pitch=Math.asin(direction.y);
    spectating=true;keys.clear();inventoryUI.setEnabled(false);
    tentInterior?.hide();foxDens?.hide();
  }
  refreshModeMenu();lockPointer();
}
function leaveSpectator(){
  if(!ready||cold.dead())return;
  resetBearThreats();
  cold.resetClock();
  if(spectating){
    spectating=false;keys.clear();yaw=survivalView.yaw;pitch=survivalView.pitch;
    player.root.visible=survivalView.playerVisible;inventoryUI.setEnabled(true);
    if(tentInterior?.inside()||foxDens?.active()){
      camera.position.copy(survivalView.cameraPosition);camera.quaternion.copy(survivalView.cameraQuaternion);camera.updateMatrixWorld();
    }else updateCamera();
  }
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
  if(cold.dead())return;
  if(!spectating)return;
  const destination=teleportLocations[Number($('destination').value)];
  if(!destination)return;
  const [x,y,z]=destination.position;
  spectatorPosition.set(x,Math.max(y,surface.height(x,z+18)??y)+12,z+18);
  yaw=Math.PI;pitch=-.5;keys.clear();updateSpectator(0);lockPointer();
};
const inventory=createInventory({storage:null});
function canHoldFood(){
  return ready&&!cold.dead()&&!spectating&&!animalPetting?.active()&&!camping?.active()&&!camping?.busy()&&!tentInterior?.transitioning()&&!foxDens?.active();
}
heldFood=createHeldFood({inventory,getPlayer:()=>player,canHold:canHoldFood});
const canHoldAxe=()=>canHoldFood()&&!tentInterior?.active();
const canChop=()=>canHoldAxe()&&locked&&!document.hidden&&document.hasFocus()&&!typing()&&!inventoryUI.isOpen()&&!commands.isOpen();
heldAxe=createHeldAxe({inventory,getPlayer:()=>player,getTrees:()=>treeStream,camera,canEquip:canHoldAxe,allowed:canChop});
function canPlaceCamp(id){
  return !cold.dead()&&!spectating&&!foxDens?.active()&&(!tentInterior?.active()||(id==='sleeping-bag'&&!!tentInterior.placementContext()));
}
const inventoryUI=createInventoryUI({inventory,heldFood,heldAxe,canHold:canHoldFood,canPlace:canPlaceCamp,onOpen:()=>{
  if(cold.dead())return;
  camping?.cancel();
  release();$('start').hidden=true;
},onClose:()=>{
  release();$('play').focus();
},onPlace:id=>{
  if(!canPlaceCamp(id))return;
  camping?.begin(id);
  if(camping?.active()||camping?.busy())heldFood.stow();
  lockPointer();
}});
inventoryUI.setEnabled(false);
const commands=createSurvivalCommands({
  menu:$('start').querySelector('.panel'),
  available:()=>ready&&!cold.dead()&&!spectating&&!inventoryUI.isOpen()&&!tentInterior?.active()&&!foxDens?.active()&&!camping?.active()&&!camping?.busy(),
  pause:()=>{inventoryUI.setEnabled(false);release();$('start').hidden=true;},
  onClose:()=>{release();inventoryUI.setEnabled(ready&&!cold.dead()&&!spectating);$('play').focus();},
  execute:executeSurvivalCommand,
});
function commandBlockReason(){
  if(!commands.isEnabled()||!commands.isOpen()||!ready||cold.dead()||spectating||inventoryUI.isOpen())return 'Commands are available only in enabled, living survival mode.';
  if(tentInterior?.active()||foxDens?.active())return 'Leave the tent or den and finish any shelter transition first.';
  if(camping?.active()||camping?.busy())return 'Finish or cancel placement and tent setup first.';
  return '';
}
function commandGroundValidator(){
  // Snapshot only on submission. Include destination-height camp bounds and
  // full model bounds rather than the player's current-height collision helper.
  const boxes=[...cameraObstacles,...camping.outdoorBounds()];
  for(const root of scene.getObjectByName('habitat-density')?.children||[])boxes.push(new THREE.Box3().setFromObject(root));
  for(const a of actors)if(a!==player&&['fox','penguin','bear','fish','orca'].includes(a.type))boxes.push(new THREE.Box3().setFromObject(a.root));
  return (x,z,radius=1)=>{
    const y=surface.height(x,z);
    if(!Number.isFinite(y)||y<=2)return null;
    const bounds=new THREE.Box3(new THREE.Vector3(x-radius,y-.5,z-radius),new THREE.Vector3(x+radius,y+Math.max(3,2*radius),z+radius));
    if(boxes.some(box=>box.intersectsBox(bounds)))return null;
    if(treeStream?.overlaps(bounds))return null;
    if(wildlifeStream?.summonOverlaps(x,z,radius))return null;
    const steps=Math.max(2,Math.ceil(radius*2));
    for(let ix=0;ix<=steps;ix++)for(let iz=0;iz<=steps;iz++){
      const h=surface.height(x-radius+2*radius*ix/steps,z-radius+2*radius*iz/steps);
      if(!Number.isFinite(h)||h<=2||Math.abs(h-y)>.35)return null;
    }
    return y;
  };
}
function executeSurvivalCommand(command,args){
  const blocked=commandBlockReason();if(blocked)return blocked;
  const safeGround=commandGroundValidator();
  const deferredBefore=treeStream?.stats.deferredQueries??0;
  const loadingMessage='Area is still loading. Wait a moment and retry the command.';
  if(command==='summon'){
    const result=wildlifeStream.summon(args,player.root.position,yaw,(x,z,radius)=>
      Math.hypot(x-player.root.position.x,z-player.root.position.z)<radius+10?null:safeGround(x,z,radius));
    return !result.startsWith('Queued ')&&(treeStream?.stats.deferredQueries??0)>deferredBefore?loadingMessage:result;
  }
  if(command!=='tp'||args.length!==2||!args.every(Number.isFinite))return 'Syntax: /tp x z';
  const [x,z]=args,y=safeGround(x,z);
  if(y===null)return (treeStream?.stats.deferredQueries??0)>deferredBefore?loadingMessage:'Unsafe destination: outside terrain, water, steep ground, or an obstacle/animal. Use /tp x z on clear dry ground.';
  keys.clear();resetBearThreats();cold.resetClock();
  player.root.position.set(x,y,z);player.root.rotation.y=yaw;
  player.origin.copy(player.root.position);player.home.copy(player.root.position);player.destination.copy(player.root.position);
  player.target=null;player.turnStepTime=0;player.groundCorrection=0;player.animationElapsed=0;
  camera.rotation.set(pitch,yaw+Math.PI,0,'YXZ');camera.updateMatrixWorld();
  updateGame(0,keys,camera);player.root.updateMatrixWorld(true);
  updateFootprints.reset();updateAnimalTracks.reset();wildlifeStream.refresh();animalTaming?.invalidate();updateCamera();
  return `Teleported to ${x.toFixed(2)}, ${y.toFixed(2)}, ${z.toFixed(2)} (ground). Camps and inventory preserved. Resume to continue.`;
}
const aim=new THREE.Vector3(),look=new THREE.Vector3(),offset=new THREE.Vector3(),cameraProbe=new THREE.Vector3();
const cameraRay=new THREE.Raycaster();
function updateCamera(){
  if(!player)return;
  aim.copy(player.root.position);aim.y+=keys.has('KeyC')?1.05:1.5;
  look.set(Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),Math.cos(yaw)*Math.cos(pitch));
  offset.copy(look).multiplyScalar(-1);
  cameraRay.set(aim,offset);cameraRay.far=4.5;
  let distance=4.5;
  if(treeStream){const hit=treeStream.rayDistance(cameraRay.ray,distance,.2);if(hit<distance)distance=Math.max(.15,hit-.2);}
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
  const wanted=captureWanted;captureWanted=false;
  if(!wanted)return;
  release();
  if(!ready||cold.dead())return;
  $('status').textContent='Mouse capture was blocked. Try again, or open the game in desktop Chrome or Edge if this embedded preview blocks capture.';
  refreshModeMenu();
  $(spectating?'spectate':'play').textContent='Retry mouse capture';
}
async function lockPointer(){
  if(cold.dead())return;
  if(!ready||inventoryUI.isOpen()||commands.isOpen())return;
  if(locked)return;
  captureWanted=true;
  try{await renderer.domElement.requestPointerLock();}
  catch{captureFailed();}
}
$('play').onclick=leaveSpectator;
renderer.domElement.addEventListener('click',()=>{
  if(commands.isOpen())return;
  if(cold.dead())return;
  if(camping?.busy())return;
  if(locked&&camping?.active())camping.place();
  else if(locked&&inventory.heldId()==='handaxe')heldAxe.swing();
  else lockPointer();
});
document.addEventListener('pointerlockchange',()=>{
  resetBearThreats();
  cold.resetClock();
  if(cold.dead()){
    locked=false;captureWanted=false;keys.clear();
    if(document.pointerLockElement===renderer.domElement)document.exitPointerLock();
    return;
  }
  locked=document.pointerLockElement===renderer.domElement;keys.clear();
  if(!locked){animalPetting?.cancel();heldAxe?.cancel();}
  if((!captureWanted||inventoryUI.isOpen()||commands.isOpen())&&locked){document.exitPointerLock();locked=false;}
  if(!locked)captureWanted=false;
  if(commands.isOpen())commands.focus();
  $('start').hidden=locked||inventoryUI.isOpen()||commands.isOpen();$('crosshair').hidden=true;
  if(!locked&&ready){$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';refreshModeMenu();}
});
document.addEventListener('pointerlockerror',captureFailed);
document.addEventListener('mousemove',event=>{
  if(cold.dead())return;
  if(!locked)return;
  if(animalPetting?.active())return;
  yaw-=event.movementX*.002;pitch=THREE.MathUtils.clamp(pitch-event.movementY*.002,-1.2,1.2);
});
window.addEventListener('keydown',event=>{
  if(typing())return;
  if(commands.isOpen())return;
  if(cold.dead())return;
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
  if(!spectating&&event.code==='KeyP'&&!event.repeat){event.preventDefault();animalTaming?.pet();return;}
  if(!spectating&&event.code==='KeyG'&&!event.repeat){event.preventDefault();animalTaming?.toggleFollow();return;}
  if(!spectating&&event.code==='KeyF'&&!event.repeat){
    event.preventDefault();
    if(camping?.active()||camping?.busy())return;
    animalPetting?.cancel();
    heldAxe?.cancel();
    if(!tentInterior?.active()&&foxDens?.interact()){heldFood.stow();return;}
    if(tentInterior?.transitioning()||tentInterior?.canInteract()){tentInterior.interact();return;}
    animalTaming?.interact();return;
  }
  if(event.code==='KeyR'&&camping?.active()&&!event.repeat){event.preventDefault();camping.rotate();return;}
  if(animalPetting?.active())return;
  if(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','ShiftLeft','ShiftRight','KeyC',...(spectating?['Space']:[])].includes(event.code)){event.preventDefault();keys.add(event.code);}
});
window.addEventListener('keyup',event=>keys.delete(event.code));
function release(){
  animalPetting?.cancel();
  heldAxe?.cancel();
  captureWanted=false;
  resetBearThreats();
  cold.resetClock();
  keys.clear();locked=false;
  if(cold.dead())return;
  if(ready){$('start').hidden=inventoryUI.isOpen()||commands.isOpen();$('crosshair').hidden=true;$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';refreshModeMenu();}
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

async function loadTerrain(entry){const response=await fetch('/viewer/data/'+entry.file);if(!response.ok)throw new Error(`Terrain ${entry.file}: HTTP ${response.status}`);const buffer=await response.arrayBuffer(),n=entry.vertexCount*3;const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,0,n),3));geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(buffer,n*4,n),3));geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(buffer,n*8,n),3));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,n*12,entry.indexCount),1));reshapeTerrain(geometry);surface.add(geometry.attributes.position.array, geometry.index.array, geometry.attributes.color.array);geometry.computeBoundingBox();const material=createTerrainMaterial(THREE);for(const mesh of createTerrainTiles(THREE,geometry,material)){scene.add(mesh);mesh.updateMatrixWorld(true);terrainMeshes.push(mesh);}}

// Fixed weights track completed work, not elapsed time or downloaded bytes.
function startupProgress(percent,stage){
  const value=ready?100:Math.min(99,Math.floor(percent));
  $('startup-progress').value=value;
  $('startup-progress').setAttribute('aria-valuetext',`${value}% — ${stage}`);
  $('startup-percent').textContent=`${value}%`;
  $('status').textContent=stage;
}
async function loadStartupAssets(definitions,onComplete){
  const loader=new GLTFLoader(),assets=new Map();
  const urls=[...new Set(definitions.map(data=>data.asset))];
  let next=0,completed=0,failed=false;
  async function worker(){
    while(!failed&&next<urls.length){
      const url=urls[next++];
      try{
        const gltf=await loader.loadAsync(url);
        if(failed)return;
        // Streaming consumes resolved GLTFs; never cache promises or failed loads.
        assets.set(url,gltf);
        onComplete(++completed,urls.length);
      }catch(error){
        failed=true;
        throw new Error(`Asset ${url}: ${error.message}`,{cause:error});
      }
    }
  }
  // Stop dequeuing on failure; Promise.all observes the remaining in-flight loads.
  await Promise.all(Array.from({length:Math.min(3,urls.length)},()=>worker()));
  return assets;
}

async function init(){startupProgress(0,'Preparing tent…');await loadTentDoor();startupProgress(5,'Loading world manifest…');const response=await fetch('/viewer/data/world.json');if(!response.ok)throw new Error(`World manifest: HTTP ${response.status}`);const world=await response.json();reshapeManifest(world);startupProgress(10,'Loading terrain…');const terrains=Array.isArray(world.terrain)?world.terrain:[world.terrain];for(let i=0;i<terrains.length;i++){if(!terrains[i])continue;await loadTerrain(terrains[i]);startupProgress(10+20*(i+1)/terrains.length,'Loading terrain…');} const anchor=world.actors.find(a=>a.type==='penguin'); const spawn=world.spawn??(anchor?[anchor.position[0]+8,anchor.position[1],anchor.position[2]+8]:[0,100,0]); if(Number.isFinite(world.viewYaw))yaw=world.viewYaw; if(Number.isFinite(world.viewPitch))pitch=THREE.MathUtils.clamp(world.viewPitch,-1.2,1.2); world.actors.unshift({id:'player',type:'human',asset:'/Human_Animated.glb',position:spawn,rotation:yaw,scale:1,clip:'Human_Idle'});startupProgress(30,'Loading model assets…');
const assets=await loadStartupAssets(world.actors,(done,total)=>startupProgress(30+40*done/total,'Loading model assets…'));
startupProgress(70,'Preparing actors…');
// Settlement clearance depends on posed wildlife bounds; preserve these actors.
for(const [i,data] of world.actors.entries()){
const gltf=assets.get(data.asset),model=clone(gltf.scene);model.traverse(o=>{if(/icosphere/i.test(o.name))o.visible=false;});const root=new THREE.Group();root.add(model);root.position.fromArray(data.position);root.rotation.y=data.rotation||0;root.scale.setScalar(data.scale??1);scene.add(root);const a={...data,age:0,root,clips:gltf.animations,mixer:new THREE.AnimationMixer(model),origin:new THREE.Vector3().fromArray(data.position),target:data.target?new THREE.Vector3().fromArray(data.target):null};actors.push(a);const clip=THREE.AnimationClip.findByName(a.clips,data.clip)||a.clips[0];if(clip){a.mixer.clipAction(clip).play();a.clip=clip.name;a.mixer.update(0);}if(a.ground)groundAnimal(a);if(!['cabin','village'].includes(a.type))register(a);if(a.type==='human'){player=a;const h=surface.height(a.root.position.x,a.root.position.z);if(h!==null)a.root.position.y=h;}
startupProgress(70+15*(i+1)/world.actors.length,'Preparing actors…');
}
startupProgress(85,'Placing settlements and preparing equipment…');
scene.updateMatrixWorld(true);
spawn[1]=player.root.position.y;
scene.userData.nearbySettlements=placeNearbySettlements({actors,definitions:world.actors,surface,spawn,seed:worldSeed});
for(const a of actors)if(['cabin','village'].includes(a.type)){cameraObstacles.push(new THREE.Box3().setFromObject(a.root));register(a);}
scene.matrixWorldAutoUpdate=false;
for(const a of actors){
  const box=new THREE.Box3().setFromObject(a.root);
  a.renderRadius=box.getSize(new THREE.Vector3()).length()*.5+box.getCenter(new THREE.Vector3()).distanceTo(a.root.position);
  a.animationElapsed=0;
}
updateFootprints=createFootprints(scene,surface,player,terrainMeshes);
updateAnimalTracks=createAnimalTracks(scene,surface,terrainMeshes,updateFootprints.sampleDepth);
camping=createCamping({scene,surface,inventory,getPlayer:()=>player,getYaw:()=>yaw,obstacles:cameraObstacles,canPlace:canPlaceCamp,getInterior:()=>tentInterior?.placementContext(),treeOverlap:bounds=>treeStream?.overlaps(bounds,10)??false});
companionRoom=createCompanionRoom({world:scene,player,getCompanions:()=>animalTaming?.liveTamed()??[],canSee:(from,to)=>animalLineOfSight(from,to,camping.tents().map(tent=>tent.mesh)),getBags:index=>camping.indoorBounds(index),
  findReturn:(animal,radius,outsidePlayer,index,measureFootprint)=>{
    const origin=animal.root.position,h=surface.height(origin.x,origin.z);
    if(!Number.isFinite(h)||h<=0)return null;
    const bounds=[...cameraObstacles,...camping.outdoorBounds()];
    for(const root of scene.getObjectByName('habitat-density')?.children??[])bounds.push(new THREE.Box3().setFromObject(root));
    const neighbors=actors.filter(a=>a!==animal&&a!==player&&!a.companionRoom&&['fox','penguin','bear'].includes(a.type))
      // Use the offset-aware bound with pose slack, not the startup diagonal.
      // Missing bounds stay candidates; precise clearance uses horizontal size.
      .filter(a=>!Number.isFinite(a.companionBroadphaseRadius)||a.companionBroadphaseRadius<=0||
        Math.hypot(a.root.position.x-origin.x,a.root.position.z-origin.z)<=3+radius+a.companionBroadphaseRadius)
      .map(a=>({p:a.root.position,radius:measureFootprint(a).radius}));
    const tents=camping.tents(),tent=tents.find(t=>camping.tentIndex(t)===index),local=new THREE.Vector3();
    const meshes=tents.map(t=>t.mesh),p=origin.clone();
    let relocationSightChecks=0;
    // Reserve the original footprint if safe, otherwise nearby ground on the
    // entrance side. Never ignore tent collision to manufacture a return slot.
    for(let ring=0;ring<=6;ring++)for(let step=0;step<(ring?16:1);step++){
      const angle=step*Math.PI/8;
      p.set(origin.x+Math.cos(angle)*ring*.5,origin.y,origin.z+Math.sin(angle)*ring*.5);
      if(Math.hypot(p.x-outsidePlayer.x,p.z-outsidePlayer.z)<radius+.5)continue;
      if(tent&&tent.mesh.worldToLocal(local.copy(p)).z<=1.43)continue;
      const floor=surface.height(p.x,p.z);
      if(!Number.isFinite(floor)||floor<=0||Math.abs(floor-h)>.35)continue;
      p.y=origin.y+floor-h;
      let safe=true;
      for(const dx of [-radius,0,radius])for(const dz of [-radius,0,radius]){
        const sample=surface.height(p.x+dx,p.z+dz);if(!Number.isFinite(sample)||sample<=0||Math.abs(sample-floor)>.35)safe=false;
      }
      if(!safe)continue;
      const footprint=new THREE.Box3(new THREE.Vector3(p.x-radius,floor+.1,p.z-radius),new THREE.Vector3(p.x+radius,p.y+2,p.z+radius));
      if(bounds.some(box=>box.intersectsBox(footprint)))continue;
      if(treeStream?.overlaps(footprint))continue;
      if(neighbors.some(a=>Math.hypot(a.p.x-p.x,a.p.z-p.z)<radius+a.radius))continue;
      if(companionRoom.blocksOutdoor(p.x,p.z,{renderRadius:radius}))continue;
      if(ring){
        if(relocationSightChecks>=8)return null;
        relocationSightChecks++;
        if(!animalLineOfSight(origin,p,meshes))continue;
      }
      return p.clone();
    }
    return null;
  }});
tentInterior=createTentInterior({world:scene,player,camera,camping,keys,getYaw:()=>yaw,setYaw:value=>{yaw=value;},companions:companionRoom,onTransition:()=>{animalPetting?.cancel();animalTaming?.invalidate();}});
setCampCollision(tentInterior.blocks);
configureBears({surface,obstacles:cameraObstacles,camping,
  treeOverlap:bounds=>treeStream?.overlaps(bounds)??false,
  treeRayDistance:(ray,length)=>treeStream?.rayDistance(ray,length)??length,
  isActive:()=>ready&&locked&&!cold.dead()&&!inventoryUI.isOpen()&&!document.hidden&&document.hasFocus()&&!spectating&&!tentInterior?.active()&&!foxDens?.active(),
  cancelSetup:()=>{if(camping.busy())camping.cancel();},
  onDeath:cause=>cold.endExpedition(cause)});
startupProgress(90,'Loading habitats…');
const habitatResponse=await fetch('/viewer/data/waypoints.json');
if(!habitatResponse.ok)throw new Error(`Habitat locations: HTTP ${habitatResponse.status}`);
const habitats=await habitatResponse.json();
for(const point of habitats.waypoints){point.position=transformWorldPoint(point.position);point.id=`${worldSeed}:${point.id}`;const h=surface.height(point.position[0],point.position[2]);if(h!==null)point.position[1]=h;}
const habitatLocations=createHabitatDensity({scene,surface,waypoints:habitats.waypoints,spawn,seed:worldSeed});
treeStream=createTreeStream({scene,surface,seed:worldSeed,spawn,habitats:habitatLocations,
  structures:cameraObstacles.slice(),authored:world.actors.filter(a=>a.type!=='human').map(a=>a.position),
  getCampBounds:()=>camping.outdoorBounds()});
setVegetationCollision(treeStream);
window.addEventListener('pagehide',event=>{if(!event.persisted){setVegetationCollision(null);treeStream.dispose();}},{once:false});
foxDens=createFoxDens({camera,player,keys,locations:habitatLocations,getYaw:()=>yaw,setYaw:value=>{yaw=value;},getPitch:()=>pitch,setPitch:value=>{pitch=value;}});
teleportLocations=[{name:'Starting area',position:spawn},...habitatLocations,
  ...world.actors.filter(a=>a.type==='cabin'||a.type==='village').map((a,i)=>({name:`${a.type==='cabin'?'Cabin':'Village'} ${i+1}`,position:a.position}))];
teleportLocations.forEach((location,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=location.name||`${location.type==='fox_den'?'Fox den':'Penguin nest'} ${i}`;$('destination').append(option);});
function tentWaypoint(tent){
  const index=camping.tentIndex(tent);
  // Front threshold in model coordinates; includes terrain slope and tent scale.
  tent.mesh.updateWorldMatrix(true,false);
  const entrance=tent.mesh.localToWorld(new THREE.Vector3(0,0,1.35));
  return {id:`${worldSeed}:tent:${index}`,type:'tent',name:`Tent ${index+1}`,position:entrance.toArray()};
}
waypointHUD=createWaypoints({
  camera,getPlayer:()=>spectating?{root:{position:spectatorPosition}}:player,
  waypoints:[...habitatLocations,...camping.tents().map(tentWaypoint)],
  subscribe:add=>camping.subscribeTentPlaced(tent=>add(tentWaypoint(tent))),
});
startupProgress(95,'Preparing wildlife streaming…');
addAnimalObstacles(scene.getObjectByName('habitat-density')?.children.map(root=>new THREE.Box3().setFromObject(root))??[]);
animalTaming=createAnimalTaming({inventory,getPlayer:()=>player,available:canTame,
  sameSpace:a=>companionRoom.sameSpace(a),worldPosition:a=>companionRoom.worldPosition(a),
  pet:a=>animalPetting.start(a),isPetting:()=>animalPetting?.active(),
  isCrouching:()=>keys.has('KeyC'),
  sensing:()=>ready&&locked&&!cold.dead()&&!inventoryUI.isOpen()&&!document.hidden&&document.hasFocus()&&!spectating&&!tentInterior?.transitioning()&&!foxDens?.active(),
  blocked:()=>(!tentInterior.inside()&&foxDens.canInteract())||tentInterior.canInteract(),canSee:companionSight});
animalTaming.blocksOutdoor=(x,z,a)=>companionRoom.blocksOutdoor(x,z,a);
animalPetting=createAnimalPetting({getPlayer:()=>player,allowed:()=>canTame()&&!inventory.heldId(),canSee:companionSight,onStart:()=>keys.clear()});
setAnimalTaming(animalTaming);
const refreshAnimalCampBounds=()=>{
  setAnimalCampBounds(camping.tents().map(tent=>new THREE.Box3().setFromObject(tent.mesh)));
  animalTaming.invalidate();
};
refreshAnimalCampBounds();camping.subscribeTentPlaced(refreshAnimalCampBounds);
wildlifeStream=createWildlifeStream({scene,surface,actors,assets,definitions:world.actors,obstacles:cameraObstacles,habitats:habitatLocations,seed:worldSeed,taming:animalTaming,treeOverlap:bounds=>treeStream?.overlaps(bounds)??false});
player.inventory=inventory;
inventoryUI.setEnabled(true);

$('world-seed').textContent=`World ${worldSeed.toString(16).toUpperCase()} · Reload starts a fresh world and backpack.`;
$('play').disabled=false;
$('spectate').disabled=false;
$('play').textContent='Enter world';
updateCamera();
ready=true;
startupProgress(100,`New expedition · World ${worldSeed.toString(16).toUpperCase()}`);
$('startup-loading').hidden=true;
}

const perf=document.createElement('div');perf.id='performance';perf.style.cssText='position:fixed;top:12px;right:14px;color:white;background:#07141eaa;padding:6px 9px;font:12px monospace;pointer-events:none';document.body.append(perf);
let samples=[],lastFrame=performance.now(),quality=1,qualityFrames=0;
const clock=new THREE.Clock();
function frame(){
  requestAnimationFrame(frame);
  if(cold.dead())return;
  // Sole budget reset/generation point, before any frame consumer or early
  // shelter/spectator branch. Paused command retries also make progress here.
  if(treeStream)treeStream.startFrame(spectating?spectatorPosition:
    (tentInterior?.spectatorOrigin()??player.root.position));
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
  animalPetting?.beforeFrame();
  heldAxe.beforeFrame(dt);
  heldFood.update({stow:camping?.active()||camping?.busy()||foxDens?.active()||(inventory.heldId()==='handaxe'&&tentInterior?.active()),hidden:spectating||tentInterior?.transitioning()});
  // Read actual enclosure, not the tent's entry/exit transition flag.
  // Cold shares movement's bounded active game time, not elapsed wall time.
  cold.update(now,dt,ready&&locked&&!inventoryUI.isOpen()&&!document.hidden&&document.hasFocus()&&!spectating,
    tentInterior?.inside()?(camping.hasIndoorBag(tentInterior.occupiedTentIndex())?'equipped-tent':'tent'):foxDens?.active()?'den':null,
    !ready?'Loading':spectating?'Spectator':'Paused');
  if(cold.dead())return;
  const predatorActive=ready&&locked&&!inventoryUI.isOpen()&&!document.hidden&&document.hasFocus()&&!spectating&&!tentInterior?.active()&&!foxDens?.active();
  treeStream?.updateFalls(predatorActive?dt:0);
  if(!predatorActive)resetBearThreats();
  if(ready&&!spectating&&(foxDens?.active()||tentInterior?.active()))updateAnimalTracks.reset();
  if(ready&&!spectating&&foxDens?.active()){
    animalTaming?.update(dt);
    waypointHUD?.setVisible(false);foxDens.update(dt,locked&&!inventoryUI.isOpen());renderer.render(foxDens.scene(),camera);return;
  }
  if(ready&&spectating){
    tentInterior?.hide();
    foxDens?.hide();
    const spectatorActive=locked&&!inventoryUI.isOpen()&&!document.hidden&&document.hasFocus();
    updateSpectator(spectatorActive?dt:0);
    animalTaming?.update(dt);
    if(spectatorActive){wildlifeStream?.update(dt,spectatorPosition);updateWildlife(dt,spectatorPosition);}
    for(const a of actors){
      if(a.companionRoom)continue;
      const distance=a.root.position.distanceTo(spectatorPosition);
      a.root.visible=a!==player&&distance<((a.type==='cabin'||a.type==='village')?6000:1000)+a.renderRadius;
      if(a.root.visible&&spectatorActive){if(a.clips.length)a.mixer.update(dt);a.root.updateMatrixWorld(true);}
    }
    updateAnimalTracks(dt,actors,spectatorPosition,spectatorActive);
    waypointHUD?.setVisible(true);waypointHUD?.update({visible:locked});
    ocean.visible=camera.position.y>=0;renderer.render(scene,camera);return;
  }
  if(ready&&tentInterior?.active()){
    animalTaming?.update(dt);
    foxDens?.hide();
    waypointHUD?.setVisible(false);
    tentInterior.update(dt,locked);
    animalPetting?.tick(locked?dt:0);
    if(locked)camping?.update();
    if(!tentInterior.inside())updateCamera();
    renderer.render(tentInterior.scene(),camera);return;
  }
  if(ready){
    camera.rotation.set(pitch,yaw+Math.PI,0,'YXZ');camera.updateMatrixWorld();
    if(locked)wildlifeStream?.update(dt,player.root.position);
    if(locked&&!camping?.busy())updateGame(dt,keys,camera);
    animalTaming?.update(dt);
    if(predatorActive)updateWildlife(dt,player.root.position,player.root.position);
    if(locked)camping?.beforeFrame();
    for(const a of actors){
      if(a.companionRoom)continue;
      const distance=a.root.position.distanceTo(player.root.position);
      const scenery=a.type==='cabin'||a.type==='village';
      a.root.visible=a===player||distance<(scenery?6000:1000)+a.renderRadius;
      if(!a.root.visible)continue;
      // Fox pose and translation share the wildlife clock, including pauses.
      if(locked&&a.clips.length&&(a.type!=='fox'||predatorActive)){
        a.animationElapsed+=dt;
        if(a===player||distance<80||a.animationElapsed>=(distance<300?1/20:1/8)){
          a.mixer.update(a.animationElapsed);a.animationElapsed=0;
        }
      }
      if(locked&&!scenery)a.root.updateMatrixWorld(true);
    }
    if(locked){camping?.tick(dt);updateFootContact(player,dt);updateFootprints();}
    animalPetting?.tick(locked?dt:0);
    if(predatorActive)updateBearContact(dt,player.root.position,yaw);
    updateAnimalTracks(dt,actors,player.root.position,predatorActive);
    if(cold.dead()){
      updateCamera();ocean.visible=camera.position.y>=0;
      renderer.render(scene,camera);return;
    }
    updateCamera();
    heldAxe.update(dt);
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
init().catch(error=>{$('startup-progress').setAttribute('aria-valuetext',`${$('startup-progress').value}% — Loading failed`);$('status').textContent='The world could not load. Reload to retry.';$('error').textContent=error.message;console.error(error);});
