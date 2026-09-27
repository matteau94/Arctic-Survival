// A small replacement terrain mesh, not a decal: contact lowers the actual snow
// surface and its lighting normals. World-aligned samples survive recentering.
export function createSnowImpressions(THREE, scene, surface, terrainMeshes) {
  // Two-centimetre spacing resolves rounded boot edges; keep detail local.
  const spacing=.02, size=6, segments=300, row=segments+1, half=size/2;
  const depths=new Map(), limit=320000;
  const center=new THREE.Vector2(1e20,1e20);
  const clip={value:new THREE.Vector3(1e20,1e20,size/2)};
  const geometry=new THREE.PlaneGeometry(size,size,segments,segments);
  geometry.rotateX(-Math.PI/2);
  const positions=geometry.attributes.position, normals=geometry.attributes.normal;
  const colors=new THREE.BufferAttribute(new Float32Array(positions.count*3),3);
  geometry.setAttribute('color',colors);
  const base=new Float32Array(positions.count);
  const material=new THREE.MeshStandardMaterial({vertexColors:true,roughness:1,metalness:0,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(geometry,material);mesh.name='deformable-snow';mesh.visible=false;
  scene.add(mesh);
  const materials=[...new Set(terrainMeshes.flatMap(m=>Array.isArray(m.material)?m.material:[m.material]))];
  const originals=materials.map(m=>({m,compile:m.onBeforeCompile,key:m.customProgramCacheKey}));
  for(const {m,compile,key} of originals){
    m.onBeforeCompile=function(shader,renderer){
      compile.call(this,shader,renderer);
      shader.uniforms.snowPatch=clip;
      if(!shader.vertexShader.includes('varying vec3 terrainWorldPosition;')){
        shader.vertexShader='varying vec3 terrainWorldPosition;\n'+shader.vertexShader;
        shader.vertexShader=shader.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nterrainWorldPosition=(modelMatrix*vec4(transformed,1.0)).xyz;');
        shader.fragmentShader='varying vec3 terrainWorldPosition;\n'+shader.fragmentShader;
      }
      shader.fragmentShader='uniform vec3 snowPatch;\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <clipping_planes_fragment>','#include <clipping_planes_fragment>\nif(max(abs(terrainWorldPosition.x-snowPatch.x),abs(terrainWorldPosition.z-snowPatch.y)) < snowPatch.z) discard;');
    };
    m.customProgramCacheKey=()=>key.call(m)+'-deformable-snow-v1';m.needsUpdate=true;
  }
  let dirty=false, stampCount=0, originX=0,originZ=0;
  let minX=segments,maxX=0,minZ=segments,maxZ=0;
  const key=(x,z)=>`${x},${z}`;
  const sampleDepth=(x,z)=>depths.get(key(Math.round(x/spacing),Math.round(z/spacing)))||0;
  function stamp(x,z,radius=.06,depth=.025){
    if(!Number.isFinite(x+z+radius+depth)||radius<=0||depth<=0)return;
    depth=Math.min(depth,.08);radius=Math.min(radius,.3);
    for(let ix=Math.ceil((x-radius)/spacing);ix<=Math.floor((x+radius)/spacing);ix++){
      for(let iz=Math.ceil((z-radius)/spacing);iz<=Math.floor((z+radius)/spacing);iz++){
        const distance=Math.hypot(ix*spacing-x,iz*spacing-z)/radius;
        if(distance>=1)continue;
        // Broad pressed floor and steep but smoothly rounded depression walls.
        const t=Math.max(0,Math.min(1,(1-distance)/.65));
        const amount=depth*t*t*t*(t*(t*6-15)+10), id=key(ix,iz);
        if(amount>(depths.get(id)||0)){
          depths.set(id,amount);dirty=true;
          minX=Math.min(minX,Math.max(0,ix-originX));maxX=Math.max(maxX,Math.min(segments,ix-originX));
          minZ=Math.min(minZ,Math.max(0,iz-originZ));maxZ=Math.max(maxZ,Math.min(segments,iz-originZ));
        }
      }
    }
    while(depths.size>limit)depths.delete(depths.keys().next().value);
    stampCount++;
  }
  function recenter(x,z){
    center.set(Math.round(x/1.5)*1.5,Math.round(z/1.5)*1.5);
    originX=Math.round((center.x-size/2)/spacing);originZ=Math.round((center.y-size/2)/spacing);
    mesh.position.set(center.x,0,center.y);
    mesh.updateMatrixWorld(true);
    // Collect only local source triangles once per 1.5 metres. Their barycentric
    // heights AND colors make the replacement join the exported terrain exactly.
    const triangles=[];
    for(const terrain of terrainMeshes){
      const g=terrain.geometry,p=g.attributes.position,c=g.attributes.color,idx=g.index;
      if(g.boundingBox&&(g.boundingBox.max.x<center.x-half||g.boundingBox.min.x>center.x+half||g.boundingBox.max.z<center.y-half||g.boundingBox.min.z>center.y+half))continue;
      for(let i=0;i<idx.count;i+=3){
        const ia=idx.getX(i),ib=idx.getX(i+1),ic=idx.getX(i+2);
        const ax=p.getX(ia),bx=p.getX(ib),cx=p.getX(ic),az=p.getZ(ia),bz=p.getZ(ib),cz=p.getZ(ic);
        if(Math.max(ax,bx,cx)<center.x-half||Math.min(ax,bx,cx)>center.x+half||Math.max(az,bz,cz)<center.y-half||Math.min(az,bz,cz)>center.y+half)continue;
        const ids=[ia,ib,ic],xs=[ax,bx,cx],zs=[az,bz,cz];
        const d=(zs[1]-zs[2])*(xs[0]-xs[2])+(xs[2]-xs[1])*(zs[0]-zs[2]);
        if(Math.abs(d)>1e-10)triangles.push({ids,xs,zs,d,p,c});
      }
    }
    for(let i=0;i<positions.count;i++){
      const wx=center.x+positions.getX(i),wz=center.y+positions.getZ(i);
      let height=-Infinity,red=.85,green=.90,blue=.94;
      for(const t of triangles){
        const {xs,zs,d,ids,p,c}=t;
        const a=((zs[1]-zs[2])*(wx-xs[2])+(xs[2]-xs[1])*(wz-zs[2]))/d;
        const b=((zs[2]-zs[0])*(wx-xs[2])+(xs[0]-xs[2])*(wz-zs[2]))/d;
        if(a<-.00001||b<-.00001||a+b>1.00001)continue;
        const h=a*p.getY(ids[0])+b*p.getY(ids[1])+(1-a-b)*p.getY(ids[2]);
        if(h<=height)continue;height=h;
        if(c){red=a*c.getX(ids[0])+b*c.getX(ids[1])+(1-a-b)*c.getX(ids[2]);green=a*c.getY(ids[0])+b*c.getY(ids[1])+(1-a-b)*c.getY(ids[2]);blue=a*c.getZ(ids[0])+b*c.getZ(ids[1])+(1-a-b)*c.getZ(ids[2]);}
      }
      base[i]=Number.isFinite(height)?height:(surface.height(wx,wz)??0);
      colors.setXYZ(i,red,green,blue);
    }
    colors.needsUpdate=true;clip.value.set(center.x,center.y,size/2);mesh.visible=true;dirty=true;
    minX=0;maxX=segments;minZ=0;maxZ=segments;
  }
  function update(position){
    if(!position)return;
    if(Math.abs(position.x-center.x)>=1.5||Math.abs(position.z-center.y)>=1.5)recenter(position.x,position.z);
    if(!dirty)return;
    for(let iz=minZ;iz<=maxZ;iz++)for(let ix=minX;ix<=maxX;ix++){
      const i=iz*row+ix;
      const edge=Math.min(ix,iz,segments-ix,segments-iz);
      const fade=Math.min(1,edge/16);
      positions.setY(i,base[i]-(depths.get(key(originX+ix,originZ+iz))||0)*fade);
    }
    for(let iz=Math.max(0,minZ-1);iz<=Math.min(segments,maxZ+1);iz++)for(let ix=Math.max(0,minX-1);ix<=Math.min(segments,maxX+1);ix++){
      const i=iz*row+ix;
      const l=ix?i-1:i,r=ix<segments?i+1:i,b=iz?i-row:i,f=iz<segments?i+row:i;
      const nx=-(positions.getY(r)-positions.getY(l))/((r-l)*spacing);
      const nz=-(positions.getY(f)-positions.getY(b))/((f-b)/row*spacing);
      const length=Math.hypot(nx,1,nz);normals.setXYZ(i,nx/length,1/length,nz/length);
    }
    positions.needsUpdate=true;normals.needsUpdate=true;
    if(minX===0&&maxX===segments){geometry.computeBoundingSphere();geometry.boundingSphere.radius+=.1;}
    dirty=false;minX=segments;maxX=0;minZ=segments;maxZ=0;
  }
  return {stamp,update,sampleDepth,mesh,get stats(){return {stampCount,vertexCount:positions.count,storedSamples:depths.size};},dispose(){scene.remove(mesh);geometry.dispose();material.dispose();for(const {m,compile,key}of originals){m.onBeforeCompile=compile;m.customProgramCacheKey=key;m.needsUpdate=true;}}};
}
