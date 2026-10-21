# Hargassner (lokal) für Home Assistant

Liest die Kesselsteuerung eines Hargassner Neo HV (getestet: Neo HV 30) lokal über
den Telnet-Datenstrom (Port 23) aus. Keine Cloud nötig.

## Installation

**HACS:** Repository als *Custom repository* (Typ *Integration*) hinzufügen, installieren, HA neu starten.

**Manuell:** `custom_components/hargassner` nach `/config/custom_components/hargassner` kopieren, HA neu starten.

Danach unter *Einstellungen → Geräte & Dienste → Integration hinzufügen → Hargassner (lokal)*
die IP des Kessels eintragen.

## Sensoren

Abgeglichen gegen den Cloud-Export (Stillstand und kompletter Abbrand).

| Sensor | Feld | Status |
|---|---|---|
| Kesselzustand | 1 | Klartext teilweise vermutet (siehe unten) |
| Sauerstoffgehalt Ist / Soll | 2 / 3 | geprüft |
| Kesseltemperatur Ist / Soll | 4 / 5 | geprüft |
| Rücklauftemperatur Ist / Soll | 6 / 7 | geprüft |
| Rauchgastemperatur | 8 | geprüft |
| Leistung | 9 | geprüft |
| Puffer oben / Mitte / unten | 12 / 13 / 14 | geprüft |
| Puffer Füllgrad | 17 | geprüft |
| Primärluft / Sekundärluft | 21 / 23 | vermutet, nicht in der Cloud |
| Saugzug Drehzahl | 26 | vermutet, nicht in der Cloud |
| Außentemperatur / gemittelt | 32 / 33 | geprüft |
| Höchste Anforderung | 34 | geprüft |
| Höchste Anforderung Puffer | 35 | geprüft (Feld 54 verhält sich fast gleich) |
| Vorlauf HK 1 | 53 | geprüft |
| Boiler 1 | 76 | geprüft |

### Kesselzustand (Feld 1)

| Code | Klartext | Sicherheit |
|---|---|---|
| 1 | Aus | sicher |
| 13 | Heiztür offen | vermutet (Saugzug läuft, Rauchgas kühlt ab, vor der Zündung) |
| 4 | Anheizen | vermutet (Leistung 100 %, O₂ 21 %, Rauchgas steigt) |
| 6 | Heizen | vermutet (stabiler Abbrand, Rauchgas ~220 °C) |

Unbekannte Codes erscheinen als „Zustand N“. Der Zahlenwert steht im Attribut `code`.

Zusätzlich gibt es für jedes andere Feld einen deaktivierten Diagnose-Sensor
„Rohwert Feld N“. Damit lassen sich weitere Werte zuordnen.

## Optionen

- **Aktualisierungsintervall** (Standard 10 s): Der Kessel sendet etwa jede Sekunde.
  HA übernimmt höchstens alle N Sekunden einen neuen Wert, um die Datenbank zu schonen.

## Hinweise

Die Feldpositionen hängen von der Kessel-Firmware ab. Die Zuordnung wurde per
Cloud-Export abgeglichen (siehe `tests/test_parser.py`). Die Cloud speichert
alle 5 Minuten einen Momentwert vom Ende des Intervalls.
