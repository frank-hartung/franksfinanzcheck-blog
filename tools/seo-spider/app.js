'use strict';
const $ = id => document.getElementById(id);
let pages = [], links = [], activeFilter = 'all', activeLinkFilter = 'all', timer = null, sitemapsAvailable = false;
let pageNumber = 1, sortKey = 'url', sortDirection = 1;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function metric(label, value, detail, color='') { return `<article class="metric ${color}"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(detail)}</small></article>`; }
function statusClass(s) { return s === 'ERROR' || (typeof s === 'number' && s >= 400) ? 'bad' : s === 'ROBOTS' ? 'neutral' : s >= 300 ? 'warn' : 'good'; }
function contains(p, value) { return String(p.issues || '').split('; ').includes(value); }
function render(state) {
  pages = state.pages || [];
  links = state.links || [];
  sitemapsAvailable = Number(state.sitemaps_found || 0) > 0 || Number(state.sitemap_urls || 0) > 0;
  $('activity').hidden = !state.running;
  $('progress').max = state.limit || 1;
  $('progress').value = state.progress || 0;
  $('activity-text').textContent = state.running ? `Geprüft: ${state.progress} / ${state.limit} URLs` : `Crawl beendet · ${state.progress} URLs geprüft`;
  $('current').textContent = state.current || '';
  if (state.error) $('message').textContent = state.error;
  if (!state.done) return;
  $('results').hidden = pages.length === 0;
  if (!pages.length) return;
  const c = state.summary || {};
  $('crawl-meta').textContent = `Host: ${state.scope || state.start_url} · ${state.robots_checked ? 'robots.txt beachtet' : 'robots.txt nicht verfügbar'} · Crawl-delay: ${state.robots_delay ?? 'nicht angegeben'} s · ${state.sitemaps_found || 0} Sitemaps / ${state.sitemap_urls || 0} Sitemap-URLs${state.check_external ? ` · externe Links geprüft: ${state.external_checked || 0}, offen: ${state.external_unchecked || 0}` : ''}${state.sitemap_unseen ? ` · ${state.sitemap_unseen} Sitemap-URLs noch nicht geprüft` : ''}${state.limit_reached ? ' · URL-Limit erreicht, Ergebnis ist gekürzt' : ''}${state.depth_skipped ? ` · ${state.depth_skipped} URLs jenseits der Tiefe ausgelassen` : ''}${state.timed_out ? ' · ZEITLIMIT: Teilbericht' : ''}${state.stopped ? ' · manuell gestoppt: Teilbericht' : ''}`;
  if (state.timed_out || state.stopped) $('message').textContent = 'Der Crawl-Bericht ist unvollständig; bitte Limit, Tiefe oder Laufzeit anpassen und erneut starten.';
  $('metrics').innerHTML = metric('Geprüfte URLs', c.pages || pages.length, `${c.indexable || 0} als indexierbar erkannt`) +
    metric('HTTP-Fehler', c.errors || 0, 'Status ≥ 400 / Verbindungsfehler', c.errors ? 'red' : '') +
    metric('Metadaten', c.metadata_issues || 0, 'Title / Description / H1', c.metadata_issues ? 'amber' : '') +
    metric('Kaputte interne Links', c.broken_links || 0, 'Ziele mit HTTP-Fehler', c.broken_links ? 'red' : '') +
    metric('Sitemap-Waisen', c.orphans || 0, 'ohne interne eingehende Links', c.orphans ? 'amber' : '') +
    metric('Noindex', c.noindex || 0, 'Noindex oder Nofollow', c.noindex ? 'amber' : '') +
    metric('Bilder ohne Alt', c.missing_alt || 0, 'leere / fehlende Alt-Texte', c.missing_alt ? 'amber' : '') +
    metric('Interne / externe Links', `${c.internal_links || 0} / ${c.external_links || 0}`, `${c.broken_external_links || 0} externe HTTP-Fehler · optionaler HEAD-Check`);
  $('link-count').textContent = `(${links.length.toLocaleString('de-DE')} Links)`;
  pageNumber = 1;
  drawRows();
  drawLinks();
}
function issueMatches(p, filter) {
  const issues = p.issues || '';
  if (filter === 'all') return true;
  if (filter === 'issues') return Boolean(issues);
  if (filter === 'errors') return p.status === 'ERROR' || (typeof p.status === 'number' && p.status >= 400);
  if (filter === 'noindex') return contains(p, 'Noindex') || contains(p, 'Nofollow directive');
  if (filter === 'sitemap') return sitemapsAvailable && (Boolean(p.sitemap) || contains(p, 'missing from sitemap') || contains(p, 'listed in sitemap'));
  if (filter === 'orphans') return Boolean(p.orphan);
  if (filter === 'redirects') return contains(p, 'Redirected') || contains(p, 'Meta refresh redirect');
  return true;
}
function drawRows() {
  if (!$('rows')) return;
  const q = $('search').value.trim().toLowerCase();
  const filtered = pages.filter(p => issueMatches(p, activeFilter) && (!q || [p.url,p.title,p.description,p.h1,p.canonical,p.indexability,p.issues,p.status,p.schema_types].join(' ').toLowerCase().includes(q)));
  filtered.sort((a,b) => {
    const x = a[sortKey] ?? '', y = b[sortKey] ?? '';
    if (typeof x === 'number' && typeof y === 'number') return (x-y)*sortDirection;
    return String(x).localeCompare(String(y), 'de', {numeric:true,sensitivity:'base'})*sortDirection;
  });
  const size = Number($('page-size').value || 50), totalPages = Math.max(1, Math.ceil(filtered.length / size));
  pageNumber = Math.min(pageNumber, totalPages);
  const start = (pageNumber - 1) * size;
  const visible = filtered.slice(start, start + size);
  $('rows').innerHTML = visible.map(p => `<tr>
    <td><span class="status ${statusClass(p.status)}">${esc(p.status)}</span></td>
    <td class="url"><a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">${esc(p.url)}</a>${p.final_url !== p.url ? `<small>→ ${esc(p.final_url)}</small>` : ''}</td>
    <td>${esc(p.title || '—')}<small>${esc(p.title_chars || 0)} Zeichen · ${esc(p.title_count || 0)} Title</small></td>
    <td>${esc(p.description || '—')}<small>${esc(p.description_chars || 0)} Zeichen · ${esc(p.description_count || 0)} Tags${p.description_px ? ` · ${Math.round(p.description_px)} px` : ''}</small></td>
    <td>${esc(p.h1 || '—')}<small>${esc(p.h1_count || 0)}× H1 · ${esc(p.h2_count || 0)}× H2</small></td>
    <td>${esc(p.words || 0)}</td>
    <td>${esc(p.canonical || '—')}<small>${esc(p.indexability || '—')}</small></td>
    <td>${!sitemapsAvailable ? '<span class="neutral">Nicht geprüft</span>' : p.sitemap ? '<span class="clear">In Sitemap</span>' : '<span class="issue">Nicht gelistet</span>'}<small>Tiefe ${esc(p.depth)} · ${esc(p.depth_origin || 'Start-URL')}</small></td>
    <td>${esc(p.inlinks)}</td><td>${esc(p.outlinks)} intern<small>${esc(p.external_links)} extern</small></td>
    <td>${esc(p.images)} Bilder<small>${esc(p.images_missing_alt)} ohne Attribut · ${esc(p.images_empty_alt)} leer/dekorativ</small></td>
    <td>${esc(p.schema_types || '—')}<small>${esc(p.schema_count)} Blöcke · ${esc(p.schema_errors)} Fehler</small></td>
    <td>${esc(p.bytes ? `${(p.bytes/1024).toFixed(1)} KB${p.truncated?'+':''}` : '—')}<small>${esc(p.elapsed_ms)} ms</small></td>
    <td>${p.issues ? `<span class="issue">${esc(p.issues)}</span>` : '<span class="clear">Keine</span>'}</td>
  </tr>`).join('');
  $('table-count').textContent = `${filtered.length.toLocaleString('de-DE')} URLs passend · ${pages.length.toLocaleString('de-DE')} insgesamt`;
  $('page-number').textContent = `Seite ${pageNumber} / ${totalPages}`;
  $('prev-page').disabled = pageNumber <= 1;
  $('next-page').disabled = pageNumber >= totalPages;
}
function drawLinks() {
  if (!$('link-rows')) return;
  const q = $('link-search').value.trim().toLowerCase();
  const filtered = links.filter(edge => {
    const internal = edge.internal !== false;
    const empty = !edge.anchor;
    return (activeLinkFilter === 'all' || (activeLinkFilter === 'internal' && internal) || (activeLinkFilter === 'external' && !internal) || (activeLinkFilter === 'empty' && empty)) &&
      (!q || [edge.source,edge.target,edge.anchor,edge.rel,edge.fragment].join(' ').toLowerCase().includes(q));
  });
  const shown = filtered.slice(0, 500);
  $('link-rows').innerHTML = shown.map(e => `<tr><td class="url">${esc(e.source)}</td><td class="url"><a href="${esc(e.target)}" target="_blank" rel="noopener noreferrer">${esc(e.target)}</a></td><td>${esc(e.anchor || '—')}</td><td>${esc(e.rel || '—')}</td><td>${esc(e.fragment || '—')}</td><td><span class="status ${e.internal === false ? 'neutral':'good'}">${e.internal === false ? 'Extern':'Intern'}</span><small>${esc(e.status ?? '—')}${e.elapsed_ms ? ` · ${e.elapsed_ms} ms` : ''}</small></td></tr>`).join('');
  $('link-table-count').textContent = `${filtered.length.toLocaleString('de-DE')} Links passend${filtered.length > shown.length ? ` · erste ${shown.length} angezeigt; vollständiger Export über Link-CSV` : ''}`;
}
$('crawl-form').addEventListener('submit', async event => {
  event.preventDefault();
  $('message').textContent = '';
  $('results').hidden = true;
  const seeds = $('seed-urls').value.split(/\r?\n/).map(s => s.trim()).filter(s => s && !s.startsWith('#'));
  if (seeds.length > 5000) { $('message').textContent = 'Die URL-Liste ist auf 5.000 Einträge begrenzt.'; return; }
  try {
    await api('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
      url:$('url').value, limit:Number($('limit').value), depth:Number($('depth').value), delay:Number($('delay').value),
      sitemap:$('sitemap-url').value, seed_urls:seeds, follow_nofollow:$('follow-nofollow').checked, check_external:$('check-external').checked
    })});
    $('activity').hidden = false;
    if (timer) clearInterval(timer);
    timer = setInterval(poll, 800);
    await poll();
  } catch (error) { $('message').textContent = error.message; }
});
async function poll() {
  try {
    const state = await api('/api/state');
    render(state);
    if (!state.running) { clearInterval(timer); timer = null; }
  } catch (error) { $('message').textContent = error.message; }
}
$('stop').addEventListener('click', async () => { try { await api('/api/stop', {method:'POST'}); $('activity-text').textContent = 'Stop wird ausgeführt …'; } catch(e) { $('message').textContent = e.message; } });
$('search').addEventListener('input', () => { pageNumber=1; drawRows(); });
$('page-size').addEventListener('change', () => { pageNumber=1; drawRows(); });
$('prev-page').addEventListener('click', () => { pageNumber=Math.max(1,pageNumber-1); drawRows(); });
$('next-page').addEventListener('click', () => { pageNumber++; drawRows(); });
document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.tab').forEach(b=>b.classList.remove('selected')); button.classList.add('selected'); activeFilter=button.dataset.filter; pageNumber=1; drawRows(); }));
document.querySelectorAll('.sort').forEach(button => button.addEventListener('click', () => { if(sortKey===button.dataset.sort) sortDirection*=-1; else {sortKey=button.dataset.sort; sortDirection=1;} drawRows(); }));
document.querySelectorAll('.link-tab').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.link-tab').forEach(b=>b.classList.remove('selected')); button.classList.add('selected'); activeLinkFilter=button.dataset.linkFilter; drawLinks(); }));
$('link-search').addEventListener('input', drawLinks);
$('baseline-file').addEventListener('change', async event => {
  const file = event.target.files && event.target.files[0];
  $('compare-message').textContent = '';
  $('comparison').hidden = true;
  if (!file) return;
  if (file.size > 10_000_000) { $('compare-message').textContent = 'Die Vergleichsdatei ist größer als 10 MB.'; return; }
  try {
    const report = JSON.parse(await file.text());
    if (!report || !Array.isArray(report.pages) || !report.pages.every(p => p && typeof p.url === 'string')) throw new Error('Kein gültiger SEO-Spider-Bericht mit pages-Array.');
    const normalize = value => { try { const u = new URL(value); u.hash=''; for (const key of [...u.searchParams.keys()]) if (key.startsWith('utm_') || ['gclid','fbclid','msclkid','dclid','gbraid','wbraid'].includes(key)) u.searchParams.delete(key); return u.href; } catch { return value; } };
    const current = new Map(pages.map(p => [normalize(p.url), p]));
    const previous = new Map(report.pages.map(p => [normalize(p.url), p]));
    const added = [...current.keys()].filter(url => !previous.has(url)).sort();
    const removed = [...previous.keys()].filter(url => !current.has(url)).sort();
    const fields = ['status','title','description','h1','canonical','robots','indexability','sitemap','depth','inlinks','outlinks','broken_internal_links','broken_external_links','images_missing_alt','schema_errors','content_hash'];
    const changed = [], unchanged=[];
    for (const url of [...current.keys()].filter(u=>previous.has(u)).sort()) {
      const now=current.get(url), before=previous.get(url), diff=fields.filter(key=>JSON.stringify(before[key] ?? null)!==JSON.stringify(now[key] ?? null)).map(field=>({field,before:before[field],after:now[field]}));
      if (diff.length) changed.push({url,diff}); else unchanged.push(url);
    }
    const totalChanges = added.length+removed.length+changed.reduce((n,item)=>n+item.diff.length,0);
    $('compare-metrics').innerHTML = metric('Neu',added.length,'URLs seit dem alten Crawl',added.length?'green':'')+metric('Entfernt',removed.length,'nicht mehr im aktuellen Crawl',removed.length?'amber':'')+metric('Geändert',changed.length,'URLs mit Feldänderungen',changed.length?'amber':'')+metric('Unverändert',unchanged.length,'identische Vergleichsfelder');
    const rows=[];
    added.forEach(url=>rows.push(`<tr><td>Neu</td><td>${esc(url)}</td><td>URL</td><td>—</td><td>vorhanden</td></tr>`));
    removed.forEach(url=>rows.push(`<tr><td>Entfernt</td><td>${esc(url)}</td><td>URL</td><td>vorhanden</td><td>—</td></tr>`));
    changed.forEach(item=>item.diff.forEach(d=>rows.push(`<tr><td>Geändert</td><td>${esc(item.url)}</td><td>${esc(d.field)}</td><td>${esc(JSON.stringify(d.before) ?? '—')}</td><td>${esc(JSON.stringify(d.after) ?? '—')}</td></tr>`)));
    $('compare-rows').innerHTML = rows.slice(0,500).join('');
    $('comparison').hidden = false;
    $('compare-message').textContent = `${totalChanges} Änderungen im Vergleich mit ${report.generated_at || 'dem ausgewählten Bericht'}. Nur die ersten 500 Feldänderungen werden in der Tabelle angezeigt.`;
  } catch(error) { $('compare-message').textContent = error.message || 'Vergleichsdatei konnte nicht gelesen werden.'; }
});
poll();
