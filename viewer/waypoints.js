import { Vector3 } from 'three';

const STORAGE_KEY = 'artic-survival.waypoints.v1';
// Single-colour symbols, distinguished by silhouette.
const ICONS = {
 fox_den: '<path d="M2 2 6 5h4l4-3-1 9-5 4-5-4Z M4.5 8l2 1m3-1-2 1M7 11h2"/>',
 penguin_nest: '<path d="M5 10C3 6 6 2 8 2s5 4 3 8M2 10q6 4 12 0l-2 4H4Z M7 5h2"/>',
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function icon(type) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  node.setAttribute('viewBox', '0 0 16 16');
  node.setAttribute('aria-hidden', 'true');
  node.setAttribute('focusable', 'false');
  node.classList.add('waypoints-icon');
  // Only these constant, inline paths are inserted as markup.
  node.innerHTML = ICONS[type];
  return node;
}

/**
 * Fixed positions use Three.js world coordinates in metres. Parent loads CSS.
 * getPlayer(): {root: Object3D}, Object3D, {position: Vector3 | [x,y,z]},
 * Vector3, or [x,y,z]; null hides the UI until a player is available.
 * setVisible is a persistent gate; update({visible}) is an additional frame gate.
 * Call update from the parent frame loop. This module never handles pointer lock.
 */
export function createWaypoints({ camera, getPlayer, waypoints = [] }) {
  let disabled = new Set();
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved)) disabled = new Set(saved.filter(id => typeof id === 'string'));
  } catch { /* Storage may be unavailable; toggles still work for this session. */ }

  const root = element('div', 'waypoints');
  root.hidden = true;
  const hud = element('div', 'waypoints-hud');
  hud.setAttribute('aria-hidden', 'true');
  const panel = element('details', 'waypoints-panel');
  const summary = element('summary', 'waypoints-summary', 'Locations');
  const hint = element('span', 'waypoints-hint', 'Esc to manage locations');
  hint.hidden = true;
  summary.append(hint);
  const list = element('ul', 'waypoints-list');
  list.setAttribute('aria-label', 'Locations and pinned waypoints');
  panel.append(summary, list);
  root.append(hud, panel);

  const ids = new Set();
  const records = [];
  let disposed = false;
  let enabled = true;
  let frameVisible = true;
  let lastUpdate = -Infinity;
  let dirty = true;
  const playerPosition = new Vector3();
  const projected = new Vector3();
  const view = new Vector3();

  for (const point of waypoints) {
    if (!point || !Object.hasOwn(ICONS, point.type) || point.id == null ||
        !Array.isArray(point.position) || point.position.length !== 3 ||
        !point.position.every(Number.isFinite)) continue;
    const id = String(point.id);
    if (ids.has(id)) continue;
    ids.add(id);
    const name = String(point.name || point.type.replaceAll('_', ' '));
    const marker = element('div', `waypoints-marker waypoints-${point.type}`);
    marker.dataset.waypointId = id;
    marker.hidden = true;
    const arrow = element('span', 'waypoints-arrow', 'âž¤');
    const label = element('span', 'waypoints-label', name);
    const distance = element('span', 'waypoints-distance');
    marker.append(icon(point.type), label, distance);
    hud.append(marker);
    const leader=element('div','waypoints-leader');leader.hidden=true;hud.append(leader);

    const row = element('li', `waypoints-row waypoints-${point.type}`);
    row.dataset.waypointId = id;
    const rowText = element('span', 'waypoints-row-text');
    const rowDistance = element('span', 'waypoints-row-distance', 'â€”');
    rowText.append(element('span', 'waypoints-row-name', name), rowDistance);
    const toggle = element('button', 'waypoints-toggle');
    toggle.type = 'button';
    const record = {
      id, name, type: point.type, position: new Vector3(...point.position), marker, leader,
      distance, rowDistance, toggle, metres: Infinity, pinned: !disabled.has(id),
      order: records.length,
    };
    function refreshToggle() {
      toggle.textContent = record.pinned ? 'Unpin' : 'Pin';
      toggle.setAttribute('aria-pressed', String(record.pinned));
      // Stable accessible name describes the toggle state through aria-pressed.
      toggle.setAttribute('aria-label', `Pin ${name}`);
    }
    record.onToggle = () => {
      record.pinned = !record.pinned;
      refreshToggle();
      // Persist only the disabled ids in this fixed set, keeping storage small.
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(records.filter(r => !r.pinned).map(r => r.id)));
      } catch { /* Private mode/quota failures must not break navigation. */ }
      dirty = true;
      update({ visible: frameVisible });
    };
    toggle.addEventListener('click', record.onToggle);
    refreshToggle();
    row.append(icon(point.type), rowText, toggle);
    list.append(row);
    records.push(record);
  }
  if (!records.length) list.append(element('li', 'waypoints-empty', 'No locations available.'));
  document.body.append(root);

  function readPlayer() {
    const player = getPlayer();
    if (!player) return false;
    const object = player.root || player;
    if (typeof object.getWorldPosition === 'function') object.getWorldPosition(playerPosition);
    else {
      const position = object.position || object;
      if (Array.isArray(position)) playerPosition.fromArray(position);
      else playerPosition.set(position.x, position.y, position.z);
    }
    return Number.isFinite(playerPosition.x) && Number.isFinite(playerPosition.y) && Number.isFinite(playerPosition.z);
  }

  function update({ visible = true } = {}) {
    if (disposed) return;
    frameVisible = Boolean(visible);
    if (!enabled || !frameVisible) {
      root.hidden = true;
      dirty = true;
      return;
    }
    const now = performance.now();
    // Project every frame so markers remain attached while the camera turns.
    dirty = false;
    lastUpdate = now;
    hint.hidden = !document.pointerLockElement;
    if (!readPlayer()) {
      root.hidden = true;
      return;
    }
    root.hidden = false;
    camera.updateWorldMatrix(true, false);
    const width = hud.clientWidth, height = hud.clientHeight;
    const candidates=[];
    for (const record of records) {
      record.metres = playerPosition.distanceTo(record.position);
      const text = `${Math.round(record.metres)} m`;
      if (record.distance.textContent !== text) {
        record.distance.textContent = text;
        record.rowDistance.textContent = text;
      }
      record.marker.hidden = true;record.leader.hidden=true;
      if (!record.pinned) continue;
      // Offset the anchor above the entrance while measuring to its real position.
      projected.copy(record.position);projected.y += 3;
      view.copy(projected).applyMatrix4(camera.matrixWorldInverse);
      if (view.z >= -camera.near) continue;
      projected.project(camera);
      if (!Number.isFinite(projected.x) || !Number.isFinite(projected.y) ||
          Math.abs(projected.x)>1 || Math.abs(projected.y)>1) continue;
      candidates.push({record,x:(projected.x*.5+.5)*width,y:(-projected.y*.5+.5)*height,bearing:Math.atan2(view.x,-view.z)});
    }
    // Fan crowded labels out in eight-degree increments, retaining true anchors.
    const focal=height/(2*Math.tan(camera.fov*Math.PI/360));
    const occupied=[],panelRect=panel.getBoundingClientRect();
    for(const candidate of candidates.sort((a,b)=>a.record.metres-b.record.metres||a.record.order-b.record.order)){
      if(occupied.length>=12)break;
      let placement=null;
      for(const row of [0,-1,1,-2,2]){
        for(const degrees of [0,-8,8,-16,16,-24,24]){
          const angle=candidate.bearing+degrees*Math.PI/180;
          if(Math.abs(angle)>=Math.PI/2)continue;
          const x=width/2+Math.tan(angle)*focal,y=candidate.y+row*84;
          if(x<76||x>width-76||y<100||y>height-65)continue;
          const rect={left:x-72,right:x+72,top:y-76,bottom:y};
          if(rect.left<panelRect.right&&rect.right>panelRect.left&&rect.top<panelRect.bottom&&rect.bottom>panelRect.top)continue;
          if(occupied.some(r=>rect.left<r.right+12&&rect.right+12>r.left&&rect.top<r.bottom+8&&rect.bottom+8>r.top))continue;
          placement={x,y,rect};break;
        }
        if(placement)break;
      }
      if(!placement)continue;
      occupied.push(placement.rect);
      const {record,x:anchorX,y:anchorY}=candidate;
      record.marker.style.left=`${placement.x}px`;record.marker.style.top=`${placement.y}px`;record.marker.hidden=false;
      const dx=anchorX-placement.x,dy=anchorY-placement.y;
      if(Math.hypot(dx,dy)>6){
        record.leader.style.left=`${placement.x}px`;record.leader.style.top=`${placement.y}px`;
        record.leader.style.width=`${Math.hypot(dx,dy)}px`;
        record.leader.style.transform=`rotate(${Math.atan2(dy,dx)}rad)`;record.leader.hidden=false;
      }
    }
  }

  function setVisible(visible) {
    if (disposed) return;
    if(enabled===Boolean(visible))return;
    enabled = Boolean(visible);
    dirty = true;
    if (!enabled) root.hidden = true;
    else update({ visible: frameVisible });
  }

  function onPanelToggle() { dirty = true; }
  panel.addEventListener('toggle', onPanelToggle);

  function dispose() {
    if (disposed) return;
    disposed = true;
    panel.removeEventListener('toggle', onPanelToggle);
    for (const record of records) record.toggle.removeEventListener('click', record.onToggle);
    root.remove();
  }

  return { update, setVisible, dispose };
}

