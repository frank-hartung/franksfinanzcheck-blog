/*!
 * ff-fixkosten-cockpit.js – Franks Fixkosten-Cockpit
 * ===================================================
 * Produktvertrag:
 *   - Rechnet ausschließlich im Browser; kein fetch, kein Formular-POST,
 *     keine Cookies und keine Übertragung der Eingabewerte.
 *   - localStorage ausschließlich nach aktivem Opt-in „auf diesem Gerät
 *     merken". Entfernen des Häkchens oder „Zurücksetzen" löscht ihn.
 *   - Keine Nutzereingabe fließt in innerHTML. Kategorien und Links sind
 *     redaktionell fest im Hugo-Markup, Geldwerte werden als Number formatiert.
 *   - Der Berechnungskern liegt unter globalThis.FFFixkostenCockpitLogik und
 *     bleibt damit ohne Browser testbar.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'ff_fixkosten_cockpit_v1';
  var MAX_AMOUNT = 1000000;

  function amount(raw) {
    if (typeof raw === 'number') return isFinite(raw) ? raw : NaN;
    var text = String(raw == null ? '' : raw).trim()
      .replace(/\s/g, '')
      .replace(/€/g, '');
    if (!text) return NaN;
    // Deutsche Schreibweise: 1.234,56 -> 1234.56. Bei nur einem Punkt
    // behandeln wir ihn als Dezimalzeichen, sofern keine Tausendergruppe folgt.
    if (text.indexOf(',') !== -1) {
      text = text.replace(/\./g, '').replace(',', '.');
    } else if (/^\d{1,3}(\.\d{3})+$/.test(text)) {
      text = text.replace(/\./g, '');
    }
    var value = Number(text);
    return isFinite(value) && value >= 0 && value <= MAX_AMOUNT ? value : NaN;
  }

  function euros(value, digits) {
    if (!isFinite(value)) return '–';
    return value.toLocaleString('de-DE', {
      style: 'currency', currency: 'EUR',
      minimumFractionDigits: typeof digits === 'number' ? digits : 2,
      maximumFractionDigits: typeof digits === 'number' ? digits : 2,
    });
  }

  function parseDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ''))) return null;
    var parts = value.split('-').map(Number);
    var date = new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0, 0);
    // Ein ungültiges Eingabedatum (etwa 2026-02-31) darf nicht still normalisiert werden.
    if (date.getFullYear() !== parts[0] || date.getMonth() !== parts[1] - 1 || date.getDate() !== parts[2]) return null;
    return date;
  }

  function startOfToday(now) {
    var d = now instanceof Date ? new Date(now) : new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate(), 12, 0, 0, 0);
  }

  function dayDifference(value, now) {
    var date = parseDate(value);
    if (!date) return null;
    return Math.round((date.getTime() - startOfToday(now).getTime()) / 86400000);
  }

  function formatDate(value) {
    var date = parseDate(value);
    return date ? date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '';
  }

  function deadlineText(item, now) {
    var days = dayDifference(item.date, now);
    var label = item.label;
    if (days === null) return null;
    if (days < 0) return label + ': Termin vom ' + formatDate(item.date) + ' liegt zurück – jetzt prüfen.';
    if (days === 0) return label + ': heute als nächsten Check vorgesehen.';
    if (days === 1) return label + ': nächster Check morgen.';
    if (days <= 30) return label + ': nächster Check in ' + days + ' Tagen (' + formatDate(item.date) + ').';
    if (days <= 90) return label + ': nächster Check in ' + days + ' Tagen (' + formatDate(item.date) + ').';
    return label + ': nächster Check am ' + formatDate(item.date) + '.';
  }

  function evaluate(rows, now) {
    var items = (rows || []).map(function (row) {
      return {
        id: String(row.id || ''),
        label: String(row.label || ''),
        amount: amount(row.amount),
        date: String(row.date || ''),
      };
    }).filter(function (row) { return isFinite(row.amount) && row.amount > 0; });

    items.sort(function (a, b) { return b.amount - a.amount || a.label.localeCompare(b.label, 'de'); });
    var total = items.reduce(function (sum, item) { return sum + item.amount; }, 0);
    var deadlines = (rows || []).map(function (row) {
      return {
        id: String(row.id || ''),
        label: String(row.label || ''),
        date: String(row.date || ''),
      };
    }).filter(function (row) { return parseDate(row.date); })
      .sort(function (a, b) { return String(a.date).localeCompare(String(b.date)); });

    return {
      items: items,
      monthly: total,
      yearly: total * 12,
      deadlines: deadlines,
      deadlineTexts: deadlines.map(function (entry) { return deadlineText(entry, now); }).filter(Boolean),
    };
  }

  function safeStorageGet() {
    try { return window.localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function safeStorageSet(value) {
    try { window.localStorage.setItem(STORAGE_KEY, value); return true; } catch (e) { return false; }
  }

  function safeStorageRemove() {
    try { window.localStorage.removeItem(STORAGE_KEY); } catch (e) { /* privacy mode: nothing to clear */ }
  }

  function textNode(tag, text, className) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  function listInto(target, items, emptyText) {
    while (target.firstChild) target.removeChild(target.firstChild);
    if (!items.length) {
      var empty = textNode(target.tagName === 'OL' ? 'li' : 'li', emptyText, 'ff-cockpit__empty');
      target.appendChild(empty);
      return;
    }
    items.forEach(function (entry) { target.appendChild(textNode('li', entry)); });
  }

  function rowsFrom(container) {
    return Array.prototype.slice.call(container.querySelectorAll('[data-ff-cockpit-row]')).map(function (row) {
      var label = row.querySelector('.ff-cockpit__category strong');
      var amountInput = row.querySelector('[data-ff-cockpit-amount]');
      var dateInput = row.querySelector('[data-ff-cockpit-date]');
      return {
        id: row.getAttribute('data-category') || '',
        label: label ? label.textContent.trim() : '',
        amount: amountInput ? amountInput.value : '',
        date: dateInput ? dateInput.value : '',
      };
    });
  }

  function writePlan(container, result) {
    var box = container.querySelector('[data-ff-cockpit-result]');
    var monthly = container.querySelector('[data-ff-cockpit-monthly]');
    var yearly = container.querySelector('[data-ff-cockpit-yearly]');
    var count = container.querySelector('[data-ff-cockpit-count]');
    var priorities = container.querySelector('[data-ff-cockpit-priorities]');
    var deadlines = container.querySelector('[data-ff-cockpit-deadlines]');
    if (!box || !monthly || !yearly || !count || !priorities || !deadlines) return;

    box.hidden = false;
    monthly.textContent = euros(result.monthly);
    yearly.textContent = euros(result.yearly);
    count.textContent = String(result.items.length);

    var priorityText = result.items.map(function (item, index) {
      var prefix = index === 0 ? 'Zuerst ansehen: ' : 'Danach: ';
      return prefix + item.label + ' mit ' + euros(item.amount) + ' pro Monat (' + euros(item.amount * 12) + ' pro Jahr).';
    });
    listInto(priorities, priorityText, 'Trag mindestens einen Monatsbetrag ein. Dann setzt das Cockpit deine erste Prüfreihenfolge.');
    listInto(deadlines, result.deadlineTexts, 'Noch kein Prüftermin erfasst. Setz dir für den größten Posten einen ruhigen Check-Termin.');
  }

  function persistedPayload(container) {
    return {
      version: 1,
      rows: rowsFrom(container).map(function (row) { return { id: row.id, amount: row.amount, date: row.date }; }),
    };
  }

  function persistIfWanted(container) {
    var remember = container.querySelector('[data-ff-cockpit-remember]');
    if (remember && remember.checked) safeStorageSet(JSON.stringify(persistedPayload(container)));
  }

  function loadPersisted(container) {
    var raw = safeStorageGet();
    if (!raw) return;
    try {
      var payload = JSON.parse(raw);
      if (!payload || payload.version !== 1 || !Array.isArray(payload.rows)) return;
      payload.rows.forEach(function (saved) {
        var row = container.querySelector('[data-ff-cockpit-row][data-category="' + String(saved.id).replace(/"/g, '') + '"]');
        if (!row) return;
        var amountInput = row.querySelector('[data-ff-cockpit-amount]');
        var dateInput = row.querySelector('[data-ff-cockpit-date]');
        if (amountInput && typeof saved.amount === 'string') amountInput.value = saved.amount;
        if (dateInput && /^\d{4}-\d{2}-\d{2}$/.test(String(saved.date || ''))) dateInput.value = saved.date;
      });
      var remember = container.querySelector('[data-ff-cockpit-remember]');
      if (remember) remember.checked = true;
      writePlan(container, evaluate(rowsFrom(container)));
    } catch (e) {
      // Beschädigte lokale Daten sind keine Nutzerdatenquelle: weg damit.
      safeStorageRemove();
    }
  }

  function copyPlan(container) {
    var result = evaluate(rowsFrom(container));
    var lines = [
      'Mein Fixkosten-Prüfplan',
      'Laufende Kosten: ' + euros(result.monthly) + ' pro Monat · ' + euros(result.yearly) + ' pro Jahr',
      '',
      'Priorität nach Betrag:',
    ];
    if (result.items.length) {
      result.items.forEach(function (item, index) {
        lines.push((index + 1) + '. ' + item.label + ': ' + euros(item.amount) + ' pro Monat');
      });
    } else {
      lines.push('Noch keine Monatsbeträge erfasst.');
    }
    lines.push('', 'Nächste Checks:');
    if (result.deadlineTexts.length) lines = lines.concat(result.deadlineTexts.map(function (entry) { return '– ' + entry; }));
    else lines.push('– Noch keinen Prüftermin erfasst.');
    lines.push('', 'Erstellt mit dem Fixkosten-Cockpit von FranksFinanzcheck.');
    return lines.join('\n');
  }

  function clipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      try {
        var area = document.createElement('textarea');
        area.value = text;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        var successful = document.execCommand('copy');
        document.body.removeChild(area);
        successful ? resolve() : reject(new Error('copy unavailable'));
      } catch (error) { reject(error); }
    });
  }

  function initialize(container) {
    var form = container.querySelector('form');
    if (!form) return;
    var result = container.querySelector('[data-ff-cockpit-result]');
    var remember = container.querySelector('[data-ff-cockpit-remember]');
    var reset = container.querySelector('[data-ff-cockpit-reset]');
    var copy = container.querySelector('[data-ff-cockpit-copy]');

    function update() {
      var evaluation = evaluate(rowsFrom(container));
      if (result && !result.hidden) writePlan(container, evaluation);
      persistIfWanted(container);
      return evaluation;
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      writePlan(container, evaluate(rowsFrom(container)));
      persistIfWanted(container);
    });

    form.querySelectorAll('[data-ff-cockpit-amount], [data-ff-cockpit-date]').forEach(function (input) {
      input.addEventListener('input', update);
      input.addEventListener('change', update);
    });

    if (remember) {
      remember.addEventListener('change', function () {
        if (remember.checked) persistIfWanted(container);
        else safeStorageRemove();
      });
    }

    if (reset) {
      reset.addEventListener('click', function () {
        if (!window.confirm('Alle Eingaben im Fixkosten-Cockpit wirklich zurücksetzen?')) return;
        form.querySelectorAll('[data-ff-cockpit-amount], [data-ff-cockpit-date]').forEach(function (input) { input.value = ''; });
        if (remember) remember.checked = false;
        safeStorageRemove();
        if (result) result.hidden = true;
      });
    }

    if (copy) {
      copy.addEventListener('click', function () {
        var original = copy.textContent;
        clipboard(copyPlan(container)).then(function () {
          copy.textContent = 'Kopiert';
          window.setTimeout(function () { copy.textContent = original; }, 2200);
        }).catch(function () {
          copy.textContent = 'Kopieren nicht möglich';
          window.setTimeout(function () { copy.textContent = original; }, 2600);
        });
      });
    }

    loadPersisted(container);
  }

  function boot() {
    document.querySelectorAll('[data-ff-fixkosten-cockpit]').forEach(initialize);
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
  }

  if (typeof globalThis !== 'undefined') {
    globalThis.FFFixkostenCockpitLogik = {
      amount: amount,
      parseDate: parseDate,
      dayDifference: dayDifference,
      evaluate: evaluate,
      deadlineText: deadlineText,
      euros: euros,
    };
  }
})();
