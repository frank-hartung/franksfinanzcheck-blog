// ============================================================
//  FranksFinanzcheck – Design-System-Builder (Figma-Plugin)
// ============================================================
//  QUELLE: figma/design-system-builder/source.js  (diese Datei ist NICHT
//  generiert; hier steht nur die Datenmarke, der Datenblock kommt aus
//  der SSOT).
//  GENERAT: figma/design-system-builder/code.js    (erzeugt von
//  scripts/design_handoff.py aus data/design/handoff.yaml – nicht von
//  Hand bearbeiten, sonst stoppt `design:handoff:check`).
//
//  WAS DIESES PLUGIN TUT
//  ---------------------
//  Es baut die Figma-Datei „FranksFinanzcheck – Design System“ aus der
//  SSOT auf – deterministisch und wiederholbar:
//    · Seiten in der Reihenfolge aus figma.page_order
//    · Variablen-Sammlungen: Primitives, Semantik (Hell/Dunkel), Abstand,
//      Radius – mit Aliasing und Dev-Mode-Code-Syntax (var(--ff-…))
//    · Textstile aus der echten Typo-Skala (Desktop + Mobil)
//    · Effektstile aus der Schatten-Skala
//    · Farbstile als Fallback für Werkzeuge ohne Variables-API
//    · Komponenten-Sets je Komponente: Zustand × Modus, als Varianten
//    · eine Cover-Seite, die den Stand der Datei belegt
//
//  WAS ES NICHT TUT
//  ----------------
//  Keine Netzverbindung (manifest: allowedDomains ["none"]), keine
//  Veröffentlichung, keine Änderung an bestehenden Produktionsdateien.
//  Zweiter Lauf: Es wird nichts doppelt angelegt – vorhandene Sammlungen,
//  Stile und Komponenten werden ERKANNT und übersprungen, das Protokoll
//  sagt, was neu ist und was schon stand.
// ============================================================

const DATA = DATA_MARKE;

/* ---------- Farbmathematik ---------- */
function hexToRgb(hex) {
  const h = String(hex).replace('#', '');
  return {
    r: parseInt(h.slice(0, 2), 16) / 255,
    g: parseInt(h.slice(2, 4), 16) / 255,
    b: parseInt(h.slice(4, 6), 16) / 255,
  };
}

function solid(hex) {
  return { type: 'SOLID', color: hexToRgb(hex) };
}

/* ---------- Protokoll ---------- */
const log = { neu: [], vorhanden: [], fehler: [] };
function neu(was) { log.neu.push(was); }
function da(was) { log.vorhanden.push(was); }
function fehler(was, err) {
  log.fehler.push(was + ': ' + (err && err.message ? err.message : String(err)));
}

/* ---------- 1. Seiten ---------- */
async function buildPages() {
  const vorhanden = figma.root.children.map((p) => p.name);
  const seiten = [];
  for (const name of DATA.pages) {
    if (vorhanden.includes(name)) {
      seiten.push(figma.root.children.find((p) => p.name === name));
      da('Seite „' + name + '“');
    } else {
      const page = figma.createPage();
      page.name = name;
      seiten.push(page);
      neu('Seite „' + name + '“');
    }
  }
  return seiten;
}

/* ---------- 2. Variablen ---------- */
async function collection(name, modeNames) {
  const vorhanden = await figma.variables.getLocalVariableCollectionsAsync();
  const treffer = vorhanden.find((c) => c.name === name);
  if (treffer) {
    da('Sammlung „' + name + '“');
    return treffer;
  }
  const c = figma.variables.createVariableCollection(name);
  // Der erste Modus heißt bei Figma „Mode 1“ – umbenennen, nicht löschen.
  c.renameMode(c.modes[0].modeId, modeNames[0]);
  for (let i = 1; i < modeNames.length; i += 1) c.addMode(modeNames[i]);
  neu('Sammlung „' + name + '“ (' + modeNames.join(' / ') + ')');
  return c;
}

async function variable(coll, name, type, scope, code) {
  const alle = await figma.variables.getLocalVariablesAsync();
  const treffer = alle.find((v) => v.name === name && v.variableCollectionId === coll.id);
  if (treffer) { da('Variable ' + name); return treffer; }
  const v = figma.variables.createVariable(name, coll, type);
  try { if (scope) v.scopes = scope; } catch (e) { /* ältere Figma-Version */ }
  if (code) { try { v.setVariableCodeSyntax('WEB', code); } catch (e) { /* optional */ } }
  neu('Variable ' + name);
  return v;
}

function modeId(coll, name) {
  const m = coll.modes.find((x) => x.name === name);
  return (m || coll.modes[0]).modeId;
}

async function buildVariables() {
  const out = { color: {}, sem: {}, float: {} };

  /* Primitives (ein Modus, Rohwerte) */
  const prim = await collection('Primitives', ['Wert']);
  const primMode = modeId(prim, 'Wert');
  for (const [name, hex] of Object.entries(DATA.colors)) {
    const v = await variable(prim, name, 'COLOR', ['ALL_FILLS', 'STROKE_COLOR'], 'var(--ff-' + name + ')');
    v.setValueForMode(primMode, { ...hexToRgb(hex), a: 1 });
    out.color[name] = v;
  }

  /* Semantik (Hell/Dunkel, ausschließlich Aliase) */
  const sem = await collection('Semantik', ['Hell', 'Dunkel']);
  for (const mode of ['Hell', 'Dunkel']) {
    const mid = modeId(sem, mode);
    const rolle = DATA.semantic[mode === 'Hell' ? 'light' : 'dark'];
    for (const [name, ziel] of Object.entries(rolle)) {
      const v = await variable(sem, name, 'COLOR',
        ['ALL_FILLS', 'STROKE_COLOR'],
        'var(--ff-' + name + ')');
      const base = out.color[ziel];
      if (base) v.setValueForMode(mid, figma.variables.createVariableAlias(base));
      out.sem[mode + '/' + name] = v;
    }
  }

  /* Abstand & Radius als FLOAT – damit Auto-Layout sie binden kann */
  const sp = await collection('Abstand', ['Wert']);
  const spMode = modeId(sp, 'Wert');
  for (const px of DATA.spacing) {
    const v = await variable(sp, 'space/' + px, 'FLOAT', ['GAP', 'WIDTH_HEIGHT'], px + 'px');
    v.setValueForMode(spMode, px);
    out.float['space/' + px] = v;
  }
  const ra = await collection('Radius', ['Wert']);
  const raMode = modeId(ra, 'Wert');
  for (const [name, px] of Object.entries(DATA.radius)) {
    const v = await variable(ra, 'radius/' + name, 'FLOAT', ['CORNER_RADIUS'], px + 'px');
    v.setValueForMode(raMode, px);
    out.float['radius/' + name] = v;
  }
  return out;
}

/* ---------- 3. Stile ---------- */
function ensureTextStyle(name) {
  const treffer = figma.getLocalTextStyles().find((s) => s.name === name);
  if (treffer) { da('Textstil ' + name); return treffer; }
  const s = figma.createTextStyle();
  s.name = name;
  neu('Textstil ' + name);
  return s;
}

async function buildTextStyles() {
  const fonts = {};
  const stile = {};
  for (const [name, t] of Object.entries(DATA.typography)) {
    for (const [variante, px] of [['Desktop', t.size], ['Mobil', t.mobile]]) {
      const style = ensureTextStyle('Typo/' + name + '/' + variante);
      const family = t.family;
      const gewicht = t.weight;
      const key = family + ':' + gewicht + ':' + (t.italic ? 'i' : 'n');
      if (!fonts[key]) {
        const wunsch = gewicht >= 700 ? 'Bold' : (t.italic ? 'Italic' : 'Regular');
        try {
          await figma.loadFontAsync({ family, style: wunsch });
          fonts[key] = wunsch;
        } catch (e) {
          // Marken-Schrift nicht installiert: Inter ist der dokumentierte
          // Ersatz (DESIGN.md §2), nicht der stille Absturz.
          try {
            await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });
            fonts[key] = 'Regular';
            fehler('Schrift „' + family + '“ fehlt, Ersatz Inter', e);
          } catch (e2) {
            fonts[key] = 'Regular';
            fehler('Schrift „' + family + '“ und Inter fehlen', e2);
          }
        }
      }
      style.fontName = { family, style: fonts[key] };
      style.fontSize = px;
      style.lineHeight = { unit: 'PERCENT', value: Math.round(t.lineHeight * 100) };
      if (t.tracking && t.tracking !== '0') {
        style.letterSpacing = { unit: 'PERCENT', value: parseFloat(t.tracking) * 100 };
      }
      stile[name + '/' + variante] = style;
    }
  }
  return stile;
}

function buildEffectStyles(elevation) {
  for (const [name, shadow] of Object.entries(elevation)) {
    if (figma.getLocalEffectStyles().find((s) => s.name === 'Schatten/' + name)) {
      da('Effektstil Schatten/' + name);
      continue;
    }
    const style = figma.createEffectStyle();
    style.name = 'Schatten/' + name;
    const m = /^0 (\d+)px (\d+)px rgba\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)$/.exec(shadow.trim());
    style.effects = m ? [{
      type: 'DROP_SHADOW',
      color: {
        r: Number(m[3]) / 255, g: Number(m[4]) / 255, b: Number(m[5]) / 255,
        a: Number(m[6]),
      },
      offset: { x: 0, y: Number(m[1]) },
      radius: Number(m[2]),
      spread: 0,
      visible: true,
      blendMode: 'NORMAL',
    }] : [];
    neu('Effektstil Schatten/' + name);
  }
}

function buildPaintStyles(colors) {
  for (const [name, hex] of Object.entries(colors)) {
    if (figma.getLocalPaintStyles().find((s) => s.name === 'Farbe/' + name)) {
      da('Farbstil Farbe/' + name);
      continue;
    }
    const style = figma.createPaintStyle();
    style.name = 'Farbe/' + name;
    style.paints = [solid(hex)];
    neu('Farbstil Farbe/' + name);
  }
}

/* ---------- 4. Komponenten ---------- */
function textNode(inhalt, stilId, colorVar) {
  const t = figma.createText();
  t.fontName = { family: 'Inter', style: 'Regular' };
  t.characters = inhalt;
  if (stilId) t.textStyleId = stilId;
  if (colorVar) {
    try {
      t.fills = [figma.variables.setBoundVariableForPaint(solid('#2E2E33'), 'color', colorVar)];
    } catch (e) { /* Bindung optional */ }
  }
  return t;
}

async function buildComponentSet(spec, seite, vars, stile) {
  const bestand = seite.children.filter((n) => n.type === 'COMPONENT_SET' && n.name === spec.figma);
  if (bestand.length) {
    da('Komponente ' + spec.figma);
    return bestand[0];
  }

  // Zustände → deutsche Vokabeln. Farbe ist ein Modus, kein Zustand.
  const zustaende = [];
  const sehen = new Set();
  for (const s of spec.states) {
    if (s === 'dark') continue;
    const wert = DATA.state_labels[s] || s;
    if (sehen.has(wert)) continue;
    sehen.add(wert);
    zustaende.push(wert);
  }

  const teile = [];
  for (const modus of ['Hell', 'Dunkel']) {
    for (const zustand of zustaende) {
      const c = figma.createComponent();
      c.name = 'Zustand=' + zustand + ', Modus=' + modus;
      c.resize(320, 48);
      c.layoutMode = 'VERTICAL';
      c.primaryAxisSizingMode = 'AUTO';
      c.counterAxisSizingMode = 'AUTO';
      c.primaryAxisAlignItems = 'CENTER';
      c.counterAxisAlignItems = 'CENTER';
      c.paddingLeft = 24; c.paddingRight = 24;
      c.paddingTop = 12; c.paddingBottom = 12;
      c.cornerRadius = spec.id.indexOf('button') === 0 ? DATA.radius.pill : DATA.radius.md;
      const semKey = (modus === 'Hell' ? 'light' : 'dark') + '/surface';
      if (vars.sem[semKey]) {
        try { c.fills = [figma.variables.setBoundVariableForPaint(solid('#FFFFFF'), 'color', vars.sem[semKey])]; } catch (e) { /* optional */ }
      }
      // Beschriftung aus dem Figma-Namen, nicht aus der technischen ID:
      // der Entwurf soll lesbar sein ("Article card", nicht "article-card").
      const beschriftung = spec.figma.split('/').pop();
      const t = textNode(beschriftung, (stile['body/Desktop'] || {}).id,
        vars.sem[(modus === 'Hell' ? 'light' : 'dark') + '/text']);
      c.appendChild(t);
      t.layoutAlign = 'CENTER';
      if (zustand === 'Deaktiviert') c.opacity = 0.48;
      teile.push(c);
    }
  }
  if (!teile.length) return null;
  const set = figma.combineAsVariants(teile, seite);
  set.name = spec.figma;
  set.x = 0;
  set.y = 0;
  neu('Komponenten-Set ' + spec.figma + ' (' + teile.length + ' Varianten)');
  return set;
}

/* ---------- 5. Cover ---------- */
function buildCover(seite, zahlen) {
  const vorhanden = seite.children.find((n) => n.name === 'Cover/Titel');
  if (vorhanden) { da('Cover'); return; }
  const f = figma.createFrame();
  f.name = 'Cover/Titel';
  f.resize(1440, 1024);
  f.fills = [solid(DATA.colors.emerald)];
  f.layoutMode = 'VERTICAL';
  f.paddingLeft = 96; f.paddingRight = 96; f.paddingTop = 96; f.paddingBottom = 96;
  f.itemSpacing = 24;

  const titel = figma.createText();
  titel.fontName = { family: 'Inter', style: 'Bold' };
  titel.characters = DATA.projekt.name + '\nDesign System';
  titel.fontSize = 96;
  titel.lineHeight = { unit: 'PERCENT', value: 100 };
  titel.fills = [solid(DATA.colors.white)];
  f.appendChild(titel);

  const zeile = figma.createText();
  zeile.fontName = { family: 'Inter', style: 'Regular' };
  zeile.characters = DATA.projekt.ziel + '\nStand ' + DATA.stand + ' · ' + DATA.projekt.sprache
    + '\n' + zahlen.collections + ' Sammlungen · ' + zahlen.variablen + ' Variablen · '
    + zahlen.stile + ' Stile · ' + zahlen.komponenten + ' Komponenten-Sets';
  zeile.fontSize = 24;
  zeile.lineHeight = { unit: 'PERCENT', value: 150 };
  zeile.fills = [solid(DATA.colors['emerald-bright'])];
  f.appendChild(zeile);

  const strich = figma.createRectangle();
  strich.resize(160, 6);
  strich.fills = [solid(DATA.colors.yellow)];
  f.appendChild(strich);

  const herkunft = figma.createText();
  herkunft.fontName = { family: 'Inter', style: 'Regular' };
  herkunft.characters = 'Erzeugt aus data/design/handoff.yaml durch scripts/design_handoff.py.\n'
    + 'Diese Datei ist ein Entwurfswerkzeug. Produktionswahrheit bleiben DESIGN.md,\n'
    + 'data/design/regelwerk.yaml und der Hugo-Bestand.';
  herkunft.fontSize = 16;
  herkunft.lineHeight = { unit: 'PERCENT', value: 160 };
  herkunft.fills = [solid(DATA.colors.white)];
  herkunft.opacity = 0.72;
  f.appendChild(herkunft);

  seite.appendChild(f);
  f.x = 0; f.y = 0;
  neu('Cover');
}

/* ---------- Rechte ---------- */
// Ein Plugin mit `documentAccess: dynamic-page` braucht zwei Dinge, die Figma
// beim Start einmalig abfragt: den Seitenwechsel (`currentpage`) und den
// Zugriff auf Schriften und Stile (`textreview`). Fehlt eines – ältere Figma-
// Version, abgelehnte Abfrage, kopierter Aufruf –, bricht der Aufbau sonst
// MITTENDRIN ab und hinterlässt eine halb gefüllte Datei. Deshalb wird vorher
// geprüft und im Zweifel gar nicht erst gebaut.
function fehlendeRechte() {
  const fehlt = [];
  if (typeof figma.setCurrentPageAsync !== 'function') {
    fehlt.push('currentpage (Seitenwechsel)');
  }
  if (typeof figma.loadFontAsync !== 'function') {
    fehlt.push('textreview (Schriften und Stile)');
  }
  return fehlt;
}

/* ---------- Bestand zählen (für die UI) ---------- */
async function bestand() {
  let variablen = 0;
  try { variablen = (await figma.variables.getLocalVariablesAsync()).length; } catch (e) { /* alt */ }
  return {
    collections: 4,
    variablen,
    stile: figma.getLocalTextStyles().length + figma.getLocalEffectStyles().length
      + figma.getLocalPaintStyles().length,
    komponenten: DATA.components.length,
  };
}

/* ---------- Lauf ---------- */
async function main() {
  // Jeder Lauf berichtet nur über sich selbst. Ohne diesen Reset würde
  // ein zweiter Lauf die Ergebnisse des ersten mitzählen und „Neu: 128“
  // melden, obwohl nichts Neues entstanden ist.
  log.neu.length = 0;
  log.vorhanden.length = 0;
  log.fehler.length = 0;

  const seiten = await buildPages();
  const byName = {};
  for (const p of seiten) byName[p.name] = p;

  const vars = await buildVariables();
  const stile = await buildTextStyles();
  buildEffectStyles(DATA.elevation);
  buildPaintStyles(DATA.colors);

  const seite = byName['02 Components'] || seiten[0];
  await figma.setCurrentPageAsync(seite);
  let x = 0;
  let y = 0;
  let reihe = 0;
  for (const spec of DATA.components) {
    const set = await buildComponentSet(spec, seite, vars, stile);
    if (!set) continue;
    set.x = x;
    set.y = y;
    x += set.width + 80;
    reihe += 1;
    if (reihe % 3 === 0) { x = 0; y += set.height + 120; }
  }

  const cover = byName['00 Cover'] || seiten[0];
  await figma.setCurrentPageAsync(cover);
  buildCover(cover, {
    collections: 4,
    variablen: Object.keys(vars.color).length + Object.keys(vars.sem).length + Object.keys(vars.float).length,
    stile: Object.keys(stile).length + Object.keys(DATA.elevation).length + Object.keys(DATA.colors).length,
    komponenten: DATA.components.length,
  });

  const zeilen = [
    '✅ Design-System aufgebaut',
    'Neu: ' + log.neu.length,
    'Bereits vorhanden: ' + log.vorhanden.length,
    'Hinweise: ' + log.fehler.length,
    '',
  ];
  for (const f of log.neu.slice(0, 40)) zeilen.push('+ ' + f);
  for (const f of log.fehler.slice(0, 6)) zeilen.push('· ' + f);
  figma.ui.postMessage({ type: 'fertig', text: zeilen.join('\n') });
}

async function los() {
  const fehlt = fehlendeRechte();
  if (fehlt.length) {
    figma.ui.postMessage({
      type: 'fertig',
      text: '⛔ Aufbau nicht gestartet – es fehlt der Zugriff:\n· '
        + fehlt.join('\n· ')
        + '\n\nSo beheben: Plugin in Figma schließen, mit „Plugins → Development → '
        + 'FranksFinanzcheck“ neu starten und die Zugriffsabfrage mit „Allow“ '
        + 'bestätigen. In älteren Figma-Versionen: Figma aktualisieren.',
    });
    return;
  }
  await figma.loadAllPagesAsync();
  await main();
  figma.ui.postMessage({ type: 'bestand', zahlen: await bestand() });
}

figma.showUI(__html__, { width: 360, height: 560, themeColors: true });

figma.ui.onmessage = (msg) => {
  if (!msg) return;
  if (msg.type === 'bestand') {
    bestand().then((zahlen) => figma.ui.postMessage({ type: 'bestand', zahlen }));
  }
  if (msg.type === 'aufbauen') {
    los().catch((e) => {
      const text = '❌ Aufbau abgebrochen: ' + (e && e.message ? e.message : String(e));
      figma.ui.postMessage({ type: 'fertig', text });
    });
  }
};
