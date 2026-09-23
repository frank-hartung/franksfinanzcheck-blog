# Newsletter-Versand-Reparatur – Report 23.09.2026

**Anlass:** Lauf **#14** von *Newsletter-Daily (Capture-Wache + Digest)*
(23.09.2026, 01:42 UTC, `workflow_dispatch`) endete rot:
„Digest-Versand fehlgeschlagen (Exit 1) – es ist nichts versandt."

**Einordnung, ehrlich:** #14 war nicht der erste Fehler des Versands, sondern
der **erste Lauf, der den echten Brevo-Netzwerkaufruf überhaupt ausführte**.
Der Workflow-Bug vom Morgen des 23.09. („Testlauf lief grün, die Mail kam nie
an" – `--send` war nur für `schedule` verdrahtet) war Stunden zuvor behoben
worden; damit erreichte der Versand-Pfad zum ersten Mal das Netz – und brach an
der nächsten, bis dahin unsichtbaren Schicht. Genau so arbeiten Latenzen:
Ein Bug verschwindet nicht, er rückt nur näher zur Postfach.

---

## 1. Befunde (Reihenfolge der Kette)

### F1 – Der Payload nannte ein Feld, das bei Brevo nicht existiert

`versende()` schickte `"preheader": betreff[:90]`. Brevos
`CreateEmailCampaign`-Schema kennt kein `preheader` – das offizielle Feld heißt
**`previewText`** (Quelle: developers.brevo.com/reference/create-email-campaign).
Eine Kampagne mit einem Schema-fremden Feld wird abgelehnt (HTTP 400,
`invalid_parameter`) oder verliert still den Preheader – beides falsch.

**Behoben:** Der Payload spricht Brevos Schema: `previewText` (aus dem
Studio-Preheader, Fallback Betreff, 300 Zeichen), dazu `mirrorActive: true`,
damit die `{{mirror}}`-Marke des Fußes beim Anbieter tatsächlich auflöst.

### F2 – Absender und Reply-To waren hart codiert, die SSOT wurde ignoriert

`sender.name` war `"FranksFinanzcheck"` im Code, die E-Mail ein Default aus
`os.environ` – die Studio-SSOT (`data/newsletter_studio.json` → `email`:
„Frank von FranksFinanzcheck", `news@franksfinanzcheck.de`, Reply-To
`kontakt@franksfinanzcheck.de`) wurde beim Versand nicht gelesen. Ein Zustand,
zwei Orte, verschiedene Werte – derselbe Vertragsbruch, den die Wache N4 sonst
beim Formular verhindert.

**Behoben:** `absender_konfig(root)` liest Name/E-Mail/Reply-To aus der SSOT;
die Repository-Variable `NEWSLETTER_ABSENDER` bleibt als bewusste Ausnahme
darüber (Vorrang env > SSOT, wie in der Checkliste dokumentiert).

### F3 – Es prüfte nichts VOR dem Anlegen der Kampagne

Der Lauf #14 legte die Kampagne blind an und überließ die Diagnose Brevo
(„invalid sender"). Dabei sind die realen Blocker alle vorab bekannt und
stehen in der Freischalt-Checkliste:

* Absender existiert im Brevo-Konto nicht (Schritt 2: *Add sender*)
* Absender vorhanden, aber **nicht verifiziert** (6-stelliger Code bzw.
  SPF/DKIM „verifiziert" – bis zum 23.09. ausdrücklich offener Punkt)
* Liste existiert nicht (`BREVO_LIST_ID` falsch)
* Liste existiert, hat aber **0 Abonnenten** – ein Live-Versand wäre eine
  Kampagne auf niemanden (das Formular ist seit dem 22.09. live; die Liste
  kann an Tag zwei schlicht noch leer sein)

**Behoben:** `vorflug()` fragt vor dem Anlegen `GET /senders` und
`GET /contacts/lists/{id}` ab und bricht mit einem laut gesprochenen Befund
ab, der den exakten nächsten Schritt nennt – bevor bei Brevo irgendetwas
entsteht. Fail-closed: Scheitert die Vorprüfung selbst am Netz, wird nicht
gesendet. Der Testversand (`--test-adresse`) ist von der leeren Liste
bewusst **nicht** betroffen – er trifft genau eine Adresse, nie die Liste.

### F4 – Brevo-Fehler wurden verstümmelt und nie wiederholt

Fehlerantworten wurden auf 200 Zeichen gekappt, ohne `code`/`message` zu
trennen; ein 502 mitten im Versand war endgültig.

**Behoben:** `brevo_fehler()` strukturiert die Anbieter-Antwort
(„HTTP 400: \<message\> · \<code\>"); der Transport wiederholt **nur**
transiente Störungen (429, 5xx, Netz) bis zu dreimal mit kurzem Abstand –
ein 400 ist ein Befund, kein Anlass für drei identische Versuche. Der
Workflow schreibt die konkrete ❌-Zeile in die Annotation, damit die Ursache
in der Actions-Übersicht steht, bevor jemand Logs aufklappt.

---

## 2. Was die Reparatur NICHT ist

* **Kein Freischalten der Liste:** Wenn Brevo den Absender `news@franksfinanzcheck.de`
  noch nicht verifiziert hat (Checkliste Schritt 2, SPF/DKIM) oder die Liste
  leer ist, meldet der nächste Lauf das jetzt **laut und mit Anleitung** –
  senden kann nur der Betreiber freischalten, das ist die Dreifachverriegelung
  und bleibt so.
* **Kein Stilllegen der Wachen:** QA (20 Regeln, blockiert vor dem Versand),
  Capture-Wache, Duplikatschutz und die `NEWSLETTER_SEND=ja`-Verriegelung
  stehen unverändert; der Selbsttest prüft sie jetzt auf 38 statt 29 Fällen.

## 3. Beweise

| Prüfung | Ergebnis |
|---|---|
| `newsletter_digest.py --selftest` | 38 Fälle grün – neu: `previewText`/SSOT-Payload, Vorflug (4 Befundarten), Wiederholung (502 ja, 400 nein) |
| `scripts/tests/test_newsletter_digest.py` | 22/22 OK – neu: Schema-Vertrag, Vorflug-Verriegelung, transiente Wiederholung |
| Capture-Wache am gebauten Zustand | `aktiv` – Anmeldeweg, Landingpage, Rechtstext, Footer-CTA greifen ineinander |
| Digest-Bau + QA (Dry-Run, netzfrei) | 2 Artikel, 100/100 · 20 Regeln · 0 Funde, 0 Warnungen |
| Gesamte Regression (620 Unittests) | nur die 4 vorbestehenden Sandbox-/Import-Fehler von `main` (identisch auf dem unberührten Stand geprüft) |

## 4. Der Weg zur ersten Mail (Reihenfolge zählt)

1. **Brevo → Senders & IPs:** Existiert `news@franksfinanzcheck.de`?
   Ist sie verifiziert (Code bestätigt, SPF/DKIM grün)? – Checkliste Schritt 2.
2. **Brevo → Listen:** Zeigt die Listen-URL dieselbe Zahl wie das Secret
   `BREVO_LIST_ID`? Stehen dort Abonnenten (Double-Opt-In durchlaufen)?
3. **Actions → Newsletter-Daily → Run workflow:** erst `test_adresse`
   (Probe auf genau eine Adresse), dann `live` an oder der nächste Cron
   (Mo–Fr 05:05 UTC).
4. Scheitert danach noch etwas, steht die Ursache jetzt in der roten
   Annotation und im Step-Summary – mit dem nächsten Schritt, nicht nur
   mit einer Fehlercode-Zeile.
