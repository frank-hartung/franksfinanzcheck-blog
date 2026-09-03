/**
 * hugo_shortcodes.mjs – Hugo-Shortcodes in lesbaren Text übersetzen
 * ================================================================
 * Wozu: Die Audiofassung wird offline gerendert. Hugo steht in der
 * Prüf- und Bauumgebung nicht zur Verfügung, deshalb blieben die
 * Shortcode-Aufrufe als Rohtext stehen – und die Parameter
 * („title=", „subtitle=", „cta url=/go/gas/") wären vorgelesen worden.
 *
 * Dieser Renderer bildet die Shortcodes aus layouts/shortcodes/ so ab,
 * wie Hugo sie auf der Seite ausgibt: Überschrift, Untertitel, dann
 * pro Tarif bzw. pro Maßnahme die Zeilen mit ihren Werten, am Ende die
 * Fußnote. Damit spricht die Audiofassung denselben Inhalt wie die
 * sichtbare Seite – und zwar in einer Reihenfolge, die beim Hören Sinn
 * ergibt (Zeile für Zeile, nicht Spalte für Spalte).
 *
 * Abgedeckt: tarifvergleich, tarif, zeile, einspartabelle, summe,
 * callout, autor-foto, placeholder. Unbekannte Shortcodes werden
 * durchlaufen gelassen (Inhalt bleibt erhalten, Aufruf verschwindet),
 * damit nichts unbemerkt aus dem Text fällt.
 */

/* ---------- Attribute eines Shortcode-Aufrufs zerlegen ---------- */
function parseAttrs(str) {
  const attrs = {};
  // name="Wert" | name='Wert' | name=Wort
  const re = /([A-Za-z0-9_-]+)\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/g;
  let m;
  while ((m = re.exec(str)) !== null) {
    attrs[m[1]] = m[3] !== undefined ? m[3] : (m[4] !== undefined ? m[4] : m[5]);
  }
  return attrs;
}

/** Wert sprachfreundlich aufbereiten: HTML-Tags weg, Zahlen lesbar. */
function cleanValue(v) {
  return String(v == null ? '' : v)
    .replace(/<br\s*\/?>/gi, ', ')
    .replace(/<small>([\s\S]*?)<\/small>/gi, '$1')
    .replace(/<[^>]+>/g, '')
    .replace(/\*\*/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
}

/* Emoji/Zeichen, die ein Vorlesesystem nur stotternd oder gar nicht
   spricht, werden zu dem Wort, das ein Mensch sagen würde. */
function speakable(v) {
  return cleanValue(v)
    .replace(/❌/g, 'Nein:')
    .replace(/✕/g, 'Nein:')
    .replace(/✓/g, 'Ja:')
    /* Der Pokal steht fast immer vor dem Wort „Empfehlung" („🏆 Empfehlung").
       Würde er selbst zu „Empfehlung", entstünde eine Dublette. Das
       Siegerkennzeichen spricht ohnehin die win-Markierung aus. */
    .replace(/🏆/g, '')
    .replace(/⚡/g, '')
    .replace(/💰/g, '')
    .replace(/💡/g, 'Tipp')
    .replace(/⚠/g, 'Achtung')
    .replace(/ℹ/g, 'Hinweis')
    .replace(/→/g, '')
    .replace(/·/g, ',')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

/* ---------- Tokenizer: Text und Shortcode-Aufrufe ---------- */
const TAG_RE = /\{\{<\s*(\/?)([A-Za-z0-9_-]+)((?:[^>](?!\}\}))*)>\}\}/g;

function tokenize(src) {
  const nodes = [];
  let last = 0;
  TAG_RE.lastIndex = 0;
  let m;
  while ((m = TAG_RE.exec(src)) !== null) {
    if (m.index > last) nodes.push({ type: 'text', value: src.slice(last, m.index) });
    nodes.push({
      type: m[1] === '/' ? 'close' : 'open',
      name: m[2],
      attrs: m[1] === '/' ? {} : parseAttrs(m[3] || '')
    });
    last = m.index + m[0].length;
  }
  if (last < src.length) nodes.push({ type: 'text', value: src.slice(last) });
  return nodes;
}

/* ---------- Baum aus den Tokens ---------- */
function buildTree(nodes) {
  const root = { type: 'root', children: [] };
  const stack = [root];
  for (const n of nodes) {
    const top = stack[stack.length - 1];
    if (n.type === 'text') {
      top.children.push(n);
    } else if (n.type === 'open') {
      const el = { type: 'sc', name: n.name, attrs: n.attrs, children: [] };
      top.children.push(el);
      stack.push(el);
    } else {
      // close: passenden Öffner suchen (robust gegen falsch geschlossene Tags)
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].name === n.name) { stack.length = i; break; }
      }
    }
  }
  return root;
}

function innerText(node) {
  return node.children
    .map((c) => (c.type === 'text' ? c.value : innerText(c)))
    .join('');
}

function childrenByName(node, name) {
  return node.children.filter((c) => c.type === 'sc' && c.name === name);
}

/* ---------- Die einzelnen Shortcodes ---------- */

/** {{< zeile label="…" >}}Wert{{< /zeile >}} im Tarifvergleich */
function renderTarifZeile(node) {
  const label = speakable(node.attrs.label || '');
  const value = speakable(innerText(node));
  if (!label && !value) return '';
  if (!value || value === '–' || value === '-') return '';
  return `* ${label}: ${value}`;
}

/** {{< zeile … >}} in der Einspartabelle (Vorher/Nachher/Ersparnis) */
function renderSparZeile(node) {
  const a = node.attrs;
  const label = speakable(a.label || '');
  const parts = [];
  if (a['vorher-main'] || a['vorher-sub']) {
    parts.push(`vorher ${speakable([a['vorher-main'], a['vorher-sub']].filter(Boolean).join(', '))}`);
  }
  if (a['nachher-main'] || a['nachher-sub']) {
    parts.push(`nachher ${speakable([a['nachher-main'], a['nachher-sub']].filter(Boolean).join(', '))}`);
  }
  if (a.ersparnis) parts.push(`Ersparnis ${speakable(a.ersparnis)}`);
  if (!label && !parts.length) return '';
  return `* ${label}: ${parts.join('; ')}`;
}

function renderTarif(node) {
  const out = [];
  const name = speakable(node.attrs.name || '');
  const tag = speakable(node.attrs.tag || '');
  const win = String(node.attrs.win || '') === 'true';
  let head = `**${name}**`;
  if (tag) head += ` (${tag})`;
  /* Das Siegerkennzeichen steht oft schon im Tag („🏆 Empfehlung").
     Dann nicht doppelt ansagen. */
  if (win && !/empfehlung/i.test(tag)) head += ' – Empfehlung';
  out.push(head);
  for (const z of childrenByName(node, 'zeile')) {
    const line = renderTarifZeile(z);
    if (line) out.push(line);
  }
  return out.join('\n');
}

function renderTarifvergleich(node) {
  const out = [];
  const title = speakable(node.attrs.title || 'Tarifvergleich');
  const subtitle = speakable(node.attrs.subtitle || '');
  out.push(`### ${title}`);
  if (subtitle) out.push(subtitle);
  const tarifs = childrenByName(node, 'tarif');
  for (const t of tarifs) out.push(renderTarif(t));
  const footnote = speakable(node.attrs.footnote || '');
  if (footnote) out.push(`Hinweis: ${footnote}`);
  return out.join('\n\n');
}

function renderEinspartabelle(node) {
  const out = [];
  const title = speakable(node.attrs.title || 'Einsparpotenziale im Vergleich');
  const subtitle = speakable(node.attrs.subtitle || '');
  out.push(`### ${title}`);
  if (subtitle) out.push(subtitle);
  for (const z of childrenByName(node, 'zeile')) {
    const line = renderSparZeile(z);
    if (line) out.push(line);
  }
  for (const s of childrenByName(node, 'summe')) {
    const a = s.attrs;
    const label = speakable(a.label || 'Summe der Maßnahmen');
    const parts = [];
    if (a['vorher-main'] || a['vorher-sub']) parts.push(`vorher ${speakable([a['vorher-main'], a['vorher-sub']].filter(Boolean).join(', '))}`);
    if (a['nachher-main'] || a['nachher-sub']) parts.push(`nachher ${speakable([a['nachher-main'], a['nachher-sub']].filter(Boolean).join(', '))}`);
    if (a.ersparnis) parts.push(`Ersparnis ${speakable(a.ersparnis)}`);
    out.push(`**${label}**: ${parts.join('; ')}`);
  }
  const footnote = speakable(node.attrs.footnote || '');
  if (footnote) out.push(`Hinweis: ${footnote}`);
  return out.join('\n\n');
}

function renderCallout(node) {
  const type = node.attrs.type || 'info';
  const label = type === 'tip' ? 'Tipp' : type === 'warning' ? 'Wichtiger Hinweis' : 'Hinweis';
  const body = speakable(innerText(node) || node.attrs.text || '');
  return body ? `**${label}:** ${body}` : '';
}

const RENDERERS = {
  tarifvergleich: renderTarifvergleich,
  einspartabelle: renderEinspartabelle,
  tarif: renderTarif,
  callout: renderCallout,
  // Reine Deko-Shortcodes: kein Vorlesetext
  'autor-foto': () => '',
  placeholder: () => '',
  // Kind-Shortcodes, die nur im Verbund Sinn ergeben: einzeln als Zeile
  zeile: (n) => renderTarifZeile(n) || renderSparZeile(n),
  summe: (n) => renderSparZeile(n)
};

function renderNode(node) {
  if (node.type === 'text') return node.value;
  if (node.type === 'root') return node.children.map(renderNode).join('');
  const fn = RENDERERS[node.name];
  if (fn) return '\n\n' + fn(node) + '\n\n';
  /* Unbekannter Shortcode: Inhalt behalten, Aufruf verwerfen.
     So geht kein Text still verloren. */
  return node.children.map(renderNode).join('');
}

/**
 * Hugo-Shortcodes eines Artikelbodys in Markdown übersetzen,
 * das der Markdown-Renderer der Prüfumgebung versteht.
 */
/**
 * Steht unmittelbar über einer Vergleichstabelle eine Überschrift mit
 * gleichem Wortlaut, wird der Tabellen-Titel nicht nochmal angesagt.
 * Das ist im Redaktionsalltag der Normalfall („## Beispielrechnung"
 * plus title="💰 Beispielrechnung") und beim Hören eine Wiederholung.
 */
function dropRepeatedHeading(md) {
  return md.replace(/(^|\n)#{2,3}\s+([^\n]+)\n\s*\n#{2,3}\s+([^\n]+)\n/g, (all, lead, first, second) => {
    const norm = (t) => t.toLowerCase().replace(/[^a-z0-9äöüß]+/gi, ' ').trim();
    return norm(first) === norm(second) ? `${lead}## ${first.trim()}\n` : all;
  });
}

export function renderShortcodes(markdown) {
  if (!/\{\{</.test(markdown)) return markdown;
  return dropRepeatedHeading(
    renderNode(buildTree(tokenize(markdown)))
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
  );
}

export default renderShortcodes;
