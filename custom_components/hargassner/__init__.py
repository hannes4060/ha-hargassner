"""Hargassner-Integration für Home Assistant (lokal über Telnet)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import HargassnerClient
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type HargassnerConfigEntry = ConfigEntry[HargassnerClient]


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
