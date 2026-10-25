"""Parser-Test gegen echten Mitschnitt + Cloud-Export (20.10.2026, 23:55)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "hargassner_parser", ROOT / "custom_components/hargassner/parser.py"
)
parser = importlib.util.module_from_spec(spec)
sys.modules["hargassner_parser"] = parser
spec.loader.exec_module(parser)

# Werte aus dem Cloud-Export, Zeitstempel 23:55
CLOUD = {
    "kessel_ist": 45.1,
    "kessel_soll": 80,
    "rauchgas": 38.7,
    "o2_ist": 2.8,
    "o2_soll": 0,
    "ruecklauf_ist": 46.9,
    "ruecklauf_soll": 65,
    "aussen": 5.6,
    "aussen_gemittelt": 6.9,
    "hk1_vorlauf_ist": 34.7,
    "puffer_oben": 51.8,
    "puffer_mitte": 42.7,
    "puffer_unten": 42.2,
    "puffer_fuellgrad": 48.6,
    "boiler1": 65.9,
}


def test_matches_cloud_export():
    line = (ROOT / "tests/sample_stillstand.txt").read_text().splitlines()[0]
    t = parser.parse_line(line)
    assert t is not None
    for key, expected in CLOUD.items():
        assert t.values[key] == expected, key


def test_rejects_garbage():
    assert parser.parse_line("") is None
    assert parser.parse_line("xyz 1 2 3") is None
    assert parser.parse_line("pm") is None


# Cloud-Export 21.10.2026, Zeile "13:30" (Kessel im Abbrand).
# Sample = Telnet-Zeilen 13:30:00-13:34:59.
CLOUD_ABBRAND = {
    "kessel_ist": 74.7,
    "rauchgas": 222.3,
    "leistung": 95.0,
    "o2_ist": 6.2,
    "o2_soll": 5.8,
    "ruecklauf_ist": 67.9,
    "hoechste_anforderung": 56.0,
    "aussen": 13.1,
    "hk1_vorlauf_ist": 38.6,
    "puffer_oben": 38.3,
    "puffer_mitte": 30.8,
    "puffer_unten": 31.1,
    "puffer_fuellgrad": 25.3,
    "puffer_anforderung": 0,
    "boiler1": 59.9,
}


def test_abbrand_matches_cloud():
    lines = (ROOT / "tests/sample_abbrand.txt").read_text().splitlines()
    telegrams = [t for t in (parser.parse_line(l) for l in lines) if t]
    assert len(telegrams) > 200
    # Die Cloud tastet je Wert zu leicht unterschiedlichen Zeitpunkten gegen
    # Intervallende ab: Der Cloud-Wert muss in der Spanne des Intervalls liegen.
    for key, expected in CLOUD_ABBRAND.items():
        vals = [t.values[key] for t in telegrams]
        assert min(vals) - 0.5 <= expected <= max(vals) + 0.5, (key, min(vals), max(vals), expected)


def test_zustand_text():
    assert parser.zustand_text(1.0) == "Aus"
    assert parser.zustand_text(6.0) == "Leistungsbrand"
    assert parser.zustand_text(13.0) == "Tür offen"
    assert parser.zustand_text(11.0) == "Restwärme"
    assert parser.zustand_text(99.0) == "Zustand 99"
    assert parser.zustand_text(None) is None


def test_anheizen_matches_display():
    """Displayfoto Info/Kessel beim Anheizen: Saugzug 90/90, Primärluft 85/85,
    Sekundärluft 5/5. Gleiche Phase im Mitschnitt vom 21.10.2026, 13:08."""
    line = ("pm 4 18.3 11.1 31.8 80 33.3 65 64.4 100 90 90 31.6 31.3 31.6 15 0 22.3 0 3 "
            "85 86 5 4 8.17 13.63 600")
    t = parser.parse_line(line)
    assert t.values["saugzug_soll"] == 90 and t.values["saugzug_ist"] == 90
    assert t.values["primaerluft_soll"] == 85 and t.values["primaerluft"] == 86
    assert t.values["sekundaerluft_soll"] == 5 and t.values["sekundaerluft"] == 4
    assert parser.zustand_text(t.values["kessel_zustand"]) == "Anheizen"


def test_hk1():
    """Mitschnitt 21.10.2026: HK heizt (Feld 54 = 40, Feld 57 = 3), danach aus."""
    parts = ["pm"] + ["0"] * 80
    parts[54], parts[57] = "40", "3"
    t = parser.parse_line(" ".join(parts))
    assert t.values["hk1_vorlauf_soll"] == 40
    assert parser.hk_text(t.values["hk1_status"]) == "Heizen"
    assert parser.hk_text(4.0) == "Aus"
