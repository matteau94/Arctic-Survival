import * as THREE from 'three';
import { clone } from 'three/addons/utils/SkeletonUtils.js';
import { register, unregister } from './gameplay.js';

const TYPES=new Set(['fox','penguin','bear','fish','orca']);
const CELL=500,MAX_ACTIVE=120;
export function createWildlifeStream({scene,surface,actors,assets,definitions,obstacles,habitats=[],seed:worldSeed=0}){
  const templates=new Map();
  for(const data of definitions)if(TYPES.has(data.type)&&!templates.has(data.type))templates.set(data.type,data);
  const authored=definitions.filter(a=>TYPES.has(a.type));
  const habitatAnimals=[];
  const habitatBounds=scene.getObjectByName('habitat-density')?.children.map(root=>new THREE.Box3().setFromObject(root))||[];
  const occupied=[];
  const exclusionBounds=[...obstacles,...habitatBounds];
  function reserved(x,z,radius){
    return habitats.some(p=>Math.hypot(x-p.position[0],z-p.position[2])<24+radius)||
      authored.some(p=>Math.hypot(x-p.position[0],z-p.position[2])<radius+12)||
      exclusionBounds.some(b=>x+radius+6>b.min.x&&x-radius-6<b.max.x&&z+radius+6>b.min.z&&z-radius-6<b.max.z)||
      occupied.some(p=>Math.hypot(x-p.x,z-p.z)<radius+p.radius+4);
  }
  const radii=new Map();
  for(const [type,template] of templates){
    const asset=assets.get(template.asset);if(!asset)continue;
    const b=new THREE.Box3().setFromObject(asset.scene);
    const radius=Math.hypot(Math.max(Math.abs(b.min.x),Math.abs(b.max.x)),
      Math.max(Math.abs(b.min.z),Math.abs(b.max.z)))*Math.abs(template.scale??1)+2;
    if(Number.isFinite(radius))radii.set(type,radius);
  }
  for(const site of habitats.filter(p=>String(p.id).includes('__density_'))){
    const type=site.type==='fox_den'?'fox':'penguin',template=templates.get(type);
    if(!template)continue;
    // Radius about asset origin covers rotations and off-centre loaded geometry.
    const radius=radii.get(type);
    if(!Number.isFinite(radius)||radius>12)continue;
    let seed=worldSeed;
    for(const character of String(site.id))seed=Math.imul(seed^character.charCodeAt(0),16777619);
    const phase=(seed>>>0)/4294967296*Math.PI*2;
    for(let i=0;i<(type==='fox'?1:2);i++)for(let attempt=0;attempt<48;attempt++){
      const angle=phase+(attempt+i*17)*2.399963229728653;
      const distance=32+attempt*.5;
      const x=site.position[0]+Math.cos(angle)*distance,z=site.position[2]+Math.sin(angle)*distance;
      if(reserved(x,z,radius))continue;
      const h=surface.height(x,z);if(!Number.isFinite(h)||h<=2)continue;
      let safe=true;
      for(let dx=-radius;dx<=radius;dx+=radius)for(let dz=-radius;dz<=radius;dz+=radius){
        const floor=surface.height(x+dx,z+dz);
        if(!Number.isFinite(floor)||floor<=2||Math.abs(floor-h)>.35)safe=false;
      }
      if(!safe)continue;
      habitatAnimals.push({...template,id:`habitat:${site.id}:${i}`,position:[x,h,z],rotation:angle,ground:undefined});
      occupied.push({x,z,radius});break;
    }
  }
  const active=new Map(),cells=new Map();
  let elapsed=1,queue=[],lastCell='';
  function remove(a){
    unregister(a);a.mixer.stopAllAction();a.mixer.uncacheRoot(a.root.children[0]);
    // Skeletons belong to each clone; geometry, textures and materials are shared.
    a.root.traverse(o=>{if(o.isSkinnedMesh)o.skeleton.dispose();});
    a.root.removeFromParent();const index=actors.indexOf(a);if(index>=0)actors.splice(index,1);
  }
  for(const a of [...actors])if(TYPES.has(a.type))remove(a);
  function plan(cx,cz){
    let seed=Math.imul(cx,73856093)^Math.imul(cz,19349663)^83492791^worldSeed;
    const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)|0;return (seed>>>0)/4294967296;};
    const result=[];
    for(let i=0;i<4;i++){
      for(let attempt=0;attempt<12;attempt++){
        const x=(cx+random())*CELL,z=(cz+random())*CELL,h=surface.height(x,z);
        if(h===null||!Number.isFinite(h))continue;
        const hx=surface.height(x+3,z),hz=surface.height(x,z+3);
        if(hx===null||hz===null||Math.hypot(hx-h,hz-h)>1.8)continue;
        const water=h<-8;
        if(!water&&h<2)continue;
        const roll=random(),type=water?(roll<.9?'fish':'orca'):(roll<.5?'fox':roll<.92?'penguin':'bear');
        const template=templates.get(type);if(!template)continue;
        const y=water?Math.max(h+4,-12):h;
        if(type==='orca'&&h>-20)continue;
        const radius=radii.get(type);
        if(!Number.isFinite(radius)||reserved(x,z,radius))continue;
        result.push({...template,id:`stream:${cx}:${cz}:${i}`,position:[x,y,z],rotation:random()*Math.PI*2,ground:undefined});break;
      }
    }
    return result;
  }
  function add(data){
    const gltf=assets.get(data.asset);if(!gltf)return;
    const model=clone(gltf.scene);model.traverse(o=>{if(/icosphere/i.test(o.name))o.visible=false;});
    const root=new THREE.Group();root.add(model);root.position.fromArray(data.position);root.rotation.y=data.rotation||0;root.scale.setScalar(data.scale??1);
    const a={...data,root,clips:gltf.animations,mixer:new THREE.AnimationMixer(model),age:0,origin:root.position.clone(),target:null,animationElapsed:0};
    const clip=THREE.AnimationClip.findByName(a.clips,data.clip)||a.clips[0];
    if(clip){a.mixer.clipAction(clip).play();a.clip=clip.name;a.mixer.update(0);}
    root.updateMatrixWorld(true);
    root.traverse(o=>{if(o.isSkinnedMesh){o.skeleton.update();o.computeBoundingBox();}});
    const bounds=new THREE.Box3().setFromObject(root);
    if(!['fish','orca'].includes(data.type)){
      const floor=surface.height(root.position.x,root.position.z);
      if(floor!==null){root.position.y+=floor-bounds.min.y+.02;root.updateMatrixWorld(true);}
    }
    a.renderRadius=bounds.getSize(new THREE.Vector3()).length();
    scene.add(root);root.updateMatrixWorld(true);actors.push(a);register(a);active.set(data.id,a);
  }
  return {update(dt,focus){
    elapsed+=dt;
    const cx=Math.floor(focus.x/CELL),cz=Math.floor(focus.z/CELL),currentCell=`${cx},${cz}`;
    if(elapsed>=.4||currentCell!==lastCell){
      elapsed=0;lastCell=currentCell;const wanted=new Set();
      for(let x=cx-2;x<=cx+2;x++)for(let z=cz-2;z<=cz+2;z++){
        const key=`${x},${z}`;wanted.add(key);if(!cells.has(key))cells.set(key,plan(x,z));
      }
      for(const key of cells.keys())if(!wanted.has(key))cells.delete(key);
      const candidates=[...authored,...habitatAnimals,...[...cells.values()].flat()].filter(d=>Math.hypot(d.position[0]-focus.x,d.position[2]-focus.z)<1100);
      candidates.sort((a,b)=>Math.hypot(a.position[0]-focus.x,a.position[2]-focus.z)-Math.hypot(b.position[0]-focus.x,b.position[2]-focus.z));
      const selected=candidates.slice(0,MAX_ACTIVE),ids=new Set(selected.map(d=>d.id));
      for(const [id,a] of active)if(!ids.has(id)){remove(a);active.delete(id);}
      queue=selected.filter(d=>!active.has(d.id));
    }
    // Spread expensive skeleton cloning over frames.
    for(let i=0;i<2&&queue.length;i++){const data=queue.shift();if(!active.has(data.id)&&active.size<MAX_ACTIVE)add(data);}
  }};
}
