const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),modules=new Map();
async function load(file){
  if(modules.has(file))return modules.get(file);
  const m=new vm.SourceTextModule(fs.readFileSync(file,'utf8'),{identifier:file});modules.set(file,m);
  await m.link((s,p)=>load(s==='three'?path.join(root,'viewer/vendor/three.module.js'):path.resolve(path.dirname(p.identifier),s)));
  await m.evaluate();return m;
}
(async()=>{
  const game=(await load(path.join(root,'viewer/gameplay.js'))).namespace;
  const THREE=modules.get(path.join(root,'viewer/vendor/three.module.js')).namespace;
  const actor={type:'human',root:new THREE.Group(),clips:['Idle','Walk','Run','CrouchWalk'].map(n=>new THREE.AnimationClip(n,1,[]))};
  actor.mixer=new THREE.AnimationMixer(actor.root);game.register(actor);
  game.surface.height=()=>1;
  const camera=new THREE.PerspectiveCamera();camera.position.set(0,3,10);camera.lookAt(0,1,0);camera.updateMatrixWorld();
  const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
  for(const [keys,rate] of [[['KeyW'],2.2352/1.3],[['KeyW','ShiftLeft'],6.25856/4.5],[['KeyW','KeyC'],.7/.9],[[],1]]){
    game.updateGame(.01,new Set(keys),camera);near(actor.action.getEffectiveTimeScale(),rate);
  }
  actor.root.position.set(0,1,0);actor.root.rotation.set(0,0,0);
  let soleY=0;
  const mesh={matrixWorld:actor.root.matrixWorld,skeleton:{update(){}},getVertexPosition(i,v){return v.set(.2,soleY,0);}};
  actor.soleSamples=[{mesh,index:0}];
  game.updateFootContact(actor,.016);near(actor.root.position.y,.992);
  // Running flight remains above the snow; grounding never cancels its lift.
  soleY=.25;game.updateFootContact(actor,.016);near(actor.root.position.y,.992);
  // On a slope the ground reference follows the supporting boot, not body centre.
  game.surface.height=x=>1+x*.5;delete actor.groundCorrection;
  game.updateFootContact(actor,.016);near(actor.root.position.y,1.092);
  near(actor.root.matrixWorld.elements[13],1.092);
  // Measure the actual shipped mesh/rig without loading its image materials.
  const original=fs.readFileSync(path.join(root,'Human_Animated.glb'));
  const jsonLength=original.readUInt32LE(12),json=JSON.parse(original.subarray(20,20+jsonLength));
  json.materials=(json.materials||[]).map(()=>({}));json.images=[];json.textures=[];
  let jsonText=JSON.stringify(json);jsonText+=' '.repeat((4-jsonText.length%4)%4);
  const jsonBytes=Buffer.from(jsonText),binary=original.subarray(20+jsonLength);
  const glb=Buffer.alloc(20+jsonBytes.length+binary.length);
  original.copy(glb,0,0,20);glb.writeUInt32LE(glb.length,8);glb.writeUInt32LE(jsonBytes.length,12);
  jsonBytes.copy(glb,20);binary.copy(glb,20+jsonBytes.length);
  const {GLTFLoader}=(await load(path.join(root,'viewer/vendor/addons/loaders/GLTFLoader.js'))).namespace;
  const gltf=await new Promise((resolve,reject)=>new GLTFLoader().parse(glb.buffer,'',resolve,reject));
  const human={type:'human',root:new THREE.Group(),clips:gltf.animations,mixer:new THREE.AnimationMixer(gltf.scene)};
  human.root.add(gltf.scene);game.surface.height=()=>0;game.register(human);
  assert.ok(human.soleSamples.length>0,'actual GLB provides outsole samples');
  for(const name of ['Human_Idle','Human_Walk','Human_Run']){
    human.mixer.stopAllAction();const clip=gltf.animations.find(c=>c.name===name);human.mixer.clipAction(clip).play();
    let min=Infinity,max=-Infinity;
    for(let i=0;i<60;i++){
      human.mixer.setTime(clip.duration*i/60);human.root.updateMatrixWorld(true);
      let lowest=Infinity;
      for(const s of human.soleSamples){s.mesh.skeleton.update();const v=new THREE.Vector3();s.mesh.getVertexPosition(s.index,v).applyMatrix4(s.mesh.matrixWorld);lowest=Math.min(lowest,v.y);}
      min=Math.min(min,lowest);max=Math.max(max,lowest);
    }
    console.log(`${name} lowest sampled sole over cycle: ${min.toFixed(4)} to ${max.toFixed(4)} m`);
    assert.ok(min<.035&&min>-.035,`${name} contacts authored ground`);
  }
  console.log('PASS: walking/sprint/crouch cadence, idle speed reset, snow contact, preserved run flight, slope contact and refreshed matrices.');
})().catch(e=>{console.error(e);process.exitCode=1;});
