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
