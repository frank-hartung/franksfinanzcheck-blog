// alert_scoping_sim.mjs – Verhaltens-Simulation des alarm-Skripts aus
// alert-on-failure.yml (github-script-Kontext gestubt).
//
// WARUM: Die PROD-SCOPING-Reparatur der Fehlalarm-Klasse #343 (21.09.2026,
// docs/INCIDENT-2026-09-21-layout-ai-fehlalarm-343.md) ist Inline-JS in YAML.
// Struktur-Tests (test_alert_scoping.py) prüfen nur, dass die Regeln IM TEXT
// stehen; diese Simulation führt das Skript wirklich aus und beweist das
// Verhalten in Produktionsszenarien – inklusive der exakten #343-Konstellation
// (roter pull_request-Lauf eines arena-Zweigs → KEIN Alarm), der
// Bestandszusagen (Phantom-Filter #218, Dedupe, Fail-open bei API-Ausfall)
// und der #602-#608-Fachkanal-Regel für Tagesdefizite (ein Zustandskanal,
// der auch an Ruhetagen belegt wird – sonst meldet das Alerting generisch).
//
// Aufruf:  node scripts/tests/sim/alert_scoping_sim.mjs <pfad-zum-rohskript.js>
// Exit 0 = alle Szenarien korrekt, Exit 1 = mindestens ein Szenario falsch.
// Der Test-Haken läuft in CI über scripts/tests/test_alert_scoping.py
// (unittest discover; GitHub-Runner bringen node mit).
import fs from 'fs';
import { createRequire } from 'module';

// github-script stellt dem Skript ein CommonJS-`require` bereit; dieses
// Harness ist ein ES-Modul und muss es deshalb nachbilden – sonst prüfte
// die Simulation eine Umgebung, die es in der Produktion nicht gibt.
const requireShim = createRequire(import.meta.url);

// Identität der Meldung (Marker + markenneutraler Titel) kommt aus derselben
// Quelle wie in der Produktion: scripts/alert_issue_identity.py schreibt die
// JSON-Datei, deren Pfad der Test über ALARM_IDENTITAET setzt (Marken-Oberfläche
// #496). Ein Test mit eigener Namensgebung würde die echte Zusage nicht prüfen.
const identPfad = process.env.ALARM_IDENTITAET;
if (!identPfad) {
  console.error('ALARM_IDENTITAET fehlt – die Simulation braucht die echte Identitäts-Quelle.');
  process.exit(2);
}
const IDENT = JSON.parse(fs.readFileSync(identPfad, 'utf8'));

const scriptPath = process.argv[2];
if (!scriptPath) {
  console.error('Usage: node alert_scoping_sim.mjs <pfad-zum-rohskript.js>');
  process.exit(2);
}
const raw = fs.readFileSync(scriptPath, 'utf8');

function makeCtx({ branch, event, conclusion, runId = 42, attempt = 1, jobs = null, jobsFail = false, openIssues = [] }) {
  const created = [];
  const updated = [];
  const github = {
    paginate: async (method) => {
      if (method === 'LIST_JOBS') {
        if (jobsFail) throw new Error('API down');
        return jobs || [];
      }
      if (method === 'LIST_ISSUES') return openIssues;
      throw new Error('unexpected paginate ' + method);
    },
    rest: {
      actions: { listJobsForWorkflowRun: 'LIST_JOBS' },
      issues: {
        listForRepo: 'LIST_ISSUES',
        createLabel: async () => { throw new Error('Label existiert bereits'); },
        create: async (o) => { created.push(o); },
        update: async (o) => { updated.push(o); },
      },
    },
  };
  const context = {
    repo: { owner: 'frank-hartung', repo: 'franksfinanzcheck-blog' },
    payload: {
      repository: { default_branch: 'main' },
      workflow_run: {
        id: runId, name: 'Layout-AI', conclusion, html_url: 'https://x/runs/' + runId,
        head_branch: branch, head_sha: '41e56bd7deadbeef', event, run_attempt: attempt,
        created_at: '2026-09-21T17:17:23Z',
      },
    },
  };
  return { github, context, created, updated };
}

let failed = 0;
let count = 0;

async function run(name, cfg, expectIssue, expectInBody = [], expectUpdates = null) {
  count++;
  const { github, context, created, updated } = makeCtx(cfg);
  const logs = [];
  // github-script führt den `script:`-Block als async-Funktionsrumpf aus –
  // genau das wird hier nachgebildet (return auf oberster Ebene ist dort legal).
  const fn = new Function('github', 'context', 'console', 'require', 'process',
    'return (async () => {' + raw + '\n})()');
  await fn(github, context, { log: (m) => logs.push(String(m)) }, requireShim, process);
  const got = created.length > 0;
  const body = created[0] ? created[0].body : '';
  const title = created[0] ? created[0].title : '';
  let ok = got === expectIssue;
  if (ok && expectIssue) {
    // Markenfläche: der Titel nennt weder Workflow noch „fehlgeschlagen“;
    // die Identität steckt unsichtbar als Marker im Body.
    ok = title === IDENT.titel;
    if (!body.includes(IDENT.marker)) ok = false;
    if (/fehlgeschlagen|Layout-AI/.test(title)) ok = false;
    for (const needle of expectInBody) if (!body.includes(needle)) ok = false;
    if (created[0].labels && JSON.stringify(created[0].labels) !== JSON.stringify(['auto-report'])) ok = false;
  }
  if (ok && expectUpdates !== null) {
    ok = updated.length === expectUpdates.anzahl;
    if (ok && expectUpdates.anzahl > 0) {
      ok = updated[0].issue_number === expectUpdates.nummer &&
           updated[0].title === IDENT.titel &&
           String(updated[0].body).includes(IDENT.marker);
    }
  }
  console.log((ok ? '✅' : '❌') + ' ' + name + (got ? ' → Issue' : ' → kein Issue') +
    (logs[0] ? ' | ' + logs[0].slice(0, 95) : ''));
  if (!ok) {
    failed++;
    console.log('   ERWARTET: ' + (expectIssue ? 'Issue „' + IDENT.titel + '“ mit: ' + expectInBody.join(' / ') : 'KEIN Issue'));
    console.log('   TITEL: ' + title);
    console.log('   BODY: ' + body.slice(0, 400));
    console.log('   UPDATES: ' + JSON.stringify(updated).slice(0, 300));
  }
}

// 1. EXAKTE #343-Konstellation: roter PR-Lauf eines arena-Zweigs → KEIN Alarm
await run('#343-Reproduktion: pull_request-Lauf arena-Zweig rot → kein Alarm',
  { branch: 'arena/01a0c4dc-franksfinanzcheck-blog', event: 'pull_request', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'j1',
             steps: [{ name: 'Lauf rot stellen, wenn Befunde offen sind', conclusion: 'failure' }] }] },
  false);
// 2. Roter push-Lauf auf Zweig (Run #12 der Serie) → KEIN Alarm
await run('push-Lauf auf arena-Zweig rot → kein Alarm',
  { branch: 'arena/01a0c4dc-franksfinanzcheck-blog', event: 'push', conclusion: 'failure', jobs: [] }, false);
// 3. Dependabot-PR rot → KEIN Alarm (sichtbar als PR-Check)
await run('pull_request-Lauf dependabot-Zweig rot → kein Alarm',
  { branch: 'dependabot/github_actions/x-1', event: 'pull_request', conclusion: 'failure', jobs: [] }, false);
// 4. ECHTER Produktions-Fehler: schedule auf main → Alarm MIT Diagnose
await run('schedule-Lauf main rot → Alarm + Schritt-Diagnose',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/9',
             steps: [{ name: 'Website bauen', conclusion: 'success' },
                     { name: 'Browser-Audit', conclusion: 'failure' }] }] },
  true, ['### Fehlgeschlagene Schritte', 'Browser-Audit', 'https://x/jobs/9', '**Event:** `schedule`', 'Layout-AI']);
// 5. push auf main rot → Alarm (Produktion)
await run('push-Lauf main rot → Alarm',
  { branch: 'main', event: 'push', conclusion: 'failure', jobs: [] }, true, ['**Event:** `push`']);
// 6. Phantom (#218): cancelled auf main, keine ausgeführten Schritte → KEIN Alarm
await run('verdrängter Wartelauf main (cancelled, 0 Schritte) → kein Alarm',
  { branch: 'main', event: 'push', conclusion: 'cancelled',
    jobs: [{ name: 'deploy', conclusion: 'cancelled', html_url: 'j', steps: [] }] }, false);
// 7. Echter Abbruch: cancelled auf main MIT erfolgreichen Schritten → Alarm
await run('echter Abbruch main (cancelled, Schritte liefen) → Alarm',
  { branch: 'main', event: 'workflow_dispatch', conclusion: 'cancelled', attempt: 2,
    jobs: [{ name: 'deploy', conclusion: 'cancelled', html_url: 'j',
             steps: [{ name: 'Build', conclusion: 'success' },
                     { name: 'Upload', conclusion: 'cancelled' }] }] },
  true, ['**Versuch:** 2', 'Upload']);
// 8. Dedupe über den ALT-TITEL (Übergangszeit) → kein Duplikat, aber stille
//    Migration auf den markenneutralen Titel samt Marker.
await run('Dedupe: offene Alt-Meldung existiert → kein Duplikat, Titel wird migriert',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 99, title: '⚠️ Workflow fehlgeschlagen: Layout-AI (failure)',
                   body: 'alter Text ohne Marker' }] },
  false, [], { anzahl: 1, nummer: 99 });
// 9. Fail-open: Job-API tot bei main-Fehler → Alarm trotzdem (ohne Diagnose)
await run('Job-API-Ausfall bei main-Fehler → Alarm trotzdem',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobsFail: true },
  true, ['Häufigste Ursachen']);

// 10. Dedupe über den MARKER (Normalfall nach der Umstellung): kein Duplikat
//     und auch keine überflüssige Umbenennung.
await run('Dedupe: offene Meldung mit Marker → kein Duplikat, keine Umschrift',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 100, title: IDENT.titel, body: IDENT.marker + '\nDetails' }] },
  false, [], { anzahl: 0 });
// 11. Fremder Vorgang offen → der eigene Alarm darf NICHT verschluckt werden
//     (die Dedupe-Vergiftung aus #218/#343 in neuer Gestalt).
await run('Dedupe: offene Meldung eines ANDEREN Vorgangs → eigener Alarm entsteht',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 101, title: '🔧 Wartung · Newsletter · Vorgang WF-0000',
                   body: '<!-- alert-key: WF-0000 -->' }] },
  true, ['Häufigste Ursachen']);

// 12. #602-Klasse: Die Kadenz bleibt bei einem echten Tagesdefizit ehrlich
//     rot, aber das Fach-Issue engine-deficit besitzt bereits die Arbeit.
//     Dann darf das zentrale Alerting KEIN generisches API-Key-Runbook daneben
//     legen.
await run('Tagesdefizit mit offenem engine-deficit-Fachissue → kein auto-report-Duplikat',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/602',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }],
    openIssues: [{ number: 601, title: 'Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE)',
                   body: '<!-- engine-deficit-id: tagesdefizit -->\nDetails',
                   labels: [{ name: 'engine-deficit' }],
                   updated_at: '2026-09-21T17:18:00Z' }] },
  false);

// 13. Fehlt der Fachkanal, bleibt das Alerting fail-open: Dann ist nicht das
//     Defizit das Problem, sondern die Zustellung der Fachmeldung.
await run('Tagesdefizit ohne engine-deficit-Fachissue → generischer Alarm fail-open',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/603',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }] },
  true, ['TAGESDEFIZIT', 'engine-deficit', 'Häufigste Ursachen']);

// 14. Ein altes engine-deficit-Issue darf die aktuelle Zustellstörung nicht
//     verschlucken. Der Fachkanal zählt nur, wenn er für diesen Lauf frisch
//     aktualisiert wurde.
await run('Tagesdefizit mit veraltetem engine-deficit-Issue → generischer Alarm fail-open',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/604',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }],
    openIssues: [{ number: 600, title: 'Content-Engine: Tagesdefizit alt',
                   body: '<!-- engine-deficit-id: tagesdefizit -->\nAlt',
                   labels: [{ name: 'engine-deficit' }],
                   updated_at: '2026-09-20T17:18:00Z' }] },
  true, ['TAGESDEFIZIT', 'engine-deficit', 'Häufigste Ursachen']);

// 15. #608-Konstellation: Ein verspäteter Montags-Slot der Kadenz-Endkontrolle
//     läuft in der Nacht auf einem RUHETAG und meldet den Vortag ehrlich rot.
//     Nach der Reparatur (WF-1F8C #608) belegt die Messung den Fachkanal an
//     JEDEM Tag: `engine_issue.py --deficit` hat das am Abend zuvor von einem
//     Reparatur-Merge geschlossene Issue #601 in genau diesem Lauf wieder
//     geöffnet und mit einem Zustandskommentar belegt (updated_at = Laufzeit).
//     Ergebnis: kein generisches auto-report-Issue mit API-Key-Runbook.
await run('#608: Ruhetag-Lauf, frisch wiedereröffneter Fachkanal → kein Duplikat',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/608',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }],
    openIssues: [{ number: 601, title: 'Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE) – nicht nachholbar',
                   body: '<!-- engine-deficit-id: tagesdefizit -->\n'
                       + '<!-- engine-deficit-tag: 2026-10-05 -->\nDetails',
                   labels: [{ name: 'engine-deficit' }],
                   updated_at: '2026-09-21T17:17:40Z' }] },
  false);

// 16. Gegenprobe zu 15: Ist der Fachkanal nach dem Merge NICHT wieder geöffnet
//     worden (alte Fassung des Melders, Rechte fehlen, gh-Ausfall), bleibt das
//     Alerting fail-open – dann ist der Melder das Problem, nicht die Quote.
await run('#608-Gegenprobe: Fachkanal blieb geschlossen → generischer Alarm fail-open',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/609',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }],
    openIssues: [] },
  true, ['TAGESDEFIZIT', 'engine-deficit', 'Häufigste Ursachen']);

console.log(failed === 0
  ? `\n✅ SIMULATION: alle ${count} Szenarien korrekt`
  : `\n❌ SIMULATION: ${failed} von ${count} Szenarien falsch`);
process.exit(failed === 0 ? 0 : 1);
