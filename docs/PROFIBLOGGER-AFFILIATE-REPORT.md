# 🏆 PROFIBLOGGER & PROFI-AFFILIATE-MARKETER – Setup-Report

**Stand:** 2026-08-19 · **Branch:** `arena/01a01b1c-franksfinanzcheck-blog`
**Auftrag:** Willkommenstext + gesamten Blog auf Profi-Niveau heben und die Blogautomatik so einrichten, dass sie dieses Niveau **mit Selbstheilung dauerhaft hält**.

---

## 1. Was getan wurde

### 1.1 Willkommenstext → Profi-Conversion-Copy (live)

Der Startseiten-Willkommenstext (`hugo.toml` → `homeInfoParams`) war solide, aber nicht auf Profi-Affiliate-Niveau. Neue Live-Version:

> **Titel:** *Bis zu 2.000 € im Jahr sparen: dein unabhängiger Finanz-Ratgeber*
>
> 💰 Bis zu 2.000 € weniger Fixkosten im Jahr – ohne Verzicht, ohne Verkaufsdruck. FranksFinanzcheck ist ein unabhängiger Ratgeber für **Strom, Gas, Internet, Versicherungen und Konto**, von Frank Hartung aus über 10 Jahren eigener Finanzpraxis. …

**Was ihn zu Profi-Copy macht (und vorher fehlte):**
| Profi-Signal | Umsetzung |
|---|---|
| **Quantifizierter Nutzen** | „bis zu 2.000 € im Jahr", „mehrere hundert Euro" – konkret statt Werbefloskel |
| **E-E-A-T / Autorität** | „Frank Hartung aus über 10 Jahren eigener Finanzpraxis" |
| **Unabhängigkeit als USP** | „unabhängig … ohne Verkaufsdruck" (Vertrauen = Konversion bei Affiliate) |
| **Klarer Handlungsaufruf** | „Starte mit deiner höchsten Rechnung – dein Geld arbeitet für dich" |
| **Alle 5 Kern-Kategorien** | Strom, Gas, Internet, Versicherungen, Konto (SEO-Breite) |
| **Markenstimme gewahrt** | konsequent „du" (kein „Sie"-Bruch) |

### 1.2 Automatik hält das Profi-Niveau (`scripts/willkommenstext_guard.py`)

Damit die wöchentliche Selbstheilung **nicht** wieder auf Generic-Copy zurückfällt, wurden drei Stellen angehoben:

1. **`FALLBACK_POOL` (10 Varianten) auf Profi-Niveau gehoben** – jede Variante
   quantifiziert jetzt (€/Euro/Zahl), nennt Frank Hartungs Erfahrung, alle 5 Kategorien,
   klaren CTA. Das ist der Text, der ausgeliefert wird, wenn keine KI-Keys vorhanden sind
   (die Automatik läuft dadurch **immer**, auch offline).
2. **Neue Profi-Validierung `PRO_KONKRET_RX`** – jeder Kandidat (KI **und** Fallback)
   muss den Nutzen konkretisieren (€ / „Euro" / Zahl), sonst wird er verworfen.
3. **KI-Prompt gestärkt** – verlangt jetzt explizit Quantifizierung + E-E-A-T-Signal.

Erfüllt bleibt die bewährte Selbstheilung: wöchentlicher Rhythmus, SEO-Standard-Trigger,
Einzigartigkeits-Verfall (Jaccard), Brand-/Integrity-Re-Signatur nach jeder Änderung.

### 1.3 🩺 Echter Selbstheilungs-Bug repariert (`scripts/blog_health_gate.py`)

Der **tägliche** Blog-Gesundheitslauf (`blog-health-daily.yml`) war **seit Monaten lautlos kaputt**:

| Fehler | Wirkung | Reparatur |
|---|---|---|
| `REPO = "/home/user/repo"` hartkodiert | In GitHub Actions (Repo liegt unter `$GITHUB_WORKSPACE`) fand `glob` **keine** Dateien → Skript „erfolgreich", heilte **nie** | Pfad-Auflösung via `GITHUB_WORKSPACE` + Skript-relativ |
| pauschales `draft: true → false` | Halb fertige Content-Engine-Entwürfe wären **ungewollt live** gegangen | **Draft-Schutz**: Entwürfe werden komplett übersprungen (Veröffentlichung = `publish.py`) |
| unsaubere H1-Injektion + kaputtes Frontmatter | `---` klebte am letzten Feld (TOML kaputt), doppelte H1 | H1-Injektion entfernt, Frontmatter sauber rekonstruiert |

**Sicherheit geprüft:** neuer Selbsttest (Pfad + Draft-Schutz + Description-Heilung) vor
jedem Schreibzugriff (Exit 2 = nichts wird geschrieben). Drafts werden garantiert nie angefasst.

---

## 2. Was bereits Profi-Niveau hatte (Bestand bestätigt)

Die Automatik ist bemerkenswert ausgereift – das wurde geprüft und bestätigt, nicht angerührt:

- **10/10 Artikel** erfüllen alle Affiliate-Profi-Signale A1–A8 (Offenlegung, E-E-A-T-`erfahrung`, ≥2 interne Links, ≥1 CTA, `author: Frank`, Schema).
- **Affiliate-Integritäts-Wache täglich** (`affiliate-integrity-daily.yml`): heilt kaputte `/go/`-Links selbstständig + Render-Beweis. **Premium-Stufe 02.09.2026:** attribut-toleranter, schlüsselgenauer Beweis (AI4) + Gateway-Beweis (AI5) + `rel="sponsored"`-Prüfung, eingefrorener Detektor-Selbsttest mit Drift-Wächter gegen `render-link.html`, fail-closed (Exit 2 → `publish_gate.py` veröffentlicht nichts), idempotente Issue-Pflege (auto-schließend), `actions: write` für den Deploy-Trigger. Shortcode-CTAs teilen denselben Attribut-Vertrag (`layouts/_partials/affiliate_anchor_attrs.html`). Siehe `AFFILIATE-INTEGRITY-GATE-REPORT.md`.
- **Affiliate-Health wöchentlich** (`affiliate-health.yml`): E2E-Redirect-Kette bis zur Endseite.
- **Blog-Doktor** (`blog_doctor.py`): kanonische Wachen-Kette (Typografie, Stil, Plagiat, Affiliate-Routing …) mit Stop-Strichen bei Sabotage.
- **Trust-/Experience-/Pillar-Boxen** in jedem Artikel (E-E-A-T), 6 Themenwelten auf der Startseite, Pinterest-CTA.
- **Selbsttest-Batterien** in jeder Wache (Sabotage-Schutz, Exit 2).

---

## 3. So hält die Automatik das Niveau dauerhaft

```
täglich:   blog_health_gate.py      → SEO-Pflichtfelder, Draft-Sicherheit (REPARIERT)
täglich:   affiliate_integrity_gate → /go/-Links heilen + Render-Beweis AI4/AI5 (Selftest, fail-closed)
wöchentl.: affiliate_profi_check A1–A8 + affiliate_marketer (CTA-Routing)
wöchentl.: willkommenstext_guard    → Profi-Text mit Konkretisierungs-Pflicht (ANGEHOBEN)
wöchentl.: seo-weekly (ganze Kette) + blog_doctor (Wachen-Orchestrierung)
```

Jede Wache hat ihren eigenen Selbsttest; der Doktor bricht bei Sabotage (Exit 2) sofort ab.
Brand-/Integrity-Locks schützen den Willkommenstext vor ungewollten Änderungen – nur der
autorisierte `willkommenstext_guard` darf ihn ändern (und signiert danach beide Locks neu).

---

## 4. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `hugo.toml` | Profi-Willkommenstext (live) |
| `scripts/willkommenstext_guard.py` | 10 Profi-Fallbacks + `PRO_KONKRET_RX`-Validierung + KI-Prompt |
| `scripts/blog_health_gate.py` | **Selbstheilungs-Bug fixiert** (Pfad + Draft-Schutz + saubere Heilung) |
| `data/brand_lock.yaml`, `data/integrity_lock.json` (+ history) | Locks neu signiert (Profi-Text geschützt, nicht revertiert) |
| `BLOG-GESUNDHEIT-REPORT.md` | neuer transparenter Tages-Report |

_„Profi-Blogger & Profi-Affiliate-Marketer Niveau mit Selbstheilung" – umgesetzt am 19.08.2026._
