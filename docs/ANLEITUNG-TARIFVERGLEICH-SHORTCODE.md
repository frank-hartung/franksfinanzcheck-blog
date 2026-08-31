# Anleitung: `tarifvergleich`-Shortcode (Premium)

**Eingeführt:** 30.08.2026 (Commit auf `premium/gas-tarif-table-optimierung`)

Mit dem `{{< tarifvergleich >}}`-Shortcode erstellst du in Sekunden visuell
hervorgehobene, voll responsive Tarif-/Preisvergleiche im FranksFinanzcheck-
Branding (Smaragdgrün/Gelb/Anthrazit).

## Was er kann

- **Desktop:** 3-4 Spalten parallel, farbcodiert, erste Spalte bleibt beim
  horizontalen Scrollen sichtbar (sticky).
- **Mobil (≤ 640 px):** Automatische Umschaltung auf vertikale Karten-Ansicht –
  jeder Tarif als eigene Karte, kein Scrollen nötig, Hauptzahl groß hervorgehoben.
- **🏆 Beste-Wahl-Ribbon** über der empfohlenen Spalte.
- **Integrierte CTA-Buttons** in jeder Spalte (Affiliate-Links).
- **Highlight-Zeile** für die zentrale Vergleichszahl (z. B. "Effektivkosten").
- **Keine Abhängigkeiten** – CSS ist im Shortcode inline, lädt 1x pro Seite.

## Einfaches Beispiel (3 Tarife)

```markdown
{{< tarifvergleich
    title="💰 Beispielrechnung: Grundversorgung vs. Wechseltarif"
    subtitle="Musterhaushalt mit 20.000 kWh · Stand: August 2026"
    footnote="Der Neukunden-Bonus gilt nur im 1. Jahr."
    cta_url="/go/gas/"
>}}

  {{< tarif name="Grundversorgung (Stadtwerk)" tag="❌ Bisher" tone="bad"
            cta_text="Nicht empfohlen" cta_muted="true" >}}
    {{< zeile label="Grundpreis / Monat" >}}14,50 €{{< /zeile >}}
    {{< zeile label="Arbeitspreis pro kWh" >}}12,80 Ct{{< /zeile >}}
    {{< zeile label="Jahreskosten" highlight="true" tone="bad" >}}
      <strong>2.734 €</strong>
    {{< /zeile >}}
    {{< zeile label="Ersparnis" tone="muted" >}}—{{< /zeile >}}
  {{< /tarif >}}

  {{< tarif name="Wechseltarif (Empfehlung)" tag="🏆 Tipp" tone="good" win="true"
            cta_text="🏆 Jetzt wechseln" cta_url="/go/gas/" >}}
    {{< zeile label="Grundpreis / Monat" >}}11,00 €{{< /zeile >}}
    {{< zeile label="Arbeitspreis pro kWh" >}}9,50 Ct{{< /zeile >}}
    {{< zeile label="Jahreskosten" highlight="true" tone="good" >}}
      <strong>1.852 €</strong>
    {{< /zeile >}}
    {{< zeile label="Ersparnis" tone="good" >}}
      <strong>−882 € im 1. Jahr</strong>
    {{< /zeile >}}
  {{< /tarif >}}

{{< /tarifvergleich >}}
```

## Parameter

### `{{< tarifvergleich >}}`

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `title` | nein | Überschrift über der Tabelle (Default: "💰 Tarifvergleich") |
| `subtitle` | nein | Zeile unter dem Titel (z. B. Verbrauch, Stand-Datum) |
| `footnote` | nein | Hinweiskasten unter der Tabelle (Markdown möglich) |
| `cta_url` | nein | Standard-Link für CTA-Buttons, falls pro Tarif nicht gesetzt |

### `{{< tarif >}}` (je eine Spalte/Karte)

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `name` | ja | Tarif-Name (wird in Überschrift gezeigt) |
| `tag` | nein | Kleines Badge über dem Namen (z. B. "❌ Bisher", "🏆 Tipp") |
| `tone` | nein | `good` (grün), `bad` (rot), `mid` (grau) – Default: `mid` |
| `win` | nein | `"true"` = Gewinnerspalte mit "🏆 Beste Wahl"-Ribbon |
| `cta_text` | nein | Button-Beschriftung. Fehlt er → kein Button |
| `cta_url` | nein | URL, überschreibt `cta_url` des Eltern-Shortcodes |
| `cta_muted` | nein | `"true"` = deaktivierter grauer Button (z. B. "Nicht empfohlen") |

### `{{< zeile >}}` (je eine Zeile)

| Parameter | Pflicht | Beschreibung |
|---|---|---|
| `label` | ja | Beschriftung links (Merkmal) |
| `card_label` | nein | Kürzeres Label für die Mobile-Karte (optional) |
| `tone` | nein | `good` (grün), `bad` (rot), `muted` (grau) für farbige Zahl |
| `highlight` | nein | `"true"` = diese Zeile wird als Hauptvergleichszahl gelb hervorgehoben |

## Tipps für gute Vergleichs-Tabellen

1. **Immer eine `highlight`-Zeile** setzen (die Zahl, die Leser zuerst sehen sollen, z. B. "Effektivkosten 1. Jahr" oder "Gesamtkosten").
2. **Maximal 3 Tarifspalten** – mehr wird auf Mobil unübersichtlich.
3. **Bonus/Ersparnis ab Folgejahren** immer separat ausweisen (Transparenz!).
4. **Einheiten konsistent**: €/Ct, Monats- und Jahreswert immer in derselben Zeile (mit `<br><small>` für den Zweitwert).
5. **CTA immer auf der Gewinnerspalte** ("🏆 Jetzt wechseln"), niemals auf der "Bisher"-Spalte.

## Responsive Verhalten

- ≥ 641 px: Tabelle mit horizontalem Scrollen (erste Spalte bleibt stehen).
- ≤ 640 px: Jeder Tarif wird zu einer Karte – die mit `highlight="true"`
  markierte Zahl erscheint als große grüne Box unter den Detailwerten.

## Funktioniert für alle Themen

- Gas, Strom, DSL, Versicherung, Konto, Kredit, Abonnements …
- Einfache Markdown-Tabellen sind weiterhin möglich (und durch das globale
  CSS `assets/css/extended/z-premium-blog.css` seit 30.08.2026 ebenfalls
  horizontal scrollbar auf Mobil).
