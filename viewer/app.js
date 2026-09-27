import * as THREE from 'three';
import { createTerrainTiles, createTerrainMaterial } from './terrain-render.js';
import { surface, register, updateGame, updateFootContact } from './gameplay.js';
import { createFootprints } from './footprints.js';
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
let player=null,ready=false,locked=false,yaw=0,pitch=-.18,updateFootprints=null;
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
  if(!ready)return;
  try{await renderer.domElement.requestPointerLock();}
  catch{captureFailed();}
}
$('play').onclick=lockPointer;
renderer.domElement.addEventListener('click',lockPointer);
document.addEventListener('pointerlockchange',()=>{
  locked=document.pointerLockElement===renderer.domElement;keys.clear();
  $('start').hidden=locked;$('crosshair').hidden=!locked;
  if(!locked&&ready){$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';}
});
document.addEventListener('pointerlockerror',captureFailed);
document.addEventListener('mousemove',event=>{
  if(!locked)return;
  yaw-=event.movementX*.002;pitch=THREE.MathUtils.clamp(pitch-event.movementY*.002,-1.2,1.2);
});
window.addEventListener('keydown',event=>{
  if(event.code==='Escape'){release();return;}
  if(!locked)return;
  if(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','ShiftLeft','ShiftRight','KeyC'].includes(event.code)){event.preventDefault();keys.add(event.code);}
});
window.addEventListener('keyup',event=>keys.delete(event.code));
function release(){
  keys.clear();locked=false;
  if(ready){$('start').hidden=false;$('crosshair').hidden=true;$('status').textContent='Expedition paused';$('play').textContent='Resume expedition';}
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

async function loadTerrain(entry){const response=await fetch('/viewer/data/'+entry.file);if(!response.ok)throw new Error(`Terrain ${entry.file}: HTTP ${response.status}`);const buffer=await response.arrayBuffer(),n=entry.vertexCount*3;const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,0,n),3));geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(buffer,n*4,n),3));geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(buffer,n*8,n),3));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,n*12,entry.indexCount),1));surface.add(geometry.attributes.position.array, geometry.index.array);geometry.computeBoundingBox();const material=createTerrainMaterial(THREE);for(const mesh of createTerrainTiles(THREE,geometry,material)){scene.add(mesh);mesh.updateMatrixWorld(true);terrainMeshes.push(mesh);}}

async function init(){const response=await fetch('/viewer/data/world.json');if(!response.ok)throw new Error(`World manifest: HTTP ${response.status}`);const world=await response.json();const terrains=Array.isArray(world.terrain)?world.terrain:[world.terrain];for(let i=0;i<terrains.length;i++){if(!terrains[i])continue;$('status').textContent=`Loading terrain ${i+1} / ${terrains.length}…`;await loadTerrain(terrains[i]);} const anchor=world.actors.find(a=>a.type==='penguin'); const spawn=world.spawn??(anchor?[anchor.position[0]+8,anchor.position[1],anchor.position[2]+8]:[0,100,0]); if(Number.isFinite(world.viewYaw))yaw=world.viewYaw; if(Number.isFinite(world.viewPitch))pitch=THREE.MathUtils.clamp(world.viewPitch,-1.2,1.2); world.actors.unshift({id:'player',type:'human',asset:'/Human_Animated.glb',position:spawn,rotation:yaw,scale:1,clip:'Human_Idle'});const loader=new GLTFLoader(),assets=new Map();for(const [i,data] of world.actors.entries()){$('status').textContent=`Loading wildlife ${i+1} / ${world.actors.length}…`;if(!assets.has(data.asset))assets.set(data.asset,await loader.loadAsync(data.asset));const gltf=assets.get(data.asset),model=clone(gltf.scene);model.traverse(o=>{if(/icosphere/i.test(o.name))o.visible=false;});const root=new THREE.Group();root.add(model);root.position.fromArray(data.position);root.rotation.y=data.rotation||0;root.scale.setScalar(data.scale??1);scene.add(root);const a={...data,age:0,root,clips:gltf.animations,mixer:new THREE.AnimationMixer(model),origin:new THREE.Vector3().fromArray(data.position),target:data.target?new THREE.Vector3().fromArray(data.target):null};actors.push(a);const clip=THREE.AnimationClip.findByName(a.clips,data.clip)||a.clips[0];if(clip){a.mixer.clipAction(clip).play();a.clip=clip.name;a.mixer.update(0);}if(a.ground)groundAnimal(a);if(['cabin','village'].includes(a.type))cameraObstacles.push(new THREE.Box3().setFromObject(root));register(a);if(a.type==='human'){player=a;const h=surface.height(a.root.position.x,a.root.position.z);if(h!==null)a.root.position.y=h;}}
scene.updateMatrixWorld(true);
scene.matrixWorldAutoUpdate=false;
for(const a of actors){
  const box=new THREE.Box3().setFromObject(a.root);
  a.renderRadius=box.getSize(new THREE.Vector3()).length()*.5+box.getCenter(new THREE.Vector3()).distanceTo(a.root.position);
  a.animationElapsed=0;
}
updateFootprints=createFootprints(scene,surface,player,terrainMeshes);
ready=true;
$('status').textContent='Your expedition begins here.';
$('play').disabled=false;
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
  if(ready){
    camera.rotation.set(pitch,yaw+Math.PI,0,'YXZ');camera.updateMatrixWorld();
    if(locked)updateGame(dt,keys,camera);
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
    if(locked){updateFootContact(player,dt);updateFootprints();}
    updateCamera();
  }
  ocean.visible=camera.position.y>=0;
  renderer.render(scene,camera);
}
camera.position.set(100,100,100);frame();
init().catch(error=>{$('status').textContent='The world could not load. Reload to retry.';$('error').textContent=error.message;console.error(error);});
