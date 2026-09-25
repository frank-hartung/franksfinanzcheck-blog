# Newsletter-Zustellung: drei Befunde aus Lauf #29 – und was davon stimmte

**Stand: 25. September 2026.** Grundlage ist der Lauf
[`Newsletter-Daily (Capture-Wache + Digest) #36123102353`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36123102353)
(workflow_dispatch, `head_sha f7749aca…`, Exit 2, Job `108032969327`) und das
Journal `data/newsletter_journal.jsonl`. Dieser Report trennt, was der Lauf
**gemeldet** hat, was davon **stimmte** – und was er verschwiegen hat, weil die
Wache sich selbst im Weg stand.

| # | Meldung des Laufs | Verdikt nach der Messung |
|---|---|---|
| 1 | `❌ TESTVERSAND FEHLGESCHLAGEN … es ist nichts versandt` | **stimmt** – der Testversand starb an der Cloudflare-Kante (HTTP 403 · Error 1010); der Versand-Client schickte den urllib-Default-User-Agent |
| 2 | `❌ [B1/resend] Sende-Domain franksfinanzcheck.de fehlt im Resend-Konto` („Konto-Domänen: None“) | **Falsch-Fund der Wache**: Resend antwortet mit `name`/`status`, die Wache las `domain`/`verified` und sah überall `None` |
| 3 | `🌫 [C0/cloudflare] DNS nicht erreichbar` und `🌫 [C7/worker] DNS nicht erreichbar` | **Messfehler der Wache**: die DoH-Abfrage-URL war mit zwei `?` gebaut (HTTP 400 bei beiden Resolvern) – „HTTP 400“ ist eine Antwort, kein Netzausfall |
| 4 | *(nicht gemeldet)* stündlicher Lifecycle-Lauf `36119608004`: `! Nachgang unvollständig (Exit 1)` | **echter Defekt**: der Mailer nahm den Export-Schlüssel entgegen und sendete ihn nie – jede Bestätigung und jeder Nachgang endete in „Worker-Antwort 403“ |

---

## 1. Der Testversand starb an der Kante – und der Grund war der User-Agent

Letzte Journal-Zeile des Laufs (nur Hash, keine Adresse – das Repo ist öffentlich):

```json
{"ts":"2026-09-25T10:16:56+00:00","modus":"sendefile","ausgabe":"test-2026-09-25",
 "empfaenger":"5ebc8f38444904a8","bytes":16066,"transport":"resend",
 "status":"fehler","detail":"HTTP 403: {… \"error-1010/\" … \"Error 1010: Access denied\"}"}
```

Diese Antwort kommt **nicht von Resend**, sondern von der Cloudflare-Kante vor
`api.resend.com`: die Anfrage hat den Anbieter nie erreicht (genau die
Verwechslung, die schon am 23.09.2026 im Brevo-Kapitel stand). Ursache diesmal
nicht die Zone, sondern der Client: `scripts/newsletter_versand.py` setzte
keinen User-Agent, also sendete urllib `Python-urllib/3.x` – eine Signatur, die
Cloudflares Bot-Filter mit Error 1010 abweist. Die Wache fragte dagegen mit
ihrem eigenen User-Agent und meldete `✅ B0 Netzweg zur Resend-API frei`:
**zwei Signaturen, zwei Wahrheiten im selben Lauf.**

Reparatur (alles in `scripts/newsletter_versand.py`):

* `UA_KENNUNG` = `FranksFinanzcheck-Newsletter/1.0 (+https://franksfinanzcheck.de; mailto:kontakt@franksfinanzcheck.de)`
* `api_headers(key, json_body)` ist **eine** Quelle für die Kopfzeilen – der
  Versand **und** die Vorprüfung B0 der Wache (`_sendesignatur`) nutzen sie.
  Ist der Mailer nicht importierbar, bleibt B0 „nicht messbar“ statt grün.
* `kanten_block(status, koerper)` (403 + `1010`/„browser's signature“) lebt im
  Mailer; die Wache importiert sie (`KANTEN_AUS_MAILER`, Reserve-Kopie nur für
  den Fall eines kaputten Mailers).
* Ein Kanten-Block wird **nicht wiederholt** und heißt in der Meldung beim
  Namen: `HTTP 403 · KANTE (Error 1010, Signaturfilter) …`.
* Die ❌-Zeile des Digests trägt die Ursache aus dem Journal
  (`versand.letzter_fehler(root, ausgabe=…)`) – damit steht sie als Annotation
  im Lauf, statt nur im Summary.

## 2. „Sende-Domain fehlt“ war ein Falsch-Fund – die Zone ist Resend-bereit

Resends `GET /domains` liefert Objekte mit **`name`** und **`status`**
(`verified`, `pending`, `not_started`, …), nicht `domain`/`verified`. Die Wache
las die alten Feldnamen, sah für jede Domäne `None` und meldete daraus einen
Fund. Der Beweis des Gegenteils kommt aus derselben Messung, die vorher gar
nicht lief (siehe Befund 3) – die Zone trägt die Resend-Einträge:

| Regel | Messung heute | Bewertung |
|---|---|---|
| C1 SPF | `v=spf1 include:_spf.mx.cloudflare.net ~all` | ✅ die eigene SPF der Zone, unverändert (SES-Modell) |
| C2 Send-Subdomain | `CNAME send → send.forge.rmta.net.` | ✅ Resend-Forge-Delegation live |
| C3 DKIM | `resend._domainkey` vorhanden (`p=…`) | ✅ live |
| C4 DMARC | `v=DMARC1; p=reject; adkim=s; aspf=s; rua=mailto:…@dmarc-reports.cloudflare.net;` | ✅ mit Berichtsweg |

Reparatur (`scripts/newsletter_zustellbarkeit.py`): `_resend_name` liest
`name` **oder** `domain`, `_resend_verifiziert` liest `status` **oder**
`verified` (und für `partially_verified` die Sende-Berechtigung). Eine Antwort
ohne `data`-Liste ist „nicht messbar“ – kein Fund, kein Grün. Die Konto-Liste
nennt Namen, und wenn es keine gibt, steht dort „keine“ statt `None`.

## 3. „DNS nicht erreichbar“ war die Wache selbst

`DOH_ENDPUNKTE` endete auf `"…?dnssec=false&"` bzw. `"…/dns-query?"`, und die
Frage begann mit `"?"` – die Abfrage ging also als `…?dnssec=false&?name=…`
hinaus, und **beide** Resolver antworteten HTTP 400. Die Wache verpackte das in
„DNS nicht erreichbar“ (C0/C7 gelb) – und entschuldigte damit jeden echten
Befund gleich mit (`curl 'https://dns.google/resolve?name=…&type=TXT'` bewies
jederzeit das Gegenteil).

Reparatur: `doh_url(basis, name, typ, extra)` baut die URL mit
`urllib.parse.urlencode` und genau **einem** `?`; `_doh` meldet HTTP-Fehler mit
Status (`dns.google: HTTP 400`), und `messluecke()` benennt die Klasse: weisen
**alle** Resolver mit 4xx ab, ist die Abfrage falsch gebaut – „kein
Netzausfall“. C4/C5/C6/C7 kennen jetzt ausdrücklich „nicht messbar“ (vorher
wurde aus einem Resolver-Ausfall z. B. C5 „kein MX auf der Zone“).

## 4. (Neu gefunden) Der Worker-Export bekam den Schlüssel nie zu sehen

Der stündliche Lifecycle-Lauf `36119608004` meldete
`! Nachgang unvollständig (Exit 1)`. Ursache: `worker_abfrage()` in
`scripts/newsletter_versand.py` nahm `key` entgegen, sendete ihn aber nicht. Der
Worker verlangt `x-ff-key` (oder `?sluessel=`) und antwortet sonst
`403 {"status":"verboten"}` – jede Bestätigung (DOpt-In-Mail!), jeder Nachgang
und der Listen-Export wären daran gestorben. Reparatur + Test: der Schlüssel
geht als `x-ff-key` mit, der Selftest misst die Kopfzeilen am echten Request.

## 5. Was jetzt zu tun ist (Menschenarbeit)

1. **Testversand erneut starten**: Actions → *Newsletter-Daily (Capture-Wache +
   Digest)* → Run workflow, `test_adresse` = eigene Adresse. Erwartung nach
   dem Fix: `✅ TESTVERSAND ERFOLGT` – oder, falls die Kante erneut 1010
   liefert, eine Meldung, die „KANTE“ und „1010“ nennt (dann ist der Zweitweg
   `NEWSLETTER_TRANSPORT=smtp` dran; das ist kein DNS-/Konto-Befund).
2. **Resend-Konto gegenprüfen**: Sending Domains → `franksfinanzcheck.de` muss
   dort stehen und `verified` sein (die DNS-Seite ist es, siehe §2). Ob sie
   dort steht, beantwortet jetzt die Wache korrekt (B1) – vorher beantwortete
   sie die Frage mit `None`.
3. **Erst danach die Liste freigeben** (`live` bzw. der Di/Fr-Cron). Die Liste
   ist weiter leer (B2 = 0) – der richtige erste Schritt ist der Testversand,
   nicht `--live`.
4. **Nachgang beobachten**: der nächste Lifecycle-Lauf (:17) sollte nicht mehr
   `Nachgang unvollständig` melden; offene Bestätigungen werden dann wirklich
   zugestellt.

## 6. Verifikation dieses Stands

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/newsletter_versand.py --selftest` | ✅ 47 Fälle (neu: Kopfzeilen/UA, Kanten-Block ohne Wiederholung, `x-ff-key`, `letzter_fehler`) |
| `python3 scripts/newsletter_zustellbarkeit.py --selftest` | ✅ 49 Fälle (neu: DoH-URL, 4xx-Messlücke, B1 in API-Form, B0 mit Sendesignatur) |
| Live-Lauf `--pruefen` (Summary) | S3 nennt jetzt die letzte Journal-Zeile: `test-2026-09-25 · fehler · HTTP 403 … error-1010` – der gescheiterte Testversand steht im Befund statt eines „nichts passiert“ |
|  `python3 -m unittest discover -s scripts/tests` | 744 Tests, 4 Fehler – **alle 4 vorbestehend** (fremde Module: affiliate_intent_guard, markdown_link_safety, saisonale_startseite, social_autopilot; im unveränderten Stand dieselben) |
| Live-Lauf `--pruefen` dieser Umgebung | C1–C4 gemessen ✅; C7/B0 „nicht messbar“ nur wegen der Netzsperre **dieser** Sandbox (TLS-Eof), nicht wegen des Repos |

Offener Rest: ein Kanten-Filter kann auch die neue Signatur abweisen. Dann ist
der Befund derselbe wie heute („KANTE“, „1010“) – der Unterschied ist, dass er
dann **stimmt** und der nächste Schritt im Satz steht.
