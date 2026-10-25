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
LOADER_SRC = Path(__file__).parent / "www" / "hargassner-loader.js"
LOADER_LOCAL_URL = "/local/hargassner/hargassner-loader.js"
KNOWN_URLS = {CARD_URL, LOADER_LOCAL_URL}

type HargassnerConfigEntry = ConfigEntry[HargassnerClient]


def _install_loader(www_dir: str) -> bool:
    """Kopiert das Ladeskript nach /config/www/hargassner/.

    Gibt True zurück, wenn /local in dieser Laufzeit erreichbar ist. Das ist nur
    der Fall, wenn /config/www schon beim Start von HA existierte; wird der
    Ordner jetzt erst angelegt, greift /local ab dem nächsten Neustart.
    """
    www = Path(www_dir)
    existed = www.is_dir()
    target = www / "hargassner" / "hargassner-loader.js"
    content = LOADER_SRC.read_bytes()
    if not target.exists() or target.read_bytes() != content:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return existed


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Liefert die Lovelace-Karte aus und lädt sie automatisch im Frontend.

    Die Karte selbst liegt unter /hargassner/ und ist erst erreichbar, wenn diese
    Integration geladen ist. HA startet den Webserver aber schon vorher. Damit ein
    Dashboard, das in dieser Phase lädt, nicht mit "Custom element doesn't exist"
    hängen bleibt, wird als Ressource ein kleines Ladeskript unter /local
    eingetragen, das die Karte bei Bedarf wiederholt nachlädt.
    """
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), True)]
        )
    except (RuntimeError, AttributeError) as err:  # z. B. ohne HTTP-Komponente
        _LOGGER.warning("Hargassner-Karte konnte nicht registriert werden: %s", err)
        return True

    try:
        local_ok = await hass.async_add_executor_job(
            _install_loader, hass.config.path("www")
        )
    except OSError as err:
        _LOGGER.warning("Hargassner-Karte: Ladeskript nicht kopiert: %s", err)
        local_ok = False

    base = LOADER_LOCAL_URL if local_ok else CARD_URL
    url = f"{base}?v={CARD_VERSION}"
    add_extra_js_url(hass, url)
    await _async_register_lovelace_resource(hass, url)
    return True


async def _async_register_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    """Trägt die Karte als Lovelace-Ressource ein bzw. hält den Eintrag aktuell."""
    try:
        data = hass.data.get("lovelace")
        mode = getattr(data, "resource_mode", None) or getattr(data, "mode", None)
        resources = getattr(data, "resources", None)
        if resources is None or mode != "storage":
            _LOGGER.info(
                "Lovelace im YAML-Modus: Ressource %s bitte manuell eintragen", url
            )
            return
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True
        ours = [
            item
            for item in resources.async_items()
            if item.get("url", "").split("?")[0] in KNOWN_URLS
        ]
        if not ours:
            await resources.async_create_item({"res_type": "module", "url": url})
            _LOGGER.info("Hargassner-Karte: Ressource %s angelegt", url)
            return
        first, *duplicates = ours
        if first["url"] != url:
            await resources.async_update_item(
                first["id"], {"res_type": "module", "url": url}
            )
            _LOGGER.info("Hargassner-Karte: Ressource auf %s aktualisiert", url)
        for item in duplicates:  # z. B. manuell zusätzlich eingetragen
            await resources.async_delete_item(item["id"])
    except Exception as err:  # noqa: BLE001 - Karte ist optional
        _LOGGER.warning("Hargassner-Karte: Ressource nicht eingetragen: %s", err)


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
