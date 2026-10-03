// One exposure accumulator; no scene objects or background timers.
export function createCold({ onDeath }) {
  const limit = 360;
  let exposure = 0, dead = false, previousActive = false;
  let lastPaint = -Infinity, lastText = '';
  const hud = document.createElement('div');
  hud.id = 'cold-status';
  hud.style.cssText = 'position:fixed;top:48px;left:12px;max-width:min(520px,90vw);padding:10px;background:#07141ef2;color:white;font:14px system-ui;white-space:pre-line;pointer-events:none;z-index:10003';
  hud.setAttribute('role', 'status');
  hud.setAttribute('aria-live', 'polite');
  document.body.append(hud);
  const end = document.createElement('dialog');
  end.setAttribute('aria-label', 'Expedition ended from cold');
  const reason = document.createElement('p');
  reason.textContent = 'Expedition ended: cold exposure reached 360 active game seconds. Enter a tent or fox den before exposure reaches the limit.';
  const restart = document.createElement('button');
  restart.textContent = 'Restart fresh expedition';
  restart.addEventListener('click', () => { if (dead) window.location.reload(); });
  end.addEventListener('cancel', event => event.preventDefault());
  end.append(reason, restart);
  document.body.append(end);

  function paint(now, active, shelter, suspended) {
    if (now - lastPaint < 1000) return;
    lastPaint = now;
    const warning = exposure >= 240 ? 'URGENT' : exposure >= 120 ? 'WARNING' : 'COLD';
    const state = !active ? `${suspended}: exposure frozen.`
      : shelter ? `${shelter === 'tent' ? 'Tent: recovering 3' : 'Fox den: recovering 1'} exposure seconds per active game second${exposure === 0 ? ' · fully recovered' : ''}.`
      : 'Outdoors: +1 exposure second per active game second.';
    const remaining = Math.ceil((limit - exposure) * 10) / 10;
    const text = `${warning} · Exposure ${exposure.toFixed(1)} / 360 game sec\nApproximately ${remaining.toFixed(1)} active outdoor game seconds until death (updated once/sec).\n${state}\nShelter: E → tent → Place on ground; approach zipper and press F. Or approach a fox den entrance and press F. Setup, positioning and entry take time: remain exposed until inside.`;
    if (text !== lastText) { hud.textContent = text; lastText = text; }
  }

  return {
    dead: () => dead,
    // Input transitions discard inactive wall time, including tab suspension.
    resetClock() { previousActive = false; },
    update(now, dt, active, shelter, suspended = 'Paused') {
      if (dead) return;
      // Match movement's bounded game time; never charge a resume frame.
      const elapsed = !previousActive || !active ? 0 : Math.max(0, Math.min(dt, .05));
      previousActive = active;
      exposure = Math.max(0, Math.min(limit, exposure + elapsed * (shelter === 'tent' ? -3 : shelter === 'den' ? -1 : 1)));
      if (exposure >= limit) {
        dead = true;
        hud.textContent = 'Expedition ended from cold · Exposure 360 / 360 sec · 0 seconds remaining.';
        onDeath(); // Explicit, one-shot terminal event; bypass HUD throttling.
        end.showModal();
        restart.focus();
        return;
      }
      paint(now, active, shelter, suspended);
    },
  };
}
