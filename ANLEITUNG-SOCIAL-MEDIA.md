# ANLEITUNG: Social-Media-Automatisierung (Mastodon & LinkedIn)

Postet neue Artikel automatisch auf Social Media – mit Titel, Kurzantwort-Hook,
Link, Cover-Bild (Mastodon) und Hashtags aus deinen Artikel-Tags.

**Workflow:** `.github/workflows/social-ai.yml` – **Montag, Mittwoch, Freitag**
09:15 und 20:45 Uhr MESZ (gleiche Kadenz wie die Content-Engine) sowie manuell
über *Actions → Social-Media-AI → Run workflow*. Di/Do/Sa/So postet der Bot
nicht (Cron + Skript-Wache). `created_at` bestehender Toots kann die API nicht
ändern – die Kadenz gilt für alle **neuen** Veröffentlichungen.

**Mastodon-SEO + Selbstheilung:** `.github/workflows/mastodon-seo.yml` – Mo/Mi/Fr
09:30 und 21:00 MESZ sowie manuell (*Actions → Mastodon-SEO*). Prüft alle
Live-Toots (Cover, Bild-Alt, Profi-Keywords/Hashtags, `language=de`, kanonischer Link,
kein Affiliate-`/go/` im Toot) und heilt per PUT. Duplikate: Option
`delete_dupes` oder Slug `__seo_dedupe__`. Report: `MASTODON-SEO-REPORT.md`.

---

## 🔧 Teil 1: Mastodon einrichten (empfohlen, kostenlos, ~5 Minuten)

Mastodon-Tokens **laufen nicht ab** – einmalig einrichten, fertig.

1. **Account erstellen** auf einer Instanz deiner Wahl, z. B.
   [mastodon.social](https://mastodon.social) oder der Finanz-nahen Community
   deiner Wahl. Profil ausfüllen (Blog-Link, kurzes Profil + Avatar).
2. **App anlegen:** In Mastodon: *Einstellungen → Entwicklung → Neue Anwendung*
   - Name: z. B. `FranksFinanzcheck Bot`
   - Berechtigungen (Scopes): nur `write:statuses` und `write:media` aktivieren
   - Speichern → Anwendung öffnen → **Zugriffstoken** kopieren
3. **GitHub-Secret setzen:** Repo → *Settings → Secrets and variables → Actions*
   → *New repository secret*:
   - Name: `MASTODON_ACCESS_TOKEN`, Wert: dein Zugriffstoken
4. **(Optional) Andere Instanz:** Variable `MASTODON_INSTANCE`
   (z. B. `https://ruhr.social`) setzen – Default ist `https://mastodon.social`.

**Fertig.** Der nächste Lauf postet automatisch. Ohne Token endet der Workflow
sauber (kein Fehler, kein Issue).

## 💼 Teil 2: LinkedIn (optional)

⚠️ **Wichtig:** LinkedIn-Access-Tokens laufen nach **~60 Tagen ab** und müssen
dann manuell erneuert werden (das Fehler-Alerting erstellt dir dann ein Issue).

1. [LinkedIn Developer Portal](https://developer.linkedin.com/) → App erstellen,
   mit deiner LinkedIn-Seite/Profil verknüpfen.
2. Produkt **„Share on LinkedIn"** hinzufügen (kostenlos).
3. Über den [OAuth-Token-Generator](https://www.linkedin.com/developers/tools/oauth/token-generator)
   einen Token mit Scope `w_member_social` erzeugen → Secret `LINKEDIN_ACCESS_TOKEN`.
4. Deine Person-URN ermitteln (`https://api.linkedin.com/v2/userinfo` mit Token
   aufrufen → Feld `sub`) → Variable `LINKEDIN_PERSON_URN = urn:li:person:<sub>`.

## 🧹 Teil 3: Altbestand behandeln (einmalig!)

Du hast bereits **74 Artikel**. Ohne Markierung würde der Bot die ältesten davon
nach und nach nachposten (max. 4 pro Lauf). Zwei Optionen:

| Option | Befehl (lokal im Repo) |
|---|---|
| **Nur NEUE Artikel posten** (empfohlen) | `python3 scripts/social_poster.py --mark-all-posted` → dann committen & pushen |
| Altbestand nach und nach mitposten | Nichts tun. Tipp: Variable `SOCIAL_MAX_PRO_LAUF = 2` setzen, damit es ruhig bleibt |

## 🧪 Teil 4: Testen (lokal)

```bash
python3 scripts/social_poster.py --dry-run   # zeigt Post-Texte, sendet nichts
```

## ⚙️ Einstellungen (Repository-Variablen)

| Variable | Default | Wirkung |
|---|---|---|
| `SOCIAL_MAX_PRO_LAUF` | `4` | Max. Posts pro Lauf (Schutz vor Dauerfeuer) |
| `MASTODON_INSTANCE` | `https://mastodon.social` | Andere Instanz nutzen |

## 🏆 Premium-Profil (Mastodon)

Ein Publikationsaccount wird nicht am Einzelpost gemessen, sondern am Profil:
Wer über einen Toot stolpert, entscheidet dort in wenigen Sekunden, ob er folgt.
`scripts/mastodon_profile_sync.py` hält dieses Profil auf Agentur-Niveau.

**Was gesetzt wird**

| Element | Inhalt | Warum |
|---|---|---|
| Bio (393/500 Z.) | Nutzen zuerst („1.000 €+ sparen“), dann 6 Ratgeber-Welten, Rhythmus Mo/Mi/Fr, KI-Transparenz, Frage-Aufruf | Mehrzeilig statt Textwand – Mastodon rendert Absätze |
| 4 Profilfelder | `Web:` · `Ratgeber:` · `Themen:` · `Pinterest:` | 4 ist das Maximum – jedes Feld muss arbeiten |
| `discoverable` | `true` | Profil erscheint im Instanz-Verzeichnis |
| `indexable` | `true` | Profil ist über die Fediverse-Suche auffindbar |

**Blog ↔ Profil-Verzahnung**

- `Web:` zeigt auf die Startseite, `Ratgeber:` direkt auf `/pillar/`
  (alle 6 Sparthemen auf einen Blick) – kein Umweg über die Navigation.
- Der Blog verlinkt zurück: Mastodon-Icon im Footer (`hugo.toml` →
  `params.socialIcons`) plus `<link rel="me">` aus `params.mastodonUrl`.
- Dieses `rel="me"` ist die Voraussetzung für den **grünen Haken** am
  `Web:`-Feld: Mastodon prüft, ob die verlinkte Seite zurückverweist.

```bash
python3 scripts/mastodon_profile_sync.py --dry-run   # zeigt Bio, Felder, Flags
```

Ausgelöst wird der Sync bewusst **manuell** (Actions → *Mastodon-Profil-Sync* →
*Run workflow*), weil Profiltexte redaktionelle Entscheidungen sind. Das Token
braucht zusätzlich den Scope `write:accounts`, sonst antwortet die API mit 403.

## ❓ FAQ

- **Doppelte Posts?** Nein – das Skript setzt `social_posted: true` ins
  Front-Matter und überspringt markierte Artikel (Deduplikation).
  *Historie:* Genau hier steckte ein Bug – ein bereits vorhandenes
  `social_posted: false` wurde nie auf `true` geflippt, wodurch betroffene
  Artikel bei **jedem** Lauf erneut gepostet wurden. Seit dem Fix in
  `set_social_flag()` wird die Zeile zuverlässig umgeschrieben.
- **Welcher Text wird gepostet?** Titel + dein `kurzantwort:`-Feld (bester Hook!)
  bzw. die Description + Link + bis zu 3 Hashtags aus den Artikel-Tags + `#Finanzen`.
- **Bilder?** Mastodon: Das Cover-Bild wird automatisch hochgeladen.
- **Fehler?** Wenn ein Lauf komplett fehlschlägt, erstellt das bestehende
  Fehler-Alerting ein Issue. Status jederzeit sichtbar in `SOCIAL-STATUS.md`.
- **X/Twitter?** Nicht enthalten – die API ist seit 2023 kostenpflichtig bzw.
  stark limitiert. Mastodon + LinkedIn decken das kostenlos ab.
