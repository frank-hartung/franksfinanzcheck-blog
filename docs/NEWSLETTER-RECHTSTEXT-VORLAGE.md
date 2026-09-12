# Newsletter: Rechtstext-Vorlage (einsetzen vor dem ersten Versand)

> **Warum diese Datei existiert.** `content/datenschutz/index.md` sagt aktuell
> wörtlich: *„Diese Website bietet derzeit **keinen Newsletter** an."* (Abschnitt 8).
> Das ist heute korrekt – und wird mit dem ersten aktiven Anmeldeformular zu einem
> Widerspruch, also zu dem Fall, wegen dem Formularseiten abgemahnt werden. Der
> Rechtstext ist damit **Voraussetzung**, nicht Fußnote der Einrichtung.
>
> Die Wache meldet das: `python3 scripts/newsletter_digest.py --check` zeigt den
> Widerspruch als Hinweis, solange alles inert ist, und als **harten Fund**, sobald
> `params.newsletterFormAction` oder `params.newsletterFormUrl` gesetzt wird.
>
> **Diese Datei ist ein Entwurf, keine Rechtsberatung.** Einsetzen, durchsehen,
> und – wie immer bei Texten mit Haftungsfragen – für die eigene Konfiguration
> prüfen. Der Platzhalter in eckigen Klammern ist der einzige Pflicht-Wert.

## 1. Block für `content/datenschutz/index.md` (ersetzt Abschnitt 8 vollständig)

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
- **Inhalt.** [1 Mail pro Werktag: die Sparechnungen, Tariffristen und Rechner
  des Tages aus dem Blog.]
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

## 2. Was der Anbieter-Block braucht, wenn Brevo genutzt wird

Für Brevo (CNIL-/DSGVO-Standard, Server in der EU) lautet der Anbieter-Satz:

> Versand und Speicherung erfolgen bei BREVO, 131 rue de La Rochefoucauld,
> 75009 Paris, Frankreich. Auftragsverarbeitungsvertrag: in den
> Brevo-Einstellungen unter *Rechtliches → DPA* als PDF abrufbar und mit
> Abschluss des Kontos wirksam.

Falls du das Konto auf US-Server stellst, brauchst du zusätzlich die
Standardvertragsklauseln – oder du lässt den Serverstandort auf EU.

## 3. Impressum prüfen

Der Newsletter-Versand ist ein geschäftsmäßiges Handeln: die im Impressum
angegebene ladungsfähige Anschrift und die verantwortliche Person müssen zum
Absender passen (`Absender` im Brevo-Konto = dieselbe Person/Anschrift wie im
Impressum, sonst ist die Mail formal angreifbar).

## 4. Reihenfolge beim Freischalten

1. Diesen Text in `content/datenschutz/index.md` einsetzen, Klammern füllen.
2. `docs/ANLEITUNG-NEWSLETTER.md` befolgen (Formular-URL, Secrets).
3. `python3 scripts/newsletter_digest.py --check` – muss ohne Fund enden.
4. Erster Versand über den Testpfad des Workflows (eine Adresse, keine Liste).
