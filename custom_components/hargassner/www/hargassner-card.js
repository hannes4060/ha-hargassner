/*
 * Hargassner-Karte für Home Assistant
 * Optik angelehnt an das Kesseldisplay (Neo HV): Kessel mit Brennraum,
 * Puffer mit Temperaturverlauf, Boiler, Heizkreis und Soll/Ist-Werte.
 *
 * Die Sensoren werden automatisch über das Attribut "schluessel" gefunden,
 * das die Integration jedem Sensor mitgibt. Konfiguration:
 *
 *   type: custom:hargassner-card
 *   title: Holzvergaser          # optional
 *   show_values: true            # optional, Soll/Ist-Tabelle
 */

const CARD_VERSION = "0.4.4";

const BURNING = new Set(["Anheizen", "Leistungsbrand"]);
const LOADED = new Set(["Tür offen", "Anheizen", "Leistungsbrand"]);
const GLOW = new Set(["Restwärme"]);

// Temperatur -> Farbe wie im Display: kalt blau, mittel violett, heiß rot
function tempColor(t, cold = 30, hot = 65) {
  if (t === null || Number.isNaN(t)) return "#3a3d46";
  const stops = [
    [0, [43, 79, 214]],
    [0.5, [155, 63, 181]],
    [1, [224, 53, 43]],
  ];
  const x = Math.max(0, Math.min(1, (t - cold) / (hot - cold)));
  let i = 0;
  while (i < stops.length - 2 && x > stops[i + 1][0]) i++;
  const [x0, c0] = stops[i];
  const [x1, c1] = stops[i + 1];
  const f = (x - x0) / (x1 - x0);
  const c = c0.map((v, k) => Math.round(v + (c1[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

const fmt = (v, digits = 0, unit = "") =>
  v === null || v === undefined || Number.isNaN(v)
    ? "–"
    : `${Number(v).toFixed(digits)}${unit}`;

class HargassnerCard extends HTMLElement {
  setConfig(config) {
    this._config = { show_values: true, ...config };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._lastKey = null;
    if (this._hass) this.hass = this._hass;
  }

  static getStubConfig() {
    return { show_values: true };
  }

  getCardSize() {
    return this._config && this._config.show_values ? 8 : 5;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config || !this.shadowRoot) return; // setConfig kommt noch
    let data;
    try {
      data = this._collect(hass);
    } catch (err) {
      this._renderError(err);
      return;
    }
    const key = JSON.stringify(data);
    if (key === this._lastKey) return;
    this._lastKey = key;
    try {
      this._render(data);
    } catch (err) {
      this._renderError(err);
    }
  }

  _renderError(err) {
    console.error("hargassner-card:", err);
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div class="screen">
      <div class="notice err">Hargassner-Karte: Fehler beim Zeichnen<br><small>${String(
        (err && err.message) || err
      ).replace(/</g, "&lt;")}</small></div></div></ha-card>`;
  }

  // Ordnet Entity-IDs den Feldschlüsseln zu. Primär über die Entity-Registry
  // (Plattform "hargassner" + translation_key), weil HA bei nicht verfügbaren
  // Sensoren die Zusatz-Attribute (auch "schluessel") weglässt.
  _keymap(hass) {
    const map = {};
    for (const [id, e] of Object.entries(hass.entities || {})) {
      if (e && e.platform === "hargassner" && e.translation_key) map[id] = e.translation_key;
    }
    for (const [id, st] of Object.entries(hass.states)) {
      const k = st.attributes && st.attributes.schluessel;
      if (k && !map[id]) map[id] = k;
    }
    return map;
  }

  _collect(hass) {
    const v = { _state: null, _hk: null, _found: 0, _unavail: 0, _conn: null };
    const map = this._keymap(hass);
    for (const [id, k] of Object.entries(map)) {
      const st = hass.states[id];
      if (!st) continue;
      if (k === "verbindung") {
        v._conn = st.state === "on";
        continue;
      }
      if (!id.startsWith("sensor.")) continue;
      v._found++;
      const bad = st.state === "unavailable" || st.state === "unknown";
      if (bad) v._unavail++;
      if (k === "kessel_zustand") {
        v._state = bad ? null : st.state;
      } else if (k === "hk1_status") {
        v._hk = bad ? null : st.state;
      } else {
        const n = parseFloat(st.state);
        v[k] = Number.isNaN(n) ? null : n;
      }
    }
    return v;
  }

  _notice(d) {
    if (d._found === 0)
      return `<div class="notice err">Keine Hargassner-Sensoren gefunden.<br><small>Ist die Integration „Hargassner (lokal)“ eingerichtet und aktiv?</small></div>`;
    if (d._conn === false || d._unavail >= d._found)
      return `<div class="notice">Keine Verbindung zum Kessel – die Integration verbindet automatisch neu.<br><small>Läuft parallel ein anderer Telnet-Client (z. B. nc)? Der Kessel lässt evtl. nur eine Verbindung zu.</small></div>`;
    return "";
  }

  _row(label, soll, ist, unit, max) {
    const pct = ist === null || ist === undefined ? 0 : Math.max(0, Math.min(100, (ist / max) * 100));
    const spct = soll === null || soll === undefined ? null : Math.max(0, Math.min(100, (soll / max) * 100));
    return `
      <div class="row">
        <span class="lbl">${label}</span>
        <span class="num">${soll === undefined ? "" : fmt(soll, unit === "%" && soll % 1 ? 1 : 0, unit)}</span>
        <span class="num ist">${fmt(ist, unit === "%" && ist % 1 ? 1 : 0, unit)}</span>
        <span class="bar"><i style="width:${pct}%"></i>${spct === null ? "" : `<b style="left:${spct}%"></b>`}</span>
      </div>`;
  }

  _logs() {
    const rows = [];
    for (let r = 0; r < 6; r++) {
      const y = 92 + r * 17;
      const off = r % 2 ? 6 : 0;
      rows.push(`<rect x="${54 + off}" y="${y}" width="${46 - off}" height="13" rx="5" class="log"/>`);
      rows.push(`<rect x="${103}" y="${y}" width="${50 - off}" height="13" rx="5" class="log"/>`);
      rows.push(`<circle cx="${58 + off}" cy="${y + 6.5}" r="3.4" class="ring"/>`);
    }
    return rows.join("");
  }

  _flames(power) {
    const h = 0.55 + 0.45 * Math.max(0, Math.min(1, (power || 0) / 100));
    const flame = (x, w, d, cls) => `
      <path class="flame ${cls}" style="animation-delay:${d}s;transform-origin:${x}px 240px;transform:scaleY(${h})"
        d="M${x - w} 240 C${x - w} 222 ${x - w / 3} 214 ${x} 192 C${x + w / 3} 214 ${x + w} 222 ${x + w} 240 Z"/>`;
    return (
      flame(70, 14, 0, "f1") + flame(92, 16, 0.3, "f2") + flame(116, 15, 0.15, "f1") +
      flame(140, 13, 0.45, "f2") + flame(82, 8, 0.2, "f3") + flame(106, 9, 0.5, "f3") +
      flame(130, 8, 0.05, "f3")
    );
  }

  _render(d) {
    const st = d._state;
    const burning = BURNING.has(st);
    const loaded = LOADED.has(st);
    const pTop = tempColor(d.puffer_oben);
    const pMid = tempColor(d.puffer_mitte);
    const pBot = tempColor(d.puffer_unten);
    const kColor = tempColor(d.kessel_ist, 30, 85);
    const fill = d.puffer_fuellgrad;
    const fillY = 104 + 160 * (1 - Math.max(0, Math.min(100, fill || 0)) / 100);
    const hkOn = d._hk ? d._hk === "Heizen" : d.hk1_vorlauf_soll !== null && d.hk1_vorlauf_soll > 0;
    const title = this._config.title ? `<div class="title">${this._config.title}</div>` : "";

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        ${title}
        <div class="screen">
          <div class="head">
            <span class="state ${burning ? "hot" : st === "Tür offen" ? "warn" : ""}">
              <i></i>Kessel: ${st || "–"}
            </span>
            <span class="out">Außen ${fmt(d.aussen, 0, " °C")}<small> · Ø ${fmt(d.aussen_gemittelt, 0, " °C")}</small></span>
          </div>
          ${this._notice(d)}
          <svg viewBox="0 0 480 290" class="scene" role="img" aria-label="Kessel, Puffer und Boiler">
            <defs>
              <linearGradient id="hg-puf" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0.12" stop-color="${pTop}"/>
                <stop offset="0.5" stop-color="${pMid}"/>
                <stop offset="0.9" stop-color="${pBot}"/>
              </linearGradient>
              <linearGradient id="hg-ember" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#ffd25a"/>
                <stop offset="1" stop-color="#e85a14"/>
              </linearGradient>
              <clipPath id="hg-tank"><rect x="252" y="100" width="84" height="168" rx="30"/></clipPath>
              <clipPath id="hg-fire"><rect x="50" y="188" width="108" height="54"/></clipPath>
            </defs>

            <!-- Kessel: Dämmung, Mantel, Wassermantel -->
            <rect x="22" y="44" width="172" height="232" rx="4" class="shell"/>
            <rect x="28" y="50" width="160" height="220" class="ins-o"/>
            <rect x="34" y="56" width="148" height="208" class="ins-y"/>
            <rect x="41" y="63" width="134" height="194" class="water" style="stroke:${kColor}"/>
            <rect x="48" y="84" width="114" height="166" class="chamber"/>

            <!-- Wassertemperatur oben -->
            <rect x="74" y="58" width="104" height="26" style="fill:${kColor}"/>
            <text x="126" y="77" class="t big" text-anchor="middle">${fmt(d.kessel_ist, 0, "°C")}</text>

            <!-- Rauchgas -->
            <rect x="8" y="58" width="64" height="26" class="flue ${burning ? "flue-hot" : ""}"/>
            <text x="40" y="77" class="t big" text-anchor="middle">${fmt(d.rauchgas, 0, "°C")}</text>
            <path d="M40 58 V36" class="pipe"/>
            ${burning ? `<path d="M40 34 q-6 -8 0 -16 q6 -8 0 -16" class="smoke"/>` : ""}

            <!-- Luftklappen rechts -->
            <rect x="164" y="92" width="9" height="40" class="flap y"/>
            <rect x="164" y="134" width="9" height="20" class="flap b"/>
            <rect x="164" y="156" width="9" height="16" class="flap y"/>
            <rect x="164" y="186" width="12" height="7" class="flap r" style="opacity:${0.35 + (d.sekundaerluft || 0) / 100}"/>
            <rect x="164" y="196" width="12" height="7" class="flap r" style="opacity:${0.35 + (d.primaerluft || 0) / 100}"/>
            <rect x="164" y="210" width="9" height="40" class="flap y"/>

            <!-- Füllraum -->
            ${loaded ? this._logs() : `<text x="105" y="150" class="t mid dim" text-anchor="middle">Füllen</text>`}

            <!-- Brennraum -->
            <rect x="50" y="188" width="108" height="54" class="grate"/>
            ${burning ? `<g clip-path="url(#hg-fire)">${this._flames(d.leistung)}</g>
              <rect x="58" y="236" width="92" height="5" rx="2" fill="url(#hg-ember)"/>
              <text x="104" y="204" class="t mid outline" text-anchor="middle">${fmt(d.leistung, 0, "%")}</text>` : ""}
            ${GLOW.has(st) ? `<rect x="58" y="230" width="92" height="10" rx="4" fill="url(#hg-ember)" class="glow"/>` : ""}

            <!-- Rücklauf / Vorlauf Leitungen -->
            <path d="M194 120 H252" class="line hot"/>
            <path d="M194 236 H252" class="line cold"/>
            <text x="198" y="228" class="t sm dim">RL ${fmt(d.ruecklauf_ist, 0, "°")}</text>

            <!-- Pumpe + Mischer -->
            <g transform="translate(222 176)">
              <circle r="13" class="pump ${burning ? "on" : ""}"/>
              <path d="M-4 -7 L8 0 L-4 7 Z" class="pump-tri ${burning ? "on" : ""}"/>
            </g>
            <g transform="translate(222 208)" class="valve ${burning ? "on" : ""}">
              <path d="M-11 -8 L0 0 L-11 8 Z M11 -8 L0 0 L11 8 Z M-5 -12 L5 -12 L0 0 Z"/>
            </g>

            <!-- Puffer -->
            <text x="294" y="64" class="t mid" text-anchor="middle">Puffer</text>
            <text x="294" y="86" class="t big" text-anchor="middle">${fmt(fill, 0, "%")}</text>
            <rect x="248" y="96" width="92" height="176" rx="34" class="tank-o"/>
            <g clip-path="url(#hg-tank)">
              <rect x="252" y="100" width="84" height="168" fill="url(#hg-puf)"/>
              <rect x="252" y="100" width="84" height="${Math.max(0, fillY - 100)}" class="unfilled"/>
              <path d="M252 ${fillY} H336" class="fillline"/>
            </g>
            <!-- Boilerwendel -->
            <g class="coil">
              <path d="M268 112 h52 M266 120 h56 M268 128 h52 M266 136 h56 M268 144 h52"/>
              <path d="M268 112 v32 M320 112 v32"/>
            </g>
            <text x="294" y="170" class="t mid" text-anchor="middle">${fmt(d.puffer_oben, 0, "°C")}</text>
            <text x="294" y="212" class="t mid" text-anchor="middle">${fmt(d.puffer_mitte, 0, "°C")}</text>
            <text x="294" y="254" class="t mid" text-anchor="middle">${fmt(d.puffer_unten, 0, "°C")}</text>

            <!-- Boiler -->
            <text x="350" y="124" class="t mid">Boiler</text>
            <text x="350" y="146" class="t big">${fmt(d.boiler1, 0, "°C")}</text>

            <!-- Heizkreis 1 -->
            <rect x="350" y="176" width="122" height="96" rx="6" class="box"/>
            <text x="362" y="198" class="t mid">HK 1</text>
            <circle cx="456" cy="193" r="6" class="sun ${hkOn ? "on" : ""}"/>
            <text x="362" y="222" class="t sm dim">VL Ist</text>
            <text x="462" y="222" class="t sm" text-anchor="end">${fmt(d.hk1_vorlauf_ist, 0, "°C")}</text>
            <text x="362" y="242" class="t sm dim">VL Soll</text>
            <text x="462" y="242" class="t sm" text-anchor="end">${fmt(d.hk1_vorlauf_soll, 0, "°C")}</text>
            <text x="362" y="262" class="t sm dim">Status</text>
            <text x="462" y="262" class="t sm" text-anchor="end">${d._hk || (d.hk1_vorlauf_soll === null || d.hk1_vorlauf_soll === undefined ? "–" : hkOn ? "Ein" : "Aus")}</text>
          </svg>

          ${this._config.show_values ? `
          <div class="vals">
            <div class="row hdr"><span></span><span class="num">Soll</span><span class="num">Ist</span><span></span></div>
            ${this._row("Kesseltemp.", d.kessel_soll, d.kessel_ist, "°C", 100)}
            ${this._row("Saugzug", d.saugzug_soll, d.saugzug_ist, "%", 100)}
            ${this._row("O₂", d.o2_soll, d.o2_ist, "%", 21)}
            ${this._row("Primärluft", d.primaerluft_soll, d.primaerluft, "%", 100)}
            ${this._row("Sekundärluft", d.sekundaerluft_soll, d.sekundaerluft, "%", 100)}
            ${this._row("Leistung", undefined, d.leistung, "%", 100)}
          </div>` : ""}
        </div>
      </ha-card>`;
  }
}

const STYLE = `
  :host { --hg-bg:#16181d; --hg-panel:#20232a; --hg-text:#ece9e1; --hg-dim:#9a9890;
          --hg-orange:#f08a1c; --hg-yellow:#f2c230; --hg-blue:#2f6fe4; --hg-red:#d9412b; }
  ha-card { overflow:hidden; background:var(--hg-bg); color:var(--hg-text);
            font-family: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace; }
  .title { padding:12px 16px 0; font-size:15px; font-weight:600; letter-spacing:.02em; }
  .screen { padding:12px 14px 14px; }
  .head { display:flex; justify-content:space-between; align-items:baseline; gap:8px; flex-wrap:wrap;
          font-size:15px; margin-bottom:4px; }
  .state { display:inline-flex; align-items:center; gap:8px; font-weight:600; }
  .state i { width:9px; height:9px; border-radius:50%; background:#5d6068; }
  .state.hot i { background:var(--hg-orange); box-shadow:0 0 8px var(--hg-orange); animation:pulse 1.6s infinite; }
  .state.warn i { background:var(--hg-yellow); }
  .out { color:var(--hg-text); } .out small { color:var(--hg-dim); font-size:12px; }
  .scene { width:100%; height:auto; display:block; }
  .notice { margin:6px 0 4px; padding:8px 10px; border-radius:8px; font-size:12.5px; line-height:1.4;
            background:#3a3216; color:#f2d98a; border:1px solid #5a4c1c; }
  .notice.err { background:#3a1a16; color:#f2b3a8; border-color:#5a2a22; }
  .notice small { color:inherit; opacity:.8; }
  .t { fill:var(--hg-text); font-family:inherit; }
  .t.big { font-size:17px; font-weight:600; } .t.mid { font-size:14px; } .t.sm { font-size:11.5px; }
  .t.dim { fill:var(--hg-dim); }
  .t.outline { paint-order:stroke; stroke:#0e0f12; stroke-width:4px; font-weight:600; }
  .shell { fill:#2a2d35; stroke:#4a4d55; }
  .ins-o { fill:none; stroke:var(--hg-orange); stroke-width:6; }
  .ins-y { fill:none; stroke:var(--hg-yellow); stroke-width:6; }
  .water { fill:none; stroke-width:7; }
  .chamber { fill:#0e0f12; }
  .flue { fill:#3a1414; stroke:#d8d4cc; stroke-width:1.5; }
  .flue-hot { fill:#6a1a12; }
  .pipe { stroke:#6b6e76; stroke-width:8; }
  .smoke { fill:none; stroke:#8a8d94; stroke-width:2.5; stroke-linecap:round; opacity:.6;
           animation:smoke 3s ease-in-out infinite; }
  .flap.y { fill:var(--hg-yellow); } .flap.b { fill:var(--hg-blue); } .flap.r { fill:var(--hg-red); }
  .log { fill:#d9cba9; stroke:#8c7b58; stroke-width:1; }
  .ring { fill:none; stroke:#8c7b58; stroke-width:1; }
  .grate { fill:#141519; stroke:#2c2f36; }
  .flame { animation:flicker 1.2s ease-in-out infinite alternate; }
  .glow { animation:pulse 2.4s ease-in-out infinite; }
  .flame.f1 { fill:#f08a1c; } .flame.f2 { fill:#e8541a; } .flame.f3 { fill:#ffd25a; }
  .line { stroke-width:5; fill:none; } .line.hot { stroke:var(--hg-red); } .line.cold { stroke:var(--hg-blue); }
  .pump { fill:#20232a; stroke:#d8d4cc; stroke-width:2.5; }
  .pump.on { stroke:#57c46b; }
  .pump-tri { fill:#d8d4cc; } .pump-tri.on { fill:#57c46b; }
  .valve path { fill:#d8d4cc; } .valve.on path { fill:#57c46b; }
  .tank-o { fill:#20232a; stroke:#d8d4cc; stroke-width:3; }
  .unfilled { fill:#0e0f12; opacity:.55; }
  .fillline { stroke:#ece9e1; stroke-width:1; stroke-dasharray:4 4; opacity:.7; }
  .coil path { fill:none; stroke:#f2e6e6; stroke-width:2; opacity:.75; }
  .box { fill:var(--hg-panel); stroke:#3a3d46; }
  .sun { fill:#4a4d55; } .sun.on { fill:var(--hg-yellow); filter:drop-shadow(0 0 4px var(--hg-yellow)); }
  .vals { margin-top:10px; border-top:1px solid #2e3139; padding-top:8px; display:grid; gap:5px; }
  .row { display:grid; grid-template-columns: 1.3fr .7fr .7fr 1.6fr; align-items:center; gap:8px; font-size:13px; }
  .row.hdr { color:var(--hg-dim); font-size:11.5px; }
  .lbl { color:var(--hg-text); }
  .num { text-align:right; color:var(--hg-dim); font-variant-numeric:tabular-nums; }
  .num.ist { color:var(--hg-text); font-weight:600; }
  .bar { position:relative; height:6px; background:#2a2d35; border-radius:3px; }
  .bar i { position:absolute; inset:0 auto 0 0; background:linear-gradient(90deg,var(--hg-yellow),var(--hg-orange));
           border-radius:3px; transition:width .6s; }
  .bar b { position:absolute; top:-3px; width:2px; height:12px; background:var(--hg-text); border-radius:1px; }
  @keyframes flicker { 0% { opacity:.85; translate:0 1px; } 50% { opacity:1; translate:-1px -2px; }
                        100% { opacity:.9; translate:1px 0; } }
  @keyframes smoke { 0%,100% { transform:translateY(0); opacity:.35; } 50% { transform:translateY(-4px); opacity:.7; } }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.45; } }
  @media (prefers-reduced-motion: reduce) { .flame, .smoke, .state.hot i { animation:none; } }
`;

if (!customElements.get("hargassner-card")) {
  customElements.define("hargassner-card", HargassnerCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "hargassner-card",
    name: "Hargassner Kessel",
    description: "Kessel, Puffer und Heizkreis im Stil des Hargassner-Displays",
    preview: true,
  });
  console.info(`%c HARGASSNER-CARD %c ${CARD_VERSION} `, "background:#f08a1c;color:#111", "background:#20232a;color:#eee");
}
