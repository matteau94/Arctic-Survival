const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const modules = new Map();
async function load(file) {
  if (modules.has(file)) return modules.get(file);
  const module = new vm.SourceTextModule(fs.readFileSync(file, 'utf8'), {identifier:file});
  modules.set(file,module);
  await module.link((specifier,parent)=>load(specifier==='three'?path.join(root,'viewer/vendor/three.module.js'):path.resolve(path.dirname(parent.identifier),specifier)));
  await module.evaluate();return module;
}
(async()=>{
  const game=(await load(path.join(root,'viewer/gameplay.js'))).namespace;
  const THREE=modules.get(path.join(root,'viewer/vendor/three.module.js')).namespace;
  const {TerrainSurface}=(await load(path.join(root,'viewer/terrain.mjs'))).namespace;
  const slope=new TerrainSurface(2);
  slope.add([0,0,0,10,10,0,0,0,10],[0,1,2]);
  assert.equal(slope.height(2,2),2);
  assert.equal(slope.height(20,20),null);
  game.surface.add([-200,1,-200,200,1,-200,200,1,200,-200,1,200],[0,1,2,0,2,3]);
  function actor(type,x,z){
    const root=new THREE.Group();root.position.set(x,1,z);
    const clips=['CrouchIdle','CrouchWalk','Idle','Walk','Run'].map(n=>new THREE.AnimationClip(n,1,[]));
    const a={type,root,clips,mixer:new THREE.AnimationMixer(root)};game.register(a);return a;
  }
  const player=actor('human',0,0), penguin=actor('penguin',5,0), bear=actor('bear',20,0);
  const camera=new THREE.PerspectiveCamera();camera.position.set(0,3,10);camera.lookAt(0,1,0);camera.updateMatrixWorld();
  game.updateGame(1,new Set(['KeyW']),camera);
  assert.equal(player.clip,'Walk');assert.ok(Math.abs(player.root.position.z+2.2352)<1e-6);
  assert.equal(penguin.state,'Fleeing');assert.ok(penguin.root.position.x>5);
  assert.equal(bear.state,'Approaching');assert.ok(bear.root.position.x<20);
  const before=player.root.position.clone();
  game.updateGame(1,new Set(['KeyW','KeyD','ShiftLeft']),camera);
  assert.ok(Math.abs(player.root.position.distanceTo(before)-6.25856)<1e-6);assert.equal(player.clip,'Run');
  game.updateGame(.1,new Set(['KeyC']),camera);assert.equal(player.clip,'CrouchIdle');
  // Mouse look must turn an idle player and retain that facing while strafing or reversing.
  function near(actual,expected,message){assert.ok(Math.abs(actual-expected)<1e-6,`${message}: ${actual} != ${expected}`);}
  function facing(x,z){
    const direction=new THREE.Vector3(0,0,1).applyQuaternion(player.root.quaternion);
    near(direction.x,x,'player facing x');near(direction.z,z,'player facing z');
  }
  camera.position.set(0,3,0);camera.lookAt(10,1,0);camera.updateMatrixWorld();
  player.root.position.set(0,1,0);
  game.updateGame(.1,new Set(),camera);
  facing(1,0);assert.equal(player.clip,'Idle');near(player.root.position.lengthSq(),1,'idle position');
  for(const [key,x,z] of [['KeyW',2.2352,0],['KeyS',-2.2352,0],['KeyA',0,-2.2352],['KeyD',0,2.2352],['ArrowUp',2.2352,0],['ArrowDown',-2.2352,0],['ArrowLeft',0,-2.2352],['ArrowRight',0,2.2352]]){
    player.root.position.set(0,1,0);
    game.updateGame(1,new Set([key]),camera);
    near(player.root.position.x,x,`${key} movement x`);near(player.root.position.z,z,`${key} movement z`);
    facing(1,0);assert.equal(player.clip,'Walk');
  }
  camera.lookAt(-10,1,0);camera.updateMatrixWorld();
  game.updateGame(.1,new Set(),camera);facing(-1,0);
  camera.position.set(0,3,10);camera.lookAt(0,1,0);camera.updateMatrixWorld();
  player.root.position.set(0,1,-199.9);
  game.updateGame(1,new Set(['KeyW']),camera);assert.equal(player.root.position.z,-199.9);assert.equal(player.clip,'Idle');
  player.root.position.set(0,1,0);
  const building={type:'cabin',root:new THREE.Mesh(new THREE.BoxGeometry(4,4,4))};
  building.root.position.set(0,2,-5);game.register(building);
  game.updateGame(2,new Set(['KeyW']),camera);assert.equal(player.root.position.z,0);
  game.surface.add([300,-20,300,500,-20,300,500,-20,500,300,-20,500],[0,1,2,0,2,3]);
  const fish=actor('fish',400,400);fish.root.position.y=-5;fish.home.y=-5;
  fish.destination.set(420,-5,400);fish.think=10;
  game.updateGame(1,new Set(),camera);assert.equal(fish.root.position.x,403);assert.equal(fish.root.position.y,-5);
  // Far wildlife must do no terrain work or advance its AI timer, then resume nearby.
  const distant=actor('penguin',game.WILDLIFE_SIMULATION_DISTANCE+100,0);
  distant.destination.set(distant.root.position.x+20,1,0);distant.think=10;
  const farPosition=distant.root.position.clone();
  const originalHeight=game.surface.height.bind(game.surface);
  let farTerrainQueries=0;
  game.surface.height=(x,z)=>{if(x>game.WILDLIFE_SIMULATION_DISTANCE) farTerrainQueries++;return originalHeight(x,z);};
  game.updateGame(1,new Set(),camera);
  assert.equal(distant.think,10);assert.ok(distant.root.position.equals(farPosition));assert.equal(farTerrainQueries,0);
  game.surface.height=originalHeight;
  distant.root.position.set(100,1,0);distant.destination.set(120,1,0);
  game.updateGame(1,new Set(),camera);
  assert.equal(distant.think,9);near(distant.root.position.x,101.1,'nearby wildlife resumes');
  // Verify the actual export has a walkable player spawn and required clips.
  const world=JSON.parse(fs.readFileSync(path.join(root,'viewer/data/world.json')));
  const terrain=new TerrainSurface();
  for(const entry of [world.terrain].flat()){
    const b=fs.readFileSync(path.join(root,'viewer/data',entry.file));
    const data=b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),n=entry.vertexCount*3;
    terrain.add(new Float32Array(data,0,n),new Uint32Array(data,n*12,entry.indexCount));
  }
  const spawn=world.actors.find(a=>a.type==='penguin').position;
  assert.ok(terrain.height(spawn[0]+8,spawn[2]+8)>0);
  const glb=fs.readFileSync(path.join(root,'Human_Animated.glb'));
  const json=JSON.parse(glb.subarray(20,20+glb.readUInt32LE(12)).toString());
  for(const name of ['Human_Idle','Human_Walk','Human_Run','Human_CrouchIdle','Human_CrouchWalk']) assert.ok(json.animations.some(a=>a.name===name),name);
  for(const file of ['viewer/app.js','viewer/gameplay.js']) new vm.SourceTextModule(fs.readFileSync(path.join(root,file),'utf8'));
  console.log('PASS: terrain, movement, camera-facing idle/strafe/backward controls, arrow controls, sprint normalization, crouch, boundaries, building collision, swimming, fleeing, approach, exported spawn and human clips.');
})().catch(error=>{console.error(error);process.exitCode=1;});
