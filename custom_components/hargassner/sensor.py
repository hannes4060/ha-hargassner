"""Sensoren für Hargassner."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HargassnerConfigEntry
from .client import HargassnerClient
from .const import MAX_RAW_FIELDS
from .entity import HargassnerEntity
from .parser import (
    FIELDS,
    HK_ZUSTAENDE,
    KESSEL_ZUSTAENDE,
    KNOWN_INDICES,
    FieldDef,
    hk_text,
    zustand_text,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HargassnerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = entry.runtime_data
    entities: list[SensorEntity] = [
        HargassnerSensor(client, entry.entry_id, f) for f in FIELDS
    ]
    # Rohwerte aller übrigen Felder, standardmäßig deaktiviert.
    # Hilft beim Zuordnen weiterer Werte (Heizkreise, Leistung, Störungen ...).
    entities += [
        HargassnerRawSensor(client, entry.entry_id, i)
        for i in range(1, MAX_RAW_FIELDS)
        if i not in KNOWN_INDICES
    ]
    async_add_entities(entities)


class HargassnerSensor(HargassnerEntity, SensorEntity):
    def __init__(self, client: HargassnerClient, entry_id: str, field: FieldDef) -> None:
        super().__init__(client, entry_id, field.key)
        self._field = field
        self._attr_name = field.name
        # Stabiler Schlüssel für die Lovelace-Karte; steht in der Entity-Registry
        # und bleibt dadurch auch erhalten, wenn der Sensor nicht verfügbar ist.
        self._attr_translation_key = field.key
        if field.kind == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif field.kind == "percent":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif field.kind == "rpm":
            self._attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif field.kind == "state":
            self._attr_icon = "mdi:fire"
        elif field.kind == "hkstate":
            self._attr_icon = "mdi:radiator"

    def _raw(self):
        telegram = self._client.latest
        if telegram is None:
            return None
        return telegram.values.get(self._field.key)

    @property
    def native_value(self):
        value = self._raw()
        if self._field.kind == "state":
            return zustand_text(value)
        if self._field.kind == "hkstate":
            return hk_text(value)
        return value

    @property
    def extra_state_attributes(self):
        attrs = {
            "schluessel": self._field.key,  # wird von der Lovelace-Karte genutzt
            "feldindex": self._field.index,
            "verifiziert": self._field.verified,
        }
        if self._field.kind in ("state", "hkstate"):
            value = self._raw()
            attrs["code"] = int(value) if isinstance(value, float) else value
            attrs["bekannte_zustaende"] = (
                KESSEL_ZUSTAENDE if self._field.kind == "state" else HK_ZUSTAENDE
            )
        return attrs


class HargassnerRawSensor(HargassnerEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, client: HargassnerClient, entry_id: str, index: int) -> None:
        super().__init__(client, entry_id, f"raw_{index}")
        self._index = index
        self._attr_name = f"Rohwert Feld {index}"

    @property
    def native_value(self):
        telegram = self._client.latest
        if telegram is None or self._index >= len(telegram.raw):
            return None
        return telegram.raw[self._index]
