# 📌 Pinterest-Compliance-Befund (FranksFinanzcheck)

**Stand:** 2026-09-02 · **Sperrdatum:** 15.08.2026
**Konto:** de.pinterest.com/franksfinanzcheck · **Zweck:** Ursachenanalyse,
Selbstauskunft und Nachweis der getroffenen Maßnahmen

> **Hinweis zur Entstehung:** Alle Pins bis zum Sperrdatum wurden **manuell**
> erstellt. Es war zu keinem Zeitpunkt ein Automatisierungs- oder
> Scheduling-Tool im Einsatz. Über die Pinterest-API wurde nie ein Pin
> erzeugt.

---

## 1. Rekonstruktion des Ablaufs

| Zeitpunkt | Ereignis |
|---|---|
| 10.08.2026 | Start des Blogs, erste 2 Artikel veröffentlicht |
| 10.–14.08. | ca. **88 Finanz-Pins** manuell erstellt |
| danach | ca. **87 Pins** für die **M&M'S Halloween Countdown Challenge** |
| **15.08.2026** | **Sperre des Kontos** |

**Gesamt: 175 Pins in 6 Tagen** auf einem neu angelegten Konto.

## 2. Selbstauskunft: Was aus unserer Sicht die Sperre ausgelöst hat

Wir haben unser Vorgehen geprüft und sehen zwei Fehler auf unserer Seite:

**a) Zu hohes Pin-Volumen in zu kurzer Zeit (Hauptursache).**
175 Pins in 6 Tagen entsprechen ~29 Pins/Tag auf einem Konto ohne jede
Historie. Uns ist heute klar, dass ein derart sprunghafter Anstieg von
null auf hohes Volumen wie automatisierte Aktivität wirken muss – auch
wenn jeder einzelne Pin von Hand erstellt wurde.

**b) Zu viele Pins auf zu wenige Zielseiten (Nebenursache).**
Die 88 Finanz-Pins verteilten sich auf lediglich **13 Zielseiten**
(7 Artikel + 6 Themenseiten), also durchschnittlich **6,8 Pins pro Ziel**.
Die Absicht war, verschiedene inhaltliche Blickwinkel desselben Ratgebers
zu zeigen. Uns ist inzwischen bewusst, dass mehrere Pins auf dieselbe URL
unabhängig von der Absicht als Repeat-Pinning gewertet werden.

**Zur zeitlichen Abfolge:** Die 87 Challenge-Pins entstanden **nach** den
Finanz-Pins. Das Konto trug zu diesem Zeitpunkt bereits die erhöhte
Risikolast aus (b). Der Challenge-Block dürfte damit der auslösende
Moment gewesen sein – nach unserem Verständnis nicht wegen seines
Inhalts, sondern wegen der zusätzlichen Volumenspitze.

## 3. Zu den 87 Challenge-Pins

Diese Pins entstanden im Rahmen der **M&M'S Halloween Countdown
Challenge**, zu der Pinterest uns **offiziell eingeladen** hat. Das
verwendete Bildmaterial stammt aus dieser Aktion. Sie sind damit weder
themenfremd im Sinne einer Zweckentfremdung des Kontos noch eine
Markenrechtsverletzung.

Wir bitten ausdrücklich darum, diese Pins bei der Prüfung als das zu
werten, was sie sind: Teilnahme an einem von Pinterest selbst
initiierten Partnerprogramm.

## 4. Was nachweislich NICHT vorlag

| Prüfpunkt | Befund |
|---|---|
| Automatisierung / Bots | **keine** – 0 Pins über API, kein Scheduling-Tool |
| Werbekennzeichnung | **25/25** Pin-Texte mit `*Werbung`-Präfix (UWG-konform) |
| Doppelte Pin-Texte | **0** Near-Duplicates (6-Wort-Shingle, Jaccard ≥ 0,25) |
| Doppelte Pin-Bilder | **0** exakte Duplikate bei 26 Cover-Bildern |
| Irreführende Weiterleitungen | **keine** – kein Pin zeigt auf eine Redirect-/Affiliate-URL |
| Cloaking | **keins** – Pins verlinken ausschließlich eigene Artikelseiten |
| Affiliate-Gateway | `/go/` mit `noindex,nofollow,noarchive`, in `robots.txt` gesperrt |
| Publikations-Kadenz Blog | nur Fri, Mon, Wed, max. 3 Artikel/Tag |

## 5. Bereits umgesetzte Maßnahmen

**Technische Begrenzung (nicht umgehbar).** Wir haben ein Gate
eingebaut, das vor jedem künftigen Pin-Vorgang greift:

- **max. 3 Pins pro Ziel-URL** (vorher bis zu 9 geplant)
- **min. 7 Tage Abstand** zwischen zwei Pins auf dieselbe URL

Unsere Pin-Planung wurde entsprechend bereinigt: von 73 auf **48
Pins**, 25 Pins zurückgestellt. Interne Mengenvorgaben, die nur durch
Mehrfach-Pins erreichbar waren, wurden abgeschafft – zusätzliche Pins
entstehen künftig ausschließlich durch neue Artikel.

**Volumen-Selbstverpflichtung.** Nach einer Reaktivierung werden wir das
Pin-Volumen dauerhaft auf ein moderates Maß begrenzen und schrittweise
aufbauen, statt erneut in kurzer Zeit viele Pins zu erstellen.

## 6. Bitte

Wir bitten um erneute Prüfung des Kontos. Falls eine Reaktivierung nicht
in Betracht kommt, bitten wir um einen konkreten Hinweis, welche Pins
oder welches Verhalten beanstandet wurden – wir möchten den Fehler
verstehen und dauerhaft abstellen.

---

_Die technischen Kennzahlen in Abschnitt 4 sind aus dem Repository
reproduzierbar (`scripts/spam_guard.py`, `scripts/pinterest_plan_guard.py`).
Die Pin-Zahlen in Abschnitt 1–3 beruhen auf Angaben des Kontoinhabers._
