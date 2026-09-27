const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
async function load(relative) {
  const module = new vm.SourceTextModule(fs.readFileSync(path.join(root, relative), 'utf8'));
  await module.link(() => { throw new Error('Unexpected import'); });
  await module.evaluate();
  return module.namespace;
}
(async () => {
  const THREE = await load('viewer/vendor/three.module.js');
  const {createTerrainTiles} = await load('viewer/terrain-render.js');
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([
    -5000, 0, -5000, -4990, 2, -5000, -5000, 1, -4990,
    0, 0, 0, 3000, 4, 0, 0, 2, 3000,
    9000, 0, 9000, 9010, 3, 9000, 9000, 1, 9010
  ], 3));
  geometry.setAttribute('normal', new THREE.Float32BufferAttribute(new Float32Array(27), 3));
  geometry.setIndex([0, 1, 2, 3, 4, 5, 6, 7, 8]);
  const material = new THREE.MeshBasicMaterial();
  const tiles = createTerrainTiles(THREE, geometry, material);
  assert.equal(tiles.length, 3);
  const triangles = [];
  for (const tile of tiles) {
    assert.equal(tile.material, material);
    assert.equal(tile.geometry.attributes.position, geometry.attributes.position);
    assert.equal(tile.geometry.attributes.normal, geometry.attributes.normal);
    const indices = Array.from(tile.geometry.index.array);
    for (let i = 0; i < indices.length; i += 3) triangles.push(indices.slice(i, i + 3).join(','));
    for (const index of indices) {
      const point = new THREE.Vector3().fromBufferAttribute(geometry.attributes.position, index);
      assert.ok(tile.geometry.boundingBox.containsPoint(point));
      assert.ok(tile.geometry.boundingSphere.containsPoint(point));
    }
    assert.ok(tile.geometry.boundingBox.max.x - tile.geometry.boundingBox.min.x <= 3000);
  }
  assert.deepEqual(triangles.sort(), ['0,1,2', '3,4,5', '6,7,8']);
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
  camera.position.set(-4995, 10, -4970);
  camera.lookAt(-4995, 0, -4995);
  camera.updateMatrixWorld();
  const frustum = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
  assert.ok(frustum.intersectsObject(tiles[0]));
  assert.ok(!frustum.intersectsObject(tiles[2]));
  console.log('Terrain tiles preserve triangles and buffers, bound crossing triangles, and cull distant tiles.');
})().catch(error => { console.error(error); process.exitCode = 1; });
