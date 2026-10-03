// Publish only browser resources, preserving the viewer's absolute URLs.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'dist');
const files = new Set(['viewer/index.html', 'viewer/app.js', 'viewer/gameplay.js', 'viewer/footprints.js', 'viewer/snow-impressions.js', 'viewer/terrain.mjs', 'viewer/terrain-render.js', 'Human_Animated.glb', 'viewer/data/world.json']);
if(fs.existsSync(path.join(root,'viewer/data/tent-door.glb')))files.add('viewer/data/tent-door.glb');
for(const file of ['viewer/waypoints.js','viewer/waypoints.css','viewer/data/waypoints.json'])files.add(file);
files.add('viewer/habitat-density.js');
files.add('viewer/fox-dens.js');
files.add('viewer/wildlife-stream.js');
files.add('viewer/world-seed.js');
const world = JSON.parse(fs.readFileSync(path.join(root, 'viewer/data/world.json'), 'utf8'));
for (const file of ['inventory.js','inventory-ui.js','inventory.css','camping.js','tent-setup.js','tent-interior.js','tent-door.js']) files.add(`viewer/${file}`);

function addDirectory(relative) {
  for (const entry of fs.readdirSync(path.join(root, relative), { withFileTypes: true })) {
    const file = `${relative}/${entry.name}`;
    if (entry.isDirectory()) addDirectory(file);
    else if (entry.isFile()) files.add(file);
  }
}
addDirectory('viewer/vendor');
for (const terrain of [world.terrain].flat().filter(Boolean)) {
  files.add(`viewer/data/${terrain.file}`);
}
for (const actor of world.actors) {
  if (!actor.asset.startsWith('/') || !actor.asset.endsWith('.glb')) {
    throw new Error(`Expected a local GLB asset: ${actor.asset}`);
  }
  files.add(actor.asset.slice(1));
}

// Validate everything before replacing a previous build.
let bytes = 0;
for (const file of files) {
  const source = path.resolve(root, file);
  if (!source.startsWith(root + path.sep) || file.split(/[\\/]/).includes('..')) {
    throw new Error(`Asset path escapes the project: ${file}`);
  }
  if (!fs.existsSync(source)) throw new Error(`Missing asset: ${file}`);
  const header = Buffer.alloc(128);
  const descriptor = fs.openSync(source, 'r');
  try { fs.readSync(descriptor, header, 0, header.length, 0); }
  finally { fs.closeSync(descriptor); }
  if (header.toString('utf8').startsWith('version https://git-lfs.github.com/spec/v1')) {
    throw new Error(`${file} is a Git LFS pointer. Enable Git LFS in Vercel Settings > Git and redeploy, or run git lfs pull locally.`);
  }
  if (file.endsWith('.glb') && header.toString('ascii', 0, 4) !== 'glTF') {
    throw new Error(`Invalid GLB model: ${file}`);
  }
  bytes += fs.statSync(source).size;
}
fs.rmSync(output, { recursive: true, force: true });
for (const file of files) {
  const destination = path.join(output, file);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.copyFileSync(path.join(root, file), destination);
}
fs.copyFileSync(path.join(root, 'viewer/index.html'), path.join(output, 'index.html'));
console.log(`Built ${files.size + 1} static files in dist (${(bytes / 1024 / 1024).toFixed(1)} MiB).`);
