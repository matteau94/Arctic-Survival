// Reuse exported linear vertex colors; no textures or extra render passes are needed.
export function createTerrainMaterial(THREE) {
  const material = new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 1, metalness: 0, side: THREE.DoubleSide
  });
  material.onBeforeCompile = shader => {
    shader.vertexShader = 'varying vec3 terrainWorldPosition;\n' + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace(
      '#include <worldpos_vertex>',
      '#include <worldpos_vertex>\nterrainWorldPosition = (modelMatrix * vec4(transformed, 1.0)).xyz;'
    );
    shader.fragmentShader = 'varying vec3 terrainWorldPosition;\n' + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <color_fragment>',
      `#include <color_fragment>
      #ifdef USE_COLOR
        float iceSurface = smoothstep(0.16, 0.30, vColor.b - vColor.r)
                         * smoothstep(0.32, 0.60, vColor.g);
        vec2 icePosition = terrainWorldPosition.xz * 0.035;
        vec2 bend = vec2(sin(icePosition.y * 1.7), sin(icePosition.x * 1.3)) * 0.34;
        vec2 fracture = abs(fract(icePosition + bend) - 0.5);
        float edge = min(fracture.x, fracture.y);
        float aa = max(fwidth(edge), 0.005);
        float cracks = 1.0 - smoothstep(0.012, 0.012 + aa, edge);
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.67, 0.81, 0.88), cracks * iceSurface * 0.55);
        float drift = sin(terrainWorldPosition.x * 0.21 + sin(terrainWorldPosition.z * 0.035));
        diffuseColor.rgb *= 0.985 + 0.015 * drift;
      #endif`
    );
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <roughnessmap_fragment>',
      `#include <roughnessmap_fragment>
      #ifdef USE_COLOR
        // Cyan ice has a much stronger blue/red separation than snow or rock.
        // Fade the response on dark surfaces so seabeds and den interiors stay matte.
        float terrainIce = smoothstep(0.16, 0.30, vColor.b - vColor.r)
                         * smoothstep(0.32, 0.60, vColor.g);
        roughnessFactor = mix(roughnessFactor, 0.30, terrainIce);
      #endif`
    );
  };
  material.customProgramCacheKey = () => 'terrain-ice-fractures-v2';
  return material;
}

// Keep vertex buffers shared while giving the renderer useful terrain culling bounds.
export function createTerrainTiles(THREE, geometry, material) {
  const position = geometry.getAttribute('position');
  const index = geometry.getIndex();
  if (!position || !index || index.count % 3 !== 0) {
    throw new Error('Terrain tiles require an indexed triangle geometry.');
  }
  const cellSize = 2048;
  const buckets = new Map();
  for (let i = 0; i < index.count; i += 3) {
    const a = index.getX(i), b = index.getX(i + 1), c = index.getX(i + 2);
    const x = Math.floor((position.getX(a) + position.getX(b) + position.getX(c)) / (3 * cellSize));
    const z = Math.floor((position.getZ(a) + position.getZ(b) + position.getZ(c)) / (3 * cellSize));
    const key = `${x},${z}`;
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = {indices: [], bounds: new THREE.Box3()};
      buckets.set(key, bucket);
    }
    bucket.indices.push(a, b, c);
    // A triangle can cross a cell boundary: include its complete extent.
    for (const vertex of [a, b, c]) {
      const vx = position.getX(vertex), vy = position.getY(vertex), vz = position.getZ(vertex);
      bucket.bounds.min.x = Math.min(bucket.bounds.min.x, vx);
      bucket.bounds.min.y = Math.min(bucket.bounds.min.y, vy);
      bucket.bounds.min.z = Math.min(bucket.bounds.min.z, vz);
      bucket.bounds.max.x = Math.max(bucket.bounds.max.x, vx);
      bucket.bounds.max.y = Math.max(bucket.bounds.max.y, vy);
      bucket.bounds.max.z = Math.max(bucket.bounds.max.z, vz);
    }
  }
  return Array.from(buckets, ([key, bucket]) => {
    const tileGeometry = new THREE.BufferGeometry();
    for (const [name, attribute] of Object.entries(geometry.attributes)) {
      tileGeometry.setAttribute(name, attribute);
    }
    tileGeometry.setIndex(bucket.indices);
    tileGeometry.boundingBox = bucket.bounds;
    // computeBoundingSphere would inspect every shared vertex, defeating culling.
    tileGeometry.boundingSphere = bucket.bounds.getBoundingSphere(new THREE.Sphere());
    const mesh = new THREE.Mesh(tileGeometry, material);
    mesh.name = `terrain-${key}`;
    return mesh;
  });
}
