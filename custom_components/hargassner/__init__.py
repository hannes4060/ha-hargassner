"""Hargassner-Integration für Home Assistant (lokal über Telnet)."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .client import HargassnerClient
from .const import CARD_VERSION, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CARD_URL = "/hargassner/hargassner-card.js"
CARD_PATH = Path(__file__).parent / "www" / "hargassner-card.js"

type HargassnerConfigEntry = ConfigEntry[HargassnerClient]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Liefert die Lovelace-Karte aus und lädt sie automatisch im Frontend."""
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), True)]
        )
        add_extra_js_url(hass, f"{CARD_URL}?v={CARD_VERSION}")
    except (RuntimeError, AttributeError) as err:  # z. B. ohne HTTP-Komponente
        _LOGGER.warning("Hargassner-Karte konnte nicht registriert werden: %s", err)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HargassnerConfigEntry) -> bool:
    interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    client = HargassnerClient(entry.data[CONF_HOST], entry.data[CONF_PORT], interval)
    client.start(lambda coro: entry.async_create_background_task(hass, coro, "hargassner"))
    entry.runtime_data = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HargassnerConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.stop()
    return ok


async def _async_reload(hass: HomeAssistant, entry: HargassnerConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
