// One seed per fresh page load; no terrain exports or per-world files.
export const worldSeed=crypto.getRandomValues(new Uint32Array(1))[0];
const phase=(worldSeed/4294967296)*Math.PI*2;
const hash=(x,z)=>{let h=Math.imul(x,374761393)^Math.imul(z,668265263)^worldSeed;h=Math.imul(h^(h>>>13),1274126177);return ((h^(h>>>16))>>>0)/4294967296;};
function noise(x,z){
  const ix=Math.floor(x),iz=Math.floor(z),fx=x-ix,fz=z-iz;
  const u=fx*fx*(3-2*fx),v=fz*fz*(3-2*fz);
  const a=hash(ix,iz)*(1-u)+hash(ix+1,iz)*u,b=hash(ix,iz+1)*(1-u)+hash(ix+1,iz+1)*u;
  return (a*(1-v)+b*v)*2-1;
}
export function transformWorldPoint(point){
  const [x,y,z]=point;
  // Smooth invertible shears change river paths and coastlines without seams.
  const nx=x+1700*Math.sin(z/19000+phase);
  const nz=z+1400*Math.sin(nx/23000+phase*1.7);
  const land=Math.min(1,Math.max(0,y/180));
  const relief=Math.max(-130,210*noise(x/6200,z/6200)+65*noise(x/2400,z/2400));
  return [nx,y+land*relief,nz];
}
export function reshapeTerrain(geometry){
  const positions=geometry.attributes.position;
  for(let i=0;i<positions.count;i++){
    const p=transformWorldPoint([positions.getX(i),positions.getY(i),positions.getZ(i)]);
    positions.setXYZ(i,...p);
  }
  positions.needsUpdate=true;geometry.computeVertexNormals();
}
export function reshapeManifest(world){
  if(world.spawn)world.spawn=transformWorldPoint(world.spawn);
  for(const a of world.actors){
    a.position=transformWorldPoint(a.position);
    if(a.target)a.target=transformWorldPoint(a.target);
    if(a.ground)a.ground={height:a.position[1],normal:[0,1,0]};
  }
}
