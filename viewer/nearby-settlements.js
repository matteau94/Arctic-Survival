import * as THREE from 'three';

// Translate existing roots only, before registering any settlement collisions.
export function placeNearbySettlements({ actors, definitions, surface, spawn, seed }) {
  const bounds = new Map(actors.map(a => [a, new THREE.Box3().setFromObject(a.root)]));
  const report = [];
  // No authored foundation naming convention is available. Require actual
  // underside hits for every visible mesh, including separate village pieces.
  // Roofs/props that cannot satisfy this strict support proof cause omission.
  function supportSamples(actor) {
    const meshes = [];
    actor.root.traverseVisible(object => { if (object.isMesh) meshes.push(object); });
    const samples = [], ray = new THREE.Raycaster();
    ray.ray.direction.set(0, 1, 0);
    let budget = 4096;
    for (const mesh of meshes) {
      if (mesh.isSkinnedMesh || mesh.isInstancedMesh) return null;
      const b = new THREE.Box3().setFromObject(mesh);
      if (b.isEmpty()) return null;
      const nx = Math.max(1, Math.ceil((b.max.x - b.min.x) / 2));
      const nz = Math.max(1, Math.ceil((b.max.z - b.min.z) / 2));
      budget -= (nx + 1) * (nz + 1);
      if (budget < 0) return null;
      for (let ix = 0; ix <= nx; ix++) for (let iz = 0; iz <= nz; iz++) {
        const x = b.min.x + (b.max.x - b.min.x) * ix / nx;
        const z = b.min.z + (b.max.z - b.min.z) * iz / nz;
        ray.ray.origin.set(x, b.min.y - 1, z);
        ray.far = b.max.y - b.min.y + 2;
        const hit = ray.intersectObject(mesh, false)[0];
        if (!hit || !Number.isFinite(hit.point.y)) return null;
        samples.push(hit.point.clone());
      }
    }
    return samples.length ? samples : null;
  }
  for (const [type, near, far] of [['cabin', 150, 300], ['village', 250, 500]]) {
    const choices = actors.filter(a => a.type === type).sort((a, b) =>
      a.root.position.distanceToSquared(new THREE.Vector3(...spawn)) -
      b.root.position.distanceToSquared(new THREE.Vector3(...spawn)));
    let accepted = null;
    const rejected = [];
    for (const actor of choices) {
      const box = bounds.get(actor), size = box.getSize(new THREE.Vector3());
      if (box.isEmpty() || ![size.x, size.y, size.z].every(Number.isFinite)) continue;
      // Two-metre support grid, bounded even for enormous authored villages.
      const nx = Math.max(1, Math.ceil((size.x + 4) / 2));
      const nz = Math.max(1, Math.ceil((size.z + 4) / 2));
      if ((nx + 3) * (nz + 3) > 4096) { rejected.push({ id: actor.id, reason: 'Footprint exceeds sample budget.' }); continue; }
      const supports = supportSamples(actor);
      if (!supports) { rejected.push({ id: actor.id, reason: 'Distinct loaded mesh undersides cannot be established within sample budget.' }); continue; }
      for (let attempt = 0; attempt < 160; attempt++) {
        const angle = seed / 4294967296 * Math.PI * 2 + attempt * 2.399963229728653;
        const radius = near + (far - near) * Math.sqrt(attempt / 159);
        const x = spawn[0] + Math.cos(angle) * radius, z = spawn[2] + Math.sin(angle) * radius;
        const dx = x - actor.root.position.x, dz = z - actor.root.position.z;
        const candidate = box.clone().translate(new THREE.Vector3(dx, 0, dz));
        const clearance = candidate.clone().expandByScalar(12);
        const spawnDX = Math.max(candidate.min.x - spawn[0], 0, spawn[0] - candidate.max.x);
        const spawnDZ = Math.max(candidate.min.z - spawn[2], 0, spawn[2] - candidate.max.z);
        if (Math.hypot(spawnDX, spawnDZ) < 35 || [...bounds].some(([other, b]) =>
          other !== actor && !b.isEmpty() && clearance.min.x < b.max.x && clearance.max.x > b.min.x &&
          clearance.min.z < b.max.z && clearance.max.z > b.min.z)) continue;
        let low = Infinity, high = -Infinity, valid = true;
        // Include exact footprint corners/edges as well as the two-metre apron.
        const xs = [candidate.min.x, candidate.max.x,
          ...Array.from({ length: nx + 1 }, (_, i) => candidate.min.x - 2 + (size.x + 4) * i / nx)];
        const zs = [candidate.min.z, candidate.max.z,
          ...Array.from({ length: nz + 1 }, (_, i) => candidate.min.z - 2 + (size.z + 4) * i / nz)];
        for (const px of xs) {
          if (!valid) break;
          for (const pz of zs) {
          const h = surface.height(px, pz), hx = surface.height(px + 1, pz), hz = surface.height(px, pz + 1);
          if (![h, hx, hz].every(Number.isFinite) || Math.min(h, hx, hz) <= 1 ||
              Math.hypot(hx - h, hz - h) > .08) { valid = false; break; }
          low = Math.min(low, h); high = Math.max(high, h);
          if (high - low > .12) { valid = false; break; }
          }
        }
        if (!valid) continue;
        const dy = high + .015 - box.min.y;
        // A single global minimum cannot establish support for other foundations.
        // Every sampled mesh underside must fit the same rigid translation.
        if (supports.some(p => {
          const h = surface.height(p.x + dx, p.z + dz);
          const gap = p.y + dy - h;
          return !Number.isFinite(h) || h <= 1 || gap < -.015 || gap > .135;
        })) continue;
        const nextY = actor.root.position.y + dy;
        if (Math.hypot(x - spawn[0], nextY - spawn[1], z - spawn[2]) > far) continue;
        actor.root.position.set(x, nextY, z);
        actor.root.updateMatrixWorld(true);
        actor.position = actor.root.position.toArray();
        actor.origin.copy(actor.root.position);
        actor.home = actor.root.position.clone();
        if (actor.target) actor.target.add(new THREE.Vector3(dx, dy, dz));
        actor.ground = undefined;
        const data = definitions.find(d => d.id === actor.id);
        data.position = actor.position.slice();
        data.ground = undefined;
        if (data.target) data.target = actor.target.toArray();
        bounds.set(actor, new THREE.Box3().setFromObject(actor.root));
        accepted = { type, id: actor.id, position: actor.position.slice() };
        break;
      }
      if (accepted) break;
    }
    report.push(accepted || { type, omitted: true, rejected,
      reason: 'No footprint with all sampled mesh undersides supported; ambiguous foundations retain original positions.' });
  }
  if (report.some(item => item.omitted)) console.warn('[nearby-settlements]', report);
  return report;
}
