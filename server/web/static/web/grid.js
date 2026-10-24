(function () {
  "use strict";
  const grid = document.querySelector("[data-live-grid]");
  if (!grid) return;

  const scheme = location.protocol === "https:" ? "wss" : "ws";
  let delay = 1000;

  function setText(tile, field, text) {
    const el = tile.querySelector('[data-field="' + field + '"]');
    if (el) el.textContent = text;
  }

  function render(pc) {
    const tile = grid.querySelector('[data-pc-id="' + pc.id + '"]');
    if (!tile) return;
    tile.className = "tile st-" + pc.state;
    setText(tile, "screen", pc.state_label);
    setText(tile, "state", pc.state_label);
    if ("user" in pc) setText(tile, "user", pc.user || "");
    if ("foreground" in pc) {
      const fg = pc.foreground;
      setText(tile, "foreground", fg ? [fg.process, fg.title].filter(Boolean).join(" · ") : "");
    }
  }

  function connect() {
    const ws = new WebSocket(scheme + "://" + location.host + "/ws/live");
    ws.onopen = function () { delay = 1000; };
    ws.onmessage = function (event) {
      const message = JSON.parse(event.data);
      if (message.type === "pc") render(message.pc);
    };
    ws.onclose = function () {
      setTimeout(connect, delay + Math.random() * 1000);
      delay = Math.min(delay * 2, 30000);
    };
  }

  connect();
})();
