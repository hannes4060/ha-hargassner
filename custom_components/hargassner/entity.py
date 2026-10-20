"""Basis-Entity für Hargassner."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .client import HargassnerClient
from .const import DOMAIN


class HargassnerEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, client: HargassnerClient, entry_id: str, key: str) -> None:
        self._client = client
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Hargassner Neo HV",
            manufacturer="Hargassner",
            model="Neo HV",
            configuration_url=None,
        )

    @property
    def available(self) -> bool:
        return self._client.connected and self._client.latest is not None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._client.add_listener(self.async_write_ha_state))
