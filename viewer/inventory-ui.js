let nextInventoryId = 0;

/** The parent owns keyboard shortcuts, pointer lock, and the CSS link. */
export function createInventoryUI({ inventory, onClose, onOpen, onPlace, canPlace=()=>true }) {
  const prefix = `inventory-${++nextInventoryId}`;
  let enabled = false;
  let selectedId = null;
  let confirmingId = null;
  let previousFocus = null;
  let opening = false;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(text, action, key) {
    const node = element('button', 'inventory-button', text);
    node.type = 'button';
    if (key) node.dataset.inventoryFocus = key;
    node.addEventListener('click', action);
    return node;
  }

  const hud = button('Inventory [E]', open);
  hud.classList.add('inventory-hud');
  hud.disabled = true;
  hud.setAttribute('aria-haspopup', 'dialog');
  hud.setAttribute('aria-controls', prefix);
  const dialog = element('dialog', 'inventory-dialog');
  dialog.id = prefix;
  dialog.setAttribute('aria-labelledby', `${prefix}-title`);
  dialog.setAttribute('aria-describedby', `${prefix}-subtitle`);
  const header = element('header', 'inventory-header');
  const heading = element('div');
  const title = element('h2', '', 'Inventory');
  title.id = `${prefix}-title`;
  const subtitle = element('p', '', 'Backpack · carried by your climber');
  subtitle.id = `${prefix}-subtitle`;
  heading.append(title, subtitle);
  const closeButton = button('Close', close, 'close');
  header.append(heading, closeButton);
  const warning = element('p', 'inventory-warning');
  warning.setAttribute('role', 'alert');
  const capacity = element('div', 'inventory-capacity');
  const content = element('div', 'inventory-content');
  const slots = element('div', 'inventory-slots');
  slots.setAttribute('role', 'group');
  slots.setAttribute('aria-label', 'Backpack items');
  const details = element('section', 'inventory-details');
  details.setAttribute('aria-label', 'Selected item details');
  const status = element('p', 'inventory-status');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  content.append(slots, details);
  dialog.append(header, warning, capacity, content, status);
  document.body.append(hud, dialog);

  const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
  const format = value => number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });

  function meter(label, value, max, unit = '') {
    const wrapper = element('div', 'inventory-meter');
    const labelNode = element('label', '', `${label}: ${format(value)} / ${format(max)}${unit}`);
    const bar = element('meter');
    bar.id = `${prefix}-${label.toLowerCase()}`;
    labelNode.htmlFor = bar.id;
    bar.min = 0;
    bar.max = Math.max(1, number(max));
    bar.value = Math.max(0, number(value));
    bar.setAttribute('aria-valuetext', labelNode.textContent);
    wrapper.append(labelNode, bar);
    return wrapper;
  }

  function render() {
    const focusKey = dialog.contains(document.activeElement)
      ? document.activeElement.dataset.inventoryFocus : null;
    const snapshot = inventory.snapshot();
    const items = snapshot.items || [];
    let selected = items.find(item => item.id === selectedId);
    if (!selected) {
      selected = items[0];
      selectedId = selected?.id ?? null;
      confirmingId = null;
    }
    warning.hidden = !snapshot.saveError;
    warning.textContent = snapshot.saveError
      ? `Inventory changes could not be saved. ${typeof snapshot.saveError === 'string' ? snapshot.saveError : 'Progress may be lost when you leave.'}` : '';
    capacity.replaceChildren(
      meter('Weight', snapshot.weight, snapshot.maxWeight, ' kg'),
      meter('Slots', snapshot.slots, snapshot.maxSlots),
    );
    slots.replaceChildren();
    if (!items.length) {
      slots.append(element('p', 'inventory-empty', 'Your backpack is empty. Items you collect will appear here.'));
    }
    for (const [index, item] of items.entries()) {
      const slot = button('', () => {
        selectedId = item.id;
        confirmingId = null;
        status.textContent = '';
        render();
      }, `item-${index}`);
      slot.classList.add('inventory-slot');
      slot.setAttribute('aria-pressed', String(item.id === selectedId));
      slot.append(element('span', 'inventory-item-name', item.name),
        element('span', 'inventory-item-meta', `${item.category || 'Item'} · ×${format(item.quantity)}`));
      slots.append(slot);
    }
    details.replaceChildren();
    if (selected) {
      details.append(element('h3', '', selected.name),
        element('p', 'inventory-category', selected.category || 'Item'),
        element('p', '', selected.description || 'No description available.'),
        element('p', 'inventory-item-meta', `Quantity: ${format(selected.quantity)} · ${format(selected.unitWeight)} kg each`));
      if(onPlace&&['tent','sleeping-bag'].includes(selected.id)){
        const placeButton=button('Place',()=>{if(!canPlace(selected.id))return;const id=selected.id;close();onPlace(id);},'place');
        placeButton.disabled=!canPlace(selected.id);details.append(placeButton);
        if(!canPlace(selected.id))details.append(element('p','','This item cannot be placed here right now.'));
      }
      if (confirmingId === selected.id) {
        const confirmation = element('div', 'inventory-confirmation');
        const prompt = element('p', '', `Permanently discard one ${selected.name}? This cannot be undone.`);
        prompt.id = `${prefix}-discard-warning`;
        const confirm = button('Discard one permanently', () => discard(selected.id), 'confirm');
        confirm.classList.add('inventory-danger');
        confirm.setAttribute('aria-describedby', prompt.id);
        confirmation.append(prompt, confirm, button('Cancel', () => {
          confirmingId = null;
          render();
          details.querySelector('[data-inventory-focus="discard"]')?.focus();
        }, 'cancel'));
        details.append(confirmation);
      } else {
        details.append(button('Discard one…', () => {
          confirmingId = selected.id;
          render();
          details.querySelector('[data-inventory-focus="cancel"]')?.focus();
        }, 'discard'));
      }
    } else {
      details.append(element('h3', '', 'Nothing carried'), element('p', '', 'Select an item to see its details.'));
    }
    if (focusKey && dialog.open) {
      const target = [...dialog.querySelectorAll('[data-inventory-focus]')]
        .find(node => node.dataset.inventoryFocus === focusKey);
      (target || details.querySelector('button') || closeButton).focus();
    }
  }

  function discard(id) {
    confirmingId = null;
    try {
      const result = inventory.remove(id, 1);
      render();
      status.textContent = result.message || (result.ok ? 'One item permanently discarded.' : 'Unable to discard this item.');
    } catch {
      render();
      status.textContent = 'Unable to discard this item.';
    }
  }

  function open() {
    if (!enabled || dialog.open || opening) return;
    opening = true;
    previousFocus = document.activeElement;
    try {
      onOpen?.();
      if (!enabled) return;
      confirmingId = null;
      status.textContent = '';
      render();
      dialog.showModal();
      closeButton.focus();
    } finally {
      opening = false;
    }
  }

  function close() {
    if (!dialog.open) return;
    dialog.close();
    confirmingId = null;
    if (previousFocus?.isConnected && typeof previousFocus.focus === 'function') previousFocus.focus();
    onClose?.();
  }

  // Prevent the browser's implicit Escape close; the parent owns that shortcut.
  dialog.addEventListener('cancel', event => event.preventDefault());
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('button:not(:disabled), [tabindex="0"]')]
      .filter(node => node.getClientRects().length);
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && (document.activeElement === first || !controls.includes(document.activeElement))) {
      event.preventDefault();
      last?.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !controls.includes(document.activeElement))) {
      event.preventDefault();
      first?.focus();
    }
  });
  inventory.subscribe(() => render());
  render();
  return {
    open,
    close,
    isOpen: () => dialog.open || opening,
    setEnabled(value) {
      enabled = Boolean(value);
      hud.disabled = !enabled;
      if (!enabled) close();
    },
  };
}
