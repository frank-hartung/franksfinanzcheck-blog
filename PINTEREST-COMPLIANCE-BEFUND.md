# 📌 Pinterest-Compliance-Befund (FranksFinanzcheck)

**Stand:** 2026-09-02 · **Sperrdatum:** 15.08.2026
**Konto:** de.pinterest.com/franksfinanzcheck · **Domain:** franksfinanzcheck.de
**Zweck:** Ursachenanalyse, Selbstauskunft und Nachweis der Behebung

> **Entstehung der Pins:** Alle Pins bis zum Sperrdatum wurden **manuell**
> erstellt. Es war zu keinem Zeitpunkt ein Automatisierungs-, Bot- oder
> Scheduling-Tool im Einsatz. Über die Pinterest-API wurde nie ein Pin
> erzeugt.

---

## 1. Hauptursache: Pins verlinkten auf das eigene Pinterest-Profil

**Das war unser zentraler Fehler.** Die Finanz-Pins trugen als Ziel-Link
überwiegend nicht den zugehörigen Blogartikel, sondern unser **eigenes
Pinterest-Profil** (`de.pinterest.com/franksfinanzcheck`).

Uns ist inzwischen klar, welche Folgen das hatte:

1. **Irreführende Verlinkung.** Ein Pin mit dem Titel „50-30-20-Regel
   einfach erklärt" verspricht eine Erklärung. Wer klickte, landete auf
   einem Profil statt auf dem Ratgeber. Das ist irreführend, auch wenn es
   nicht so gemeint war.
2. **Selbstreferenzielle Schleife.** Nutzer wurden von Pinterest zurück
   nach Pinterest geleitet. Es entstand kein Mehrwert, und das
   Klickverhalten (sofortiges Zurückspringen) musste als negatives
   Qualitätssignal wirken.
3. **Extremes Repeat-Muster.** Da nahezu alle Finanz-Pins dasselbe Ziel
   trugen, zeigten sie faktisch **auf eine einzige URL**. Das entspricht
   dem Bild von Link-Spam, selbst bei einzigartigen Pin-Texten und Bildern.

Der Fehler beruhte auf einem Missverständnis darüber, was in das Feld für
den Ziel-Link gehört. Unsere eigene Pin-Planung
(`data/pinterest_plan.yaml`) sah durchgehend Blogartikel als Ziel vor –
kein einziger geplanter Pin verwies auf Pinterest. Die manuelle Umsetzung
ist davon abgewichen.

## 2. Verstärkende Faktoren

**a) Zu hohes Pin-Volumen in zu kurzer Zeit.**
175 Pins in 6 Tagen (~29/Tag) auf einem erst am 10.08.2026 gestarteten
Konto ohne Historie. Ein solcher Sprung von null auf hohes Volumen muss
wie automatisierte Aktivität wirken.

**b) Wenige Zielseiten.**
Zum Sperrzeitpunkt existierten erst 7 Artikel und 6 Themenseiten. Selbst
bei korrekter Verlinkung wären das zu wenige Ziele für 88 Pins gewesen.

**c) Verbleibende Pins auf die Startseite.**
Soweit nicht das Profil verlinkt wurde, zeigten Pins teils auf die nackte
Startseite (`http://franksfinanzcheck.de`) statt auf den konkreten
Artikel – zusätzlich über `http://` statt `https://`.

## 3. Rekonstruktion des Ablaufs

| Zeitpunkt | Ereignis |
|---|---|
| 10.08.2026 | Start des Blogs, erste 2 Artikel |
| 10.–14.08. | ca. **88 Finanz-Pins**, überwiegend mit Profil-Link |
| danach | ca. **87 Pins** für die **M&M'S Halloween Countdown Challenge** |
| **15.08.2026** | **Sperre des Kontos** |

Die Challenge-Pins entstanden **nach** den Finanz-Pins. Das Konto trug zu
diesem Zeitpunkt bereits die Last aus der fehlerhaften Verlinkung; der
zusätzliche Volumenblock dürfte den Ausschlag gegeben haben.

## 4. Zu den 87 Challenge-Pins

Diese Pins entstanden im Rahmen der **M&M'S Halloween Countdown
Challenge**, zu der Pinterest uns **offiziell eingeladen** hat; das
Bildmaterial stammt aus dieser Aktion. Sie sind damit weder eine
Zweckentfremdung des Kontos noch eine Markenrechtsverletzung, und sie
tragen den beschriebenen Verlinkungsfehler nicht.

Wir bitten, diese Pins als das zu werten, was sie sind: Teilnahme an
einem von Pinterest selbst initiierten Partnerprogramm.

## 5. Was nachweislich NICHT vorlag

| Prüfpunkt | Befund |
|---|---|
| Automatisierung / Bots | **keine** – 0 Pins über die API, kein Scheduling-Tool |
| Werbekennzeichnung | **25/25** Pin-Texte mit `*Werbung`-Präfix (UWG-konform) |
| Doppelte Pin-Texte | **0** Near-Duplicates (6-Wort-Shingle, Jaccard ≥ 0,25) |
| Doppelte Pin-Bilder | **0** exakte Duplikate bei 26 Cover-Bildern |
| Affiliate-Weiterleitungen | **kein** Pin zeigte auf eine Affiliate- oder Redirect-URL |
| Cloaking | **keins** – Zielseiten sind normale Artikelseiten |
| Affiliate-Gateway `/go/` | `noindex,nofollow,noarchive`, in `robots.txt` gesperrt |
| Erreichbarkeit der Website | durchgehend **online**, HTTP→HTTPS-Weiterleitung aktiv |
| Blog-Kadenz | nur Mon, Wed, Fri, max. 3 Artikel/Tag |

## 6. Umgesetzte Maßnahmen

**a) Verlinkung korrigiert.** Künftig verlinkt **jeder** Pin ausschließlich
die zugehörige Artikelseite auf `https://franksfinanzcheck.de` – nie das
Pinterest-Profil, nie die nackte Startseite, immer mit HTTPS.

**b) Technische Begrenzung (nicht umgehbar).** Vor jedem künftigen
Pin-Vorgang greift ein Gate:

- **max. 3 Pins pro Ziel-URL**
- **min. 7 Tage Abstand** zwischen zwei Pins auf dieselbe URL

Die Pin-Planung wurde entsprechend bereinigt: von 73 auf **48 Pins**
auf 29 verschiedene Zielseiten, 25 Pins zurückgestellt. Interne
Mengenvorgaben, die nur durch Mehrfach-Pins erreichbar waren, wurden
abgeschafft – zusätzliche Pins entstehen künftig durch neue Artikel.

**c) Volumen-Selbstverpflichtung.** Nach einer Reaktivierung bauen wir das
Pin-Volumen moderat und schrittweise auf.

## 7. Bitte

Wir bitten um erneute Prüfung des Kontos. Der ursächliche Fehler ist
identifiziert, verstanden und technisch abgestellt. Sollte eine
Reaktivierung nicht in Betracht kommen, bitten wir um einen konkreten
Hinweis, welche Pins beanstandet wurden.

---

_Die Kennzahlen in Abschnitt 5 sind aus dem Repository reproduzierbar
(`scripts/spam_guard.py`, `scripts/pinterest_plan_guard.py`). Die Angaben
zu Anzahl und Verlinkung der veröffentlichten Pins in Abschnitt 1–4
beruhen auf Auskunft des Kontoinhabers und ließen sich nach der Sperre
nicht mehr technisch verifizieren._
