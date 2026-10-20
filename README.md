# Hargassner (lokal) für Home Assistant

Liest die Kesselsteuerung eines Hargassner Neo HV (getestet: Neo HV 30) lokal über
den Telnet-Datenstrom (Port 23) aus. Keine Cloud nötig.

## Installation

**HACS:** Repository als *Custom repository* (Typ *Integration*) hinzufügen, installieren, HA neu starten.

**Manuell:** `custom_components/hargassner` nach `/config/custom_components/hargassner` kopieren, HA neu starten.

Danach unter *Einstellungen → Geräte & Dienste → Integration hinzufügen → Hargassner (lokal)*
die IP des Kessels eintragen.

## Sensoren

| Sensor | Feld | Status |
|---|---|---|
| Kesseltemperatur Ist / Soll | 4 / 5 | geprüft |
| Rücklauftemperatur Ist / Soll | 6 / 7 | geprüft |
| Rauchgastemperatur | 8 | geprüft |
| Sauerstoffgehalt Ist | 2 | geprüft |
| Sauerstoffgehalt Soll | 3 | offen (im Stillstand 0) |
| Puffer oben / Mitte / unten | 12 / 13 / 14 | geprüft |
| Puffer Füllgrad | 17 | geprüft |
| Außentemperatur / gemittelt | 32 / 33 | geprüft |
| Vorlauf HK 1 | 53 | geprüft |
| Boiler 1 | 76 | geprüft |
| Kesselzustand (roh) | 1 | offen |

Zusätzlich gibt es für jedes andere Feld einen deaktivierten Diagnose-Sensor
„Rohwert Feld N“. Damit lassen sich weitere Werte zuordnen.

## Optionen

- **Aktualisierungsintervall** (Standard 10 s): Der Kessel sendet etwa jede Sekunde.
  HA übernimmt höchstens alle N Sekunden einen neuen Wert, um die Datenbank zu schonen.

## Hinweise

Die Feldpositionen hängen von der Kessel-Firmware ab. Die Zuordnung wurde per
Cloud-Export abgeglichen (siehe `tests/test_parser.py`).
