"""Parser für den Telnet-Datenstrom (pm-Zeilen) der Hargassner-Steuerung.

Bewusst ohne Home-Assistant-Abhängigkeiten, damit er sich einzeln testen lässt.
Die Feldindizes beziehen sich auf die per Leerzeichen getrennte Zeile,
Index 0 ist das "pm".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    """Beschreibung eines bekannten Feldes im pm-Telegramm."""

    key: str
    index: int
    name: str
    unit: str | None = None
    kind: str = "temperature"  # temperature | percent | rpm | state
    verified: bool = True  # gegen Cloud-Export abgeglichen


# Kesselzustände (Feld 1), beobachtet beim Neo HV 30.
# 1 ist sicher (Stillstand). Die übrigen Namen sind aus dem Verlauf abgeleitet
# (Saugzug, Luftklappen, Rauchgas) und noch mit dem Display zu bestätigen.
KESSEL_ZUSTAENDE: dict[int, str] = {
    1: "Aus",
    4: "Anheizen",
    6: "Heizen",
    13: "Heiztür offen",
}


def zustand_text(value: float | str | None) -> str | None:
    """Übersetzt den Zahlenwert aus Feld 1 in einen Klartext."""
    if value is None:
        return None
    try:
        code = int(float(value))
    except ValueError:
        return str(value)
    return KESSEL_ZUSTAENDE.get(code, f"Zustand {code}")


# verified=True: gegen Cloud-Export abgeglichen
#   (20.10.2026 Stillstand, 21.10.2026 12:20-14:24 inkl. Abbrand).
# verified=False: aus dem Verlauf abgeleitet, nicht in der Cloud vorhanden.
FIELDS: tuple[FieldDef, ...] = (
    FieldDef("kessel_zustand", 1, "Kesselzustand", None, "state", False),
    FieldDef("o2_ist", 2, "Sauerstoffgehalt Ist", "%", "percent"),
    FieldDef("o2_soll", 3, "Sauerstoffgehalt Soll", "%", "percent"),
    FieldDef("leistung", 9, "Leistung", "%", "percent"),
    FieldDef("saugzug", 26, "Saugzug Drehzahl", "U/min", "rpm", False),
    FieldDef("primaerluft", 21, "Primärluft", "%", "percent", False),
    FieldDef("sekundaerluft", 23, "Sekundärluft", "%", "percent", False),
    FieldDef("hoechste_anforderung", 34, "Höchste Anforderung", "°C"),
    FieldDef("puffer_anforderung", 35, "Höchste Anforderung Puffer", "°C"),
    FieldDef("kessel_ist", 4, "Kesseltemperatur Ist", "°C"),
    FieldDef("kessel_soll", 5, "Kesseltemperatur Soll", "°C"),
    FieldDef("ruecklauf_ist", 6, "Rücklauftemperatur Ist", "°C"),
    FieldDef("ruecklauf_soll", 7, "Rücklauftemperatur Soll", "°C"),
    FieldDef("rauchgas", 8, "Rauchgastemperatur", "°C"),
    FieldDef("puffer_oben", 12, "Puffer oben", "°C"),
    FieldDef("puffer_mitte", 13, "Puffer Mitte", "°C"),
    FieldDef("puffer_unten", 14, "Puffer unten", "°C"),
    FieldDef("puffer_fuellgrad", 17, "Puffer Füllgrad", "%", "percent"),
    FieldDef("aussen", 32, "Außentemperatur", "°C"),
    FieldDef("aussen_gemittelt", 33, "Außentemperatur gemittelt", "°C"),
    FieldDef("hk1_vorlauf_ist", 53, "Vorlauf HK 1", "°C"),
    FieldDef("boiler1", 76, "Boiler 1", "°C"),
)

KNOWN_INDICES = frozenset(f.index for f in FIELDS)


@dataclass
class Telegram:
    """Ein geparstes pm-Telegramm."""

    values: dict[str, float | str]
    raw: list[str]


def _to_value(token: str) -> float | str:
    try:
        return float(token)
    except ValueError:
        return token


def parse_line(line: str) -> Telegram | None:
    """Parst eine pm-Zeile. Gibt None zurück, wenn die Zeile unbrauchbar ist."""
    parts = line.strip().split()
    if len(parts) < 2 or parts[0] != "pm":
        return None
    values: dict[str, float | str] = {}
    for field in FIELDS:
        if field.index < len(parts):
            values[field.key] = _to_value(parts[field.index])
    return Telegram(values=values, raw=parts)
