# Hargassner (lokal) für Home Assistant

Liest die Kesselsteuerung eines Hargassner Neo HV (getestet: Neo HV 30) lokal über
den Telnet-Datenstrom (Port 23) aus. Keine Cloud nötig.

## Installation

**HACS:** Repository als *Custom repository* (Typ *Integration*) hinzufügen, installieren, HA neu starten.

**Manuell:** `custom_components/hargassner` nach `/config/custom_components/hargassner` kopieren, HA neu starten.

Danach unter *Einstellungen → Geräte & Dienste → Integration hinzufügen → Hargassner (lokal)*
die IP des Kessels eintragen.

## Lovelace-Karte

Die Integration bringt eine Karte im Stil des Kesseldisplays mit: Kessel mit Brennraum
und Flammen, Puffer mit Temperaturverlauf, Boiler, Heizkreis 1 und Soll/Ist-Werte.
Sie wird automatisch geladen: Die Integration kopiert ein kleines Ladeskript nach
`/config/www/hargassner/` und trägt es als Lovelace-Ressource ein
(`/local/hargassner/hargassner-loader.js`). Das Ladeskript holt die eigentliche Karte und versucht
es während des HA-Starts wiederholt, bis die Integration geladen ist. So erscheint nach einem
Neustart kein „Custom element doesn't exist“ mehr.

- Gab es `/config/www` beim Start noch nicht, wird der Ordner angelegt; das Ladeskript greift dann
  ab dem nächsten Neustart (bis dahin wird die Karte direkt eingebunden).
- Im YAML-Modus von Lovelace die Ressource `/local/hargassner/hargassner-loader.js` manuell
  eintragen (Typ *JavaScript-Modul*).

![Hargassner-Karte](docs/card.png)

Dashboard bearbeiten → *Karte hinzufügen* → „Hargassner Kessel“, oder per YAML:

```yaml
type: custom:hargassner-card
title: Holzvergaser    # optional
show_values: true      # optional, Soll/Ist-Tabelle
```

Die Karte findet die Sensoren selbst (über die Entity-Registry, Plattform `hargassner`), es ist keine
Konfiguration nötig. Reißt die Verbindung zum Kessel ab, zeigt die Karte einen Hinweis statt leerer Werte.

## Sensoren

Abgeglichen gegen den Cloud-Export (Stillstand und Abbrand) und gegen Displayfotos (Anheizen).

| Sensor | Feld | Status |
|---|---|---|
| Kesselzustand | 1 | geprüft (Display) |
| Sauerstoffgehalt Ist / Soll | 2 / 3 | geprüft |
| Kesseltemperatur Ist / Soll | 4 / 5 | geprüft |
| Rücklauftemperatur Ist / Soll | 6 / 7 | geprüft |
| Rauchgastemperatur | 8 | geprüft |
| Leistung | 9 | geprüft |
| Saugzug Soll / Ist (%) | 10 / 11 | geprüft (Display) |
| Puffer oben / Mitte / unten | 12 / 13 / 14 | geprüft |
| Puffer Füllgrad | 17 | geprüft |
| Primärluft Soll / Ist | 20 / 21 | geprüft (Display) |
| Sekundärluft Soll / Ist | 22 / 23 | geprüft (Display) |
| Saugzug Drehzahl | 26 | vermutet |
| Außentemperatur / gemittelt | 32 / 33 | geprüft |
| Höchste Anforderung | 34 | geprüft |
| Höchste Anforderung Puffer | 35 | geprüft |
| Puffer Solltemperatur / Ausschalttemperatur TPO | 41 / 42 | vermutet (Display 45 °C) |
| Vorlauf Ist HK 1 | 53 | geprüft |
| Vorlauf Soll HK 1 | 54 | geprüft (Display) |
| Status HK 1 (0 = Aus, 1 = Heizen) | 57 | geprüft (Display), 3/4 noch offen |
| Boiler 1 | 76 | geprüft |

### Kesselzustand (Feld 1)

| Code | Klartext |
|---|---|
| 1 | Aus |
| 13 | Tür offen |
| 4 | Anheizen |
| 6 | Leistungsbrand |
| 9 | Ausbrand |
| 11 | Restwärme |

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
