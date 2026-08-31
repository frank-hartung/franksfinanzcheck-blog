## Rechenbeispiel: Was ein Funkloch wirklich kostet

Ein 100-Mbit/s-Anschluss für 34,99 € im Monat nützt wenig, wenn im Homeoffice nur 12 Mbit/s ankommen. Videokonferenzen brechen ab, die Cloud-Sicherung dauert dreimal so lang, der Streaming-Stick wechselt auf 480p. Der effektive Preis pro nutzbarem Megabit steigt von 0,35 € auf fast 3 €.

Drei realistische Wege, Stand 2026:

| Lösung | Einmal-Kosten | Laufende Kosten | Wann sie greift |
|---|---|---|---|
| Router umstellen + Kanalwechsel | 0 € | 0 € | 1–2 Zimmer, Sichtkontakt |
| Set-Repeater (kein Mesh) | 40–80 € | 0 € | Eine Etage, eine tote Ecke |
| 2er-Mesh (WLAN 6) | 150–250 € | 0 € | Haus, mehrere Wände, Homeoffice |
| Powerline mit WLAN | 70–130 € | 0 € | Altbau mit dicken Wänden, Stromkreis zusammen |

Ein Mesh-Set für 180 €, über 36 Monate gerechnet, kostet 5 € im Monat – weniger als eine einzige unnötige Router-Miete. Wer den Provider-Router für 5–8 €/Monat mietet und parallel Funklöcher hat, zahlt doppelt: einmal für Hardware, einmal für nicht gelieferte Leistung.

## Typische WLAN-Fehler, die Speed fressen

**Router im Technikschrank.** Holz, Metallgitter und ein Stapel Kartons dämpfen 5 GHz brutal. Frei, erhöht, möglichst zentral – das allein holt oft 30–50 % Reichweite zurück.

**2,4 GHz und 5 GHz unter demselben Namen, ohne Band-Steering.** Alte Geräte kleben am langsamen Band und ziehen das ganze Netz nach unten. Getrennte SSIDs („Zuhause“ und „Zuhause-5G“) geben dir die Kontrolle.

**Kanal 1, 6 oder 11 in einem Mehrfamilienhaus, in dem sechs Nachbarn dasselbe tun.** Eine kostenlose Analyse-App zeigt die Belegung. Auf 5 GHz sind 36/40/44 oft leer, während 2,4 GHz überfüllt ist.

**Repeater, der das Signal halbiert.** Ein klassischer Repeater nutzt dasselbe Radio zum Empfangen und Senden. Mesh mit Rückkanal oder eine LAN-Anbindung des zweiten Knotens vermeidet den Halbierungs-Effekt.

**Firmware von 2023.** Sicherheitslücken und kaputte Mesh-Roaming-Profile. Einmal im Quartal im Router-Menü nach Updates sehen.

## Schritt-für-Schritt: vom Funkloch zum nutzbaren Homeoffice

1. **Messen, nicht schätzen.** Speedtest per Kabel am Router, dann per WLAN am Schreibtisch, im Schlafzimmer, auf der Terrasse. Notiere Download, Upload, Ping. Alles unter 30 % der Vertragswerte ist ein Funk- oder Leitungsproblem – beides musst du trennen.
2. **Kabel-Referenz.** Liegt der LAN-Test klar unter dem Vertrag, ist es der Anschluss (Provider anrufen, Entstörungsnummer, 14-Tage-Protokoll). Liegt LAN gut und WLAN schlecht, arbeitest du am Funk.
3. **Position.** Router auf Augenhöhe, weg von Mikrowelle, DECT-Basis und Bluetooth-Lautsprechern. Antennen senkrecht.
4. **Kanal und Band.** 5 GHz für Arbeitsgeräte, 2,4 GHz für Smarthome. DFS-Kanäle meiden, wenn die FritzBox ständig neu startet (Radar-Erkennung).
5. **Mesh oder Powerline entscheiden.** Mehr als zwei Wände aus Stein oder eine Etage dazwischen → Mesh. Altbau mit Stahlträgern → Powerline testen (im selben Stromkreis).
6. **Gäste-WLAN an, IoT getrennt.** Kameras und Staubsaugerroboter gehören nicht ins Arbeitsnetz.
7. **Nach 7 Tagen erneut messen.** Dieselbe Uhrzeit, dieselben drei Orte. Nur Zahlen beweisen, dass die Maßnahme wirkt.

## Was Mesh, Repeater und Powerline 2026 konkret unterscheiden

Mesh-Systeme (WLAN 6/6E) halten eine gemeinsame SSID und reichen Clients an den stärkeren Knoten weiter, ohne dass Zoom abbricht. Repeater tun das oft nicht – das Handy bleibt am schwachen Knoten hängen. Powerline hängt an der Hausverkabelung: Unterputz-LED-Netzteile und FI-Schalter können den Durchsatz auf 20–40 Mbit/s drücken, selbst wenn die Packung „1.200 Mbit“ verspricht. Deshalb immer mit Rückgaberecht kaufen und 48 Stunden im Zielfunkloch testen.

Wer Glasfaser mit 300 Mbit/s oder mehr hat, sollte den zweiten Mesh-Knoten per LAN-Kabel anbinden (Backhaul). Dann bleibt das Funkspektrum den Geräten, und du holst im Homeoffice endlich das, wofür du den Tarif bezahlst.
