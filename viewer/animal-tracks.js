import * as THREE from 'three';

// Runtime decals only: terrain and animal resources are never modified.
const CAPACITY=512, NEAR=65, MAX_ANIMALS=12, LIFE=75;
const RAY_BUDGET=10, RAYS_PER_STAMP=5, PENDING_LIFE=.35, PLANE_TOLERANCE=.02;
// GLTFLoader strips dots from Blender bone names.
const footNames={fox:/^toes_(front|hind)[._]?([LR])$/i,bear:/^(manus|pes|digits)[._]?([LR][FH]|[FH][LR])$/i,penguin:/^foot[._]?([LR])$/i};
export function createAnimalTracks(scene,surface,terrainMeshes,sampleDepth=()=>0){
  const geometry=new THREE.PlaneGeometry(1,1);
  geometry.rotateX(-Math.PI/2);
  const births=new Float32Array(CAPACITY).fill(-LIFE),kinds=new Float32Array(CAPACITY);
  geometry.setAttribute('birth',new THREE.InstancedBufferAttribute(births,1));
  geometry.setAttribute('kind',new THREE.InstancedBufferAttribute(kinds,1));
  const material=new THREE.ShaderMaterial({transparent:true,depthTest:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,
    uniforms:{now:{value:0}},
    vertexShader:`attribute float birth; attribute float kind;
      varying vec2 p; varying float born; varying float species;
      void main(){p=vec2(uv.x*2.-1.,1.-uv.y*2.);born=birth;species=kind;
        gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(position,1.);}`,
    fragmentShader:`uniform float now; varying vec2 p; varying float born; varying float species;
      float oval(vec2 q,vec2 r){return 1.-smoothstep(.8,1.,length(q/r));}
      void main(){float mark=0.;
        if(species>1.5){
          mark=oval(p-vec2(0.,-.25),vec2(.33,.38));
          for(int i=0;i<3;i++){float x=float(i-1)*.4;
            mark=max(mark,oval(vec2(p.x-x*(p.y+.6),p.y-.25),vec2(.15,.62)));}
        }else{
          mark=oval(p-vec2(0.,-.28),vec2(.52,.4));
          for(int i=0;i<5;i++){if(species<.5&&i==4)break;
            float x=(float(i)-(species<.5?1.5:2.))*(species<.5?.38:.32);
            mark=max(mark,oval(p-vec2(x,.38-abs(x)*.28),vec2(.17,.23)));}
        }
        float alpha=mark*.3*(1.-smoothstep(45.,75.,now-born));
        if(alpha<.005)discard;gl_FragColor=vec4(.23,.32,.39,alpha);}`});
  const mesh=new THREE.InstancedMesh(geometry,material,CAPACITY);
  mesh.name='animal-snow-tracks';mesh.frustumCulled=false;mesh.count=0;scene.add(mesh);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const states=new WeakMap(),point=new THREE.Vector3(),normal=new THREE.Vector3(),color=new THREE.Color();
  const ray=new THREE.Raycaster(),hits=[],bary=new THREE.Vector3();
  const va=new THREE.Vector3(),vb=new THREE.Vector3(),vc=new THREE.Vector3();
  const corner=new THREE.Vector3(),landing=new THREE.Vector3();
  const pose=new THREE.Object3D(),up=new THREE.Vector3(0,1,0),turn=new THREE.Quaternion();
  let cursor=0,frame=0,disposed=false,priority=0,rays=0,lastStates=[];
  function prepare(a){
    const feet=new Map(),meshes=[],totals=new Float32Array(4);
    a.root.traverseVisible(m=>{
      if(!m.isSkinnedMesh||meshes.length>=4)return;
      const indices=m.geometry.attributes.skinIndex,weights=m.geometry.attributes.skinWeight;
      if(!indices||!weights)return;
      const groups=m.skeleton.bones.map(b=>{
        const match=b.name.match(footNames[a.type]);
        if(!match)return -1;
        const name=a.type==='bear'?match[2]:match.slice(1).join('');
        if(!feet.has(name)&&feet.size<4)feet.set(name,{id:feet.size,bounds:new THREE.Box3(),samples:[null,null,null],touching:true,pending:null});
        return feet.get(name)?.id??-1;
      });
      if(!groups.some(g=>g>=0))return;
      meshes.push({m,indices,weights,groups,stride:Math.max(1,Math.ceil(indices.count/4096))});
    });
    const list=[...feet.values()];
    // Two bounded passes over bind geometry: <=4096 candidates/mesh/pass,
    // four meshes. Animation pose never determines which sole vertices we keep.
    for(let pass=0;pass<2;pass++)for(const {m,indices,weights,groups,stride} of meshes){
      for(let i=0;i<indices.count;i+=stride){
        totals.fill(0);
        for(let j=0;j<4;j++){
          const g=groups[indices.getComponent(i,j)];
          if(g>=0)totals[g]+=weights.getComponent(i,j);
        }
        let group=-1,bestWeight=.5;
        for(let g=0;g<list.length;g++)if(totals[g]>=bestWeight){group=g;bestWeight=totals[g];}
        if(group<0)continue;
        const foot=list[group],b=foot.bounds;
        point.fromBufferAttribute(m.geometry.attributes.position,i).applyMatrix4(m.bindMatrix);
        if(pass===0){b.expandByPoint(point);continue;}
        const height=Math.max(b.max.y-b.min.y,1e-6);
        if(point.y>b.min.y+height*.18)continue;
        const width=Math.max(b.max.x-b.min.x,1e-6),length=Math.max(b.max.z-b.min.z,1e-6);
        for(let slot=0;slot<3;slot++){
          const x=(b.min.x+b.max.x)*.5,z=b.min.z+length*(.2+slot*.3);
          const score=((point.x-x)/width)**2+((point.z-z)/length)**2+4*((point.y-b.min.y)/height)**2;
          if(!foot.samples[slot]||score<foot.samples[slot].score)foot.samples[slot]={mesh:m,index:i,score};
        }
      }
    }
    for(const foot of list)foot.samples=foot.samples.filter((sample,i,all)=>sample&&!all.slice(0,i).some(other=>other?.mesh===sample.mesh&&other.index===sample.index));
    return {feet:list.filter(f=>f.samples.length),last:a.root.position.clone(),frame};
  }
  function snowHit(p){
    if(rays>=RAY_BUDGET)return null;
    rays++;
    ray.set(va.set(p.x,p.y+.2,p.z),vb.set(0,-1,0));ray.near=0;ray.far=.4;hits.length=0;
    ray.intersectObjects(terrainMeshes,false,hits);
    const hit=hits[0];if(!hit||hit.point.y<=0||!hit.face)return null;
    const g=hit.object.geometry,c=g.attributes.color,pos=g.attributes.position;
    if(!c)return null;
    const {a:ia,b:ib,c:ic}=hit.face;
    va.fromBufferAttribute(pos,ia);vb.fromBufferAttribute(pos,ib);vc.fromBufferAttribute(pos,ic);
    point.copy(hit.point);hit.object.worldToLocal(point);
    THREE.Triangle.getBarycoord(point,va,vb,vc,bary);
    color.setRGB(c.getX(ia)*bary.x+c.getX(ib)*bary.y+c.getX(ic)*bary.z,
      c.getY(ia)*bary.x+c.getY(ib)*bary.y+c.getY(ic)*bary.z,
      c.getZ(ia)*bary.x+c.getZ(ib)*bary.y+c.getZ(ic)*bary.z);
    if(color.r<.55||color.g<.55||color.b-color.r>.16)return null;
    normal.copy(hit.face.normal).transformDirection(hit.object.matrixWorld);
    return normal.y>=.8?hit:null;
  }
  function stamp(pending){
    // Reserve the centre AND all four corner rays inside the same hard budget.
    if(rays+RAYS_PER_STAMP>RAY_BUDGET)return false;
    const hit=snowHit(pending.point);if(!hit)return false;
    pose.position.copy(hit.point);
    pose.quaternion.setFromUnitVectors(up,normal);
    turn.setFromAxisAngle(up,pending.yaw);pose.quaternion.multiply(turn);
    const size=pending.type==='bear'?.32:pending.type==='fox'?.10:.13;
    pose.scale.set(size,1,size*1.25);pose.updateMatrix();
    let minX=Infinity,maxX=-Infinity,minZ=Infinity,maxZ=-Infinity;
    for(const x of [-.5,.5])for(const z of [-.5,.5]){
      corner.set(x,0,z).applyMatrix4(pose.matrix);
      minX=Math.min(minX,corner.x);maxX=Math.max(maxX,corner.x);
      minZ=Math.min(minZ,corner.z);maxZ=Math.max(maxZ,corner.z);
      const support=snowHit(corner);
      if(!support||Math.abs(support.point.y-corner.y)>PLANE_TOLERANCE)return false;
    }
    // Conservatively inspect every 2cm depth cell in the quad's AABB plus a
    // one-cell apron. This also catches depressions between the corner rays.
    const ix0=Math.floor(minX/.02)-1,ix1=Math.ceil(maxX/.02)+1;
    const iz0=Math.floor(minZ/.02)-1,iz1=Math.ceil(maxZ/.02)+1;
    if((ix1-ix0+1)*(iz1-iz0+1)>1024)return false;
    for(let ix=ix0;ix<=ix1;ix++)for(let iz=iz0;iz<=iz1;iz++)if(sampleDepth(ix*.02,iz*.02)>0)return false;
    // Centre/corner checks are a conservative finite sample, not a continuous
    // proof that the entire quad covers snow or matches every terrain triangle.
    pose.position.y+=.008;pose.updateMatrix();mesh.setMatrixAt(cursor,pose.matrix);
    births[cursor]=material.uniforms.now.value;kinds[cursor]=pending.type==='bear'?1:pending.type==='fox'?0:2;
    cursor=(cursor+1)%CAPACITY;mesh.count=Math.min(CAPACITY,mesh.count+1);return true;
  }
  function updateAnimalTracks(dt,actors,focus,active=true){
    if(disposed)return;
    frame++;material.uniforms.now.value+=dt;
    if(!active){updateAnimalTracks.reset();return;}
    let prepared=false,changed=false;
    const admitted=[];
    for(const a of actors){
      if(a.companionRoom)continue;
      if(!footNames[a.type]||!a.root.visible||a.root.position.distanceToSquared(focus)>NEAR*NEAR||admitted.length>=MAX_ANIMALS)continue;
      let state=states.get(a);
      if(!state){if(prepared)continue;prepared=true;state=prepare(a);states.set(a,state);}
      admitted.push(state);
      const travel=a.root.position.distanceTo(state.last),continuous=state.frame===frame-1;
      state.last.copy(a.root.position);state.frame=frame;
      const walking=continuous&&travel>.0001&&travel<=Math.max(.5,dt*12)&&(/walk|run/i.test(a.clip||'')||(a.type==='fox'&&/^ArcticFox_(Trot|Gallop)$/.test(a.clip||'')));
      let previous=null;
      for(const foot of state.feet){
        if(!continuous||travel>Math.max(.5,dt*12)||foot.pending&&material.uniforms.now.value-foot.pending.time>PENDING_LIFE)foot.pending=null;
        let contacts=0;landing.set(0,0,0);
        for(const sample of foot.samples){
          if(previous!==sample.mesh){sample.mesh.skeleton.update();previous=sample.mesh;}
          sample.mesh.getVertexPosition(sample.index,point).applyMatrix4(sample.mesh.matrixWorld);
          const h=surface.height(point.x,point.z),gap=point.y-h;
          if(h!==null&&gap>=-.035&&gap<=(foot.touching?.055:.035)){contacts++;landing.add(point);}
        }
        const touching=foot.samples.length>=2&&contacts>=2;
        if(walking&&touching&&!foot.touching&&!foot.pending){
          foot.pending={point:landing.multiplyScalar(1/contacts).clone(),yaw:a.root.rotation.y,type:a.type,time:material.uniforms.now.value};
        }
        foot.touching=touching;
      }
    }
    // Drop all queued contacts when an actor leaves admission or despawns.
    for(const state of lastStates)if(!admitted.includes(state))clearPending(state);
    lastStates=admitted;
    rays=0;let attempts=0;
    const start=admitted.length?priority++%admitted.length:0;
    // Rotate actor priority; take at most one queued foot per actor per round.
    // A foot holds one original touchdown for <=.35s, never a growing trail.
    for(let round=0;round<4&&attempts<2;round++)for(let i=0;i<admitted.length&&attempts<2;i++){
      const state=admitted[(start+i)%admitted.length];
      let foot=null;
      for(const candidate of state.feet)if(candidate.pending&&(!foot||candidate.pending.time<foot.pending.time))foot=candidate;
      if(!foot)continue;
      const pending=foot.pending;foot.pending=null;attempts++;
      changed=stamp(pending)||changed;
    }
    if(changed){mesh.instanceMatrix.needsUpdate=true;geometry.attributes.birth.needsUpdate=true;geometry.attributes.kind.needsUpdate=true;}
  }
  function clearPending(state){
    state.frame=-1;
    for(const foot of state.feet){foot.pending=null;foot.touching=true;}
  }
  updateAnimalTracks.reset=()=>{for(const state of lastStates)clearPending(state);lastStates=[];};
  updateAnimalTracks.dispose=()=>{
    if(disposed)return;
    disposed=true;
    updateAnimalTracks.reset();
    mesh.removeFromParent();mesh.dispose();geometry.dispose();material.dispose();
  };
  return updateAnimalTracks;
}
