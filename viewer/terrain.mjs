// Index triangles in X/Z cells so movement does not raycast the entire world.
export class TerrainSurface {
  constructor(cellSize = 256) { this.cellSize = cellSize; this.cells = new Map(); }
  add(positions, indices) {
    const s = this.cellSize;
    for (let i = 0; i < indices.length; i += 3) {
      const a = indices[i]*3, b = indices[i+1]*3, c = indices[i+2]*3;
      const t = [positions[a],positions[a+1],positions[a+2],positions[b],positions[b+1],positions[b+2],positions[c],positions[c+1],positions[c+2]];
      for (let x=Math.floor(Math.min(t[0],t[3],t[6])/s); x<=Math.floor(Math.max(t[0],t[3],t[6])/s); x++) {
        for (let z=Math.floor(Math.min(t[2],t[5],t[8])/s); z<=Math.floor(Math.max(t[2],t[5],t[8])/s); z++) {
          const key=`${x},${z}`;
          if (!this.cells.has(key)) this.cells.set(key, []);
          this.cells.get(key).push(t);
        }
      }
    }
  }
  height(x,z) {
    let height = -Infinity;
    for (const t of this.cells.get(`${Math.floor(x/this.cellSize)},${Math.floor(z/this.cellSize)}`) || []) {
      const d=(t[5]-t[8])*(t[0]-t[6])+(t[6]-t[3])*(t[2]-t[8]);
      if (Math.abs(d)<1e-10) continue;
      const a=((t[5]-t[8])*(x-t[6])+(t[6]-t[3])*(z-t[8]))/d;
      const b=((t[8]-t[2])*(x-t[6])+(t[0]-t[6])*(z-t[8]))/d;
      if (a>=-1e-6 && b>=-1e-6 && a+b<=1.000001) height=Math.max(height,a*t[1]+b*t[4]+(1-a-b)*t[7]);
    }
    return Number.isFinite(height) ? height : null;
  }
}
