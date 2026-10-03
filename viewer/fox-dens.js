import * as THREE from 'three';

// Build only the occupied den; release its meshes when the player leaves.
export function createFoxDens({camera,player,keys,locations,getYaw,setYaw,getPitch,setPitch}){
  const dens=locations.filter(p=>p.type==='fox_den'&&Array.isArray(p.position)&&p.position.length===3&&p.position.every(Number.isFinite));
  const prompt=document.createElement('div');
  prompt.style.cssText='position:fixed;bottom:110px;left:50%;transform:translateX(-50%);padding:10px 18px;background:#17252de8;color:white;border-radius:8px;pointer-events:none';
  prompt.hidden=true;document.body.append(prompt);
  let room=null,cells=null,nearby=null,homeYaw=0,homePitch=0,denName='Fox den';
  const position=new THREE.Vector3(),direction=new THREE.Vector3(),move=new THREE.Vector3();
  const step=.65;
  function build(id){
    let seed=2166136261;for(const c of String(id))seed=Math.imul(seed^c.charCodeAt(0),16777619);
    const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;};
    room=new THREE.Scene();room.background=new THREE.Color('#161b20');room.fog=new THREE.Fog('#161b20',12,30);
    room.add(new THREE.HemisphereLight(0xa7b7c4,0x47382b,.9));
    const entranceLight=new THREE.PointLight(0xc6e6ff,35,18,1.5);entranceLight.position.set(0,1.8,1);room.add(entranceLight);
    const lamp=new THREE.PointLight(0xffddad,8,10,1.3);lamp.name='view-light';room.add(lamp);
    const earth=new THREE.MeshStandardMaterial({color:0x665749,roughness:1});
    const rock=new THREE.MeshStandardMaterial({color:0x3d4145,roughness:1});
    const bedding=new THREE.MeshStandardMaterial({color:0x827a66,roughness:1});
    const frost=new THREE.MeshStandardMaterial({color:0xb5ccd4,roughness:.8});
    const pebble=new THREE.IcosahedronGeometry(1,1),box=new THREE.BoxGeometry(1,1,1);
    // Collect lightweight transforms, then upload one draw batch per geometry/material.
    const batches=new Map();
    function mesh(geometry,material,x,y,z,sx,sy,sz){
      const key=geometry.uuid+material.uuid;
      if(!batches.has(key))batches.set(key,{geometry,material,items:[]});
      const m=new THREE.Object3D();m.position.set(x,y,z);m.scale.set(sx,sy,sz);batches.get(key).items.push(m);return m;
    }
    const chambers=[{x:0,z:-7-random()*2,r:2.3+random()*.5}];
    const paths=[{a:{x:0,z:1},b:chambers[0],r:1.1}];
    const count=2+Math.floor(random()*3);
    for(let i=0;i<count;i++){
      const parent=chambers[Math.floor(random()*chambers.length)];
      const side=i%2?1:-1,angle=side*(.6+random()*.7);
      const length=5+random()*3;
      const child={x:parent.x+Math.sin(angle)*length,z:parent.z-Math.cos(angle)*length,r:1.8+random()*.8};
      chambers.push(child);paths.push({a:parent,b:child,r:.95+random()*.25});
    }
    function distance(x,z,{a,b}){const dx=b.x-a.x,dz=b.z-a.z,t=THREE.MathUtils.clamp(((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz),0,1);return Math.hypot(x-a.x-t*dx,z-a.z-t*dz);}
    cells=new Set();
    const minX=Math.floor(Math.min(-2,...chambers.map(c=>c.x-c.r-1))/step);
    const maxX=Math.ceil(Math.max(2,...chambers.map(c=>c.x+c.r+1))/step);
    const minZ=Math.floor(Math.min(...chambers.map(c=>c.z-c.r-1))/step);
    for(let x=minX;x<=maxX;x++)for(let z=minZ;z<=3;z++){
      const wx=x*step,wz=z*step;
      if(chambers.some(c=>Math.hypot(wx-c.x,wz-c.z)<c.r)||paths.some(p=>distance(wx,wz,p)<p.r))cells.add(`${x},${z}`);
    }
    for(const key of cells){
      const [x,z]=key.split(',').map(Number),wx=x*step,wz=z*step;
      mesh(box,earth,wx,-.09,wz,step,.18,step);
      mesh(box,earth,wx,2.8,wz,step,.3,step);
      mesh(pebble,rock,wx,2.65+random()*.16,wz,.58,.35,.58);
      for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1]])if(!cells.has(`${x+dx},${z+dz}`)){
        mesh(box,earth,wx+dx*step*.5,1.25,wz+dz*step*.5,dx?.25:step,2.5,dz?.25:step);
        for(let j=0;j<3;j++)mesh(pebble,random()<.14?frost:rock,wx+dx*step*.7,.4+j*.8,wz+dz*step*.7,dx?.18:.4,.49,dz?.18:.4);
      }
    }
    for(const [index,c] of chambers.entries()){
      const nursery=index%3!==2;
      mesh(pebble,nursery?bedding:frost,c.x,.015,c.z,c.r*.55,.035,c.r*.5);
      for(let i=0;i<(nursery?38:12);i++){
        const a=random()*Math.PI*2,r=random()*c.r*.6;
        const straw=mesh(box,nursery?bedding:frost,c.x+Math.cos(a)*r,.055,c.z+Math.sin(a)*r,.025,.02,.3+random()*.4);straw.rotation.y=random()*Math.PI;
      }
      for(let i=0;i<7;i++){const a=random()*Math.PI*2;mesh(pebble,rock,c.x+Math.cos(a)*c.r*.75,.1,c.z+Math.sin(a)*c.r*.75,.12,.12,.2);}
      // Roots hang above head clearance; the walking plane stays unobstructed.
      for(let i=0;i<12;i++){
        const a=random()*Math.PI*2,r=random()*c.r*.8;
        const root=mesh(box,earth,c.x+Math.cos(a)*r,2.35,c.z+Math.sin(a)*r,.035,.3+random()*.25,.035);
        root.rotation.z=(random()-.5)*.6;
      }
    }
    mesh(box,frost,0,.015,.8,1.6,.025,1.1);
    // A luminous snow plug marks the same entrance used by the leave prompt.
    const daylight=new THREE.MeshBasicMaterial({color:0xcbe9ff});
    mesh(box,daylight,0,1.15,1.8,1.1,2.1,.03);
    for(const {geometry,material,items} of batches.values()){
      const batch=new THREE.InstancedMesh(geometry,material,items.length);
      items.forEach((item,i)=>{item.updateMatrix();batch.setMatrixAt(i,item.matrix);});
      batch.instanceMatrix.needsUpdate=true;batch.computeBoundingSphere();room.add(batch);
    }
    position.set(0,1.55,0);setYaw(Math.PI);setPitch?.(0);
  }
  function clear(){
    const geometries=new Set(),materials=new Set();room.traverse(o=>{if(o.isMesh){geometries.add(o.geometry);materials.add(o.material);if(o.isInstancedMesh)o.dispose();}});
    for(const g of geometries)g.dispose();for(const m of materials)m.dispose();room=null;cells=null;
  }
  function canMove(x,z){
    // Circle against missing grid squares, inflated for the visible wall lining.
    const radius=.36;
    for(let ix=Math.round((x-radius)/step);ix<=Math.round((x+radius)/step);ix++){
      for(let iz=Math.round((z-radius)/step);iz<=Math.round((z+radius)/step);iz++){
        if(cells.has(`${ix},${iz}`))continue;
        const dx=Math.max(Math.abs(x-ix*step)-step/2,0),dz=Math.max(Math.abs(z-iz*step)-step/2,0);
        if(dx*dx+dz*dz<radius*radius)return false;
      }
    }
    return true;
  }
  function refresh(){
    nearby=null;
    if(room){prompt.textContent=position.z>-.9?'F · Leave fox den':`${denName} · WASD to explore · Return to the snowy entrance to leave`;return;}
    let nearest=3.5;
    for(const den of dens){const [x,y,z]=den.position,distance=Math.hypot(player.root.position.x-x,player.root.position.z-z);if(distance<nearest&&Math.abs(player.root.position.y-y)<3){nearby=den;nearest=distance;}}
    prompt.textContent='F · Enter fox den';
  }
  return {
    active:()=>!!room,scene:()=>room,
    interact(){refresh();if(room){if(position.z<=-.9)return true;clear();setYaw(homeYaw);setPitch?.(homePitch);keys.clear();prompt.hidden=true;return true;}if(!nearby)return false;homeYaw=getYaw();homePitch=getPitch();denName=nearby.name||'Fox den';build(nearby.id??nearby.position.join(','));keys.clear();return true;},
    update(dt,running){
      refresh();prompt.hidden=!running||(!room&&!nearby);
      if(!room)return;
      if(running){
        const yaw=getYaw();move.set(0,0,0);
        const forward=Number(keys.has('KeyW')||keys.has('ArrowUp'))-Number(keys.has('KeyS')||keys.has('ArrowDown'));
        const right=Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'));
        move.set(Math.sin(yaw)*forward-Math.cos(yaw)*right,0,Math.cos(yaw)*forward+Math.sin(yaw)*right).normalize().multiplyScalar(Math.min(dt,.1)*1.8);
        const steps=Math.max(1,Math.ceil(move.length()/.08));move.divideScalar(steps);
        for(let i=0;i<steps;i++){
          if(canMove(position.x+move.x,position.z))position.x+=move.x;
          if(canMove(position.x,position.z+move.z))position.z+=move.z;
        }
      }
      direction.set(Math.sin(getYaw())*Math.cos(getPitch()),Math.sin(getPitch()),Math.cos(getYaw())*Math.cos(getPitch()));
      camera.position.copy(position);camera.lookAt(direction.add(position));camera.updateMatrixWorld();room.getObjectByName('view-light').position.copy(position);
    },
    hide(){prompt.hidden=true;},
  };
}
