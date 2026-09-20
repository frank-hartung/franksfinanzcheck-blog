/* Keine Fetch-Aufrufe, kein Analytics, kein LocalStorage für Audit-/GSC-Daten. */
'use strict';

function parseCSV(text) {
  text = text.replace(/^\uFEFF/, '');
  const first = text.split(/\r?\n/)[0];
  const delimiter = [';', ',', '\t'].sort((a, b) => first.split(b).length - first.split(a).length)[0];
  const rows = []; let row = [], cell = '', quoted = false, closed = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') { quoted = false; closed = true; }
      else cell += c;
    } else if (c === '"' && !cell && !closed) quoted = true;
    else if (c === delimiter) { row.push(cell); cell = ''; closed = false; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); if (row.some(v => v.trim())) rows.push(row);
      row = []; cell = ''; closed = false;
    } else {
      if (closed && c.trim()) throw new Error('Ungültige CSV: Zeichen nach einem geschlossenen Textfeld.');
      if (!closed) cell += c;
    }
  }
  if (quoted) throw new Error('Die CSV enthält ein nicht geschlossenes Anführungszeichen.');
  row.push(cell); if (row.some(v => v.trim())) rows.push(row);
  return rows;
}

function parseGSC(text) {
  const rows = parseCSV(text);
  if (rows.length < 2) throw new Error('Die CSV enthält keine Datenzeilen.');
  const headers = rows.shift().map(v => v.trim().toLowerCase());
  const find = (...keys) => headers.findIndex(h => keys.includes(h));
  const query = find('suchanfragen', 'häufigste suchanfragen', 'top queries', 'queries', 'query');
  const page = find('seiten', 'häufigste seiten', 'top pages', 'pages', 'page', 'seite');
  const label = query >= 0 ? query : page;
  const clicks = find('klicks', 'clicks'), impressions = find('impressionen', 'impressions');
  const position = find('position', 'durchschnittliche position', 'average position');
  if ([label, clicks, impressions, position].some(i => i < 0)) {
    throw new Error('Benötigt: Suchanfragen oder Seiten, Klicks, Impressionen, Position (auch englische Überschriften). Bitte nicht den Datums-/Länder-Export wählen.');
  }
  const german = headers.includes('klicks');
  function number(value, integer = false) {
    let s = (value || '').trim().replace(/[\s\u00a0\u202f]/g, '');
    if (german) s = s.replace(/\./g, '').replace(',', '.');
    else s = s.replace(/,/g, '');
    if (!/^\d+(\.\d+)?$/.test(s)) throw new Error(`Ungültiger Messwert: ${String(value).slice(0, 40)}`);
    const n = Number(s);
    if (!Number.isFinite(n) || (integer && !Number.isSafeInteger(n))) throw new Error('Ungültiger Zahlenwert in der CSV.');
    return n;
  }
  return rows.map((r, i) => {
    if (r.length !== headers.length) throw new Error(`Zeile ${i + 2}: Spaltenzahl passt nicht zum CSV-Kopf.`);
    const item = { label: r[label].trim(), clicks: number(r[clicks], true), impressions: number(r[impressions], true), position: number(r[position]), kind: query >= 0 ? 'query' : 'page' };
    if (!item.label || item.clicks > item.impressions || item.position < 1) throw new Error(`Zeile ${i + 2}: unplausible Suchdaten.`);
    item.ctr = item.impressions ? item.clicks / item.impressions : 0;
    return item;
  });
}

if (typeof module !== 'undefined') module.exports = { parseCSV, parseGSC };

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  const audit = JSON.parse($('audit-data').textContent);
  const nf = new Intl.NumberFormat('de-DE');
  const dec = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 1 });
  const pct = n => new Intl.NumberFormat('de-DE', { style: 'percent', maximumFractionDigits: 1 }).format(n);
  function el(tag, text, cls) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; }
  function clear(node) { node.replaceChildren(); }
  function link(url, text) {
    const a = el('a', text);
    try { const u = new URL(url); if (u.protocol === 'https:') a.href = u.href; } catch { /* Text statt unsicherem Link */ }
    a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
  }
  const labels = { 'index-control': 'Indexierungssteuerung korrigieren', 'canonical-count': 'Canonical eindeutig ausgeben', 'canonical-target': 'Canonical-Ziel prüfen', 'pager-canonical': 'Folgeseite eigenständig auszeichnen', 'schema-json': 'Strukturierte Daten reparieren', 'sitemap-missing': 'Sitemap vervollständigen', 'sitemap-target': 'Sitemap-Ziel bereinigen', 'sitemap-canonical': 'Sitemap und Canonical abgleichen', 'sitemap-duplicate': 'Sitemap-Duplikat entfernen', 'title-missing': 'Seitentitel ergänzen', 'title-length': 'Titel redaktionell prüfen', 'description-missing': 'Meta-Description ergänzen', 'description-length': 'Beschreibung redaktionell prüfen', 'h1-count': 'Hauptüberschrift prüfen', 'language': 'Dokumentsprache setzen', 'social-meta': 'Social-Vorschau ergänzen', 'broken-link': 'Defekte interne Links reparieren', 'broken-anchor': 'Abschnittslinks prüfen', 'image-alt': 'Bildbeschreibung ergänzen', 'image-missing': 'Fehlendes Bild wiederherstellen', 'orphan-page': 'Seite intern verlinken', 'duplicate-title': 'Doppelte Titel unterscheiden', 'duplicate-description': 'Doppelte Beschreibungen unterscheiden' };
  function metric(parent, label, value, hint) { const box = el('div', undefined, 'metric'); box.append(el('span', label), el('strong', value), el('small', hint)); parent.append(box); }
  function renderFindings(parent, rows) {
    clear(parent);
    if (!rows.length) { parent.append(el('p', 'Keine Befunde für diese Auswahl.', 'empty')); return; }
    for (const f of rows) {
      const article = el('article', undefined, 'finding'), body = el('div');
      body.append(el('h3', labels[f.code] || f.code), link(new URL(f.url, audit.base_url).href, f.url), el('p', f.detail, 'detail'), el('p', f.action), el('small', `${f.owner === 'human' ? 'Manuelle Umsetzung / Prüfung' : 'Automatische Behebung'} · ${f.channel}`));
      article.append(el('span', f.severity, `badge ${f.severity.toLowerCase()}`), body); parent.append(article);
    }
  }
  function showView() {
    let view = location.hash.slice(1) || 'ueberblick';
    if (!document.querySelector(`.view[id="${CSS.escape(view)}"]`)) view = 'ueberblick';
    document.querySelectorAll('.view').forEach(s => s.hidden = s.id !== view);
    document.querySelectorAll('nav a').forEach(a => { if (a.dataset.view === view) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    document.title = `${document.querySelector(`nav [data-view="${view}"]`).textContent.trim()} | SEO-Cockpit`;
  }
  window.addEventListener('hashchange', () => { showView(); $('main').focus({ preventScroll: true }); }); showView();
  $('theme').addEventListener('click', () => { const dark = document.documentElement.dataset.theme === 'dark' || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches); document.documentElement.dataset.theme = dark ? 'light' : 'dark'; });
  const s = audit.summary;
  $('audit-date').textContent = new Date(audit.generated_at).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' });
  $('nav-count').textContent = nf.format(audit.findings.length);
  metric($('metrics'), 'Indexierbare Seiten', nf.format(s.indexable), `${nf.format(s.pages)} HTML-Seiten geprüft`);
  metric($('metrics'), 'Technische Fehler', nf.format(s.p1), 'P1 · zuerst bearbeiten');
  metric($('metrics'), 'Struktur & Metadaten', nf.format(s.p2), 'P2 · gezielt verbessern');
  metric($('metrics'), 'Redaktionelle Hinweise', nf.format(s.p3), 'P3 · manuell abwägen');
  $('next-title').textContent = s.p1 ? 'Zuerst die technischen Stolpersteine.' : s.p2 ? 'Die Grundlage steht. Jetzt die Details.' : 'Technisch geprüft. Inhaltlich dranbleiben.';
  $('next-description').textContent = s.p1 ? `${s.p1} P1-Befunde im Build brauchen Aufmerksamkeit. Beginne mit Indexierung und defekten Linkzielen.` : 'Prüfe die offenen Hinweise und nutze echte Suchdaten, um redaktionelle Arbeit zu priorisieren. Ein bestandener Audit garantiert keine Rankings.';
  if (!audit.findings.length) {
    $('next-description').textContent = 'Keine offenen Befunde in den lokalen Prüfungen. Importiere echte Suchdaten, um die nächsten inhaltlichen Verbesserungen zu priorisieren. Das ist keine Rankinggarantie.';
    $('next-link').href = '#suchdaten'; $('next-link').textContent = 'Eigene Suchdaten importieren';
  }
  renderFindings($('top-findings'), audit.findings.slice(0, 3));
  function filterFindings() {
    const query = $('finding-search').value.toLocaleLowerCase('de');
    const rows = audit.findings.filter(f => (!$('priority').value || f.severity === $('priority').value) && `${f.url} ${labels[f.code]} ${f.detail} ${f.action}`.toLocaleLowerCase('de').includes(query));
    $('finding-count').textContent = `${rows.length} von ${audit.findings.length} Befunden`; renderFindings($('findings'), rows);
  }
  $('priority').addEventListener('change', filterFindings); $('finding-search').addEventListener('input', filterFindings); filterFindings();
  function renderPages() {
    const q = $('page-search').value.toLocaleLowerCase('de'), filter = $('index-filter').value;
    const rows = audit.pages.filter(p => (filter === 'all' || p.indexable === (filter === 'indexable')) && `${p.title} ${p.path}`.toLocaleLowerCase('de').includes(q));
    $('page-count').textContent = `${rows.length} von ${audit.pages.length} Seiten`; clear($('pages'));
    for (const p of rows) {
      const tr = el('tr'), name = el('td'); name.append(link(p.url, p.title || '(Ohne Titel)'), el('small', p.path)); tr.append(name);
      for (const value of [p.indexable ? 'Indexierbar' : 'Noindex', p.in_sitemap ? 'Ja' : 'Nein', p.incoming, p.depth ?? 'Nicht erreicht', p.findings]) tr.append(el('td', value));
      const cell = el('td'), button = el('button', 'Snippet'); button.type = 'button'; button.addEventListener('click', () => { $('snippet-page').value = p.path; loadSnippet(); location.hash = 'snippet'; }); cell.append(button); tr.append(cell); $('pages').append(tr);
    }
    if (!rows.length) { const tr = el('tr'), td = el('td', 'Keine Seiten gefunden. Suchbegriff oder Filter ändern.'); td.colSpan = 7; tr.append(td); $('pages').append(tr); }
  }
  $('page-search').addEventListener('input', renderPages); $('index-filter').addEventListener('change', renderPages); renderPages();
  for (const p of audit.pages) { const option = el('option', p.title ? `${p.path} — ${p.title}` : p.path); option.value = p.path; $('snippet-page').append(option); }
  function renderSnippet() {
    const title = $('snippet-title').value, description = $('snippet-description').value;
    $('preview-title').textContent = title || 'Dein Seitentitel'; $('preview-description').textContent = description || 'Deine Beschreibung';
    $('title-length').textContent = `${[...title].length} Zeichen · grobe Orientierung: etwa 30–65`;
    $('description-length').textContent = `${[...description].length} Zeichen · grobe Orientierung: etwa 70–165`;
    $('copy-message').textContent = '';
  }
  function loadSnippet() { const p = audit.pages.find(p => p.path === $('snippet-page').value); if (!p) return; $('snippet-title').value = p.title; $('snippet-description').value = p.description; $('preview-url').textContent = p.url; renderSnippet(); }
  $('snippet-page').addEventListener('change', loadSnippet); $('snippet-title').addEventListener('input', renderSnippet); $('snippet-description').addEventListener('input', renderSnippet); loadSnippet();
  $('copy-snippet').addEventListener('click', async () => {
    const value = `seoTitle: ${JSON.stringify($('snippet-title').value)}\ndescription: ${JSON.stringify($('snippet-description').value)}`;
    try { await navigator.clipboard.writeText(value); $('copy-message').textContent = 'Kopiert. Vorhandene Felder im Frontmatter ersetzen, nicht doppelt hinzufügen.'; }
    catch { $('copy-message').textContent = `Kopieren nicht verfügbar. Manuell übernehmen:\n${value}`; }
  });
  let gsc = [], fileName = '', importVersion = 0;
  function renderGSC() {
    $('gsc-results').hidden = !gsc.length; if (!gsc.length) return;
    const start = $('gsc-start').value, end = $('gsc-end').value;
    const period = start && end ? start <= end ? `${start} bis ${end} (selbst angegeben)` : 'Ungültiger Zeitraum: Start liegt nach Ende.' : 'Zeitraum nicht angegeben';
    $('gsc-message').textContent = `${fileName} · ${gsc.length} Zeilen · ${period}. Nur im aktuellen Tab gespeichert.`;
    const clicks = gsc.reduce((sum, r) => sum + r.clicks, 0), impressions = gsc.reduce((sum, r) => sum + r.impressions, 0);
    clear($('gsc-metrics')); metric($('gsc-metrics'), 'Klicks im Export', nf.format(clicks), 'Eigene GSC-Daten'); metric($('gsc-metrics'), 'Impressionen im Export', nf.format(impressions), 'Kein Suchvolumen'); metric($('gsc-metrics'), 'CTR im Export', pct(impressions ? clicks / impressions : 0), 'Aus Klicks und Impressionen'); metric($('gsc-metrics'), 'Ø Position im Export', impressions ? dec.format(gsc.reduce((sum, r) => sum + r.position * r.impressions, 0) / impressions) : '–', 'Nach Impressionen gewichtet');
    const rows = gsc.filter(r => $('gsc-filter').value === 'all' || (r.impressions >= 100 && r.position >= 4 && r.position <= 20)).sort((a, b) => b.impressions - a.impressions);
    clear($('gsc-rows'));
    for (const r of rows.slice(0, 1000)) {
      const tr = el('tr');
      const action = r.position > 10 ? 'Suchintention, Inhaltstiefe & interne Links prüfen' : r.ctr < .03 ? 'Titel & Description mit Suchintention abgleichen' : 'Inhalt aktuell halten; SERP manuell prüfen';
      for (const value of [r.label, nf.format(r.clicks), nf.format(r.impressions), pct(r.ctr), dec.format(r.position), action]) tr.append(el('td', value));
      $('gsc-rows').append(tr);
    }
    if (!rows.length) { const tr = el('tr'), td = el('td', 'Keine Treffer für diese Chancen-Heuristik. Wähle „Alle importierten Zeilen“.'); td.colSpan = 6; tr.append(td); $('gsc-rows').append(tr); }
    $('gsc-count').textContent = `${rows.length} Treffer · ${Math.min(rows.length, 1000)} angezeigt (maximal 1.000). Keine Rank-Tracking-Zeitreihe.`;
    $('connection-note').textContent = `${gsc.length} eigene GSC-Zeilen sind in diesem Tab verfügbar. Beim Neuladen wird der Import gelöscht.`;
    $('connection-note').previousElementSibling.textContent = 'Eigene Suchdaten importiert.';
  }
  $('gsc-file').addEventListener('change', async event => {
    const version = ++importVersion, file = event.target.files[0]; if (!file) return;
    gsc = []; $('gsc-results').hidden = true; clear($('gsc-rows')); clear($('gsc-metrics'));
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('Datei zu groß. Bitte einen CSV-Export bis 5 MB wählen.');
      const text = await file.text(); if (version !== importVersion) return;
      gsc = parseGSC(text); fileName = file.name; renderGSC();
    } catch (error) { $('gsc-message').textContent = `Import nicht möglich: ${error.message}`; $('connection-note').previousElementSibling.textContent = 'Keine gültigen Suchdaten importiert.'; $('connection-note').textContent = 'Prüfe die Fehlermeldung im Bereich Suchdaten.'; }
  });
  $('gsc-filter').addEventListener('change', renderGSC); $('gsc-start').addEventListener('change', renderGSC); $('gsc-end').addEventListener('change', renderGSC);
  $('gsc-clear').addEventListener('click', () => { importVersion++; gsc = []; fileName = ''; $('gsc-file').value = ''; $('gsc-start').value = ''; $('gsc-end').value = ''; $('gsc-results').hidden = true; clear($('gsc-rows')); clear($('gsc-metrics')); $('gsc-message').textContent = 'Import gelöscht. Wähle eine CSV-Datei, um neue Suchdaten zu prüfen.'; $('connection-note').previousElementSibling.textContent = 'Suchdaten sind noch nicht verbunden.'; $('connection-note').textContent = 'Importiere einen eigenen Google-Search-Console-Export für echte Klicks, Impressionen und Suchchancen.'; });
}
