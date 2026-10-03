import * as THREE from 'three';

const installed = new WeakMap();
const TYPES = ['fox_den', 'penguin_nest'];
const TARGETS = { fox_den: 40, penguin_nest: 10 };
const TAU = Math.PI * 2;

function randomFor(key) {
  let state = 2166136261;
  for (const character of key) state = Math.imul(state ^ character.charCodeAt(0), 16777619);
  return () => {
    state += 0x6D2B79F5;
    let n = Math.imul(state ^ state >>> 15, 1 | state);
    n ^= n + Math.imul(n ^ n >>> 7, 61 | n);
    return ((n ^ n >>> 14) >>> 0) / 4294967296;
  };
}

/**
 * Call after terrain and actor meshes have loaded, before createWaypoints.
 * Returns originals plus actual mesh entrance waypoints, in world metres.
 * The saved 4 dens + 1 colony remain: add 36 + 9, not 40 + 10.
 * Each base has ten deterministic slots (legacy slot zero, variants 1..9).
 * New centres use spawn + (base - spawn) * .1, with bounded local searching.
 * Original terrain sites cannot be compressed without editing saved terrain.
 * No terrain mutation, wildlife spawning, collision registration or frame hook.
 * scene.userData.habitatDensity exposes counts, omissions and dispose().
 * Repeated calls on the same scene return its existing sites; dispose to rebuild.
 */
export function createHabitatDensity({ scene, surface, waypoints, spawn, seed=0 }) {
  if (installed.has(scene)) return installed.get(scene).slice();
  const input = Array.isArray(waypoints) ? waypoints : waypoints?.waypoints;
  const origin = Array.isArray(spawn) ? spawn : [spawn?.x, spawn?.y, spawn?.z];
  if (!scene?.isScene || typeof surface?.height !== 'function' || !Array.isArray(input) ||
      !origin.every(Number.isFinite) || origin.length !== 3) {
    throw new TypeError('Habitat density requires scene, loaded surface, waypoint array and spawn.');
  }
  const ids = new Set();
  const originals = input.filter(point => {
    if (!point || point.id == null || ids.has(String(point.id))) return false;
    ids.add(String(point.id));
    return true;
  });
  const bases = originals.filter(point => TYPES.includes(point.type) &&
    Array.isArray(point.position) && point.position.length === 3 && point.position.every(Number.isFinite))
    .sort((a, b) => String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0);

  scene.updateMatrixWorld(true);
  // Direct model groups include cabins/villages and wildlife. Conservative bounds
  // avoid them all, without relying on names which the app does not assign.
  const blocked = scene.children.filter(object => object.isGroup && object.visible)
    .map(object => new THREE.Box3().setFromObject(object)).filter(box => !box.isEmpty());
  const terrain = [];
  scene.traverse(object => {
    if (object.isMesh && object.name.startsWith('terrain-') && object.geometry.attributes.color) {
      terrain.push({ mesh: object, box: new THREE.Box3().setFromObject(object) });
    }
  });
  const ray = new THREE.Raycaster();
  ray.ray.direction.set(0, -1, 0);
  function iceFree(x, z, y) {
    if (!terrain.length) return true;
    const candidates = terrain.filter(({ box }) => x >= box.min.x && x <= box.max.x &&
      z >= box.min.z && z <= box.max.z).map(({ mesh }) => mesh);
    ray.ray.origin.set(x, y + 10, z);
    ray.far = 20;
    const hit = ray.intersectObjects(candidates, false)[0];
    if (!hit?.face || Math.abs(hit.point.y - y) > .2) return false;
    const color = hit.object.geometry.attributes.color;
    // Same cyan separation as terrain-render.js; any icy triangle corner rejects.
    return [hit.face.a, hit.face.b, hit.face.c].every(index =>
      !(color.getZ(index) - color.getX(index) > .16 && color.getY(index) > .32));
  }

  const occupied = bases.map(point => ({ x: point.position[0], z: point.position[2], radius: 20 }));
  const plans = [], missing = [];
  function validate(x, z) {
    const radius = 12;
    if (Math.hypot(x - origin[0], z - origin[2]) < 30 ||
        occupied.some(p => Math.hypot(x - p.x, z - p.z) < radius + p.radius + 12) ||
        blocked.some(box => x + radius + 4 > box.min.x && x - radius - 4 < box.max.x &&
          z + radius + 4 > box.min.z && z - radius - 4 < box.max.z)) return null;
    const y = surface.height(x, z);
    if (!Number.isFinite(y) || y <= 1) return null;
    const hx = surface.height(x + 1, z), hz = surface.height(x, z + 1);
    if (!Number.isFinite(hx) || !Number.isFinite(hz)) return null;
    const sx = hx - y, sz = hz - y;
    if (Math.hypot(sx, sz) > .18) return null;
    // Two-metre grid validates footprint and approach; every geometry vertex is
    // also sampled below. No null-to-zero coercion and no extrapolated heights.
    for (let dx = -radius; dx <= radius; dx += 2) {
      for (let dz = -radius; dz <= radius; dz += 2) {
        const h = surface.height(x + dx, z + dz);
        if (!Number.isFinite(h) || h <= 1 || Math.abs(h - y - dx * sx - dz * sz) > .22) return null;
      }
    }
    for (const [dx, dz] of [[0, 0], [-10, -10], [-10, 10], [10, -10], [10, 10]]) {
      if (!iceFree(x + dx, z + dz, surface.height(x + dx, z + dz))) return null;
    }
    return y;
  }
  for (const type of TYPES) {
    const sources = bases.filter(point => point.type === type);
    let remaining = Math.max(0, TARGETS[type] - sources.length);
    for (const [baseIndex, base] of sources.entries()) {
      const count = Math.min(9, Math.ceil(remaining / (sources.length - baseIndex)));
      remaining -= count;
      const cx = origin[0] + (base.position[0] - origin[0]) * .1;
      const cz = origin[2] + (base.position[2] - origin[2]) * .1;
      for (let variant = 1; variant <= count; variant++) {
        const id = `${base.id}__density_${variant}`;
        if (ids.has(id)) { missing.push(id); continue; }
        const random = randomFor(`${seed}:${id}`), phase = random() * TAU;
        let plan;
        // Bounded to 220 m from compressed base; never fall back to distant land.
        for (let attempt = 0; attempt < 320; attempt++) {
          const angle = phase + attempt * 2.399963229728653;
          const radius = 36 + 184 * Math.sqrt(attempt / 319);
          const x = cx + Math.cos(angle) * radius, z = cz + Math.sin(angle) * radius;
          const y = validate(x, z);
          if (y === null) continue;
          plan = { id, type, baseId: base.id, variant, x, y, z, yaw: random() * TAU };
          plans.push(plan);
          occupied.push({ x, z, radius: 12 });
          ids.add(id);
          break;
        }
        if (!plan) missing.push(id);
      }
    }
    if (remaining) missing.push(`${type}: ${remaining} slots lack base waypoints`);
  }

  const root = new THREE.Group();
  root.name = 'habitat-density';
  const materials = {
    snow: new THREE.MeshStandardMaterial({ color: 0xc9d5da, roughness: 1, side: THREE.DoubleSide }),
    earth: new THREE.MeshStandardMaterial({ color: 0x504b43, roughness: 1, side: THREE.DoubleSide }),
    stone: new THREE.MeshStandardMaterial({ color: 0x777d7d, roughness: 1 }),
  };
  const pebble = new THREE.IcosahedronGeometry(1, 0);
  const geometries = new Set([pebble]);
  const generated = [];
  function dispose() {
    root.removeFromParent();
    root.traverse(object => { if (object.isInstancedMesh) object.dispose(); });
    for (const geometry of geometries) geometry.dispose();
    for (const material of Object.values(materials)) material.dispose();
    installed.delete(scene);
    if (scene.userData.habitatDensity?.root === root) delete scene.userData.habitatDensity;
  }
  try {
    for (const plan of plans) {
      const group = new THREE.Group();
      group.name = plan.id;
      group.position.set(plan.x, plan.y, plan.z);
      group.rotation.y = plan.yaw;
      group.userData = { habitatType: plan.type, baseId: plan.baseId, variant: plan.variant };
      const random = randomFor(`${seed}:${plan.id}`), c = Math.cos(plan.yaw), s = Math.sin(plan.yaw);
      function ground(x, z) {
        const y = surface.height(plan.x + c * x + s * z, plan.z - s * x + c * z);
        if (!Number.isFinite(y) || y <= 1) throw new Error(`Unsupported habitat vertex: ${plan.id}`);
        return y - plan.y;
      }
      const surfaces = new Map();
      function meshFrom(vertices, material) {
        if (!surfaces.has(material)) surfaces.set(material, []);
        const target = surfaces.get(material);
        for (const value of vertices) target.push(value);
      }
      function flushSurfaces() {
        for (const [material, vertices] of surfaces) {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
          geometry.computeVertexNormals();
          geometry.computeBoundingBox();
          geometry.computeBoundingSphere();
          geometries.add(geometry);
          const mesh = new THREE.Mesh(geometry, material);
          mesh.frustumCulled = true;
          group.add(mesh);
        }
      }
      const stones = [];
      function stone(x, z, rx, ry, rz) {
        stones.push({ x, y: ground(x, z) + ry * .65, z, rx, ry, rz, yaw: random() * TAU });
      }
      let entranceZ;
      if (plan.type === 'fox_den') {
        const width = 1.25 + random() * .3, height = 1.25 + random() * .25;
        const depth = 3.4 + random() * .7;
        entranceZ = 1.5;
        const outer = [], inner = [];
        const triangle = (array, a, b, d) => array.push(...a, ...b, ...d);
        const quad = (array, a, b, d, e) => { triangle(array, a, b, d); triangle(array, a, d, e); };
        function arc(angle, z, outside) {
          const x = Math.cos(angle) * (width + (outside ? 1.15 : 0));
          return [x, ground(x, z) - .08 + Math.sin(angle) * (height + (outside ? 1.15 : 0)), z];
        }
        // Hollow vaulted tunnel: open mouth, thick arch, roof, sides and closed
        // rear. Terrain itself remains the accessible floor (no painted hole).
        for (let i = 0; i < 16; i++) {
          const a = i * Math.PI / 16, b = (i + 1) * Math.PI / 16;
          for (let j = 0; j < 4; j++) {
            const front = entranceZ - depth * j / 4, rear = entranceZ - depth * (j + 1) / 4;
            quad(outer, arc(a, front, true), arc(b, front, true), arc(b, rear, true), arc(a, rear, true));
            quad(inner, arc(b, front, false), arc(a, front, false), arc(a, rear, false), arc(b, rear, false));
          }
          quad(outer, arc(a, entranceZ, false), arc(b, entranceZ, false), arc(b, entranceZ, true), arc(a, entranceZ, true));
          const rear = entranceZ - depth;
          triangle(inner, [0, ground(0, rear) - .08, rear], arc(a, rear, true), arc(b, rear, true));
        }
        meshFrom(outer, materials.snow);
        meshFrom(inner, materials.earth);
        // Uneven drifts bury the straight tunnel flanks and rear without closing
        // its mouth. Every base follows the existing terrain, within the footprint.
        function drift(cx, cz, rx, rz, rise) {
          const vertices = [], rings = 5, segments = 16;
          function point(ring, segment) {
            const t = ring / rings, a = segment * TAU / segments;
            const ripple = 1 + .065 * Math.sin(a * 3 + plan.variant);
            const x = cx + Math.cos(a) * rx * t * ripple;
            const z = cz + Math.sin(a) * rz * t * ripple;
            return [x, ground(x, z) + .025 + rise * Math.pow(Math.max(0, 1 - t * t), .7), z];
          }
          for (let ring = 0; ring < rings; ring++) for (let i = 0; i < segments; i++) {
            quad(vertices, point(ring,i),point(ring+1,i),point(ring+1,i+1),point(ring,i+1));
          }
          meshFrom(vertices, materials.snow);
        }
        drift(-2.25,-1.15,1.45,2.5,1.25+random()*.55);
        drift(2.25,-1.4,1.5,2.65,1.3+random()*.5);
        drift(0,entranceZ-depth-.65,2.8,1.75,1.4+random()*.45);
        // Exposed dirt apron and a meandering paired paw trail identify the entry.
        const marks=[];
        function patch(x,z,rx,rz) {
          const centre=[x,ground(x,z)+.035,z];
          for(let i=0;i<10;i++){
            const a=i*TAU/10,b=(i+1)*TAU/10;
            triangle(marks,centre,[x+Math.cos(a)*rx,ground(x+Math.cos(a)*rx,z+Math.sin(a)*rz)+.035,z+Math.sin(a)*rz],
              [x+Math.cos(b)*rx,ground(x+Math.cos(b)*rx,z+Math.sin(b)*rz)+.035,z+Math.sin(b)*rz]);
          }
        }
        patch(0,entranceZ+.1,.9,.6);
        for(let i=0;i<12;i++){
          const z=entranceZ+.8+i*.42,x=Math.sin(i*.45)*.35+(i%2?.17:-.17);
          patch(x,z,.075,.11);
          for(let toe=0;toe<3;toe++)patch(x+(toe-1)*.045,z-.11,.023,.035);
        }
        meshFrom(marks,materials.earth);
        for(let i=0;i<12;i++){
          const side=i%2?1:-1;
          stone(side*(width+.2+random()*.6),entranceZ-.2-random()*depth,.2+random()*.25,.16+random()*.2,.2+random()*.3);
        }
        for (let i = 0; i < 18; i++) {
          const angle = Math.PI + i * Math.PI / 17;
          stone(Math.cos(angle) * 3.1, -.4 + Math.sin(angle) * 3.4,
            .65 + random() * .3, .4 + random() * .25, .65 + random() * .3);
        }
      } else {
        // One colony waypoint, five to seven visibly separate stone nest rings.
        entranceZ = 6.8;
        const nests = 5 + plan.variant % 3;
        for (let nest = 0; nest < nests; nest++) {
          const angle = nest * TAU / nests + random() * .12;
          const nx = Math.cos(angle) * 3.8, nz = Math.sin(angle) * 3.8;
          const radius = .8 + random() * .22;
          for (let i = 0; i < 14; i++) {
            const a = i * TAU / 14;
            stone(nx + Math.cos(a) * radius, nz + Math.sin(a) * radius,
              .22 + random() * .07, .16 + random() * .06, .22 + random() * .07);
          }
        }
        // Two stones visibly delimit the clear colony approach marked by its pin.
        stone(-1.1, entranceZ, .4, .3, .4);
        stone(1.1, entranceZ, .4, .3, .4);
      }
      flushSurfaces();
      const instances = new THREE.InstancedMesh(pebble, materials.stone, stones.length);
      const transform = new THREE.Object3D();
      stones.forEach((stone, index) => {
        transform.position.set(stone.x, stone.y, stone.z);
        transform.scale.set(stone.rx, stone.ry, stone.rz);
        transform.rotation.y = stone.yaw;
        transform.updateMatrix();
        instances.setMatrixAt(index, transform.matrix);
      });
      instances.instanceMatrix.needsUpdate = true;
      instances.computeBoundingBox();
      instances.computeBoundingSphere();
      instances.frustumCulled = true;
      group.add(instances);
      root.add(group);
      const x = plan.x + s * entranceZ, z = plan.z + c * entranceZ;
      const entranceHeight = plan.y + ground(0, entranceZ);
      generated.push({ id: plan.id, type: plan.type,
        name: `${plan.type === 'fox_den' ? 'Fox den' : 'Penguin colony'} ${bases.filter(p=>p.type===plan.type).length+generated.filter(p=>p.type===plan.type).length+1}`,
        position: [x, entranceHeight, z] });
    }
    scene.add(root);
    // Required when the parent disables scene.matrixWorldAutoUpdate.
    root.updateMatrixWorld(true);
  } catch (error) {
    dispose();
    throw error;
  }
  const combined = [...originals, ...generated];
  const counts = Object.fromEntries(TYPES.map(type => [type, combined.filter(point => point.type === type).length]));
  scene.userData.habitatDensity = { root, counts, added: generated.length, missing, dispose,
    iceChecked: terrain.length > 0, extentScale: .1, searchRadius: 220 };
  installed.set(scene, combined);
  if (TYPES.some(type => counts[type] !== TARGETS[type])) {
    console.warn('[habitat-density] Safe placement shortfall; retained real sites only.', { counts, targets: TARGETS, missing });
  }
  if (!terrain.length) console.warn('[habitat-density] No colored terrain meshes available; ice exclusion could not be checked.');
  return combined.slice();
}
