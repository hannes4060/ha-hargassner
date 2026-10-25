"""Konstanten für die Hargassner-Integration."""

DOMAIN = "hargassner"
DEFAULT_PORT = 23
DEFAULT_NAME = "Hargassner"

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 10  # Sekunden; Kessel sendet ca. 1x pro Sekunde


# Maximale Feldanzahl, für die Rohwert-Sensoren angelegt werden
MAX_RAW_FIELDS = 120

# Version der Lovelace-Karte (Cache-Busting im Browser)
CARD_VERSION = "0.4.2"
