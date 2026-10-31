#!/usr/bin/env node
// ============================================================
//  FIGMA-PLUGIN-SIMULATION – das Plugin wird ohne Figma geprüft
//  ------------------------------------------------------------
//  WARUM ES DIESE DATEI GIBT (31.10.2026)
//  --------------------------------------
//  Ein Figma-Plugin ist Code, der in einer Umgebung läuft, die im CI
//  nicht existiert. Genau deshalb wird es sonst nur „von Hand mal
//  gestartet“ – und Fehler wie ein fehlender Log-Reset fallen erst beim
//  Kunden auf. Diese Datei bildet die Plugin-API so weit nach, dass der
//  komplette Aufbau real durchläuft: Seiten, Variablen mit Aliasen,
//  Text-/Farb-/Effektstile, Komponenten-Sets, Cover.
//
//  WAS SIE BEWEIST
//  ---------------
//    1. Der Aufbau läuft ohne Ausnahme bis zum Protokoll durch.
//    2. Die Zahlen stimmen (Seiten, Sammlungen, Variablen, Sets).
//    3. Der ZWEITE Lauf legt NICHTS an: „Neu: 0“, alles „vorhanden“.
//    4. Kein Netz: Das Plugin ruft kein `fetch`/`XMLHttpRequest` auf.
//
//  BENUTZUNG
//    node scripts/tests/figma_plugin_sim.mjs [--json]
//  Exit 0 = bestanden, 1 = Befund. Keine Abhängigkeiten, kein Netz.
// ============================================================
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HIER = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HIER, '..', '..');
const PLUGIN = join(ROOT, 'figma', 'design-system-builder');
const alsJson = process.argv.includes('--json');

/* ---------- Mini-Figma ---------- */
function baueFigma() {
  const zustand = {
    seiten: [],
    sammlungen: [],
    variablen: [],
    textstile: new Set(),
    farbstile: new Set(),
    effektstile: new Set(),
    protokoll: '',
    netzAufrufe: [],
  };

  const seite = (name) => {
    const p = { name, children: [], appendChild(c) { this.children.push(c); } };
    zustand.seiten.push(p);
    return p;
  };

  const text = () => ({ type: 'TEXT', characters: '', fontName: {}, fills: [], layoutAlign: '' });
  const frame = () => ({
    type: 'FRAME', children: [], appendChild(c) { this.children.push(c); },
    resize() {}, layoutMode: '', x: 0, y: 0,
  });
  const rechteck = () => ({ type: 'RECTANGLE', fills: [], resize() {}, x: 0, y: 0 });
  const komponente = () => ({
    type: 'COMPONENT', name: '', fills: [], x: 0, y: 0,
    resize() {}, appendChild() {},
  });

  const benannt = (objekt, eintrag) => {
    Object.defineProperty(objekt, 'name', {
      get() { return objekt._name || ''; },
      set(wert) { objekt._name = wert; eintrag.add(wert); },
    });
    return objekt;
  };

  const api = {
    root: { children: zustand.seiten },
    setCurrentPageAsync: async () => {},
    loadAllPagesAsync: async () => {},
    showUI() {},
    closePlugin() {},
    ui: {
      postMessage(m) { if (m && m.type === 'fertig') zustand.protokoll = m.text; },
      onmessage: null,
    },
    createText: text,
    createFrame: frame,
    createRectangle: rechteck,
    createComponent: komponente,
    combineAsVariants(teile, ziel) {
      const set = { type: 'COMPONENT_SET', name: '', width: 320, height: 48, x: 0, y: 0, children: teile };
      ziel.appendChild(set);
      return set;
    },
    loadFontAsync: async () => {},
    getLocalTextStyles: () => [...zustand.textstile].map((name) => ({ name })),
    getLocalPaintStyles: () => [...zustand.farbstile].map((name) => ({ name })),
    getLocalEffectStyles: () => [...zustand.effektstile].map((name) => ({ name })),
    createTextStyle: () => benannt({ fontName: {}, fontSize: 0, lineHeight: null, letterSpacing: null }, zustand.textstile),
    createPaintStyle: () => benannt({ paints: [] }, zustand.farbstile),
    createEffectStyle: () => benannt({ effects: [] }, zustand.effektstile),
    variables: {
      async getLocalVariableCollectionsAsync() { return zustand.sammlungen; },
      async getLocalVariablesAsync() { return zustand.variablen; },
      createVariableCollection(name) {
        const modes = [{ modeId: 'm0', name: 'Mode 1' }];
        const c = {
          name, id: 'c-' + name, modes,
          renameMode(id, n) { const m = modes.find((x) => x.modeId === id); if (m) m.name = n; },
          addMode(n) { modes.push({ modeId: 'm' + modes.length, name: n }); },
        };
        zustand.sammlungen.push(c);
        return c;
      },
      createVariable(name, coll, type) {
        const v = { name, type, variableCollectionId: coll.id, setValueForMode() {}, setVariableCodeSyntax() {} };
        zustand.variablen.push(v);
        return v;
      },
      createVariableAlias: (v) => ({ type: 'VARIABLE_ALIAS', id: v.name }),
      setBoundVariableForPaint: (p) => p,
    },
  };

  // createPage muss die Seite an root.children hängen – genau wie Figma.
  api.createPage = () => {
    const p = seite('Seite ' + (zustand.seiten.length + 1));
    return p;
  };
  return { api, zustand };
}

/* ---------- Lauf ---------- */
function baue(api, html) {
  const quelle = readFileSync(join(PLUGIN, 'code.js'), 'utf8');
  for (const verboten of ['fetch(', 'XMLHttpRequest', 'require(', 'import(']) {
    if (quelle.includes(verboten)) throw new Error('Plugin greift auf ' + verboten + ' zu – es darf kein Netz nutzen');
  }
  // Das Plugin erwartet die globale Variable `figma` – genau wie in Figma.
  // eslint-disable-next-line no-new-func
  new Function('__html__', 'figma', quelle)(html, api);
  if (typeof api.ui.onmessage !== 'function') throw new Error('ui.onmessage wurde nicht registriert');
  return quelle;
}

async function starte(api) {
  api.ui.onmessage({ type: 'aufbauen' });
  await new Promise((r) => setTimeout(r, 400));
}

function protokollFeld(text, feld) {
  const zeile = String(text).split('\n').find((l) => l.startsWith(feld));
  if (!zeile) return null;
  const m = zeile.match(/(\d+)/);
  return m ? Number(m[1]) : null;
}

// Fehlen die Rechte, darf das Plugin NICHTS halb bauen – weder Seiten noch
// Variablen. Es muss abbrechen und den Grund nennen. Dieses Szenario prüft
// genau das: ein abgelehnter Zugriff ist die häufigste Ursache für einen
// abgebrochenen Erstaufbau.
async function pruefeRechteSchutz() {
  const html = readFileSync(join(PLUGIN, 'ui.html'), 'utf8');
  const quelle = readFileSync(join(PLUGIN, 'code.js'), 'utf8');
  const faelle = [
    { name: 'ohne Seitenwechsel (currentpage)', ohneSeitenwechsel: true, ohneSchriften: false },
    { name: 'ohne Schriften/Stile (textreview)', ohneSeitenwechsel: false, ohneSchriften: true },
  ];
  const befund = [];
  for (const fall of faelle) {
    const zustand = { seiten: [], protokoll: '' };
    const api = {
      root: { children: [] },
      createPage() {
        const p = { name: 'S' + (zustand.seiten.length + 1), children: [], appendChild() {} };
        zustand.seiten.push(p);
        this.root.children.push(p);
        return p;
      },
      setCurrentPageAsync: fall.ohneSeitenwechsel ? undefined : async () => {},
      loadAllPagesAsync: async () => {},
      loadFontAsync: fall.ohneSchriften ? undefined : async () => {},
      showUI() {}, closePlugin() {},
      ui: { postMessage(m) { if (m && m.type === 'fertig') zustand.protokoll = m.text; }, onmessage: null },
      getLocalTextStyles: () => [], getLocalPaintStyles: () => [], getLocalEffectStyles: () => [],
    };
    // eslint-disable-next-line no-new-func
    new Function('__html__', 'figma', quelle)(html, api);
    api.ui.onmessage({ type: 'aufbauen' });
    await new Promise((r) => setTimeout(r, 250));
    if (zustand.seiten.length !== 0) {
      befund.push(fall.name + ': es wurden trotzdem ' + zustand.seiten.length + ' Seiten gebaut');
    }
    if (!String(zustand.protokoll).startsWith('⛔')) {
      befund.push(fall.name + ': kein klarer Abbruchhinweis im Protokoll');
    }
  }
  return befund;
}

async function main() {
  const html = readFileSync(join(PLUGIN, 'ui.html'), 'utf8');
  const { api, zustand } = baueFigma();
  baue(api, html);

  await starte(api);
  const ersterLauf = {
    seiten: zustand.seiten.length,
    sammlungen: zustand.sammlungen.length,
    variablen: zustand.variablen.length,
    textstile: zustand.textstile.size,
    farbstile: zustand.farbstile.size,
    effektstile: zustand.effektstile.size,
    neu: protokollFeld(zustand.protokoll, 'Neu: '),
    komponenten: (zustand.seiten.find((p) => p.name === '02 Components') || { children: [] }).children.length,
    protokoll: zustand.protokoll,
  };

  await starte(api);
  const zweiterLauf = {
    seiten: zustand.seiten.length,
    sammlungen: zustand.sammlungen.length,
    variablen: zustand.variablen.length,
    textstile: zustand.textstile.size,
    neu: protokollFeld(zustand.protokoll, 'Neu: '),
    vorhanden: protokollFeld(zustand.protokoll, 'Bereits vorhanden: '),
  };

  const befund = await pruefeRechteSchutz();
  if (!String(ersterLauf.protokoll).startsWith('✅')) befund.push('erster Lauf endet nicht mit ✅');
  if (ersterLauf.seiten !== 7) befund.push('erwartet 7 Seiten, gebaut ' + ersterLauf.seiten);
  if (ersterLauf.sammlungen !== 4) befund.push('erwartet 4 Variablen-Sammlungen, gebaut ' + ersterLauf.sammlungen);
  if (ersterLauf.variablen < 50) befund.push('zu wenige Variablen: ' + ersterLauf.variablen);
  if (ersterLauf.textstile < 10) befund.push('zu wenige Textstile: ' + ersterLauf.textstile);
  if (ersterLauf.effektstile !== 4) befund.push('erwartet 4 Schattenstile, gebaut ' + ersterLauf.effektstile);
  if (ersterLauf.komponenten < 15) befund.push('zu wenige Komponenten-Sets: ' + ersterLauf.komponenten);
  if (zweiterLauf.neu !== 0) befund.push('zweiter Lauf meldet „Neu: ' + zweiterLauf.neu + '“ statt 0');
  if (zweiterLauf.variablen !== ersterLauf.variablen) befund.push('zweiter Lauf legt Variablen doppelt an');
  if (zweiterLauf.seiten !== ersterLauf.seiten) befund.push('zweiter Lauf legt Seiten doppelt an');

  if (alsJson) {
    console.log(JSON.stringify({ ersterLauf, zweiterLauf, befund }, null, 2));
  } else {
    console.log('Figma-Plugin-Simulation');
    console.log('  Lauf 1: ' + ersterLauf.seiten + ' Seiten · ' + ersterLauf.sammlungen + ' Sammlungen · '
      + ersterLauf.variablen + ' Variablen · ' + ersterLauf.textstile + ' Textstile · '
      + ersterLauf.farbstile + ' Farbstile · ' + ersterLauf.effektstile + ' Schatten · '
      + ersterLauf.komponenten + ' Komponenten-Sets');
    console.log('  Lauf 2: Neu ' + zweiterLauf.neu + ' · vorhanden ' + zweiterLauf.vorhanden);
    console.log('  Rechte-Schutz: fehlende Rechte brechen ab, ohne halb zu bauen');
    if (befund.length) {
      console.log('  ❌ ' + befund.length + ' Befund(e):');
      for (const b of befund) console.log('     · ' + b);
    } else {
      console.log('  ✅ Aufbau vollständig, zweiter Lauf legt nichts an.');
    }
  }
  return befund.length ? 1 : 0;
}

main().then((code) => process.exit(code)).catch((e) => {
  console.error('❌ Simulation abgebrochen: ' + (e && e.message ? e.message : e));
  process.exit(2);
});
