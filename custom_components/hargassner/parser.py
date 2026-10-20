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
    kind: str = "temperature"  # temperature | percent | number | raw
    verified: bool = True  # gegen Cloud-Export abgeglichen


# Abgeglichen gegen Cloud-Export vom 20.10.2026 (Neo HV 30, Stillstand).
# verified=False: Position plausibel, aber im Stillstand nicht eindeutig (Wert 0),
# muss mit einem Mitschnitt im Abbrand bestätigt werden.
FIELDS: tuple[FieldDef, ...] = (
    FieldDef("kessel_zustand", 1, "Kesselzustand", None, "raw", False),
    FieldDef("o2_ist", 2, "Sauerstoffgehalt Ist", "%", "percent"),
    FieldDef("o2_soll", 3, "Sauerstoffgehalt Soll", "%", "percent", False),
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
