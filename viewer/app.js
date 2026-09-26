import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';
const $ = id => document.getElementById(id);
const scene = new THREE.Scene(); scene.background = new THREE.Color('#8aa9ba');
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .01, 2000000);
const renderer = new THREE.WebGLRenderer({antialias:true, logarithmicDepthBuffer:true});
renderer.setSize(innerWidth,innerHeight); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.15; document.body.prepend(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement); controls.enableDamping=true; controls.maxDistance=900000; controls.minDistance=.05;
scene.add(new THREE.HemisphereLight(0xdff5ff,0x485263,2.4)); const sun = new THREE.DirectionalLight(0xfff4df,2.8); sun.position.set(3000,8000,4000); scene.add(sun);
const ocean = new THREE.Mesh(new THREE.PlaneGeometry(1000000,1000000),new THREE.MeshStandardMaterial({color:0x247993,transparent:true,opacity:.4,roughness:.3,metalness:.2,depthWrite:false,side:THREE.DoubleSide})); ocean.rotation.x=-Math.PI/2; ocean.position.y=0;scene.add(ocean);
let following=true, waterOn=true, playing=true, selected=null, speed=25;
const terrainMeshes=[]; const actors=[], species=new Map(), keys=new Set(), terrainBounds=new THREE.Box3();
const info={penguin:'Coastal colonies · Snowfields and rocky shores',polar_bear:'Sea ice and coastal tundra · Arctic predator',polarbear:'Sea ice and coastal tundra · Arctic predator',bear:'Sea ice and coastal tundra · Arctic predator',seal:'Ice edges and coastal waters',fish:'Submerged habitat · Explore below the waterline',walrus:'Coastal shallows and sea ice',fox:'Tundra and rocky uplands'};
const pretty=s=>s.replace(/[_-]/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
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
function boundsFor(a){a.root.updateMatrixWorld(true);return new THREE.Box3().setFromObject(a.root);}
function focus(a){selected=a;following=true; const b=boundsFor(a), center=b.getCenter(new THREE.Vector3()), size=b.getSize(new THREE.Vector3()); const r=Math.max(size.length()*.8,.5); controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(r*.85,r*.45,r).applyAxisAngle(new THREE.Vector3(0,1,0),a.rotation||0));camera.near=Math.max(.005,Math.min(.1,r/1000));camera.updateProjectionMatrix();controls.update();speed=Math.max(2,r*.6);updateSpeed();$('animal').textContent=pretty(a.type)+' · '+(species.get(a.type).indexOf(a)+1)+' / '+species.get(a.type).length;$('habitat').textContent=info[a.type.toLowerCase()]||'Wildlife habitat · Local terrain';$('animation').replaceChildren();for(const clip of a.clips){const option=document.createElement('option');option.value=clip.name;option.textContent=clip.name;$('animation').append(option)}$('animation').value=a.clip||'';for(const button of $('species').children)button.classList.toggle('active',button.dataset.type===a.type);}
function setClip(a,name){const clip=THREE.AnimationClip.findByName(a.clips,name);if(!clip)return;a.mixer.stopAllAction();a.mixer.clipAction(clip).reset().play();a.clip=name;a.mixer.update(0);if(a.ground){a.root.position.y=a.position[1];groundAnimal(a);}}
function overview(){following=false;if(terrainBounds.isEmpty())return; const c=terrainBounds.getCenter(new THREE.Vector3()),s=terrainBounds.getSize(new THREE.Vector3()),r=Math.max(s.x,s.z,s.y,100);controls.target.copy(c);camera.position.copy(c).add(new THREE.Vector3(r*.55,r*.7,r*.7));camera.near=.1;camera.updateProjectionMatrix();speed=r/25;updateSpeed();}
function updateSpeed(){$('speed').textContent=`Travel ${speed.toFixed(speed<10?1:0)} m/s`;}
$('overview').onclick=overview;$('pause').onclick=()=>{playing=!playing;$('pause').textContent=playing?'Pause':'Play';};$('water').onclick=()=>{waterOn=!waterOn;$('water').textContent='Water: '+(waterOn?'on':'off');};$('next').onclick=()=>{if(!selected)return;const group=species.get(selected.type);focus(group[(group.indexOf(selected)+1)%group.length]);};$('animation').onchange=()=>{if(selected)setClip(selected,$('animation').value);};
window.addEventListener('keydown',e=>{if(e.target.matches('select,input,textarea'))return;keys.add(e.code);if(['KeyW','KeyA','KeyS','KeyD','Equal','Minus'].includes(e.code))e.preventDefault();if(e.code==='Equal'||e.code==='NumpadAdd')speed*=2;if(e.code==='Minus'||e.code==='NumpadSubtract')speed=Math.max(.1,speed/2);updateSpeed();});window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>keys.clear());window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
async function loadTerrain(entry){const response=await fetch('/viewer/data/'+entry.file);if(!response.ok)throw new Error(`Terrain ${entry.file}: HTTP ${response.status}`);const buffer=await response.arrayBuffer(),n=entry.vertexCount*3;const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,0,n),3));geometry.setAttribute('normal',new THREE.BufferAttribute(new Float32Array(buffer,n*4,n),3));geometry.setAttribute('color',new THREE.BufferAttribute(new Float32Array(buffer,n*8,n),3));geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,n*12,entry.indexCount),1));geometry.computeBoundingBox();terrainBounds.union(geometry.boundingBox);const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,side:THREE.DoubleSide}));mesh.name=entry.name||'Terrain';scene.add(mesh);mesh.updateMatrixWorld(true);terrainMeshes.push(mesh);}
async function init(){const response=await fetch('/viewer/data/world.json');if(!response.ok)throw new Error(`World manifest: HTTP ${response.status}`);const world=await response.json();const terrains=Array.isArray(world.terrain)?world.terrain:[world.terrain];for(let i=0;i<terrains.length;i++){if(!terrains[i])continue;$('status').textContent=`Loading terrain ${i+1} / ${terrains.length}…`;await loadTerrain(terrains[i]);} overview();const loader=new GLTFLoader(),assets=new Map();for(const [i,data] of world.actors.entries()){$('status').textContent=`Loading wildlife ${i+1} / ${world.actors.length}…`;if(!assets.has(data.asset))assets.set(data.asset,await loader.loadAsync(data.asset));const gltf=assets.get(data.asset),model=clone(gltf.scene);model.traverse(o=>{if(/icosphere/i.test(o.name))o.visible=false;});const root=new THREE.Group();root.add(model);root.position.fromArray(data.position);root.rotation.y=data.rotation||0;root.scale.setScalar(data.scale??1);scene.add(root);const a={...data,age:0,root,clips:gltf.animations,mixer:new THREE.AnimationMixer(model),origin:new THREE.Vector3().fromArray(data.position),target:data.target?new THREE.Vector3().fromArray(data.target):null};actors.push(a);if(!species.has(a.type))species.set(a.type,[]);species.get(a.type).push(a);setClip(a,data.clip||gltf.animations[0]?.name);}
for(const [type,group] of species){const button=document.createElement('button');button.dataset.type=type;button.textContent=`${pretty(type)} · ${group.length}`;button.onclick=()=>{const index=selected?.type===type?(group.indexOf(selected)+1)%group.length:0;focus(group[index]);};$('species').append(button);} $('status').textContent=`${actors.length} placed assets · ${terrains.filter(Boolean).length} terrain sections`;const first=actors.find(a=>/penguin/i.test(a.type))||actors[0];if(first)focus(first);else if(world.spawn){controls.target.fromArray(world.spawn);camera.position.copy(controls.target).add(new THREE.Vector3(20,15,20));}}
const clock=new THREE.Clock(),direction=new THREE.Vector3(),right=new THREE.Vector3(),motion=new THREE.Vector3();function frame(){requestAnimationFrame(frame);const dt=Math.min(clock.getDelta(),.05);if(playing){for(const a of actors){a.age+=dt;a.mixer.update(dt);if(a===selected&&a.ground)groundAnimal(a);if(a.target&&a.duration>0)a.root.position.lerpVectors(a.origin,a.target,Math.min(a.age/a.duration,1));}}camera.getWorldDirection(direction);direction.y=0;direction.normalize();right.crossVectors(direction,camera.up).normalize();motion.set(0,0,0);if(keys.has('KeyW'))motion.add(direction);if(keys.has('KeyS'))motion.sub(direction);if(keys.has('KeyD'))motion.add(right);if(keys.has('KeyA'))motion.sub(right);if(motion.lengthSq()){motion.normalize().multiplyScalar(speed*dt*(keys.has('ShiftLeft')||keys.has('ShiftRight')?5:1));camera.position.add(motion);controls.target.add(motion);}ocean.visible=waterOn&&camera.position.y>=0;controls.update();renderer.render(scene,camera);}camera.position.set(100,100,100);updateSpeed();frame();init().catch(error=>{$('status').textContent='Scene could not finish loading';$('error').textContent=error.message;console.error(error);});





