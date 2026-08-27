# 🚨 PINTEREST-SPAM-SPERRUNG — PREMIUM-AKTIONSPLAN (Agentur-Niveau)

**Profil:** https://de.pinterest.com/franksfinanzcheck/
**Domain:** https://franksfinanzcheck.de
**Stand:** 27.08.2026 (Update abends) · **Status:** 🔴 Domain bei Pinterest
gesperrt (Spam-Markierung, Fehler 404 beim Crawlen) · 🟢 **API-Trial-Zugang
für die App „FranksFinanzcheck Blog“ heute GENEHMIGT**
**Zuständigkeits-Hinweis:** Dieses Dokument beantwortet die Frage *„Soll ich die
fehlenden Pins jetzt manuell hinterlegen?“* mit **KLAR: NEIN — solange die
Sperre besteht.** Begründung und Schritte unten.

---

## ⭐ UPDATE 27.08.: API-Zugang genehmigt — aber das ist (noch) keine Entsperrung

Die heutige Pinterest-Mail bedeutet: Deine **Entwickler-App** ist freigegeben
(Trial access) → Du darfst jetzt Tokens erzeugen und die API nutzen.
**Das ist getrennt von der Domain-Sperre zu sehen:**

| Was freigegeben ist | Was (noch) gesperrt ist |
|---|---|
| App darf API-Aufrufe machen (Boards/Pins im **eigenen** Konto lesen & schreiben) | Die **Domain** `franksfinanzcheck.de` bleibt als Spam/404 markiert |

➡️ **Erlaubt & sinnvoll JETZT:** Token einrichten, **Lese-Zugriffe** (Profil-Audit,
Boards auslesen) laufen lassen, Profil/Boards über die API prüfen.
➡️ **Verboten JETZT:** Pins posten, die auf die gesperrte Domain verlinken.
Die Domain-Notbremse blockt das weiterhin (hebe sie NICHT vor der nachgewiesenen
Entsperrung auf). Trial-Hinweis: Pins sind auf dein eigenes Konto beschränkt;
Massen-Posting an einen gesperrten Link gefährdet den frischen App-Zugang zusätzlich.

### 🔑 Wahrscheinlichste Sperr-Ursache gefunden: HTTPS auf der Domain AUS

Der GitHub-Pages-Status der Live-Domain zeigt **`https_enforced: false`** –
die Site wird auf `http://franksfinanzcheck.de` ausgeliefert, **HTTPS ist nicht
aktiv** (Test schlägt mit SSL-Fehler fehl). Wenn Pinterests Crawler die Seite
nicht sicher öffnen kann, wertet er jeden Link als **tot (404)** → genau das
ist „Link-Spam“ für Pinterest. **Das zuerst reparieren:**

**Fix (1 Klick, von dir – dieses API-Token darf Pages-Einstellungen nicht
ändern, 403):** GitHub → Repo **Settings → Pages** → Bereich *Custom domain*:
1. Bei **„Enforce HTTPS“** das Häkchen **setzen** (aktuell aus). Falls es sich
   nicht setzen lässt: kurz warten (GitHub stellt das Zertifikat automatisch
   aus, sobald die DNS-A-/CNAME-Einträge auf GitHub Pages zeigen), dann erneut.
2. Domain `franksfinanzcheck.de` bleibt eingetragen (CNAME gepflegt, Pages-
   Status `built`); nach Aktivieren 10–30 Min. warten.
3. Testen: `https://franksfinanzcheck.de/` lädt ohne Warnung, ebenso
   `https://franksfinanzcheck.de/pinterest-e238f.html` (Claim-Datei).
4. **Rich-Pin-Debugger** https://developers.pinterest.com/tools/url-debugger/
   mit einer Artikel-URL: liefert er jetzt statt 404 die OG-Daten, ist das der
   stärkste Beweis für den Appeal.

### 🛠️ Technisch zusätzlich abgesichert (heute eingebaut)

- **Canary-Limit:** Nach der Entsperrung postet jeder Lauf **maximal 3 Pins**
  (`PINTEREST_MAX_PINS_PER_RUN`, Default 3; Rest bleibt sicher in der Queue) –
  kein Massen-Posting mehr, das die Sperre mit ausgelöst hat.
- **`generate_pins.py`** nutzt jetzt die kuratierten Premium-Pin-Texte
  (`pin_title`/`pin_description`) und respektiert Notbremse + Canary + Draft-Schutz.
- **API-Anleitung korrigiert:** Der Scope für den Profil-Audit heißt
  `user_accounts:read` (nicht `profile:read`, das es in der v5-API nicht gibt).

---

## 1. Kernfrage: Jetzt manuell pinnen? → NEIN.

### Warum jeder Pin-Versuch jetzt schädlich ist

Pinterest hat nicht den einzelnen Pin, sondern die **Domain `franksfinanzcheck.de`**
als Spam klassifiziert („blocked website / link spam“). In dieser Phase gilt:

1. **Jeder neue Pin, der auf die Domain verlinkt, ist ein weiterer Verstoß.**
   Der Spam-Filter sieht: *gesperrte Domain + neuer Link-Versuch = Umgehungs-
   versuch.* Das eskaliert die Abstrafung — typische Stufen:
   Link-Entfernung → Pin-Löschung/W Shadowban (Pins unsichtbar, Profil lebt)
   → Board-Einschränkung → **Account-Sperrung** (im Wiederholungsfall ohne Vorwarnung).
2. **Pins ohne Link** (Bild hochladen, URL weglassen) sind nutzlos: Sie bringen
   **null Traffic, null Affiliate-Umsatz**, verwässern das Profil und zählen
   trotzdem als Aktivität auf einem abgestraften Konto. Kein Vorteil, nur Risiko.
3. **Auch die Automatik ist jetzt hart blockiert.** Mit Stand 27.08. ist eine
   **Domain-Notbremse** im Code aktiv: API-Posting, Queue und das Legacy-
   Nachpinnen brechen ab, solange die Sperre besteht
   (`data/pinterest_domain_block.json`).
4. **RSS-Auto-Publish sofort trennen!** Falls in Pinterest *Create → Auto-publish
   → RSS feed* (`https://franksfinanzcheck.de/index.xml`) verbunden ist:
   **JETZT trennen.** Ein laufender Auto-Feed würde täglich neue Pins auf die
   gesperrte Domain setzen — der schnellste Weg zur Account-Sperre.

> ✅ **Richtig in der Sperrphase:** Profil-Setup optimieren (das geht ohne
> Links!), Domain technisch sauber halten, Entsperrung beantragen, Pins
> fertig vorbereiten. Gepinnt wird **erst nach Aufhebung der Sperre — getaktet.**

---

## 2. Warum wurde die Domain gesperrt? (Die häufigsten Ursachen — sortiert nach Wahrscheinlichkeit)

Pinterest sperrt neue Domains mit Affiliate-Fokus sehr schnell, wenn mehrere
Signale zusammenkommen. Auf franksfinanzcheck.de treffen strukturell zu:

| # | Risiko-Signal | Status im Projekt | Gewichtung |
|---|---|---|---|
| 1 | **Neue Domain + viele Affiliate-Links** (jeder Artikel → /go/ → CHECK24) | 25/25 Artikel Affiliate | 🔴 hoch |
| 2 | **Sehr schnelles Pin-Wachstum** aus dem Nichts (18+ Pins in wenigen Tagen, oft per Bulk/API) | geplant: 18 Pins queued | 🔴 hoch |
| 3 | **Wiederholte Pins auf dieselbe Domain** ohne etabliertes Konto (Repeat-Domain-Spam) | UTM-Varianten gleicher URL | 🟡 mittel |
| 4 | **Generische/monetäre Domänen-Wahrnehmung** (Tarifvergleich, „sparen“, Werbung-Prefix) | Thema per se Affiliate | 🟡 mittel |
| 5 | Fehlende Domain-Verifizierung / kein Business-Konto bei ersten Pins | Claim-Datei liegt bereit, Status Dashboard prüfen | 🟡 mittel |
| 6 | Keyword-Dichte-Signale im Blog (Spam-Guard zeigt Warnungen: „dns“ 6,4 %, „kwh“ 3,8 %, „mbit“ 3,5 %) | B1-Warnungen bekannt | 🟢 gering für Pinterest, aber SEO-Relevant |
| 7 | Garantie-/Superlativ-Formulierungen („beste…“, „garantiert“) | B2-Warnungen bekannt | 🟢 gering |

**Erkenntnis:** Es ist fast nie *ein* Pin — es ist das Muster *„neues Affiliate-
Konto pinnst massiv auf eine neue Domain“*. Die Reparatur muss deshalb auf
**Domain-Ebene + Konto-Ebene + Verhaltens-Ebene** ansetzen, nicht an einzelnen Pins.

---

## 3. Aktionsplan — Phase für Phase

### PHASE 0 — Sofort (heute, 15 Min.) — kein Pin, kein Link

- [ ] **RSS-Auto-Publish trennen**, falls aktiv (Pinterest → Settings →
      *Create Pins in bulk* → *Auto-publish* → Feed entfernen).
- [ ] **Keine neuen Pins manuell anlegen** (auch nicht ohne Link) — auch
      nicht über die jetzt freigeschaltete API.
- [ ] **API-Token einrichten ist erlaubt** (Lese-Zugriff!): Die App ist
      freigegeben → nach `ANLEITUNG-PINTEREST-API.md` OAuth durchführen
      (`--auth-url` → `--exchange`). Mit Token den **Live-Profil-Audit**
      laufen lassen (`scripts/pinterest_profile_audit.py`), um Name/Bio/
      Boards/Verifikation direkt auszulesen. **Posting blockt die Notbremse
      automatisch** (Status: `python3 scripts/spam_guard.py --domain-status`).
- [ ] **Offene Pins im Profil NICHT löschen.** Massenlöschung ist selbst ein
      Spam-Signal. Stehen lassen, ggf. später über den Support klären.

### PHASE 1 — Profil auf Premium bringen (ohne Links, komplett ungefährlich)

Diese Schritte berühren die gesperrte Domain nicht und machen das Konto
für den Review „menschlich & seriös“:

- [ ] **Business-Konto** aktivieren (falls privat) — Pflicht für Verifikation
      und Appeal.
- [ ] **Anzeigename:** `FranksFinanzcheck | Geld sparen & Tarife clever wechseln`
- [ ] **Bio** einfügen (fertiger Copy-Paste-Block in `PINTEREST-PROFILE-REPORT.md`).
- [ ] **Profilbild hochladen:** `static/images/social/pinterest-profilbild-marke-1000.png`
- [ ] **6 Boards anlegen** exakt nach `data/pinterest_boards.yaml` (Namen =
      SEO-Suchbegriffe) mit den fertigen Beschreibungen aus
      `PINTEREST-PROFILE-REPORT.md` — **Boards bleiben leer bzw. bekommen
      erst NACH der Entsperrung Pins.**
- [ ] **6 Board-Cover hochladen** (rein visuelle Boards, keine Links nötig):
      `static/images/boards/cover-*.png` (Zuordnung im Profile-Report).
- [ ] **Echtes Nutzer-Signal:** 10–15 Pins **fremder, etablierter Accounts**
      (Stiftung Warentest, Verbraucherzentrale, Banken-Blogs) auf die Boards
      repinnen. Das zeigt dem System: *echter Kurator, kein reiner
      Selbstvermarkter.* (Keine eigenen Links!)

### PHASE 2 — Domain technisch vorbereiten (während der Prüfung)

- [ ] **🔴 ZUERST: HTTPS aktivieren** (vermutliche Sperr-Ursache, siehe oben):
      GitHub **Settings → Pages → „Enforce HTTPS“** Häkchen setzen, bis
      `https://franksfinanzcheck.de/` sauber lädt. Ohne HTTPS bleibt jeder
      Link für Pinterests Crawler ein 404 — der Appeal hat dann kaum Chance.
- [ ] **Domain-Claim prüfen/erneuern:** Claim-Datei `static/pinterest-e238f.html`
      liegt aus, `<p:domain_verify>` im Head. Nach Deploy im Dashboard
      *Settings → Claimed accounts* bestätigen, dass `franksfinanzcheck.de`
      verifiziert ist. Eine verifizierte Domain wird deutlich seltener als Spam
      eingestuft. (Mit API-Token lässt sich der Claim-Status jetzt auch live
      prüfen.)
- [ ] **Rich Pins validieren** (erst, wenn die Domain wieder erreichbar ist):
      https://developers.pinterest.com/tools/url-debugger/ mit einer
      Artikel-URL. OpenGraph/Structured-Daten sind im Hugo-Theme bereits
      gepflegt (meta_report Ø 99/100).
- [ ] **Meta-Daten prüfen:** Jeder Artikel hat saubere OG-Tags
      (`og:title`, `og:description`, `og:image` = 2:3-Cover 1000×1500) —
      über den lokalen Build verifizierbar, kein Pinterest-Kontakt nötig.
- [ ] **Blog-Spam-Signale abbauen** (SEO-Nebenkriegsschauplatz, zeigt dem
      Reviewer aber Sorgfalt): die B1/B2-Warnungen aus `SPAM-REPORT.md`
      (Keyword-Dichte „dns/kwh/mbit“, Superlative „beste…“) in Ruhe entschärfen.

### PHASE 3 — Offizieller Appeal (die Entsperrung beantragen)

- [ ] **Kontakt** (deutsch oder englisch, sachlich, kurz):
      Pinterest-Hilfe → *Account settings* → *Appeal blocked account /
      website* bzw. https://help.pinterest.com/contact → Kategorie
      *„My website was marked as spam“*.
- [ ] **Textbaustein** (ehrlich, werblich knapp):

      > Sehr geehrtes Pinterest-Team,
      >
      > meine Website https://franksfinanzcheck.de wurde als Spam markiert.
      > Es handelt sich um einen redaktionellen Ratgeber-Blog zu Strom-, Gas-,
      > DSL- und Versicherungstarifen mit eigener Recherche und konkreten
      > Sparbeträgen. Alle Artikel enthalten Affiliate-Links (CHECK24), die
      > transparent und werblich gekennzeichnet sind (*Werbung) — es gibt keine
      > getarnten Links, keine Link-Kürzer, keine irreführenden Versprechen.
      >
      > Möglicherweise entstand die Markierung durch eine zu schnelle Folge
      > von Pins beim Start des Kontos. Ich habe die automatischen Pins
      > gestoppt, das Konto auf ein Business-Profil mit verifizierter Domain
      > umgestellt und werde Inhalte künftig redaktionell getaktet pinnen.
      >
      > Bitte prüfen Sie die Domain erneut. Vielen Dank.
      >
      > Mit freundlichen Grüßen — Frank [Nachname], franksfinanzcheck.de

- [ ] **Bearbeitungszeit:** erfahrungsgemäß 3–14 Tage. **Nicht nachfassen**
      innerhalb von 5 Tagen (ungeduldige Doppel-Anfragen wirken spammy).
- [ ] Parallel: falls E-Mail-Benachrichtigung von Pinterest kam, **direkt auf
      diese antworten**.

### PHASE 4 — Nach der Entsperrung: getaktet, nicht auf einmal

Erst wenn Pinterest die Freigabe bestätigt hat:

- [ ] **Verifizieren, dass die Domain wirklich wieder „durch“ ist:** Erst
      einen einzelnen Test-Pin OHNE Link setzen (nur Bild) oder den Rich-Pin-
      Debugger erfolgreich durchlaufen lassen. Kein 403/404/Block-Hinweis mehr.
- [ ] Notbremse aufheben:
      `python3 scripts/spam_guard.py --domain-unblock`
- [ ] **Canary-Start: maximal 3 Pins im ERSTEN Lauf** (ist jetzt der Default:
      `PINTEREST_MAX_PINS_PER_RUN=3`), dann 2–3 pro Tag, nach 2–3 Wochen
      sauberen Betriebs auf 4–5 steigern — **niemals** die 18 Pins an einem Tag.
- [ ] **Fertige Artefakte nutzen** (alles vorbereitet):
  - **Bulk-Upload-CSV:** `data/pins_upload.csv` — 18 Pins, fertig getaktet
    (3/Tag an Publikationstagen), mit `*Werbung`-Kennzeichnung, Board-Routing
    und 2:3-Cover-Media-URLs. Vor dem Upload **kurz neu generieren**, damit
    die Scheduling-Daten frisch sind:
    `python3 scripts/spam_guard.py --gen-csv --max 50`
    Upload: Pinterest → *Create → Pins in bulk (CSV)* → Datei hochladen.
    (Das Scheduling-Feld in der CSV taktet von selbst – auch dort gilt:
    nicht alle Termine auf denselben Tag legen.)
  - **Oder API:** `PINTEREST_ACCESS_TOKEN` (jetzt freigeschaltet) setzen, dann
    postet `pinterest-ai.yml` über die Engine — **Canary-Limit 3/Lauf +
    A1-Limit 10/Std., 40/Tag** sind eingebaut; die 6 Boards werden automatisch
    angelegt/routet.
  - **Manuell einzeln:** `data/pin_queue.yaml` (10 Pins) + `PIN-STATUS.md`.
- [ ] **Mischung pflegen:** Eigene Pins weiter mit Re-Pins fremder Inhalte
      mischen (ca. 50/50 in den ersten 4 Wochen).
- [ ] **2 Wochen nach Start:** Pinterest-Analytics beobachten — Impressionen
      > 0 je Pin = Domain „verteilt“ wieder. Bleiben Impressionen bei 0:
      Shadowban möglich → ein zweiter, höflicher Appeal.

---

## 4. Was das Repo jetzt automatisch schützt (eingebaut am 27.08.2026)

| Schutz | Wirkung |
|---|---|
| **Domain-Notbremse** `data/pinterest_domain_block.json` | Solange die Datei existiert, blockt `spam_guard.api_preflight()` **jeden** API-Posting-Lauf (A0) — die Engine und `generate_pins.py` setzen keinen Pin. Env-Override `PINTEREST_DOMAIN_BLOCKED=1/0` für Tests. |
| `--domain-block / --domain-unblock / --domain-status` | Kommandos zum bewussten Setzen/Aufheben (Aufhebung nur manuell nach Bestätigung). |
| **Werbe-Kennzeichnungs-Garantie im Sync** | `pinterest_pin_text_sync.py` ergänzt jetzt zwingend `*Werbung |`, wenn der Ziel-Artikel Affiliate-Links enthält (alle Artikel) — auch wenn der kuratierte Plan-Pin ein redaktioneller EP-Pin ist. Verhindert, dass der nächste Sync-Lauf die UWG-Pflichtkennzeichnung entfernt. |
| **Draft-Schutz in `generate_pins.py`** | Draft-Artikel (nicht live) werden nicht mehr gepinnt — tote Links sind ein Spam-Signal. |
| **Profile-Audit vollständig** | Copy-Paste-Report enthält jetzt alle **6 Boards** mit Beschreibung + Cover-Zuordnung (vorher nur 1 Board durch Einrückungsfehler). |
| **Fertige Bulk-CSV** | `data/pins_upload.csv` (18 Pins, getaktet, gekennzeichnet) als sicherer Upload-Start nach Entsperrung. |
| **Canary-Posting-Limit** | Nach Entsperrung postet jeder Lauf max. 3 Pins (`api_run_capacity()` / `PINTEREST_MAX_PINS_PER_RUN`); Rest bleibt in der Queue. Verhindert das Massen-Posting-Muster, das die Sperre mit auslöste. |
| **Premium-Texte im Legacy-Lauf** | `generate_pins.py` nutzt `pin_title`/`pin_description` aus dem Frontmatter (statt generischer Meta-Texte), kein doppelter `*Werbung`-Prefix. |
| **Scope korrigiert** | Profil-Audit braucht `user_accounts:read` (v5-API; `profile:read` existiert nicht) — in `ANLEITUNG-PINTEREST-API.md` berichtigt. |

---

## 5. Antwort auf die Frage in einem Satz

> **Nein — keine Pins manuell hinterlegen, solange die Domain gesperrt ist.**
> Jeder Pin auf `franksfinanzcheck.de` ist jetzt ein zusätzlicher Spam-Verstoß
> und gefährdet das gesamte Konto. Profil/Boards/Cover optimieren (ohne Links),
> Entsperrung per Appeal beantragen, RSS trennen — und die fertig vorbereiteten
> 18 Pins (`data/pins_upload.csv`) **danach** getaktet mit 2–3 Pins/Tag hochladen.

---

## 6. Anhang: Konkrete Fremdaccounts zum Repinnen (verifiziert aktiv, Stand 27.08.2026)

**Warum das sicher ist:** Ein repinnter Pin behält den **Original-Link**
(urlaubsguru.de usw.), nicht `franksfinanzcheck.de`. Es entsteht also **kein
einziger Link auf die gesperrte Domain** – null Risiko, aber ein echtes
„Kurator“-Signal für dein Konto.

### 6.1 Accounts, die auf Pinterest wirklich aktiv sind

| Account (Pinterest-Handle) | Follower | Themen | Auf dein Board |
|---|---|---|---|
| **Urlaubsguru** – `pinterest.com/urlaubsguru` | ~29,7 Tsd. | Reisen, Urlaub Deutschland/Europa, Geheimtipps | 🗺️ Günstig reisen |
| **Reiseuhu** – `pinterest.com/reiseuhu` | ~8 Tsd. | Urlaubsdeals, Roadtrips, Reiseplanung | 🗺️ Günstig reisen |
| **Urlaubstracker** – `pinterest.com/urlaubstracker` | groß | Reiseschnäppchen, Last-Minute, Flüge/Hotels | 🗺️ Günstig reisen |
| **Clever Finance Girls** (Katja Groesser) – `pinterest.com/cleverfinancegirls` | ~3,9 Tsd. | Budget, Sparpläne, Geld organisieren, Finanzen für Frauen | 💰 Budget & Haushaltskasse · Geld sparen |
| **freaky finance** – `pinterest.com/freakyfinance` | ~1,4 Tsd. | Sparen, ETF/Vermögensaufbau, Finanz-Blogger-Content (kuratiert große Pinnwände) | 💰 Geld sparen (Thema „Sparen“ passt; Fokus liegt eher auf Investieren) |

> ⚠️ **Ehrliche Lage zu 3 deiner 6 Boards:** Für **Strom & Gas**, **Internet & DSL**
> und **Versicherungen** gibt es auf Pinterest praktisch **keine etablierten
> deutschen Marken-Accounts** (Energie-/Versicherungsthemen sind nicht
> „pinterestig“; Stiftung Warentest/Verbraucherzentrale/Finanztip sind dort
> nicht aktiv gepflegt). Diese Boards füllst du am besten über **gezielte
> Suchbegriffe** (siehe 6.3) mit guten Infografiken/Checklisten oder mit
> allgemeinen „Haushalt sparen“-Pins der Finance-Curatoren oben.

### 6.2 So funktioniert das Repinnen (Schritt für Schritt)

1. Auf Pinterest einloggen → **Suchleiste** nutzen oder einen Account-Link
   oben öffnen.
2. Passenden Pin öffnen (Bild + Text kurz prüfen: seriös, hilfreich, zum
   Board-Thema passend).
3. Roten Button **„Speichern“** klicken → im Dialog **dein eigenes Board**
   wählen (das passende der 6) → bestätigen.
4. Fertig: Der Pin erscheint auf deinem Board, Link bleibt beim Urheber.

**Regeln während der Sperre:**
- ✅ Nur **repinnen** (fremde Inhalte) – **keine** eigenen Pins, **keine**
  Links auf franksfinanzcheck.de.
- ✅ Lieber wenige **hochwertige** Pins (viele Saves, seriöse Domain, klare
  Grafik) als Massenware – Boards voller Spam-Pins schaden dir selbst.
- ✅ **Tempo menschlich halten:** 2–4 Pins pro Tag, verteilt über ein paar
  Tage – nicht 15 in 10 Minuten am Stück.
- ✅ Auf alle 6 Boards verteilen, damit kein Board leer wirkt.
- ❌ Keine Pins von zwielichtigen Shopping-/Schnäppchen-Seiten, keine
  „Schnell reich“-Inhalte, keine reinen Werbe-Pins.

### 6.3 Suchbegriffe pro Board (zum Selber-Finden guter Pins)

- **Geld sparen / Frugalismus:** `geld sparen im alltag`, `sparchallenge`,
  `spartipps haushalt`, `no spend`, `haushaltstipps geld`, `52 wochen sparen`
- **Budget & Haushaltskasse:** `haushaltsbuch vorlage`, `budget planen`,
  `50 30 20 regel`, `budgetierung`, `finanzen organisieren`
- **Strom & Gas sparen:** `strom sparen tipps`, `energie sparen haushalt`,
  `heizkosten sparen`, `stromfresser`, `energiesparen`
- **Internet & DSL:** `wlan verbessern`, `wlan tipps`, `handyvertrag
  vergleichen` (nur wenige gute Pins – hier reichen 1–2)
- **Günstig reisen:** `günstig reisen`, `urlaubstipps`, `reisebudget`,
  `mietwagen tipps`, `urlaub in deutschland`, `roadtrip deutschland`
- **Versicherungen:** `versicherungen checkliste`, `privathaftpflicht`,
  `hausrat versicherung` (sehr dünn – 1–2 passende Spar-/Checklisten-Pins
  genügen; Rest über allgemeine Finanzen-Inhalte auffüllen)

**Menge:** Ziel sind ~10–15 fremde Pins insgesamt, gleichmäßig verteilt
(Reise & Budget können mehr abbekommen, Strom/DSL/Versicherung je 1–3).
Nach der Entsperrung mischst du deine eigenen Pins dazu (50/50 in den ersten
Wochen).

---

_Erstellt als Premium-Agentur-Dokument, 27.08.2026. Quellen: Pinterest Community
Guidelines (Spam & Affiliate-Policy), UWG-Werbekennzeichnung, Repo-Soll-Zustand
(`data/pinterest_boards.yaml`, `data/pinterest_profile_target.yaml`)._
