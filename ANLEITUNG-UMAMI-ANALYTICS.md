# 📊 Anleitung: Umami-Analytics einrichten (ca. 10 Minuten)

**Zweck:** Cookieless, DSGVO-freundliches Analytics für `franksfinanzcheck.de` – ohne
Consent-Zwang, ohne Cookie-Banner-Pflicht, ohne Google.

Die Integration ist im Blog **fertig eingebaut** (`layouts/_partials/extend_head.html`).
Es fehlt nur die Website-ID in `hugo.toml` → `[params.umami] websiteId`.

---

## 1. Umami-Cloud-Account anlegen (5 Minuten)

1. **https://cloud.umami.is** öffnen → **„Get started for free" / „Sign up"**
2. Registrieren mit **E-Mail + Passwort** (oder, falls angeboten, direkt per GitHub/Google –
   spart die Passwort-Verwaltung). Nutzername/Verein: privat, z. B. `frankhartung`.
3. **Bestätigungs-E-Mail** öffnen und Link klicken (auch Spam-Ordner prüfen).
4. Einloggen unter https://cloud.umami.is/login.

> **Kosten:** Free-Tier ist kostenlos (~100.000 Events/Monat, begrenzte Anzahl Websites –
> für FranksFinanzcheck reichlich). Keine Kreditkarte nötig.
> Alternative später: self-hosting auf eigenem VPS (dann `src`/`hostUrl` in `hugo.toml` ändern).

## 2. Website anlegen & ID kopieren (3 Minuten)

1. Im Dashboard: **Settings → Websites → „+ Add website"** (oder der „Add website"-Button
   beim ersten Login)
2. Felder ausfüllen:
   - **Name:** `FranksFinanzcheck`
   - **Domain:** `franksfinanzcheck.de`
   - **Share URL / Enable URL:** aus (kann später für öffentliche Statistik an)
3. **Save** → dann auf die Website klicken → **„Edit" → „Tracking code"**
4. Im Snippet die ID aus `data-website-id="…"` kopieren, z. B.:
   ```html
   <script async defer src="https://cloud.umami.is/script.js" data-website-id="1a2b3c4d-5678-90ef-ghij-klmnopqrstuv"></script>
   ```
   → **Die UUID hinter `data-website-id` ist die gesuchte Website-ID.**

## 3. ID im Blog eintragen (2 Minuten)

In `hugo.toml`:

```toml
[params.umami]
  websiteId = "1a2b3c4d-…"   # ← deine ID
  src = "https://cloud.umami.is/script.js"
  hostUrl = ""                          # Cloud: leer lassen
  consentRequired = false               # Empfehlung, siehe unten
```

Committen/pushen → der nächste Deploy (Mo/Mi/Fr oder manuell) aktiviert das Tracking.

### Entscheidung `consentRequired`

| Wert | Verhalten | Empfehlung |
|---|---|---|
| `false` ✅ | Script lädt cookieless ohne Einwilligung (DNT/„Do Not Track" wird respektiert, `data-do-not-track` ist gesetzt). Umami setzt **keine Cookies**, speichert keine personenbezogenen Daten → in DE üblich ohne Consent zulässig. **Erstbesucher (Pinterest-Traffic!) werden gemessen.** | **Empfohlen für Wachstum** |
| `true` | Script lädt erst nach Klick auf „Alle akzeptieren". Strengste Auslegung – aber: **Erstbesucher werden NICHT gemessen**, genau der Traffic, den Pinterest bringen soll. | Nur wenn du maximal streng sein willst |

## 4. Funktion prüfen (nach dem Deploy)

1. Live-Blog öffnen → Seitenquelltext anzeigen → `cloud.umami.is/script.js` mit deiner
   `data-website-id` muss enthalten sein.
2. In Umami: **Dashboard → Realtime** → Blog-Seite im Browser aktualisieren → Besuch
   erscheint (Achtung: AdBlocker/Privacy-Extensions blocken Umami ggf. – im Zweifel
   incognito ohne Extensions testen).
3. **Adblocker-Hinweis:** ein kleiner Teil der Besucher (Werbe-/Tracking-Blocker) wird
   generell nicht erfasst – das ist bei Privacy-Analytics normal und okay.

## 5. Pinterest-Traffic ablesen (KW 37+)

- Umami zeigt unter **Traffic → Referrers/UTM** die Quellen – deine Pins tragen
  `?utm_source=pinterest&utm_medium=social&utm_campaign=pins`
- So siehst du pro Pin-Kampagne: Klicks, Zielseiten, Verweildauer → Winner-Pins bekommen
  nächste Woche mehr Budget (manuelle Wiederholungspins).

---

## FAQ

**Verschlüsselt die ID irgendwas?** Nein – die Website-ID ist öffentlich (steht später im
Seitenquelltext). Kein Secret, darf im Repo/Chat stehen.

**Umami vs. Google Analytics?** GA4 braucht in DE i. d. R. Consent (Cookies), speichert
personenbezogene Daten, ist komplex. Umami: 2 KB Script, keine Cookies, klare UI.

**Was ist mit der Datenschutzerklärung?** ✅ Bereits enthalten – `content/datenschutz/index.md` hat den Abschnitt „Statistik und Reichweitenmessung (Umami – cookieless)" mit DNT-Hinweis und Rechtsgrundlage. Am 31.08.2026 ergänzt: aktiver Modus = cookieless ohne Einwilligung (Art. 6 Abs. 1 lit. f DSGVO).

---

*Erstellt 31.08.2026 · ergänzt die Referenz aus `hugo.toml` („siehe ANLEITUNG-UMAMI-ANALYTICS.md").*
