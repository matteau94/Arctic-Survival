import * as THREE from 'three';

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

export function createCamping({scene,surface,inventory,getPlayer,getYaw,obstacles}){
  const placed=[];
  let ghost=null,item=null,rotation=0,candidate=null,valid=false;
  const hint=document.createElement('div');
  hint.style.cssText='position:fixed;left:50%;top:80px;transform:translateX(-50%);max-width:90vw;padding:12px 18px;background:#081b29e8;color:white;border:1px solid #8cbdc7;border-radius:8px;text-align:center;pointer-events:none;z-index:1;font:14px system-ui';
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
  function add(p){const mesh=campModel(p.id);transform(mesh,p);scene.add(mesh);placed.push({data:p,mesh});}
  for(const p of inventory.snapshot().placements)add(p);
  function disposeGhost(){
    if(!ghost)return;
    scene.remove(ghost);const materials=new Set();
    ghost.traverse(o=>{if(o.isMesh){o.geometry.dispose();materials.add(o.material);}});
    materials.forEach(m=>m.dispose());ghost=null;
  }
  function cancel(){disposeGhost();item=null;candidate=null;hint.hidden=true;}
  function update(){
    if(!item)return;
    const player=getPlayer();if(!player)return;
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
    hint.textContent=`${item==='tent'?'Small tent':'Sleeping bag'} · ${valid?'Click to place':'Choose dry, clear, gently sloping ground'} · R rotate · Esc cancel`;
  }
  return {
    begin(id){if(!sizes[id])return;cancel();item=id;rotation=0;ghost=campModel(id,true);scene.add(ghost);hint.hidden=false;update();},
    active:()=>Boolean(item),cancel,update,
    rotate(){rotation+=Math.PI/4;update();},
    place(){
      update();if(!valid||!candidate)return;
      const id=item,p={...candidate};const result=inventory.deploy(id,p);
      if(!result.ok){hint.textContent=result.message;return;}
      add({id,...p});cancel();
    },
  };
}
