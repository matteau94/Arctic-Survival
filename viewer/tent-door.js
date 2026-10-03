import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

let asset;
const mixers=new WeakMap();
export async function loadTentDoor(){
  try{
    asset=await new GLTFLoader().loadAsync('/viewer/data/tent-door.glb');
    if(!asset.animations.length)asset=null;
  }catch{asset=null;console.warn('Using the built-in tent door; Blender animation is unavailable.');}
}
export function createTentDoor(preview=false){
  if(!asset){
    const root=new THREE.Group();root.name='BlenderTentDoor';
    const panels=[];
    for(const side of [-1,1]){
      const geometry=new THREE.BufferGeometry();
      geometry.setAttribute('position',new THREE.Float32BufferAttribute([0,0,1.91,side*1.68,0,1.91,0,3,1.91],3));geometry.computeVertexNormals();
      const material=new THREE.MeshStandardMaterial({color:0xc87731,side:THREE.DoubleSide,roughness:1,transparent:preview,opacity:preview?.45:1});
      const panel=new THREE.Mesh(geometry,material);panel.userData.side=side;root.add(panel);panels.push(panel);
    }
    root.userData.fallbackPanels=panels;return root;
  }
  const root=asset.scene.clone(true);
  root.name='BlenderTentDoor';
  root.traverse(o=>{if(o.isMesh){
    o.geometry=o.geometry.clone();o.material=o.material.clone();
    o.material.side=THREE.DoubleSide;
    if(preview){o.material.transparent=true;o.material.opacity=.45;o.material.depthWrite=false;}
  }});
  const mixer=new THREE.AnimationMixer(root);
  for(const clip of asset.animations)mixer.clipAction(clip).setLoop(THREE.LoopOnce,1).play();
  mixer.setTime(0);mixers.set(root,mixer);
  return root;
}
export function animateTentDoor(root,progress,closing=false){
  if(root.userData.fallbackPanels){
    const amount=THREE.MathUtils.clamp(closing?1-progress:progress,0,1);
    for(const panel of root.userData.fallbackPanels){panel.scale.x=1-amount*.9;panel.position.x=panel.userData.side*1.5*amount;}
    root.updateMatrixWorld(true);return;
  }
  const mixer=mixers.get(root);if(!mixer)return;
  // Blender frames 1–90 open; 125–204 close. Export starts at frame 1.
  mixer.setTime((closing?124+79*progress:89*progress)/30);
  root.updateMatrixWorld(true);
}
