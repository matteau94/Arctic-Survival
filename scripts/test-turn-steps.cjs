const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..'),modules=new Map();
async function load(file){
  if(modules.has(file))return modules.get(file);
  const module=new vm.SourceTextModule(fs.readFileSync(file,'utf8'),{identifier:file});
  modules.set(file,module);
  await module.link((specifier,parent)=>load(specifier==='three'?path.join(root,'viewer/vendor/three.module.js'):path.resolve(path.dirname(parent.identifier),specifier)));
  await module.evaluate();return module;
}
(async()=>{
  const game=(await load(path.join(root,'viewer/gameplay.js'))).namespace;
  const THREE=modules.get(path.join(root,'viewer/vendor/three.module.js')).namespace;
  game.surface.add([-20,1,-20,20,1,-20,20,1,20,-20,1,20],[0,1,2,0,2,3]);
  const rootObject=new THREE.Group();rootObject.position.y=1;
  const clips=['Idle','Walk','Run','CrouchIdle','CrouchWalk'].map(name=>new THREE.AnimationClip(name,1,[]));
  const player={type:'human',root:rootObject,clips,mixer:new THREE.AnimationMixer(rootObject)};
  game.register(player);
  const camera=new THREE.PerspectiveCamera();
  function look(yaw){camera.position.set(0,3,0);camera.lookAt(Math.sin(yaw),3,Math.cos(yaw));camera.updateMatrixWorld();}
  function tick(keys=new Set()){game.updateGame(1/60,keys,camera);player.mixer.update(1/60);}
  look(Math.PI/2);tick();
  assert.equal(player.state,'Turning');assert.equal(player.clip,'Walk');
  assert.ok(player.root.rotation.y>0&&player.root.rotation.y<.1,'body turns gradually');
  const initial=player.root.position.clone();
  for(let i=0;i<120;i++)tick();
  assert.ok(player.root.position.equals(initial),'turning does not translate the actor');
  assert.ok(Math.abs(player.root.rotation.y-Math.PI/2)<1e-6);
  assert.equal(player.state,'Idle');assert.equal(player.clip,'Idle');
  player.root.rotation.y=Math.PI-.04;look(-Math.PI+.04);tick();
  assert.ok(player.root.rotation.y>Math.PI-.04,'wraparound takes shortest arc');
  for(let i=0;i<90;i++)tick();
  look(0);tick(new Set(['KeyC']));
  assert.equal(player.state,'Turning');assert.equal(player.clip,'CrouchWalk');
  for(let i=0;i<180;i++)tick(new Set(['KeyC']));
  assert.equal(player.clip,'CrouchIdle');
  const before=player.root.position.clone();tick(new Set(['KeyD']));
  assert.equal(player.clip,'Walk');assert.ok(player.root.position.distanceTo(before)>0);
  assert.ok(Math.abs(player.root.rotation.y-Math.PI*2)<1e-6,'strafe retains camera facing');
  console.log('PASS: visible turn steps, limited rotation, stationary position, shortest arc, idle settling, crouched turns and strafe facing.');
})().catch(error=>{console.error(error);process.exitCode=1;});
