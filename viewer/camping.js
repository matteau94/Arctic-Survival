import { hudHint } from './cold.js';
import * as THREE from 'three';
import { startTentSetup } from './tent-setup.js';
import { createTentDoor } from './tent-door.js';

const tentScale={x:1.6,y:2,z:1.4};
const sizes={tent:[1.05*tentScale.x,1.35*tentScale.z],'sleeping-bag':[.36,1]};

// Small procedural meshes: no downloaded assets, textures, or Blender exports.
function campModel(id,preview=false){
  const group=new THREE.Group();
  const material=color=>new THREE.MeshStandardMaterial({color,roughness:.85,side:THREE.DoubleSide,transparent:preview,opacity:preview?.45:1,depthWrite:!preview});
  const fabric=material(id==='tent'?0xc87731:0x287e89),trim=material(0x253747);
  function box(w,h,d,x,y,z,mat){const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);mesh.position.set(x,y,z);group.add(mesh);return mesh;}
  if(id==='tent'){
    // Open-front A-frame: 3.36 m wide, 3.78 m deep, 3 m ridge height.
    // The central doorway has standing headroom for the climber.
    group.scale.set(tentScale.x,tentScale.y,tentScale.z);
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.Float32BufferAttribute([
      -1.05,0,-1.35, 0,1.5,-1.35, 0,1.5,1.35,
      -1.05,0,-1.35, 0,1.5,1.35, -1.05,0,1.35,
      0,1.5,-1.35, 1.05,0,-1.35, 1.05,0,1.35,
      0,1.5,-1.35, 1.05,0,1.35, 0,1.5,1.35,
      -1.05,0,-1.35, 1.05,0,-1.35, 0,1.5,-1.35,
    ],3));
    geometry.computeVertexNormals();group.add(new THREE.Mesh(geometry,fabric));
    const door=createTentDoor(preview);
    const doorMount=new THREE.Group();
    doorMount.scale.set(1/tentScale.x,1/tentScale.y,1/tentScale.z);
    doorMount.add(door);group.add(doorMount);
    box(2.1,.025,2.7,0,.015,0,trim);
    for(const z of [-1.35,1.35]){
      for(const sign of [-1,1]){
        const a=new THREE.Vector3(sign*1.05,0,z),b=new THREE.Vector3(0,1.5,z);
        const pole=new THREE.Mesh(new THREE.CylinderGeometry(.018,.018,a.distanceTo(b),6),trim);
        pole.position.copy(a).add(b).multiplyScalar(.5);
        pole.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),b.sub(a).normalize());group.add(pole);
      }
    }
  }else{
    box(.72,.16,2,0,.13,0,fabric);
    box(.60,.12,.32,0,.25,.73,trim);
    for(let i=0;i<7;i++)box(.73,.015,.018,0,.218,-.85+i*.23,trim);
    box(.018,.015,1.6,.33,.22,-.15,trim);
  }
  return group;
}

export function createCamping({scene,surface,inventory,getPlayer,getYaw,obstacles,canPlace=()=>true,getInterior=()=>null}){
  const placed=[];
  const tentListeners=new Set();
  const equippedTents=new Set(); // Updated only when a committed indoor bag is added.
  let ghost=null,item=null,rotation=0,candidate=null,valid=false,setup=null;
  const hint=document.createElement('div');
  hint.className='camping-hint';
  hint.hidden=true;hint.setAttribute('role','status');document.body.append(hint);
  function transform(mesh,p){
    mesh.position.set(p.x,p.y+.035,p.z);
    const normal=new THREE.Vector3(-p.slopeX,1,-p.slopeZ).normalize();
    const forward=new THREE.Vector3(Math.sin(p.yaw),0,Math.cos(p.yaw));
    forward.addScaledVector(normal,-forward.dot(normal)).normalize();
    const right=new THREE.Vector3().crossVectors(normal,forward).normalize();
    mesh.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right,normal,forward));
    mesh.updateMatrixWorld(true);
  }
  function add(p){
    const mesh=campModel(p.id);transform(mesh,p);
    if(p.tentIndex===undefined)scene.add(mesh);
    else{const interior=getInterior();if(interior?.tentIndex===p.tentIndex)interior.scene.add(mesh);}
    placed.push({data:p,mesh});
    if(p.id==='sleeping-bag'&&p.tentIndex!==undefined)equippedTents.add(p.tentIndex);
  }
  for(const p of inventory.snapshot().placements)add(p);
  function disposeGhost(){
    if(!ghost)return;
    ghost.removeFromParent();const materials=new Set();
    ghost.traverse(o=>{if(o.isMesh){o.geometry.dispose();materials.add(o.material);}});
    materials.forEach(m=>m.dispose());ghost=null;
  }
  function cancel(){if(setup){const previous=setup;setup=null;previous.cancel();}disposeGhost();item=null;candidate=null;hint.hidden=true;}
  function update(){
    if(!item)return;
    valid=false;candidate=null;
    if(!canPlace(item)){cancel();return;}
    const player=getPlayer();if(!player)return;
    const interior=getInterior();
    if(interior){
      if(item!=='sleeping-bag'){cancel();return;}
      const yaw=getYaw(),p={x:player.root.position.x+Math.sin(yaw)*1.8,y:0,z:player.root.position.z+Math.cos(yaw)*1.8,yaw:yaw+rotation,slopeX:0,slopeZ:0,tentIndex:interior.tentIndex};
      if(ghost.parent!==interior.scene)interior.scene.add(ghost);
      transform(ghost,p);
      const bounds=new THREE.Box3().setFromObject(ghost);
      // Keep the complete rotated model inside the walls and clear of the doorway.
      valid=bounds.min.x>=-3.4&&bounds.max.x<=3.4&&bounds.min.z>=-3.9&&bounds.max.z<=3.9;
      if(bounds.min.x<1.5&&bounds.max.x>-1.5&&bounds.max.z>1.9)valid=false;
      const playerPosition=player.root.position;
      if(bounds.min.x<playerPosition.x+.4&&bounds.max.x>playerPosition.x-.4&&bounds.min.z<playerPosition.z+.4&&bounds.max.z>playerPosition.z-.4)valid=false;
      for(const existing of placed)if(existing.data.tentIndex===p.tentIndex&&new THREE.Box3().setFromObject(existing.mesh).intersectsBox(bounds))valid=false;
      ghost.traverse(o=>{if(o.isMesh)o.material.color.set(valid?0x70e7b0:0xef6464);});
      candidate=p;
      hudHint(hint,'warm',`${valid?'Click · Place bag':'Clear floor needed'} · R ↻ · Esc × · Permanent`,`${valid?'Ready to place sleeping bag.':'Cannot place: clear floor needed away from walls, doorway, player and other equipment.'} Indoor bags restore warmth; bare tents only block cold. Placement is permanent. R rotates; Esc cancels.`);
      return;
    }
    const yaw=getYaw(),distance=item==='tent'?4.5:3.5;
    const x=player.root.position.x+Math.sin(yaw)*distance,z=player.root.position.z+Math.cos(yaw)*distance;
    const h=surface.height(x,z),hx=surface.height(x+.5,z),hz=surface.height(x,z+.5);
    valid=[h,hx,hz].every(v=>Number.isFinite(v)&&v>0);
    const p={x,y:h??0,z,yaw:yaw+rotation,slopeX:valid?(hx-h)*2:0,slopeZ:valid?(hz-h)*2:0};
    if(Math.hypot(p.slopeX,p.slopeZ)>.25)valid=false;
    const [w,d]=sizes[item],c=Math.cos(p.yaw),s=Math.sin(p.yaw);
    for(const u of [-w,0,w])for(const v of [-d,0,d]){
      const dx=u*c+v*s,dz=-u*s+v*c,height=surface.height(x+dx,z+dz);
      if(!Number.isFinite(height)||height<=0||Math.abs(height-(p.y+p.slopeX*dx+p.slopeZ*dz))>.12)valid=false;
    }
    transform(ghost,p);
    const bounds=new THREE.Box3().setFromObject(ghost);
    if(obstacles.some(b=>b.intersectsBox(bounds)))valid=false;
    for(const existing of placed){
      if(existing.data.tentIndex!==undefined)continue;
      // A sleeping bag may fit inside a tent; same-type items cannot overlap.
      const b=new THREE.Box3().setFromObject(existing.mesh);
      if(existing.data.id===item&&b.intersectsBox(bounds))valid=false;
      if(existing.data.id!==item&&b.intersectsBox(bounds)){
        const tent=item==='tent'?{data:p}:existing,bag=item==='sleeping-bag'?p:existing.data;
        const deltaX=bag.x-tent.data.x,deltaZ=bag.z-tent.data.z;
        const ct=Math.cos(tent.data.yaw),st=Math.sin(tent.data.yaw);
        const angle=bag.yaw-tent.data.yaw;
        const bw=.36*Math.abs(Math.cos(angle))+Math.abs(Math.sin(angle));
        const bd=.36*Math.abs(Math.sin(angle))+Math.abs(Math.cos(angle));
        if(Math.abs(deltaX*ct-deltaZ*st)+bw>sizes.tent[0]-.15||Math.abs(deltaX*st+deltaZ*ct)+bd>sizes.tent[1]-.10)valid=false;
      }
    }
    ghost.traverse(o=>{if(o.isMesh)o.material.color.set(valid?0x70e7b0:0xef6464);});
    candidate=p;
    hudHint(hint,item==='tent'?'tent':'warm',`${valid?'Click · Place':'Clear ground needed'} · R ↻ · Esc × · Permanent · Still exposed`,`${valid?'Ready to place.':'Cannot place: choose dry, clear, gently sloping ground.'} Bare tents only block cold; indoor sleeping bags restore warmth. Outdoor bags give no warmth. Placement is permanent. R rotates; Esc cancels. Setup, positioning and entry take time: remain exposed until inside.`);
  }
  return {
    tents:()=>placed.filter(p=>p.data.id==='tent'),
    subscribeTentPlaced(callback){
      tentListeners.add(callback);
      return ()=>tentListeners.delete(callback);
    },
    tentIndex:tent=>placed.indexOf(tent),
    hasIndoorBag:tentIndex=>equippedTents.has(tentIndex),
    showInterior(room,tentIndex){
      for(const entry of placed)if(entry.data.tentIndex!==undefined){room.add(entry.mesh);entry.mesh.visible=entry.data.tentIndex===tentIndex;}
    },
    begin(id){if(!sizes[id]||!canPlace(id))return;cancel();item=id;rotation=0;ghost=campModel(id,true);(getInterior()?.scene??scene).add(ghost);hint.hidden=false;update();},
    active:()=>Boolean(item),cancel,update,
    busy:()=>Boolean(setup),
    beforeFrame(){setup?.beforeFrame();},
    tick(dt){if(setup){const label=setup.tick(dt);if(setup&&label)hudHint(hint,'tent',`${label.split(' · ').slice(1).join(' · ')} · Still exposed`,`${label}. Remain exposed until inside.`);}},
    rotate(){rotation+=Math.PI/4;update();},
    place(){
      if(setup)return;
      update();if(!valid||!candidate)return;
      const id=item,p={...candidate};
      if(id==='tent'){
        const player=getPlayer(),start=player.root.position.clone();
        const direction=new THREE.Vector3(p.x-start.x,0,p.z-start.z).normalize();
        const end=new THREE.Vector3(p.x,0,p.z).addScaledVector(direction,-2.6);
        let previousHeight=surface.height(start.x,start.z);
        // Only animate a short approach when its entire route is traversable.
        for(let i=1;i<=20;i++){
          const x=THREE.MathUtils.lerp(start.x,end.x,i/20),z=THREE.MathUtils.lerp(start.z,end.z,i/20),h=surface.height(x,z);
          if(!Number.isFinite(h)||h<=0||Math.abs(h-previousHeight)>.2||obstacles.some(b=>x>b.min.x-.5&&x<b.max.x+.5&&z>b.min.z-.5&&z<b.max.z+.5)){
            hudHint(hint,'tent','Move closer · Clear approach needed','Move closer to a clear, gentle approach before setting up the tent.');return;
          }
          previousHeight=h;
        }
        disposeGhost();item=null;candidate=null;
        const tent=campModel(id);transform(tent,p);scene.add(tent);
        function removeTent(){scene.remove(tent);const materials=new Set();tent.traverse(o=>{if(o.isMesh){o.geometry.dispose();materials.add(o.material);}});materials.forEach(m=>m.dispose());}
        setup=startTentSetup({player,scene,surface,position:p,tent,
          onCancel:()=>{removeTent();hint.hidden=true;},
          onComplete:()=>{
            setup=null;const result=inventory.deploy(id,p);
            if(result.ok){
              const entry={data:{id,...p},mesh:tent};placed.push(entry);hint.hidden=true;
              for(const callback of tentListeners){
                try{callback(entry);}catch(error){console.error('Tent placement listener failed',error);}
              }
            }
            else{removeTent();hudHint(hint,'tent',result.message);}
          },
        });
        return;
      }
      const result=inventory.deploy(id,p);
      if(!result.ok){hudHint(hint,'tent',result.message);return;}
      add({id,...p});cancel();
    },
  };
}
