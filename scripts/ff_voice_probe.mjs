/**
 * ff_voice_probe.mjs — Messfühler für das Paritäts-Gate.
 * ------------------------------------------------------------
 * Das Paritäts-Gate (scripts/ff_voice_parity_check.py) muss denselben
 * Text und dieselbe Blockreihenfolge aus ZWEI Implementierungen
 * vergleichen:
 *   · Browser-Regie: static/premium/ff-voice.js (JavaScript)
 *   · Tonspur-Regie: scripts/ff_voice_backends.py + ff_voice_audio.py
 *
 * Dieser Fühler nimmt eine JSON-Anfrage auf stdin entgegen und gibt die
 * Antwort der BROWSER-Seite als JSON auf stdout aus. Die Python-Seite
 * vergleicht dann. Ohne dieses Fenster in die echte Engine wäre die
 * Parität nur behauptet, nicht geprüft.
 *
 * Anfrage:  { "samples": [{"text": "...", "lang": "de"}],
 *             "runs":    [{"text": "...", "lang": "de"}],
 *             "pages":   [{"html": "...", "cfg": {...}}] }
 * Antwort:  { "normalized": ["..."], "runs": [[[{text,lang}]]],
 *             "pages": [[{lang,type,text}]] }
 */

import { loadPage, ensureToolbar } from './ff_voice_qa_lib.mjs';

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
  });
}

const raw = await readStdin();
let req = { samples: [], runs: [], pages: [] };
try { req = JSON.parse(raw || '{}'); } catch (e) { req = { samples: [], runs: [], pages: [] }; }

/** Führt die echte Engine auf einer beliebigen Seiten-HTML aus. */
function runOnPage(html) {
  const { win } = loadPage(html);
  return win.__ffVoice;
}

const out = { normalized: [], runs: [], pages: [], error: null };

try {
  // Ein Fenster genügt für die reinen Text-Regeln.
  const probe = runOnPage(
    '<!doctype html><html lang="de"><body>'
    + '<div id="ff-voice-bar" role="region" data-page-lang="de">'
    + '<button id="ff-voice-play"><span id="ff-voice-play-label"></span></button>'
    + '<button id="ff-voice-summary"><span id="ff-voice-summary-label"></span></button>'
    + '<span id="ff-voice-status"></span></div>'
    + '<script type="application/json" id="ff-voice-config">{"title":"T","lang":"de","readingTime":1}</script>'
    + '</body></html>'
  );
  for (const s of req.samples || []) {
    out.normalized.push(probe.speechNormalize(s.text, s.lang));
  }
  for (const s of req.runs || []) {
    // Jeder Lauf-Satz wird in einem eigenen Fenster gerechnet — die
    // Wortlauf-Regie ist zustandslos, das Fenster ist nur der Rahmen.
    out.runs.push(probe.languageRuns(s.text, s.lang)
      .map((r) => ({ text: r.text, lang: r.lang })));
  }
  for (const page of req.pages || []) {
    const api = runOnPage(ensureToolbar(page.html, (page.cfg && page.cfg.lang) || 'de'));
    out.pages.push(api.collectBlocks().map((b) => ({ lang: b.lang, type: b.type, text: b.text })));
  }
} catch (e) {
  out.error = e.message;
}

process.stdout.write(JSON.stringify(out));
process.exit(out.error ? 1 : 0);
