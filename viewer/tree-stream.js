import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CELL = 128, RING = 2, PER_CHUNK = 8;
const MAX_CHUNKS = (RING * 2 + 1) ** 2, MAX_TREES = MAX_CHUNKS * PER_CHUNK;
// Retain a full worst-case 64-frame FIFO round at four completed plans/frame.
const MAX_QUERY_CELLS = 256;
const MAX_PLANS_PER_FRAME = 4, MAX_PENDING = 128;
const MAX_HARVESTED = 512, MAX_DAMAGE = 64, MAX_FALLS = 4, HITS = 4;
const keyFor = (x, z) => `${x},${z}`;
function randomFor(seed, x, z) {
  let state = seed ^ Math.imul(x, 73856093) ^ Math.imul(z, 19349663) ^ 0x74726565;
  return () => { state = Math.imul(state, 1664525) + 1013904223 | 0; return (state >>> 0) / 4294967296; };
}
function segmentDistanceSq(x, z, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az;
  const t = Math.max(0, Math.min(1, ((x-ax)*dx + (z-az)*dz) / (dx*dx + dz*dz || 1)));
  return (x-ax-t*dx)**2 + (z-az-t*dz)**2;
}
function nearBox(x, z, box, margin) {
  return x > box.min.x-margin && x < box.max.x+margin && z > box.min.z-margin && z < box.max.z+margin;
}

// One small runtime mesh with colored bark, irregular branch tiers and snow tips.
// All chunks share its geometry/material; there are no textures or disk assets.
function evergreenGeometry() {
  const pieces = [];
  function piece(source, color, y) {
    const geometry = source.toNonIndexed(); source.dispose();
    geometry.translate(0, y, 0);
    const positions = geometry.attributes.position;
    const rgb = new THREE.Color(color), colors = [];
    for (let i = 0; i < positions.count; i++) colors.push(rgb.r, rgb.g, rgb.b);
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    pieces.push(geometry);
  }
  piece(new THREE.CylinderGeometry(.035, .18, 6.15, 7), 0x665345, 2.925);
  for (let tier = 0; tier < 7; tier++) {
    const radius = 1.15 * (1-tier/8), height = 1.65-tier*.09, y = 1.4+tier*.66;
    const branch = new THREE.ConeGeometry(radius, height, 9);
    const p = branch.attributes.position;
    for (let i=0; i<p.count; i++) {
      const angle = Math.atan2(p.getZ(i),p.getX(i));
      const ripple = 1 + .12*Math.sin(angle*3+tier*1.7);
      p.setXYZ(i,p.getX(i)*ripple,p.getY(i),p.getZ(i)*ripple);
    }
    branch.rotateY(tier*.83); branch.computeVertexNormals();
    piece(branch, tier%2 ? 0x334d43 : 0x284238, y);
    piece(new THREE.ConeGeometry(radius*.56, height*.53, 9), 0xc3d1d2, y+height*.25+.015);
  }
  const merged = mergeGeometries(pieces);
  for (const geometry of pieces) geometry.dispose();
  merged.computeBoundingSphere();
  return merged;
}

export function createTreeStream({ scene, surface, seed, spawn, habitats, structures,
  authored = [], getCampBounds = () => [] }) {
  spawn=spawn.slice();structures=structures.map(box=>box.clone());
  authored=authored.map(position=>position.slice());
  const geometry = evergreenGeometry();
  const material = new THREE.MeshStandardMaterial({ vertexColors:true, roughness:1 });
  const root = new THREE.Group(); root.name = 'runtime-conifers'; scene.add(root);
  const chunks = new Map(), queryCache = new Map(), pending = new Map(), matrix = new THREE.Object3D();
  // Expedition-local identities survive plan/cache eviction. Never evict harvests.
  const harvested = new Set(), damage = new Map(), falls = [];
  const fallAxis = new THREE.Vector3(), fallTurn = new THREE.Quaternion();
  const queryBox = new THREE.Box3(), rayBox = new THREE.Box3(), rayHit = new THREE.Vector3();
  const sites = habitats.map(p => p.position.slice());
  const routes = [...sites, ...structures.map(b => [
    (b.min.x+b.max.x)/2, 0, (b.min.z+b.max.z)/2
  ])];
  // Freeze placement inputs for this expedition. Later camps must fit the trees,
  // never change their seeded plans after eviction or on a different visit.
  const camps = getCampBounds().map(box=>box.clone());
  let queue = [], lastCell = '', disposed = false, harvesting = false;
  const stats = { chunks:0, trees:0, queued:0, candidates:0, rejected:0, evicted:0,
    get harvested(){return harvested.size;},maxHarvested:MAX_HARVESTED,
    get damaged(){return damage.size;},maxDamaged:MAX_DAMAGE,
    get falling(){return falls.length;},maxFalling:MAX_FALLS,
    queryCells:0, maxQueryCells:MAX_QUERY_CELLS,
    plansThisFrame:0, heightCallsThisFrame:0, maxPlansPerFrame:MAX_PLANS_PER_FRAME,
    maxHeightCallsPerFrame:MAX_PLANS_PER_FRAME*PER_CHUNK*9,
    pending:0, maxPending:MAX_PENDING, deferredQueries:0, queueFull:0,
    maxChunks:MAX_CHUNKS, maxTrees:MAX_TREES, candidatesPerChunk:PER_CHUNK, chunksPerFrame:1 };
  function reserved(x,z) {
    return Math.hypot(x-spawn[0],z-spawn[2]) < 40 ||
      sites.some(p => Math.hypot(x-p[0],z-p[2]) < 36) ||
      structures.some(b => nearBox(x,z,b,14)) || camps.some(b => nearBox(x,z,b,10)) ||
      authored.some(p => Math.hypot(x-p[0],z-p[2]) < 12) ||
      // There is no authored path network. Reserve straight approach corridors
      // to known entrances/settlements; this does not claim route walkability.
      routes.some(p => segmentDistanceSq(x,z,spawn[0],spawn[2],p[0],p[2]) < 10**2);
  }
  function plan(cx,cz) {
    const random = randomFor(seed,cx,cz), result = [];
    // Patchy stands with empty tundra chunks, stable across load order/eviction.
    if(random() < .28) return result;
    // Centers stay 22 m inside the cell; 18 m groves leave >=8 m across seams.
    const groves=Array.from({length:random()<.5?1:2},()=>({
      x:cx*CELL+22+random()*(CELL-44),z:cz*CELL+22+random()*(CELL-44)
    }));
    for (let i=0;i<PER_CHUNK;i++) {
      const grove=groves[i%groves.length], angle=random()*Math.PI*2, spread=5+random()*13;
      const x=grove.x+Math.cos(angle)*spread;
      const z=grove.z+Math.sin(angle)*spread;
      const width=.7+random()*.45, scale=.62+random()*.55, yaw=random()*Math.PI*2;
      stats.candidates++;
      // Maximum canopy pair is 2*1.15*1.12*1.15 < 3 m. No candidate retries.
      if(result.some(t=>(x-t.x)**2+(z-t.z)**2<3.2**2)){stats.rejected++;continue;}
      if(reserved(x,z)){stats.rejected++;continue;}
      const y=dryHeight(x,z);
      if(!Number.isFinite(y)||y<4||y>1400){stats.rejected++;continue;}
      // Nine dry samples cover roots and a 3 m shoreline/ice apron. Reject
      // unknown terrain, icy triangle corners, steep slopes and discontinuities.
      let valid=true;
      for(const dx of [-3,0,3])for(const dz of [-3,0,3]) {
        if(!dx&&!dz)continue;
        const h=dryHeight(x+dx,z+dz);
        if(!Number.isFinite(h)||h<4||Math.abs(h-y)>.28*Math.hypot(dx,dz))valid=false;
      }
      if(!valid){stats.rejected++;continue;}
      const heightScale=scale*(1-.3*Math.min(1,y/1400));
      const radius=.18*width;
      const box=new THREE.Box3(new THREE.Vector3(x-radius,y-.3,z-radius),
        new THREE.Vector3(x+radius,y+6*heightScale,z+radius));
      result.push({id:`${seed}:${cx},${cz}:${i}`,x,y,z,width,heightScale,yaw,radius,box});
    }
    return result;
  }
  function dryHeight(x,z) {
    stats.heightCallsThisFrame++;
    return surface.height(x,z,true);
  }
  function cached(cx,cz) {
    const key=keyFor(cx,cz), resident=chunks.get(key);
    if(resident)return resident.trees;
    if(queryCache.has(key)) {
      const trees=queryCache.get(key);queryCache.delete(key);queryCache.set(key,trees);return trees;
    }
    return null;
  }
  function generate(cx,cz) {
    const key=keyFor(cx,cz), existing=cached(cx,cz);
    if(existing!==null){pending.delete(key);return existing;}
    // Only startFrame calls this function. Charge before any terrain work.
    if(stats.plansThisFrame>=MAX_PLANS_PER_FRAME)return null;
    stats.plansThisFrame++;
    const trees=plan(cx,cz);
    if(queryCache.size>=MAX_QUERY_CELLS)queryCache.delete(queryCache.keys().next().value);
    queryCache.set(key,trees);pending.delete(key);
    stats.queryCells=queryCache.size;return trees;
  }
  function treesAt(cx,cz) {
    const trees=cached(cx,cz);
    if(trees!==null)return trees;
    const key=keyFor(cx,cz);
    if(!pending.has(key)) {
      if(pending.size<MAX_PENDING)pending.set(key,[cx,cz]);
      else stats.queueFull++;
    }
    stats.pending=pending.size;stats.deferredQueries++;
    return null; // Unknown must never be mistaken for a clear, empty cell.
  }
  function remove(key) {
    const chunk=chunks.get(key); if(!chunk)return;
    for(const t of chunk.trees)damage.delete(t.id);
    chunk.mesh?.removeFromParent(); chunk.mesh?.dispose();
    stats.trees-=chunk.trees.filter(t=>!harvested.has(t.id)).length; stats.evicted++; chunks.delete(key);
    stats.chunks=chunks.size;
  }
  function add(cx,cz) {
    if(chunks.size>=MAX_CHUNKS)return;
    const trees=cached(cx,cz);
    if(trees===null)return false;
    queryCache.delete(keyFor(cx,cz));stats.queryCells=queryCache.size;
    let mesh=null;
    if(trees.length) {
      mesh=new THREE.InstancedMesh(geometry,material,trees.length);
      mesh.position.set(cx*CELL,0,cz*CELL);
      for(const [i,t] of trees.entries()) {
        matrix.position.set(t.x-cx*CELL,t.y,t.z-cz*CELL);
        matrix.rotation.set(0,t.yaw,0);matrix.scale.set(t.width,t.heightScale,t.width);
        if(harvested.has(t.id))matrix.scale.setScalar(0);
        matrix.updateMatrix();
        mesh.setMatrixAt(i,matrix.matrix);
      }
      mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingBox();mesh.computeBoundingSphere();
      mesh.frustumCulled=true;root.add(mesh);root.updateMatrixWorld(true);
    }
    chunks.set(keyFor(cx,cz),{cx,cz,trees,mesh});
    stats.chunks=chunks.size;stats.trees+=trees.filter(t=>!harvested.has(t.id)).length;
    return true;
  }
  function startFrame(position) {
    if(disposed)return;
    stats.plansThisFrame=0;stats.heightCallsThisFrame=0;
    const cx=Math.floor(position.x/CELL),cz=Math.floor(position.z/CELL),key=keyFor(cx,cz);
    if(key!==lastCell) {
      lastCell=key;
      // Evict first, even after teleport: never temporarily exceed the hard cap.
      for(const [id,c] of chunks)if(Math.abs(c.cx-cx)>RING||Math.abs(c.cz-cz)>RING)remove(id);
      queue=[];
      for(let dx=-RING;dx<=RING;dx++)for(let dz=-RING;dz<=RING;dz++)
        if(!chunks.has(keyFor(cx+dx,cz+dz)))queue.push([cx+dx,cz+dz,dx*dx+dz*dz]);
      queue.sort((a,b)=>a[2]-b[2]);
    }
    // At most two priority plans: focus first, then the nearest render request.
    // This reserves at least two of the four slots for FIFO collision demand.
    generate(cx,cz);
    if(queue.length){
      const [x,z]=queue[0];generate(x,z);
      if(add(x,z))queue.shift();
    }
    // Duplicate requests never move to the back. New demand joins the tail;
    // even under continuous priority misses, accepted requests advance >=2/frame.
    for(const [key,[x,z]] of pending) {
      if(stats.plansThisFrame>=MAX_PLANS_PER_FRAME)break;
      pending.delete(key);generate(x,z);
    }
    stats.queued=queue.length;stats.pending=pending.size;
  }
  // Queries enqueue unloaded cells, never generate synchronously. Check all
  // cells to request a complete footprint together; unknown always fails closed.
  function overlaps(bounds, margin=0) {
    if(disposed)return false;
    const minX=Math.floor((bounds.min.x-margin-2)/CELL),maxX=Math.floor((bounds.max.x+margin+2)/CELL);
    const minZ=Math.floor((bounds.min.z-margin-2)/CELL),maxZ=Math.floor((bounds.max.z+margin+2)/CELL);
    if((maxX-minX+1)*(maxZ-minZ+1)>MAX_CHUNKS)return true;
    let unresolved=false;
    for(let x=minX;x<=maxX;x++)for(let z=minZ;z<=maxZ;z++) {
      const trees=treesAt(x,z);
      if(trees===null){unresolved=true;continue;}
      if(trees.some(t=>!harvested.has(t.id)&&nearBox(t.x,t.z,bounds,t.radius+margin)&&bounds.max.y+margin>t.y-.3&&bounds.min.y-margin<t.y+6*t.heightScale))return true;
    }
    return unresolved;
  }
  function rayDistance(ray, length, padding=0, ignoreId=null) {
    if(disposed)return length;
    ray.at(length,rayHit);queryBox.setFromPoints([ray.origin,rayHit]).expandByScalar(padding+1);
    const minX=Math.floor(queryBox.min.x/CELL),maxX=Math.floor(queryBox.max.x/CELL);
    const minZ=Math.floor(queryBox.min.z/CELL),maxZ=Math.floor(queryBox.max.z/CELL);
    if((maxX-minX+1)*(maxZ-minZ+1)>MAX_CHUNKS)return 0;
    let nearest=length;
    let unresolved=false;
    for(let x=minX;x<=maxX;x++)for(let z=minZ;z<=maxZ;z++) {
      const trees=treesAt(x,z);
      if(trees===null){unresolved=true;continue;}
      for(const t of trees) {
        if(harvested.has(t.id)||t.id===ignoreId)continue;
        rayBox.copy(t.box).expandByScalar(padding);
        if(rayBox.containsPoint(ray.origin))return 0;
        if(ray.intersectBox(rayBox,rayHit))nearest=Math.min(nearest,ray.origin.distanceTo(rayHit));
      }
    }
    return unresolved?0:nearest;
  }
  function blocksMove(from,x,z,radius=.5) {
    if(disposed)return false;
    // Swept trunk circles prevent sprint tunnelling, with local chunk broadphase.
    const minX=Math.floor((Math.min(from.x,x)-radius-1)/CELL),maxX=Math.floor((Math.max(from.x,x)+radius+1)/CELL);
    const minZ=Math.floor((Math.min(from.z,z)-radius-1)/CELL),maxZ=Math.floor((Math.max(from.z,z)+radius+1)/CELL);
    if((maxX-minX+1)*(maxZ-minZ+1)>MAX_CHUNKS)return true;
    let unresolved=false;
    for(let cx=minX;cx<=maxX;cx++)for(let cz=minZ;cz<=maxZ;cz++) {
      const trees=treesAt(cx,cz);
      if(trees===null){unresolved=true;continue;}
      for(const t of trees) {
        if(harvested.has(t.id))continue;
        if(from.y<t.y-.8||from.y>t.y+6*t.heightScale)continue;
        if(segmentDistanceSq(t.x,t.z,from.x,from.z,x,z)<(radius+t.radius)**2)return true;
      }
    }
    return unresolved;
  }
  // Target only resident rendered trunks, never query-only plans. A local 3x3
  // chunk lookup visits <=72 candidates, does no terrain work and enqueues none.
  function chopTarget(position,yaw) {
    if(disposed||!root.visible)return null;
    const cx=Math.floor(position.x/CELL),cz=Math.floor(position.z/CELL);
    let closest=null,best=Infinity;
    for(let x=cx-1;x<=cx+1;x++)for(let z=cz-1;z<=cz+1;z++){
      const chunk=chunks.get(keyFor(x,z));if(!chunk?.mesh?.visible)continue;
      for(const t of chunk.trees){
        if(harvested.has(t.id)||Math.abs(position.y-t.y)>.65)continue;
        const dx=t.x-position.x,dz=t.z-position.z,d=Math.hypot(dx,dz);
        if(d<.01||d-t.radius>1.65||d>=best||(Math.sin(yaw)*dx+Math.cos(yaw)*dz)/d<.9)continue;
        best=d;closest=t;
      }
    }
    return closest?{...closest,hits:damage.get(closest.id)||0}:null;
  }
  function chop(id,position,yaw,grantWood) {
    if(harvesting)return {ok:false,message:'Tree harvest is already in progress.'};
    // Caller also refreshes terrain/structure LOS at the moment of impact.
    const t=chopTarget(position,yaw);
    if(!t||t.id!==id)return {ok:false,message:'Swing missed. Face a nearby trunk and try again.'};
    if(harvested.size>=MAX_HARVESTED)return {ok:false,message:'Expedition tree limit reached (512). Previously felled trees stay removed.'};
    const hits=damage.get(id)||0;
    if(!hits&&damage.size>=MAX_DAMAGE)return {ok:false,message:'Too many partly chopped trees (64). Finish one nearby or leave this area first.'};
    if(hits+1<HITS){damage.set(id,hits+1);return {ok:true,message:`Chop ${hits+1}/${HITS} · Conifer`};}
    if(falls.length>=MAX_FALLS)return {ok:false,message:'Wait for the falling trees to settle, then retry.'};
    // Synchronous inventory transaction: failure leaves the tree at 3/4 hits.
    let reward;
    harvesting=true;
    try{reward=grantWood();}finally{harvesting=false;}
    if(!reward.ok)return {ok:false,message:`${reward.message} Make room for 3 Wood (1.5 kg), then retry the final hit.`};
    harvested.add(id);damage.delete(id);stats.trees--;
    const chunk=chunks.get(keyFor(Math.floor(t.x/CELL),Math.floor(t.z/CELL)));
    matrix.position.set(0,0,0);matrix.rotation.set(0,0,0);matrix.scale.setScalar(0);matrix.updateMatrix();
    chunk.mesh.setMatrixAt(chunk.trees.findIndex(tree=>tree.id===id),matrix.matrix);
    chunk.mesh.instanceMatrix.needsUpdate=true;
    // One temporary draw per fall, sharing the existing geometry and material.
    const mesh=new THREE.Mesh(geometry,material);
    mesh.position.set(t.x,t.y,t.z);mesh.scale.set(t.width,t.heightScale,t.width);
    mesh.rotation.y=t.yaw;root.add(mesh);mesh.updateWorldMatrix(true,true);
    falls.push({mesh,age:0,y:t.y,yaw,base:mesh.quaternion.clone()});
    return {ok:true,message:`Tree felled · ${reward.message}`};
  }
  function updateFalls(dt){
    if(disposed)return;
    for(let i=falls.length-1;i>=0;i--){
      const f=falls[i];f.age+=Math.max(0,Math.min(dt,.05));
      if(f.age>=2){f.mesh.removeFromParent();falls.splice(i,1);continue;}
      const t=Math.min(1,f.age/1.25);
      fallAxis.set(Math.cos(f.yaw),0,-Math.sin(f.yaw));
      fallTurn.setFromAxisAngle(fallAxis,Math.PI*.49*t*t);
      f.mesh.quaternion.copy(f.base).premultiply(fallTurn);
      // Settle then sink: bounded cosmetic fall, no persistent log collider.
      f.mesh.position.y=f.y-Math.max(0,(f.age-1.35)/.65)*2;
      f.mesh.updateWorldMatrix(true,true);
    }
  }
  const api={ startFrame, overlaps, blocksMove, rayDistance, chopTarget, chop, updateFalls, stats,
    dispose(){
      if(disposed)return;disposed=true;
      for(const key of [...chunks.keys()])remove(key);
      for(const f of falls)f.mesh.removeFromParent();falls.length=0;harvested.clear();damage.clear();
      queue=[];queryCache.clear();pending.clear();stats.pending=0;stats.queryCells=0;stats.queued=0;root.removeFromParent();geometry.dispose();material.dispose();
      if(scene.userData.treeStream===api)delete scene.userData.treeStream;
    } };
  scene.userData.treeStream=api;
  return api;
}
