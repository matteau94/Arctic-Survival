const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
async function load(file){const m=new vm.SourceTextModule(fs.readFileSync(path.join(root,file),'utf8'));await m.link(()=>{});await m.evaluate();return m.namespace;}
(async()=>{
  const THREE=await load('viewer/vendor/three.module.js');
  const {createSnowImpressions}=await load('viewer/snow-impressions.js');
  const {createTerrainMaterial}=await load('viewer/terrain-render.js');
  const geometry=new THREE.PlaneGeometry(100,100);geometry.rotateX(-Math.PI/2);
  geometry.setAttribute('color',new THREE.Float32BufferAttribute(Array(4).fill([.8,.85,.9]).flat(),3));
  const terrain=new THREE.Mesh(geometry,createTerrainMaterial(THREE)),scene=new THREE.Scene();scene.add(terrain);
  const snow=createSnowImpressions(THREE,scene,{height:()=>0},[terrain]);
  snow.stamp(0,0,.08,.035);snow.update({x:0,z:0});
  assert.equal(snow.sampleDepth(0,0),.035);
  const p=snow.mesh.geometry.attributes.position,n=snow.mesh.geometry.attributes.normal;
  let minimum=0,tilted=false;
  for(let i=0;i<p.count;i++){minimum=Math.min(minimum,p.getY(i));if(n.getY(i)<.99)tilted=true;}
  assert.ok(minimum<-.034,'Actual vertex positions lowered beneath original ground');
  assert.ok(tilted,'Depression walls have sloped lighting normals');
  assert.equal(snow.sampleDepth(.3,0),0,'No deformation away from boot contact');
  snow.stamp(0,0,.08,.02);assert.equal(snow.sampleDepth(0,0),.035,'Repeated contact does not accumulate bottomless holes');
  snow.update({x:10,z:0});snow.update({x:0,z:0});
  assert.equal(snow.sampleDepth(0,0),.035,'Depressions survive leaving and returning');
  const shader={uniforms:{},vertexShader:'#include <worldpos_vertex>',fragmentShader:'#include <clipping_planes_fragment>\n#include <color_fragment>\n#include <roughnessmap_fragment>'};
  terrain.material.onBeforeCompile(shader);
  assert.ok(shader.fragmentShader.includes('discard;'),'Original surface cannot cover depression');
  assert.ok(shader.fragmentShader.includes('iceSurface'),'Existing terrain shader preserved');
  assert.equal(snow.stats.vertexCount,90601,'Detail remains bounded to a local patch');
  assert.ok(snow.sampleDepth(.04,0)>snow.sampleDepth(.06,0),'Smoothly rounded impression wall');
  assert.ok(snow.sampleDepth(.06,0)>0,'Intermediate edge samples preserve the rounded contour');
  snow.dispose();assert.equal(scene.children.length,1);
  console.log('PASS: real geometric depressions, wall normals, bounded mesh, persistence, shader chaining and disposal.');
})().catch(e=>{console.error(e);process.exitCode=1;});
