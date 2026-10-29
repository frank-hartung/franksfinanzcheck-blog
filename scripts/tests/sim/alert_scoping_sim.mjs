// alert_scoping_sim.mjs – Verhaltens-Simulation des alarm-Skripts aus
// alert-on-failure.yml (github-script-Kontext gestubt).
//
// WARUM: Die PROD-SCOPING-Reparatur der Fehlalarm-Klasse #343 (21.09.2026,
// docs/INCIDENT-2026-09-21-layout-ai-fehlalarm-343.md) ist Inline-JS in YAML.
// Struktur-Tests (test_alert_scoping.py) prüfen nur, dass die Regeln IM TEXT
// stehen; diese Simulation führt das Skript wirklich aus und beweist das
// Verhalten in Produktionsszenarien – inklusive der exakten #343-Konstellation
// (roter pull_request-Lauf eines arena-Zweigs → KEIN Alarm), der
// Bestandszusagen (Phantom-Filter #218, Dedupe, Fail-open bei API-Ausfall),
// der #632-Frühabbruch-Diagnose für Phase 0.5 und der #602-#608-Fachkanal-
// Regel für Tagesdefizite (ein Zustandskanal,
// der auch an Ruhetagen belegt wird – sonst meldet das Alerting generisch)
// und der Nachführung offener Meldungen bei geändertem Rat (WF-9E5A / #761).
//
// Aufruf:  node scripts/tests/sim/alert_scoping_sim.mjs <pfad-zum-rohskript.js>
// Exit 0 = alle Szenarien korrekt, Exit 1 = mindestens ein Szenario falsch.
// Der Test-Haken läuft in CI über scripts/tests/test_alert_scoping.py
// (unittest discover; GitHub-Runner bringen node mit).
import fs from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
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
const IDENTITIES = JSON.parse(fs.readFileSync(identPfad, 'utf8'));

const scriptPath = process.argv[2];
if (!scriptPath) {
  console.error('Usage: node alert_scoping_sim.mjs <pfad-zum-rohskript.js>');
  process.exit(2);
}
const raw = fs.readFileSync(scriptPath, 'utf8');

function makeCtx({ branch, event, conclusion, workflowName = 'Layout-AI', runId = 42, attempt = 1, jobs = null, jobsFail = false, updateFail = false, openIssues = [] }) {
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
        // updateFail: Die Issue-API lehnt das Schreiben ab (Rechte, Ausfall).
        update: async (o) => { if (updateFail) throw new Error('API down (update)'); updated.push(o); },
      },
    },
  };
  const context = {
    repo: { owner: 'frank-hartung', repo: 'franksfinanzcheck-blog' },
    payload: {
      repository: { default_branch: 'main' },
      workflow_run: {
        id: runId, name: workflowName, conclusion, html_url: 'https://x/runs/' + runId,
        head_branch: branch, head_sha: '41e56bd7deadbeef', event, run_attempt: attempt,
        created_at: '2026-09-21T17:17:23Z',
      },
    },
  };
  return { github, context, created, updated };
}

let failed = 0;
let count = 0;

async function run(name, cfg, expectIssue, expectInBody = [], expectUpdates = null, expectNotInBody = []) {
  count++;
  const workflowName = cfg.workflowName || 'Layout-AI';
  const identity = IDENTITIES[workflowName];
  if (!identity) throw new Error('Keine Identität für Workflow „' + workflowName + '“');
  const { github, context, created, updated } = makeCtx({ ...cfg, workflowName });
  const logs = [];
  // github-script liest die Identität pro Lauf aus einer Datei. Die Simulation
  // wechselt dieselbe Quelle passend zum simulierten Workflow statt etwa
  // Content-Engine-Fehler mit der Layout-AI-Identität zu testen.
  // Eigenes, nur für uns angelegtes Temp-Verzeichnis (mkdtemp, Rechte 0700)
  // statt eines vorhersagbaren Namens im gemeinsamen /tmp.
  const identityFile = join(fs.mkdtempSync(join(tmpdir(), 'alert-identity-')), `identity-${count}.json`);
  const previousIdentityFile = process.env.ALARM_IDENTITAET;
  fs.writeFileSync(identityFile, JSON.stringify(identity), { encoding: 'utf8', flag: 'wx' });
  process.env.ALARM_IDENTITAET = identityFile;
  // github-script führt den `script:`-Block als async-Funktionsrumpf aus –
  // genau das wird hier nachgebildet (return auf oberster Ebene ist dort legal).
  const fn = new Function('github', 'context', 'console', 'require', 'process',
    'return (async () => {' + raw + '\n})()');
  // Ein Absturz des Skripts stellt in der Produktion das Alerting selbst rot –
  // er wird deshalb als benannter Grund gezählt statt die Simulation abzubrechen.
  let absturz = null;
  try {
    await fn(github, context, { log: (m) => logs.push(String(m)) }, requireShim, process);
  } catch (e) {
    absturz = e;
  } finally {
    if (previousIdentityFile === undefined) delete process.env.ALARM_IDENTITAET;
    else process.env.ALARM_IDENTITAET = previousIdentityFile;
    fs.unlinkSync(identityFile);
  }
  const got = created.length > 0;
  const body = created[0] ? created[0].body : '';
  const title = created[0] ? created[0].title : '';
  // Diagnose (20.09.2026-Nachtrag F-09): Jede verletzte Erwartung wird BENANNT
  // gesammelt. Ein bloßes „falsch“ mit 400-Zeichen-Body-Slice hat schon einmal
  // eine Stunde gekostet, weil die verletzte Nadel hinter dem Slice lag.
  const gruende = [];
  let ok = got === expectIssue;
  if (!ok) gruende.push(expectIssue ? 'kein Issue erstellt' : 'Issue erstellt, aber keiner erwartet');
  if (absturz) {
    ok = false;
    gruende.push('Skript abgestürzt: ' + absturz.message);
  }
  if (ok && expectIssue) {
    // Markenfläche: der Titel nennt weder Workflow noch „fehlgeschlagen“;
    // die Identität steckt unsichtbar als Marker im Body.
    if (title !== identity.titel) gruende.push('Titel ≠ Identität: ' + JSON.stringify(title));
    if (!body.includes(identity.marker)) gruende.push('Marker fehlt im Body');
    if (/fehlgeschlagen|Layout-AI|Content-Engine/.test(title)) gruende.push('Rohname im Titel');
    for (const needle of expectInBody) {
      if (!body.includes(needle)) gruende.push('erwartete Nadel fehlt: ' + JSON.stringify(needle));
    }
    for (const needle of expectNotInBody) {
      if (body.includes(needle)) gruende.push('verbotene Nadel im Body: ' + JSON.stringify(needle));
    }
    if (created[0].labels && JSON.stringify(created[0].labels) !== JSON.stringify(['auto-report'])) {
      gruende.push('Labels ≠ [auto-report]: ' + JSON.stringify(created[0].labels));
    }
    ok = gruende.length === 0;
  }
  if (ok && expectUpdates !== null) {
    ok = updated.length === expectUpdates.anzahl;
    if (!ok) gruende.push('Updates: ' + updated.length + ' statt ' + expectUpdates.anzahl);
    if (ok && expectUpdates.anzahl > 0) {
      ok = updated[0].issue_number === expectUpdates.nummer &&
           updated[0].title === identity.titel &&
           String(updated[0].body).includes(identity.marker);
      if (!ok) gruende.push('Update-Ziel/Titel/Marker stimmt nicht: ' + JSON.stringify(updated).slice(0, 200));
      // Nachgeführte Meldungen (WF-9E5A / #761): Der neue Body wird genauso
      // streng geprüft wie ein neu angelegter – Rat, Lauf, keine Altlasten.
      const neuBody = String(updated[0].body);
      for (const needle of expectUpdates.imBody || []) {
        if (!neuBody.includes(needle)) gruende.push('Update: erwartete Nadel fehlt: ' + JSON.stringify(needle));
      }
      for (const needle of expectUpdates.nichtImBody || []) {
        if (neuBody.includes(needle)) gruende.push('Update: verbotene Nadel im Body: ' + JSON.stringify(needle));
      }
      ok = ok && gruende.length === 0;
    }
  }
  console.log((ok ? '✅' : '❌') + ' ' + name + (got ? ' → Issue' : ' → kein Issue') +
    (logs[0] ? ' | ' + logs[0].slice(0, 95) : ''));
  if (!ok) {
    failed++;
    console.log('   GRUND: ' + gruende.join(' · '));
    console.log('   ERWARTET: ' + (expectIssue ? 'Issue „' + identity.titel + '“ mit: ' + expectInBody.join(' / ') : 'KEIN Issue'));
    console.log('   TITEL: ' + title);
    console.log('   BODY: ' + body);
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
  true, ['### Fehlgeschlagene Schritte', 'Browser-Audit', 'https://x/jobs/9', '**Event:** `schedule`', 'Layout-AI',
         '<!-- alert-runbook: allgemein -->'],
  null, ['Offen seit']);
// 5. WF-A535 #632: Frühabbruch in Phase 0.5 darf nicht mit dem generischen
//    API-Key-/GitHub-Runbook oder dem irreführenden Tagesdefizit-Label enden.
await run('#632-Reproduktion: Phase 0.5 + Schlussklassifikation → präzises Runbook',
  { workflowName: 'Content-Engine v2', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'engine', conclusion: 'failure', html_url: 'https://x/jobs/632',
             steps: [
               { name: 'Phase 0.5 – Kadenz-Gate sicherstellen (Selbsttest + Selbstheilung)', conclusion: 'failure' },
               { name: 'Do not report a quota deficit as success', conclusion: 'failure' },
             ] }] },
  true,
  ['Vorgang **WF-A535**', 'Frühabbruch vor der Endabnahme', 'Phase 0.5',
   'Selbsttest-Exit 2', 'python3 scripts/selftest_ki.py --trap <skript>',
   '<!-- alert-runbook: engine-fruehabbruch -->'],
  null,
  ['Häufigste Ursachen', 'API-Key abgelaufen', 'GitHub-Ausfall', 'Transienter Fehler']);

// 6. Andere Content-Engine-Klasse: den Annotation-Classifier erklären, ohne
//    die Phase-0.5-spezifische KI-Probe zu behaupten.
await run('Content-Engine-Schluss-Classifier → Klassen-Runbook ohne Key-Raten',
  { workflowName: 'Content-Engine v2', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'engine', conclusion: 'failure', html_url: 'https://x/jobs/633',
             steps: [{ name: 'Do not report a quota deficit as success', conclusion: 'failure' }] }] },
  true,
  ['Abschluss-Classifier', 'FRÜHABBRUCH', 'TAGESDEFIZIT', 'RELEASE-CRASH', 'SYNCHRONVERLUST',
   '<!-- alert-runbook: engine-schlussklassifikation -->'],
  null,
  ['Häufigste Ursachen', 'API-Key abgelaufen', 'GitHub-Ausfall', 'Transienter Fehler',
   'selftest_ki.py --trap']);

// 7. Identische Schritttexte in einem anderen Workflow dürfen nicht in die
//    Content-Engine-Sonderbehandlung geraten.
//    WF-53E2 / #780 (16.10.2026): Der erste rote Schritt ist hier ein
//    Selbsttest-Schritt – seitdem bekommt er den Selbsttest-Rat statt des
//    Standardrats. Die Zusage des Szenarios bleibt unverändert: kein
//    Engine-Runbook außerhalb der Content-Engine.
await run('gleichnamige Schritte in fremdem Workflow → kein Engine-Runbook (Selbsttest-Rat)',
  { workflowName: 'Layout-AI', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/634',
             steps: [
               { name: 'Phase 0.5 – Kadenz-Gate sicherstellen (Selbsttest + Selbstheilung)', conclusion: 'failure' },
               { name: 'Do not report a quota deficit as success', conclusion: 'failure' },
             ] }] },
  true,
  ['<!-- alert-runbook: selbsttest -->', 'Code-Regression, kein Betriebsausfall'],
  null,
  ['Frühabbruch vor der Endabnahme', 'selftest_ki.py --trap <skript>', 'API-Key abgelaufen']);

// 8. push auf main rot → Alarm (Produktion)
await run('push-Lauf main rot → Alarm',
  { branch: 'main', event: 'push', conclusion: 'failure', jobs: [] }, true, ['**Event:** `push`']);
// 9. Phantom (#218): cancelled auf main, keine ausgeführten Schritte → KEIN Alarm
await run('verdrängter Wartelauf main (cancelled, 0 Schritte) → kein Alarm',
  { branch: 'main', event: 'push', conclusion: 'cancelled',
    jobs: [{ name: 'deploy', conclusion: 'cancelled', html_url: 'j', steps: [] }] }, false);
// 10. Echter Abbruch: cancelled auf main MIT erfolgreichen Schritten → Alarm
await run('echter Abbruch main (cancelled, Schritte liefen) → Alarm',
  { branch: 'main', event: 'workflow_dispatch', conclusion: 'cancelled', attempt: 2,
    jobs: [{ name: 'deploy', conclusion: 'cancelled', html_url: 'j',
             steps: [{ name: 'Build', conclusion: 'success' },
                     { name: 'Upload', conclusion: 'cancelled' }] }] },
  true, ['**Versuch:** 2', 'Upload']);
// 11. Dedupe über den ALT-TITEL (Übergangszeit) → kein Duplikat, aber stille
//    Migration auf den markenneutralen Titel samt Marker.
await run('Dedupe: offene Alt-Meldung existiert → kein Duplikat, Titel wird migriert',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 99, title: '⚠️ Workflow fehlgeschlagen: Layout-AI (failure)',
                   body: 'alter Text ohne Marker' }] },
  false, [], { anzahl: 1, nummer: 99 });
// 12. Fail-open: Job-API tot bei main-Fehler → Alarm trotzdem (ohne Diagnose)
await run('Job-API-Ausfall bei main-Fehler → Alarm trotzdem',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobsFail: true },
  true, ['Häufigste Ursachen']);

// 13. Dedupe über den MARKER (Normalfall nach der Umstellung): kein Duplikat
//     und auch keine überflüssige Umschrift – die Meldung trägt bereits den
//     Rat dieses Laufs (Klassen-Marker seit WF-9E5A / #761) UND keinen
//     älteren Lauf (Lagebild-Stufe 2 seit WF-E813 / #815, 26.10.2026).
await run('Dedupe: offene Meldung mit Marker + gleichem Lauf → kein Duplikat, keine Umschrift',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 100, title: IDENTITIES['Layout-AI'].titel,
                   body: IDENTITIES['Layout-AI'].marker + '\n<!-- alert-runbook: allgemein -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/42)\nDetails' }] },
  false, [], { anzahl: 0 });
// 14. Fremder Vorgang offen → der eigene Alarm darf NICHT verschluckt werden
//     (die Dedupe-Vergiftung aus #218/#343 in neuer Gestalt).
await run('Dedupe: offene Meldung eines ANDEREN Vorgangs → eigener Alarm entsteht',
  { branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [],
    openIssues: [{ number: 101, title: '🔧 Wartung · Newsletter · Vorgang WF-0000',
                   body: '<!-- alert-key: WF-0000 -->' }] },
  true, ['Häufigste Ursachen']);

// 15. #602-Klasse: Die Kadenz bleibt bei einem echten Tagesdefizit ehrlich
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

// 16. Fehlt der Fachkanal, bleibt das Alerting fail-open: Dann ist nicht das
//     Defizit das Problem, sondern die Zustellung der Fachmeldung.
await run('Tagesdefizit ohne engine-deficit-Fachissue → generischer Alarm fail-open',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/603',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }] },
  true, ['TAGESDEFIZIT', 'engine-deficit', 'Häufigste Ursachen']);

// 17. Ein altes engine-deficit-Issue darf die aktuelle Zustellstörung nicht
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

// 18. #608-Konstellation: Ein verspäteter Montags-Slot der Kadenz-Endkontrolle
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

// 19. Gegenprobe zu 18: Ist der Fachkanal nach dem Merge NICHT wieder geöffnet
//     worden (alte Fassung des Melders, Rechte fehlen, gh-Ausfall), bleibt das
//     Alerting fail-open – dann ist der Melder das Problem, nicht die Quote.
await run('#608-Gegenprobe: Fachkanal blieb geschlossen → generischer Alarm fail-open',
  { branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'endkontrolle', conclusion: 'failure', html_url: 'https://x/jobs/609',
             steps: [{ name: 'TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig', conclusion: 'failure' }] }],
    openIssues: [] },
  true, ['TAGESDEFIZIT', 'engine-deficit', 'Häufigste Ursachen']);

// 9. WF-7B6B / #654: Install-Schritt rot (npm ci) → Manifest-Diagnose statt des
//    irreführenden API-Key-Rats. Vorfall: package.json war ungültiges JSON, npm ci
//    brach in Sekunde 1 ab – die Meldung riet trotzdem zu Schlüsseln.
await run('#654-Reproduktion: npm ci rot auf main → Manifest-Diagnose, kein API-Key-Rat',
  { workflowName: 'E2E-Tests (Playwright)', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'Playwright-Suite (Desktop + Mobile)', conclusion: 'failure',
             html_url: 'https://x/jobs/113296822355',
             steps: [{ name: 'Abhängigkeiten installieren', conclusion: 'failure' }] }] },
  true, ['Abhängigkeiten nicht installierbar', 'manifest_guard.py', '### Fehlgeschlagene Schritte',
         '<!-- alert-runbook: installation -->'],
  null, ['API-Key abgelaufen']);
// 10. Deploy: die Manifest-Wache rot → dieselbe Diagnose (Produktionspfad).
await run('Deploy: Manifest-Schutz rot → Manifest-Diagnose',
  { workflowName: 'Deploy auf GitHub Pages', branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'deploy', conclusion: 'failure', html_url: 'https://x/jobs/9001',
             steps: [{ name: 'Manifest-Schutz (package.json & Lockfile – fail-closed)', conclusion: 'failure' }] }] },
  true, ['Abhängigkeiten nicht installierbar', 'manifest_guard.py'], null, ['API-Key abgelaufen']);
// 11. Gegenprobe: ein Fehler OHNE Install-Bezug behält das bisherige Runbook.
await run('Gegenprobe: E2E-Suite rot ohne Install-Bezug → bisheriges Runbook',
  { workflowName: 'E2E-Tests (Playwright)', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'Playwright-Suite (Desktop + Mobile)', conclusion: 'failure', html_url: 'https://x/jobs/7',
             steps: [{ name: 'E2E-Suite ausführen', conclusion: 'failure' }] }] },
  true, ['Häufigste Ursachen', 'API-Key abgelaufen'], null, ['Abhängigkeiten nicht installierbar']);

// WF-9E5A / #761 (15.10.2026): Offsite-Backup. Exakte Konstellation des
// Vorfalls: Repo-Job grün, KV-Job rot in „Voraussetzungen prüfen“, weil Ziel,
// Zugänge und Namespace-ID nie eingerichtet wurden. Die Meldung riet zu
// GROQ/GEMINI-Schlüsseln und „neu starten“ – beides hilft hier nicht.
const BACKUP_KV_JOB = 'KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)';
await run('#761-Reproduktion: KV-Backup ohne Einrichtung → Einrichtungs-Runbook, kein Neustart-/Key-Rat',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [
      { name: 'backup', conclusion: 'success', html_url: 'https://x/jobs/116311519162',
        steps: [{ name: 'Bundle + Arbeitskopie erstellen, verifizieren, verschlüsseln', conclusion: 'success' }] },
      { name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/116311519313',
        steps: [{ name: 'Selbsttest (Export, Probe, Einrichtungsprüfung – fail-closed)', conclusion: 'success' },
                { name: 'Voraussetzungen prüfen (fail-closed – kein Schein-Grün)', conclusion: 'failure' }] }] },
  true,
  ['Vorgang **WF-9E5A**', 'Einrichtung unvollständig – ein Neustart hilft nicht', 'E1–E8',
   'docs/ANLEITUNG-OFFSITE-BACKUP.md', 'schließt diese Meldung automatisch', 'https://x/jobs/116311519313',
   '<!-- alert-runbook: backup-einrichtung -->',
   // Links statt Pfadangaben: jüngster Lauf (aktuelle Checkliste) und Anleitung.
   '(https://github.com/frank-hartung/franksfinanzcheck-blog/actions/workflows/backup-offsite.yml)',
   '(https://github.com/frank-hartung/franksfinanzcheck-blog/blob/main/docs/ANLEITUNG-OFFSITE-BACKUP.md)'],
  null,
  ['Häufigste Ursachen', 'API-Key abgelaufen', 'GROQ', 'Transienter Fehler', 'Offen seit']);
// Fristwarnung: Sicherung gelaufen, nur ein Zugang läuft bald ab.
await run('WF-9E5A: Fristwarnung rot → „Sicherung ist gelaufen“, Zugang erneuern',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/7611',
             steps: [{ name: 'Fristwarnung – Zugänge rechtzeitig erneuern', conclusion: 'failure' }] }] },
  true, ['Die Sicherung ist gelaufen', 'Zugänge erneuern', 'Environment `backup`',
         '<!-- alert-runbook: backup-frist -->'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'Einrichtung unvollständig']);
// Andere Backup-Schritte: eigenes Runbook ohne GROQ/GEMINI-Rat.
await run('WF-9E5A: Export rot → Backup-Runbook ohne GROQ/GEMINI-Rat',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/7612',
             steps: [{ name: 'Exportieren, verschlüsseln, Rückweg prüfen', conclusion: 'failure' }] }] },
  true, ['Exportieren, verschlüsseln, Rückweg prüfen', 'cloudflarestatus', 'Abschnitt „Fehlerbilder“',
         '<!-- alert-runbook: backup -->'],
  null, ['API-Key abgelaufen', 'GROQ', 'Einrichtung unvollständig', 'Die Sicherung ist gelaufen']);

// LAGEBILD NACHFÜHREN (WF-9E5A / #761): #761 wurde geschrieben, bevor es die
// Klasse „Einrichtung unvollständig“ gab, und riet deshalb zu GROQ/GEMINI.
// Der Dedupe-Pfad fasste offene Meldungen nie an – der falsche Rat wäre bis zum
// ersten grünen Lauf stehen geblieben. Nachgebildet ist der echte Body von #761
// (Identitäts-Marker, KEIN Klassen-Marker, allgemeines Runbook).
const BACKUP_IDENT = IDENTITIES['Offsite-Backup'];
const ALT_761_BODY = BACKUP_IDENT.marker + '\n'
  + '> Vorgang **WF-9E5A** · Bereich *Sicherung* · Zuordnung: `python3 scripts/alert_issue_identity.py --tabelle`\n\n'
  + '## Offsite-Backup ist fehlgeschlagen (failure)\n\n'
  + '- **Run:** [Details ansehen](https://x/runs/38701800402)\n\n'
  + '### Was du tun solltest\n'
  + '1. Öffne das Log des oben rot markierten Schritts – es nennt die echte Ursache.\n'
  + '2. Häufigste Ursachen:\n'
  + '   - **API-Key abgelaufen** (GROQ/GEMINI) → Secrets in den Repo-Einstellungen aktualisieren\n'
  + '   - **Transienter Fehler** → Workflow manuell neu starten (Actions → Run workflow)';
const KV_JOB_EINRICHTUNG_ROT = [
  { name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/7620',
    steps: [{ name: 'Selbsttest (Export, Probe, Einrichtungsprüfung – fail-closed)', conclusion: 'success' },
            { name: 'Voraussetzungen prüfen (fail-closed – kein Schein-Grün)', conclusion: 'failure' }] }];
await run('#761-Nachführung: offene Meldung mit GROQ-Rat → gleiche Nummer, Einrichtungs-Rat, kein Duplikat',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7620,
    jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel, body: ALT_761_BODY,
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [],
  { anzahl: 1, nummer: 761,
    imBody: ['<!-- alert-runbook: backup-einrichtung -->', 'Einrichtung unvollständig – ein Neustart hilft nicht',
             'E1–E8', 'https://x/runs/7620', 'https://x/jobs/7620', 'Voraussetzungen prüfen',
             '**Offen seit:** 15.10.2026, 09:54:25', 'actions/workflows/backup-offsite.yml'],
    nichtImBody: ['GROQ', 'Häufigste Ursachen', 'API-Key abgelaufen', 'https://x/runs/38701800402'] });
// Idempotenz: Steht der Rat schon drin UND der aufgezeichnete Lauf ist der
// aktuelle, bleibt die Meldung unberührt (keine tägliche Umschrift).
await run('Nachführung idempotent: gleicher Rat + gleicher Lauf → keine Umschrift',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7621,
    jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/7621)\nRat von heute',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [], { anzahl: 0 });
// Lagebild-Verfall (WF-E813 / #815, 26.10.2026): Gleicher Rat, aber der Body
// zeigt noch den VORTÄGLICHEN Lauf. Die Meldung wird mit dem jüngsten Lauf
// erneuert – gleicher Rat, neue Zeit, neuer Run-Link, neue Job-Marker.
await run('Lagebild-Verfall: gleicher Rat + älterer Lauf im Body → Lauf-Nachweis erneuert',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7621,
    jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/7620)\nRat von gestern',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [],
  { anzahl: 1, nummer: 761,
    imBody: ['<!-- alert-runbook: backup-einrichtung -->', 'Einrichtung unvollständig – ein Neustart hilft nicht',
             'https://x/runs/7621', 'https://x/jobs/7620', '**Offen seit:** 15.10.2026, 09:54:25',
             '<!-- alert-jobs: ["' + BACKUP_KV_JOB + '"]'],
    nichtImBody: ['https://x/runs/7620)', 'GROQ'] });
// Reihenfolgeschutz: Ein ÄLTERES Ereignis (verspätete Zustellung, Re-Run
// eines alten Laufs) darf ein jüngeres Lagebild NICHT überschreiben.
await run('Reihenfolgeschutz: älterer Lauf im Ereignis → Body bleibt beim jüngeren Lauf',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7619,
    jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/7621)\nRat von gerade eben',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [], { anzahl: 0 });
// Fail-open auch auf dem Lagebild-Verfalls-Pfad (26.10.2026, WF-9E5A):
// Gleiche Klasse, älterer Lauf im Body, aber die Issue-API lehnt das Update
// ab. Kein Absturz, kein Duplikat – die Meldung bleibt unverändert offen.
await run('Lagebild-Verfall scheitert an der API → kein Absturz, kein Duplikat, Meldung bleibt offen',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7624,
    updateFail: true, jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/7620)\nAlt',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [], { anzahl: 0 });
// Klassenwechsel: Einrichtung erledigt, danach scheitert der Export → der
// Einrichtungs-Rat wäre jetzt falsch und wird ersetzt.
await run('Klassenwechsel: Einrichtungs-Rat offen, jetzt Export rot → Rat „backup“ ersetzt ihn',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7622,
    jobs: [{ name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/7622',
             steps: [{ name: 'Exportieren, verschlüsseln, Rückweg prüfen', conclusion: 'failure' }] }],
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\n1. **Einrichtung unvollständig – ein Neustart hilft nicht.**',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [],
  { anzahl: 1, nummer: 761,
    imBody: ['<!-- alert-runbook: backup -->', 'Abschnitt „Fehlerbilder“', 'Exportieren, verschlüsseln, Rückweg prüfen'],
    nichtImBody: ['alert-runbook: backup-einrichtung', 'Einrichtung unvollständig', 'GROQ'] });
// Unsichere Diagnose: Ohne Job-Lage fiele die Klasse auf den allgemeinen
// Backup-Rat zurück. Ein präziser Rat darf davon nicht überschrieben werden.
await run('Job-API-Ausfall bei offener Meldung → präziser Rat bleibt (keine Umschrift)',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', jobsFail: true,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel,
                   body: BACKUP_IDENT.marker + '\n<!-- alert-runbook: backup-einrichtung -->\nRat',
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [], { anzahl: 0 });
// Fail-open: Lehnt die API das Nachführen ab, darf das Alerting nicht
// abstürzen und kein Duplikat anlegen – die Meldung bleibt offen.
await run('Nachführen scheitert an der API → kein Absturz, kein Duplikat',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure', updateFail: true,
    jobs: KV_JOB_EINRICHTUNG_ROT,
    openIssues: [{ number: 761, title: BACKUP_IDENT.titel, body: ALT_761_BODY,
                   created_at: '2026-10-15T07:54:25Z' }] },
  false, [], { anzahl: 0 });
// Allgemein, nicht nur Backup: Bestand ohne Klassen-Marker (z. B. #767) wird
// beim nächsten roten Lauf einmal nachgeführt und trägt danach den Marker.
await run('Bestand ohne Klassen-Marker (fremder Workflow) → einmal nachgeführt mit Marker',
  { branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7623,
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/7623',
             steps: [{ name: 'Browser-Audit', conclusion: 'failure' }] }],
    openIssues: [{ number: 767, title: IDENTITIES['Layout-AI'].titel,
                   body: IDENTITIES['Layout-AI'].marker + '\nDetails', created_at: '2026-10-15T11:11:40Z' }] },
  false, [],
  { anzahl: 1, nummer: 767,
    imBody: ['<!-- alert-runbook: allgemein -->', 'Häufigste Ursachen', 'Browser-Audit', 'https://x/runs/7623',
             '**Offen seit:** 15.10.2026, 13:11:40'],
    nichtImBody: ['Einrichtung unvollständig'] });
// Gegenprobe: derselbe Schrittname in einem fremden Workflow → Standard-Runbook.
await run('WF-9E5A-Gegenprobe: „Voraussetzungen prüfen“ in fremdem Workflow → Standard-Runbook',
  { workflowName: 'Layout-AI', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/7613',
             steps: [{ name: 'Voraussetzungen prüfen (fail-closed – kein Schein-Grün)', conclusion: 'failure' }] }] },
  true, ['Häufigste Ursachen'], null, ['Einrichtung unvollständig', 'ANLEITUNG-OFFSITE-BACKUP']);
// 12. WF-E813 (15.10.2026): Der F-01-Schritt misst nur HTTP-Kopfzeilen.
//     Der Standardrat „API-Key abgelaufen" trifft auf diesen Kanal NIE zu und
//     nannte nicht den einzigen Schritt, der hilft (A1 im Dashboard). Die
//     Meldung muss die Klasse erklären (BEFUND vs. STOERUNG) statt zu raten.
await run('WF-E813-Reproduktion: F-01-Header-Wache rot -> Header-Triage, kein Schluessel-Rat',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'Live-Messung (täglich und auf Zuruf)', conclusion: 'failure',
             html_url: 'https://x/jobs/116390346576',
             steps: [{ name: 'Sicherheits-Header auswerten (F-01) · Befund · Störung · grün', conclusion: 'failure' }] }] },
  true, ['Sicherheits-Header auswerten', 'BEFUND = es wurde gemessen',
         'cloudflare/edge-schutz.md', 'docs/SICHERHEIT-BETRIEB-RUNBOOK.md',
         'FF Sicherheits-Header', '### Fehlgeschlagene Schritte',
         // WF-E813 / #809 (19.10.2026): Der Body trägt die fehlgeschlagenen
         // Jobs maschinenlesbar – die Schließseite prüft genau dagegen.
         '<!-- alert-jobs: ["Live-Messung (täglich und auf Zuruf)"]'],
  null, ['API-Key abgelaufen', 'Häufigste Ursachen']);
// 13. Dieselbe Wache, anderer Prüfschritt (Inhalts-/Betriebs-/Automatik-Wache):
//     auch hier ist ein Schlüssel-Rat irreführend – der Verweis geht auf die
//     vier Wachen und ihre Selbsttests.
await run('Sicherheits-Wache: anderer Prüfschritt rot -> Wachen-Runbook, kein Schluessel-Rat',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'Quellseite (offline, mit Selbsttests)', conclusion: 'failure',
             html_url: 'https://x/jobs/2',
             steps: [{ name: 'Betriebs-Wache – Deckel, Turnstile, Schlüsselrollen (F-02/F-03/F-08, offline)', conclusion: 'failure' }] }] },
  true, ['F-01 bis F-10', 'npm run test:sicherheit'], null, ['API-Key abgelaufen']);
// 14. Gegenprobe: Ein Workflow OHNE Wachen-Bezug behält das bisherige Runbook
//     (die neue Triage darf nicht zum neuen Standardrat werden).
await run('Gegenprobe: Layout-AI rot -> bisheriges Runbook bleibt stehen',
  { workflowName: 'Layout-AI', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/3',
             steps: [{ name: 'Layout-Prüfung', conclusion: 'failure' }] }] },
  true, ['Häufigste Ursachen', 'API-Key abgelaufen'], null, ['FF Sicherheits-Header']);

// WF-E813 x WF-9E5A (15.10.2026): Der Nachfuehr-Mechanismus aus #761 muss auch
//     fuer die Sicherheits-Wache greifen. Wechselt die Klasse des Rats in einer
//     offenen Meldung (hier: allgemein -> sicherheit-header), wird sie neu
//     geschrieben. Ohne eigenen Klassennamen bliebe „API-Key abgelaufen" in
//     #767 stehen, obwohl die Wache laengst BEFUND von STOERUNG trennt.
await run('WF-E813: offene Meldung bekommt beim Klassenwechsel den neuen Rat',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7670,
    jobs: [{ name: 'Live-Messung (täglich und auf Zuruf)', conclusion: 'failure',
             html_url: 'https://x/jobs/116390346576',
             steps: [{ name: 'Sicherheits-Header auswerten (F-01) · Befund · Störung · grün', conclusion: 'failure' }] }],
    openIssues: [{ number: 767, title: IDENTITIES['Sicherheits-Wache'].titel,
                   body: IDENTITIES['Sicherheits-Wache'].marker + '\nDetails', created_at: '2026-10-15T11:11:40Z' }] },
  false, [],
  { anzahl: 1, nummer: 767,
    imBody: ['<!-- alert-runbook: sicherheit-header -->', 'FF Sicherheits-Header',
             'docs/SICHERHEIT-BETRIEB-RUNBOOK.md', 'Sicherheits-Header auswerten'],
    nichtImBody: ['API-Key abgelaufen', 'Häufigste Ursachen'] });

// #809 (19.10.2026): Im echten Lauf waren F-01 UND Worker rot. Der
// bisherige Header-Vorrang behauptete trotzdem „ausschließlich HTTP“.
const LIVE_809 = [{ name: 'Live-Messung (täglich und auf Zuruf)', conclusion: 'failure',
  html_url: 'https://x/jobs/118065546628', steps: [
    { name: 'Sicherheits-Header auswerten (F-01) · Befund · Störung · grün', conclusion: 'failure' },
    { name: 'Worker-Zustand messen – Budget, Bot-Schutz, Exporte (F-02/F-03/F-08)', conclusion: 'failure' },
    { name: 'Live-Nachweis abschließen (F-01/F-02/F-03/F-08)', conclusion: 'failure' }
  ] }];
await run('#809-Reproduktion: Header UND Worker rot → beide Handlungswege',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'schedule', conclusion: 'failure', jobs: LIVE_809 },
  true, ['<!-- alert-runbook: sicherheit-live -->', 'Zwei unabhängige Live-Prüfungen',
         'FF Sicherheits-Header', '**Worker:**', 'A3/A4 und D2',
         'KV_NAMESPACE_ID_ABO', 'edge:freigabe:apply', 'edge:b7:apply',
         'vollständiger erfolgreicher Live-Nachweis'],
  null, ['ausschließlich HTTP-Kopfzeilen', 'API-Key abgelaufen', 'du musst nichts manuell prüfen']);

await run('#809: nur Worker-Auswertung rot → Worker-Triage, keine Header-Reparatur',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'workflow_dispatch', conclusion: 'failure',
    jobs: [{ name: 'Live-Messung (täglich und auf Zuruf)', conclusion: 'failure', html_url: 'https://x/jobs/8091',
      steps: [{ name: 'Worker-Zustand auswerten (F-02/F-03/F-08) · Befund · Störung · grün', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: sicherheit-worker -->', 'authentifizierte Betriebsbild', 'STOERUNG',
         'öffentliche/minimale oder veraltete /healthz-Antwort', 'Kein Secret entfernen'],
  null, ['FF Sicherheits-Header', 'ausschließlich HTTP-Kopfzeilen', 'API-Key abgelaufen']);

await run('#809: Einzelmessungen grün, Nachweis unvollständig → Nachweis-Triage',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'Live-Messung (täglich und auf Zuruf)', conclusion: 'failure', html_url: 'https://x/jobs/8092',
      steps: [{ name: 'Live-Nachweis abschließen (F-01/F-02/F-03/F-08)', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: sicherheit-nachweis -->', 'Live-Nachweis unvollständig', 'TEILWEISE',
         'kein zusätzlicher Sicherheitsbefund', 'test_sicherheits_nachweis'],
  null, ['FF Sicherheits-Header', 'API-Key abgelaufen']);

await run('#809: bestehender Header-Rat wird bei zwei roten Messungen nachgeführt',
  { workflowName: 'Sicherheits-Wache', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: LIVE_809, openIssues: [{ number: 809, title: IDENTITIES['Sicherheits-Wache'].titel,
      body: IDENTITIES['Sicherheits-Wache'].marker + '\n<!-- alert-runbook: sicherheit-header -->',
      created_at: '2026-10-19T12:43:55Z' }] },
  false, [], { anzahl: 1, nummer: 809,
    imBody: ['<!-- alert-runbook: sicherheit-live -->', 'Zwei unabhängige Live-Prüfungen', '**Worker:**'],
    nichtImBody: ['ausschließlich HTTP-Kopfzeilen', 'API-Key abgelaufen'] });

await run('#809-Gegenprobe: gleicher Worker-Schritt in fremdem Workflow bleibt Standard',
  { workflowName: 'Layout-AI', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'anderer Lauf', conclusion: 'failure', html_url: 'https://x/jobs/8093',
      steps: [{ name: 'Worker-Zustand auswerten', conclusion: 'failure' }] }] },
  true, ['Häufigste Ursachen'], null, ['<!-- alert-runbook: sicherheit-worker -->']);

// WF-53E2 / #780 (16.10.2026): Ein roter Selbsttest ist eine Code-Regression.
//     Exakte Konstellation des Vorfalls: Der Detektor-Selbsttest der
//     Affiliate-Wache war seit dem Merge von #776 rot, danach scheiterte nur
//     noch die Schlussbewertung. Die Meldung riet zu GROQ/GEMINI und zum
//     Neustart – beides kann einen Offline-Selbsttest weder rot noch grün
//     machen. Derselbe Merge erzeugte am selben Tag #777, #778 und #783.
const AFFILIATE_WACHE = 'Affiliate-Integritäts-Wache (täglich)';
const SELBSTTEST_780 = [{ name: 'integritaet', conclusion: 'failure',
  html_url: 'https://x/jobs/116888354398',
  steps: [{ name: 'Hugo installieren (Extended, verifiziert, mehrquellig)', conclusion: 'success' },
          { name: 'Detektor-Selbsttest (Wache muss sehen können)', conclusion: 'failure' },
          { name: 'Lauf bewerten (rot nur bei unheilbarem Werkzeugfehler)', conclusion: 'failure' }] }];
await run('#780-Reproduktion: Detektor-Selbsttest rot → Selbsttest-Rat, kein Schlüssel-/Neustart-Rat',
  { workflowName: AFFILIATE_WACHE, branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: SELBSTTEST_780 },
  true,
  ['Vorgang **WF-53E2**', '<!-- alert-runbook: selbsttest -->', 'Code-Regression, kein Betriebsausfall',
   'python3 scripts/selftest_runner.py', 'Detektor-Selbsttest (Wache muss sehen können)',
   'https://x/jobs/116888354398', 'schließt sich beim nächsten grünen Lauf'],
  null,
  ['Häufigste Ursachen', 'API-Key abgelaufen', 'Transienter Fehler', 'Workflow manuell neu starten']);
// #778 (gleicher Merge): die Content-Reserve starb an ihren Selbsttests –
// der Rat muss derselbe sein, nicht „Schlüssel prüfen“.
await run('#778-Reproduktion: „Selbsttests aller Wachen“ rot → Selbsttest-Rat',
  { workflowName: 'Content-Reserve (täglicher Vorrat)', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'reserve', conclusion: 'failure', html_url: 'https://x/jobs/116881739147',
             steps: [{ name: 'Selbsttests aller Wachen (entdeckt, uhrfest, schreibfrei)', conclusion: 'failure' },
                     { name: 'Stock shortage must not look successful', conclusion: 'failure' }] }] },
  true, ['Vorgang **WF-D4E0**', '<!-- alert-runbook: selbsttest -->', 'selftest_runner.py'],
  null, ['API-Key abgelaufen', 'Häufigste Ursachen']);
// Der ERSTE rote Schritt entscheidet: Ein Selbsttest, der nur als Folge
// eines früheren Fehlers rot wird, macht daraus keine Code-Regression.
await run('#780-Gegenprobe: erster roter Schritt ist kein Selbsttest → bisheriger Rat',
  { workflowName: 'Layout-AI', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'layout-audit', conclusion: 'failure', html_url: 'https://x/jobs/7801',
             steps: [{ name: 'Browser-Audit', conclusion: 'failure' },
                     { name: 'Selbsttest der Wache (Sabotage-Proben)', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: allgemein -->', 'Häufigste Ursachen'],
  null, ['alert-runbook: selbsttest', 'Code-Regression, kein Betriebsausfall']);
// Vorrang: Spezifische Klassen schlagen den Selbsttest-Rat (Installation
// kennt die Ursache genauer; das Backup hat seine eigene Anleitung).
await run('#780-Vorrang: Install-Schritt rot vor dem Selbsttest → Installations-Rat',
  { workflowName: AFFILIATE_WACHE, branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: 'integritaet', conclusion: 'failure', html_url: 'https://x/jobs/7802',
             steps: [{ name: 'Abhängigkeiten', conclusion: 'failure' },
                     { name: 'Detektor-Selbsttest (Wache muss sehen können)', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: installation -->', 'Abhängigkeiten nicht installierbar'],
  null, ['alert-runbook: selbsttest', 'API-Key abgelaufen']);
await run('#780-Vorrang: Backup-Selbsttest rot → Backup-Rat bleibt',
  { workflowName: 'Offsite-Backup', branch: 'main', event: 'schedule', conclusion: 'failure',
    jobs: [{ name: BACKUP_KV_JOB, conclusion: 'failure', html_url: 'https://x/jobs/7803',
             steps: [{ name: 'Selbsttest (Export, Probe, Einrichtungsprüfung – fail-closed)', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: backup -->'], null, ['alert-runbook: selbsttest', 'API-Key abgelaufen']);
// Lagebild (#761-Mechanismus): #780 steht mit dem allgemeinen Rat offen.
// Der nächste rote Lauf schreibt dieselbe Meldung mit dem Selbsttest-Rat
// neu – keine zweite Meldung, kein Schlüssel-Rat mehr.
const AFFILIATE_IDENT = IDENTITIES[AFFILIATE_WACHE];
await run('#780-Nachführung: offene Meldung mit allgemeinem Rat → gleiche Nummer, Selbsttest-Rat',
  { workflowName: AFFILIATE_WACHE, branch: 'main', event: 'schedule', conclusion: 'failure', runId: 7804,
    jobs: SELBSTTEST_780,
    openIssues: [{ number: 780, title: AFFILIATE_IDENT.titel,
                   body: AFFILIATE_IDENT.marker + '\n<!-- alert-runbook: allgemein -->\n'
                     + '   - **API-Key abgelaufen** (GROQ/GEMINI) → Secrets in den Repo-Einstellungen aktualisieren',
                   created_at: '2026-10-16T08:40:23Z' }] },
  false, [],
  { anzahl: 1, nummer: 780,
    imBody: ['<!-- alert-runbook: selbsttest -->', 'Code-Regression, kein Betriebsausfall',
             'https://x/runs/7804', '**Offen seit:** 16.10.2026, 10:40:23'],
    nichtImBody: ['API-Key abgelaufen', 'Häufigste Ursachen', 'alert-runbook: allgemein'] });

// WF-E813-Folgebefund (26.10.2026): „Cloudflare-Worker deployen“ war seit
//     25.10. still rot (fail-closed, fehlender Produktions-Zugang) und stand
//     NICHT in der Wacht-Liste – der Heilungsschritt der Sicherheits-Wache
//     (Runbook D2) war unsichtbar. Drei Szenarien: Zugang, Tests, Deploy.
const WORKER_DEPLOY = 'Cloudflare-Worker deployen';
await run('Worker-Deploy ohne Produktions-Zugang → Einrichtungs-Rat, kein Schlüssel-/Neustart-Rat',
  { workflowName: WORKER_DEPLOY, branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'Deploy klick-zaehler', conclusion: 'failure', html_url: 'https://x/jobs/wd1',
             steps: [{ name: 'Worker-Tests', conclusion: 'success' },
                     { name: 'Produktive Ressource auflösen (lesend, ohne neuen Speicher)', conclusion: 'failure' }] }] },
  true, ['Vorgang **' + IDENTITIES[WORKER_DEPLOY].code + '**', 'Fail-closed – gewollt, kein Betriebsausfall',
         'cloudflare-produktion', 'CF_WORKERS_DEPLOY_TOKEN', 'worker_ressourcen.py',
         '<!-- alert-runbook: worker-deploy-zugang -->', 'kein Betriebsausfall'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'GROQ', 'Transienter Fehler']);
await run('Worker-Deploy: Environment-Policy ungeschützt → Reviewer-/main-/Admin-Bypass-Rat',
  { workflowName: WORKER_DEPLOY, branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'Produktions-Environment absichern (nur main, Reviewer, kein Admin-Bypass)',
             conclusion: 'failure', html_url: 'https://x/jobs/wd-policy',
             steps: [{ name: 'Produktions-Environment absichern (vor Zugriff auf Secrets)',
                       conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: worker-deploy-zugang -->', 'Environment zuerst absichern',
         'Required Reviewer', '`can_admins_bypass=false`', 'worker_environment_guard.py',
         'CF_WORKERS_DEPLOY_TOKEN'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'GROQ', 'GITHUB_TOKEN']);
await run('Worker-Deploy: rote Worker-Tests → Selbsttest-Rat (Code-Regression)',
  { workflowName: WORKER_DEPLOY, branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'Deploy newsletter-worker', conclusion: 'failure', html_url: 'https://x/jobs/wd2',
             steps: [{ name: 'Worker-Tests', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: selbsttest -->', 'Code-Regression, kein Betriebsausfall', 'selftest'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'Fail-closed – gewollt']);
await run('Worker-Deploy: Deploy-Schritt rot → Deploy-Rat mit Live-Nachweis-Pflicht',
  { workflowName: WORKER_DEPLOY, branch: 'main', event: 'workflow_dispatch', conclusion: 'failure',
    jobs: [{ name: 'Deploy klick-zaehler', conclusion: 'failure', html_url: 'https://x/jobs/wd3',
             steps: [{ name: 'Worker-Tests', conclusion: 'success' },
                     { name: 'Produktive Ressource auflösen (lesend, ohne neuen Speicher)', conclusion: 'success' },
                     { name: 'Deploy', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: worker-deploy -->', 'Ein grüner Plan ist kein Deploy', 'bau`-Stempel'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen']);
// 26.10.2026: CodeQL-Sicherheitswache. Das Gate war bei echten Fundstellen
//     (js/incomplete-sanitization, js/regex/missing-regexp-anchor) still rot.
await run('CodeQL-Gate: echte Fundstelle → Heilungs-Rat, kein Schlüssel-Rat',
  { workflowName: 'CodeQL-Sicherheitswache', branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'CodeQL (javascript)', conclusion: 'failure', html_url: 'https://x/jobs/cq1',
             steps: [{ name: 'CodeQL analysieren', conclusion: 'success' },
                     { name: 'Sicherheits-Gate (null Security-Fundstellen)', conclusion: 'failure' }] }] },
  true, ['Vorgang **' + IDENTITIES['CodeQL-Sicherheitswache'].code + '**',
         '<!-- alert-runbook: codeql-fund -->', 'Echte Security-Fundstelle im Code – kein Betriebsausfall',
         'Im Code heilen, nicht wegdrücken', 'CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'GROQ']);
await run('CodeQL: Analyse-Störung ohne Gate-Rot → Störungs-Rat, kein Heilungs-Rat',
  { workflowName: 'CodeQL-Sicherheitswache', branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'CodeQL (python)', conclusion: 'failure', html_url: 'https://x/jobs/cq2',
             steps: [{ name: 'CodeQL initialisieren', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: codeql -->', 'Analyse- oder Upload-Störung, kein Code-Befund', 'githubstatus'],
  null, ['im Code heilen, nicht wegdrücken', 'Häufigste Ursachen', 'API-Key abgelaufen']);
// 27.10.2026 (WF-E813/#815): Der Skript-Syntax-Lauf prüft den LIEGENDEN
//     Stand (#864) und seit dieser Stufe die Trigger-Vollständigkeit. Er stand
//     nicht auf der Wacht-Liste; jetzt hat er einen eigenen Rat, der weder
//     Schlüssel noch Neustart empfiehlt.
const SKRIPT_SYNTAX = 'Skript-Syntax (liegender Stand)';
await run('Skript-Syntax: Syntaxfehler im liegenden Stand → Code-Regressions-Rat',
  { workflowName: SKRIPT_SYNTAX, branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'syntax', conclusion: 'failure', html_url: 'https://x/jobs/ss1',
             steps: [{ name: 'Wache selbst prüfen', conclusion: 'success' },
                     { name: 'Alle Skripte kompilieren (fail-closed)', conclusion: 'failure' }] }] },
  true, ['Vorgang **' + IDENTITIES[SKRIPT_SYNTAX].code + '**',
         '<!-- alert-runbook: skript-syntax -->', 'Code- oder Vertragsregression, kein Betriebsausfall',
         'skript_syntax_heiler.py'],
  null, ['Häufigste Ursachen', 'API-Key abgelaufen', 'GROQ']);
await run('Trigger-Wache rot → Vertragsregressions-Rat mit Pfad-Ergänzung',
  { workflowName: SKRIPT_SYNTAX, branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'syntax', conclusion: 'failure', html_url: 'https://x/jobs/ss2',
             steps: [{ name: 'Trigger-Wache – was ein Lauf prüft, muss ihn auslösen', conclusion: 'failure' }] }] },
  true, ['<!-- alert-runbook: skript-syntax -->', 'npm run trigger:check',
         'BEIDEN Listen', 'Abschnitt F2'],
  null, ['Häufigste Ursachen', 'Transienter Fehler']);
// Gegenprobe: Der Rat ist an den KANAL gebunden, nicht an den Schrittnamen.
await run('Skript-Syntax-Rat gilt nur für den eigenen Kanal (Gegenprobe)',
  { workflowName: 'Layout-AI', branch: 'main', event: 'push', conclusion: 'failure',
    jobs: [{ name: 'Layout-AI', conclusion: 'failure', html_url: 'https://x/jobs/ss3',
             steps: [{ name: 'Trigger-Wache – was ein Lauf prüft, muss ihn auslösen', conclusion: 'failure' }] }] },
  true, ['Häufigste Ursachen'], null, ['<!-- alert-runbook: skript-syntax -->']);

// Nachführung der neuen Klassen über die #761/#815-Mechanik: Eine offene
// Meldung mit veraltetem Allgemeinnrat bekommt den neuen Kanal-Rat.
await run('Worker-Deploy: offene Meldung mit Allgemeinnrat → Zugang-Rat nachgeführt',
  { workflowName: WORKER_DEPLOY, branch: 'main', event: 'push', conclusion: 'failure', runId: 8701,
    jobs: [{ name: 'Deploy klick-zaehler', conclusion: 'failure', html_url: 'https://x/jobs/wd4',
             steps: [{ name: 'Produktive Ressource auflösen (lesend, ohne neuen Speicher)', conclusion: 'failure' }] }],
    openIssues: [{ number: 870, title: IDENTITIES[WORKER_DEPLOY].titel,
                   body: IDENTITIES[WORKER_DEPLOY].marker + '\n<!-- alert-runbook: allgemein -->\n'
                     + '- **Run:** [Details ansehen](https://x/runs/8690)',
                   created_at: '2026-10-26T10:40:00Z' }] },
  false, [],
  { anzahl: 1, nummer: 870,
    imBody: ['<!-- alert-runbook: worker-deploy-zugang -->', 'CF_WORKERS_DEPLOY_TOKEN', 'https://x/runs/8701',
             '**Offen seit:** 26.10.2026, 11:40:00'],
    nichtImBody: ['alert-runbook: allgemein', 'Häufigste Ursachen'] });

// 12. KANAL-HYGIENE (Sicherheitsaudit 15.10.2026, F-09): Der Workflow-Name
//    stammt aus dem Webhook. Er darf den Body nicht steuern – kein Markdown,
//    keine Mention (@all würde Dritte benachrichtigen), kein HTML, kein
//    Zeilenumbruch. Die Rohwerte bleiben nur dort stehen, wo exakt verglichen
//    wird (Dedupe gegen den Alt-Titel, Content-Engine-Erkennung).
const BOESER_NAME = 'Layout-AI` @all [Klick](http://boese.example)\nZweite Zeile';
await run('F-09: Markdown/Mention im Workflow-Namen wird entschärft',
  { workflowName: BOESER_NAME, branch: 'main', event: 'schedule', conclusion: 'failure', jobs: [] },
  true, ['ist fehlgeschlagen', 'Layout-AI·'], null, ['@all', '[Klick]', '](http://boese']);
// 13. Gegenprobe: saubere Namen kommen unverändert durch (die Entschärfung
//     darf den Normalfall nicht verstümmeln).
await run('F-09 Gegenprobe: sauberer Name bleibt lesbar',
  { workflowName: 'Layout-AI', branch: 'main', event: 'push', conclusion: 'failure', jobs: [] },
  true, ['**Workflow:** Layout-AI', '**Branch:** main'], null, ['Layout-AI·']);

console.log(failed === 0
  ? `\n✅ SIMULATION: alle ${count} Szenarien korrekt`
  : `\n❌ SIMULATION: ${failed} von ${count} Szenarien falsch`);
process.exit(failed === 0 ? 0 : 1);
