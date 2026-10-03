/** Backpack data only. Weights are kilograms; each stack occupies one slot. */
export const ITEM_DEFINITIONS = Object.freeze(Object.fromEntries([
  { id: 'food', name: 'Trail food', description: 'A packed ration of trail food.', category: 'food', unitWeight: 0.3, maxStack: 6 },
  { id: 'water', name: 'Water', description: 'A sealed one-litre bottle of water.', category: 'water', unitWeight: 1, maxStack: 4 },
  { id: 'bandages', name: 'Bandages', description: 'A clean, wrapped bandage.', category: 'medical', unitWeight: 0.05, maxStack: 10 },
  { id: 'rope', name: 'Rope', description: 'A coil of climbing rope.', category: 'equipment', unitWeight: 1.5, maxStack: 1 },
  { id: 'matches', name: 'Matches', description: 'A small waterproof box of matches.', category: 'equipment', unitWeight: 0.02, maxStack: 5 },
  { id: 'ice-axe', name: 'Ice axe', description: 'A steel-headed mountaineering ice axe.', category: 'equipment', unitWeight: 0.75, maxStack: 1 },
  { id: 'tent', name: 'Small tent', description: 'A compact one-person tent. Place on dry, gently sloping ground.', category: 'camping', unitWeight: 2, maxStack: 1 },
  { id: 'sleeping-bag', name: 'Sleeping bag', description: 'An insulated sleeping bag. Place on the ground or inside your tent.', category: 'camping', unitWeight: 1.2, maxStack: 1 },
].map((definition) => [definition.id, Object.freeze(definition)])));

const STORAGE_KEY = 'artic-survival.inventory';
const VERSION = 2;
const MAX_SLOTS = 24;
const MAX_WEIGHT_GRAMS = 20000;
const STARTER_ITEMS = [
  ['food', 3], ['water', 2], ['bandages', 3],
  ['rope', 1], ['matches', 1], ['ice-axe', 1],
  ['tent', 1], ['sleeping-bag', 1],
];
const definitionFor = (id) => typeof id === 'string'
  && Object.prototype.hasOwnProperty.call(ITEM_DEFINITIONS, id)
  ? ITEM_DEFINITIONS[id] : undefined;
const validQuantity = (quantity) => Number.isSafeInteger(quantity) && quantity > 0;

function totals(items) {
  let grams = 0;
  let slots = 0;
  for (const [id, quantity] of items) {
    const definition = definitionFor(id);
    grams += Math.round(definition.unitWeight * 1000) * quantity;
    slots += Math.ceil(quantity / definition.maxStack);
  }
  return { grams, slots };
}

function capacityError(items) {
  const { grams, slots } = totals(items);
  if (grams > MAX_WEIGHT_GRAMS) return 'The backpack cannot hold more than 20 kg.';
  if (slots > MAX_SLOTS) return 'The backpack has only 24 stack slots.';
  return null;
}

function readSavedItems(raw) {
  const saved = JSON.parse(raw);
  if (!saved || ![1, VERSION].includes(saved.version) || !Array.isArray(saved.items)) {
    throw new Error('Unsupported or invalid inventory save.');
  }
  const items = new Map();
  for (const item of saved.items) {
    if (!item || !definitionFor(item.id) || !validQuantity(item.quantity)
      || items.has(item.id)) {
      throw new Error('Inventory save contains unknown, duplicate, or invalid items.');
    }
    items.set(item.id, item.quantity);
  }
  if(saved.version===1){
    items.set('tent',(items.get('tent')||0)+1);
    items.set('sleeping-bag',(items.get('sleeping-bag')||0)+1);
  }
  const placements=saved.version===1?[]:saved.placements??[];
  if(!Array.isArray(placements)||placements.length>100||placements.some(p=>
    !p||!['tent','sleeping-bag'].includes(p.id)||
    !['x','y','z','yaw','slopeX','slopeZ'].every(k=>Number.isFinite(p[k]))||
    Math.abs(p.x)>1e7||Math.abs(p.z)>1e7||Math.abs(p.y)>1e5||Math.hypot(p.slopeX,p.slopeZ)>.3||
    (p.tentIndex!==undefined&&(p.id!=='sleeping-bag'||!Number.isSafeInteger(p.tentIndex)||p.tentIndex<0||placements[p.tentIndex]?.id!=='tent'||placements[p.tentIndex]?.tentIndex!==undefined||p.y!==0||p.slopeX!==0||p.slopeZ!==0))
  ))throw new Error('Invalid campsite save.');
  const migrationOverflow=saved.version===1||saved.campingMigration===true;
  const count=totals(items);
  const error = migrationOverflow&&count.grams<=MAX_WEIGHT_GRAMS+3200&&count.slots<=MAX_SLOTS+2?null:capacityError(items);
  if (error) throw new Error(error);
  return {items,placements,migrationOverflow};
}

/**
 * storage accepts a localStorage-compatible object; null disables persistence.
 * Version 2 saves keep item quantities and campsite placements together.
 * Version 1 saves receive camping supplies once, preserving all existing items.
 * Quantities may span multiple stacks. Invalid saves are rejected in full;
 * the starter kit is used, and the original save is left until a successful edit.
 * saveError is null or a diagnostic string. Failed saves keep edits in memory.
 */
export function createInventory({ storage } = {}) {
  let items = new Map(STARTER_ITEMS);
  let placements=[];
  let migrationOverflow=false;
  let saveError = null;
  const listeners = new Set();

  if (storage === undefined) {
    try {
      storage = typeof window === 'undefined' ? null : window.localStorage;
    } catch {
      storage = null;
      saveError = 'Local storage is unavailable; inventory changes are kept in memory only.';
    }
  }
  if (storage != null) {
    try {
      const raw = storage.getItem(STORAGE_KEY);
      if (raw !== null && raw !== undefined) ({items,placements,migrationOverflow}=readSavedItems(raw));
    } catch (error) {
      saveError = `Could not load inventory; using starter kit. ${error instanceof Error ? error.message : 'Storage read failed.'}`;
    }
  }

  function snapshot() {
    const { grams, slots } = totals(items);
    return {
      items: Array.from(items, ([id, quantity]) => {
        const { name, description, category, unitWeight } = definitionFor(id);
        return { id, name, description, category, quantity, unitWeight };
      }),
      weight: grams / 1000,
      maxWeight: MAX_WEIGHT_GRAMS / 1000,
      slots,
      maxSlots: MAX_SLOTS,
      saveError,
      placements:placements.map(p=>({...p})),
    };
  }

  function commit(next, message) {
    items = next;
    if(!capacityError(items))migrationOverflow=false;
    if (storage != null) {
      try {
        storage.setItem(STORAGE_KEY, JSON.stringify({
          version: VERSION,
          placements,
          campingMigration:migrationOverflow,
          items: Array.from(items, ([id, quantity]) => ({ id, quantity })),
        }));
        saveError = null;
      } catch {
        saveError = 'Could not save inventory; changes are kept in memory only.';
      }
    }
    // Give every subscriber its own detached view of this exact commit.
    const notifications = Array.from(listeners, (callback) => [callback, snapshot()]);
    const result = { ok: true, message: saveError ? `${message} ${saveError}` : message };
    for (const [callback, state] of notifications) {
      try { callback(state); } catch { /* A subscriber cannot undo a committed edit. */ }
    }
    return result;
  }

  function change(id, quantity, removing) {
    const definition = definitionFor(id);
    if (!definition) return { ok: false, message: 'Unknown inventory item.' };
    if (!validQuantity(quantity)) {
      return { ok: false, message: 'Quantity must be a positive safe integer.' };
    }
    const current = items.get(id) || 0;
    if (removing && quantity > current) {
      return { ok: false, message: `Not enough ${definition.name} in the backpack.` };
    }
    const updated = removing ? current - quantity : current + quantity;
    if (!Number.isSafeInteger(updated)) {
      return { ok: false, message: 'Quantity is too large.' };
    }
    const next = new Map(items);
    if (updated === 0) next.delete(id);
    else next.set(id, updated);
    const error = capacityError(next);
    if (error&&!removing) return { ok: false, message: error };
    return commit(next, `${removing ? 'Removed' : 'Added'} ${quantity} × ${definition.name}.`);
  }

  return Object.freeze({
    snapshot,
    deploy(id,position){
      if(!['tent','sleeping-bag'].includes(id)||!(items.get(id)>0))return {ok:false,message:'This item is not in your backpack.'};
      if(placements.length>=100)return {ok:false,message:'Campsite placement limit reached.'};
      if(!position||!['x','y','z','yaw','slopeX','slopeZ'].every(k=>Number.isFinite(position[k]))||Math.hypot(position.slopeX,position.slopeZ)>.3)return {ok:false,message:'Invalid campsite position.'};
      const tentIndex=position.tentIndex;
      if(tentIndex!==undefined&&(id!=='sleeping-bag'||!Number.isSafeInteger(tentIndex)||tentIndex<0||placements[tentIndex]?.id!=='tent'||placements[tentIndex]?.tentIndex!==undefined||position.y!==0||position.slopeX!==0||position.slopeZ!==0))return {ok:false,message:'Invalid tent placement.'};
      const next=new Map(items),quantity=next.get(id)-1;
      if(quantity)next.set(id,quantity);else next.delete(id);
      // Placements are append-only, so their indices also identify tents in older saves.
      placements=[...placements,{id,...Object.fromEntries(['x','y','z','yaw','slopeX','slopeZ'].map(k=>[k,position[k]])),...(tentIndex===undefined?{}:{tentIndex})}];
      return commit(next,`${definitionFor(id).name} placed.`);
    },
    add: (id, quantity = 1) => change(id, quantity, false),
    remove: (id, quantity = 1) => change(id, quantity, true),
    // Subscriptions notify after successful edits, not upon registration.
    subscribe(callback) {
      if (typeof callback !== 'function') throw new TypeError('Subscriber must be a function.');
      const listener = (state) => callback(state);
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
  });
}
