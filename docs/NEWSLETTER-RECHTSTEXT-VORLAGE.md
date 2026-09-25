# Newsletter: Rechtstext-Vorlage (einsetzen vor dem ersten Versand)

> **Status 22.09.2026: § 8 ist gesetzt.** `content/datenschutz/index.md` enthält den
> Newsletter-Abschnitt (Double-Opt-In-Nachweis, Speicherdauer, Widerruf,
> Auftragsverarbeiter); der erste Satz kommt aus `{{< newsletter_status >}}` und
> liest damit `data/newsletter_studio.json`. Der Fall, den diese Datei beschrieben
> hat – eine Anmeldeseite neben der Behauptung, es gebe keinen Newsletter – ist
> nicht mehr baubar, weil Website, Wache und Rechtstext dieselbe Quelle lesen.
>
> **Warum die Datei bleibt:** sie ist der Wortlaut-Entwurf (auch für
> E-Mail-Signatur, Impressum und die Präferenzseite) und die Begründung der Fristen.
> Nach dem ersten Versand hier gegenlesen und anpassen, statt im Template zu raten.
>
> **Die Wache meldet jeden Rückfall:** `python3 scripts/newsletter_digest.py --check`
> zeigt einen Widerspruch zwischen Rechtstext und Anmeldeweg als Hinweis, solange
> alles inert ist, und als **harten Fund**, sobald `capture.form_action` im Studio-JSON
> oder `params.newsletterFormAction` in `hugo.toml` gesetzt wird.
>
> **Diese Datei ist ein Entwurf, keine Rechtsberatung.** Einsetzen, durchsehen,
> und – wie immer bei Texten mit Haftungsfragen – für die eigene Konfiguration
> prüfen. Der Platzhalter in eckigen Klammern ist der einzige Pflicht-Wert.

## 1. Block für `content/datenschutz/index.md` (ersetzt Abschnitt 8 vollständig)

> **Längst eingesetzt** – der Block unten ist die Referenz, nicht eine offene Aufgabe. Er bleibt
> abgedruckt, weil er den Wortlaut für E-Mail-Signatur, Impressum und die
> Präferenzseite liefert und weil die Fristen dort begründet sind.

```markdown
## 8. Newsletter / Kontaktaufnahme

**Newsletter.** Du kannst dich über [die Anmeldeseite](/newsletter/) oder das
Formular im Fußbereich für den Newsletter von FranksFinanzcheck anmelden.
Dafür verarbeiten wir deine E-Mail-Adresse sowie die im Formular zusätzlich
angegebenen Angaben.

- **Double-Opt-In.** Nach der Anmeldung senden wir eine Bestätigungs-Mail. Der
  Newsletter wird erst nach deinem Klick auf den Bestätigungslink verschickt.
  Wir speichern Anmeldezeitpunkt, Bestätigungszeitpunkt und deine IP-Adresse,
  um nachweisen zu können, dass die Anmeldung von dir stammt (Art. 6 Abs. 1
  lit. a, Art. 7 Abs. 1 DSGVO).
- **Inhalt.** [Höchstens 2 Newsletter pro Woche (Dienstag und Freitag): Spartipps, Tariffristen und Rechner
  aus dem Blog.]
- **Rechtsgrundlage.** Art. 6 Abs. 1 lit. a DSGVO (Einwilligung).
- **Speicherdauer.** Deine Adresse bleibt auf der Liste, bis du dich abmeldest.
  Nach Abmeldung löschen wir die Adresse innerhalb von [30] Tagen; Nachweise
  zur erteilten Einwilligung bewahren wir gemäß Art. 7 Abs. 1 DSGVO für
  [3] Jahre auf (berechtigtes Interesse zur Abwehr von Ansprüchen).
- **Widerruf.** Jeder Newsletter enthält am Ende einen Link, mit dem du die
  Liste sofort verlässt. Du kannst die Einwilligung außerdem jederzeit mit
  Wirkung für die Zukunft widerrufen, z. B. per Mail an [deine Adresse].
- **Auftragsverarbeiter.** Versand und Speicherung erfolgen bei
  [Name des Anbieters, Anschrift]. Mit dem Anbieter besteht ein
  Auftragsverarbeitungsvertrag (Art. 28 DSGVO).
```

> Beim Ersetzen bleibt der Überschriftentext „Newsletter" erhalten – die Wache
> erkennt den Abschnitt an der Überschrift. Die eckigen Klammern sind Pflichtfelder:
> keine Klammer darf im Live-Text übrig bleiben (`.github`-Wache:
> `newsletter_digest.py --check`, Regel N7).

## 2. Was der Anbieter-Block im Eigenbetrieb braucht

Zwei Auftragsverarbeiter, ein Satz für jeden (beide USA-Unternehmen →
DSGVO-Grundlage beachten):

> Versand erfolgt über **Resend** (Resend, Inc., 548 Market St, San
> Francisco, CA 94104, USA) – Auftragsverarbeitungsvertrag (DPA) unter
> resend.com/legal/dpa, Übermittlung in die USA auf Grundlage der
> Standardvertragsklauseln der EU-Kommission.
> Die Adresse, Themenwahl und Bestätigungsnachweise werden in einem
> dedizierten Speicher von **Cloudflare** (Cloudflare, Inc., 101 Townsend
> St., San Francisco, CA 94107, USA) gehalten – Auftragsverarbeitungsvertrag
> unter cloudflare.com/de/privacy; Cloudflare ist unter dem EU-US Data
> Privacy Framework (DPF) zertifiziert, die Übermittlung ist damit auf den
> Angemessenheitsbeschluss (**Art. 45 DSGVO**) gestützt (wie der CDN-Abschnitt
> dieser Datenschutzerklärung).

Die Wache verlangt den Begriff „Auftragsverarbeitungsvertrag“ im Text –
der Satz darf ihn nicht auslassen, auch wenn die Begründung (DPF vs.
Klauseln) je nach Anbieter anders klingt.

## 3. Impressum prüfen

Der Newsletter-Versand ist ein geschäftsmäßiges Handeln: die im Impressum
angegebene ladungsfähige Anschrift und die verantwortliche Person müssen zum
Absender passen (`email.absender` im Studio-JSON = dieselbe Person/Anschrift
wie im Impressum, sonst ist die Mail formal angreifbar).

## 4. Reihenfolge beim Freischalten

1. Diesen Text in `content/datenschutz/index.md` einsetzen, Klammern füllen.
2. `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` befolgen (Worker, CNAME,
   Resend-Domain, Secrets, `newsletterFormAction`).
3. `python3 scripts/newsletter_digest.py --check` – muss ohne Fund enden.
4. Erster Versand über den Testpfad des Workflows (eine Adresse, keine Liste).
