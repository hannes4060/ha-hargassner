"""Binärsensoren für Hargassner."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HargassnerConfigEntry
from .entity import HargassnerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HargassnerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([HargassnerConnection(entry.runtime_data, entry.entry_id)])


class HargassnerConnection(HargassnerEntity, BinarySensorEntity):
    """Zeigt an, ob der Telnet-Datenstrom läuft."""

    _attr_name = "Verbindung"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client, entry_id: str) -> None:
        super().__init__(client, entry_id, "connection")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self._client.connected
