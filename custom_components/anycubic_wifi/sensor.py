import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    ("Model", ["model"], None),
    ("IP", ["ip"], None),
    ("Firmware Version", ["version"], None),
    ("Printer State", ["state"], None),
    ("Current Bed Temp", ["temp", "curr_hotbed_temp"], UnitOfTemperature.CELSIUS),
    ("Target Bed Temp", ["temp", "target_hotbed_temp"], UnitOfTemperature.CELSIUS),
    ("Current Nozzle Temp", ["temp", "curr_nozzle_temp"], UnitOfTemperature.CELSIUS),
    ("Target Nozzle Temp", ["temp", "target_nozzle_temp"], UnitOfTemperature.CELSIUS),
    ("Print Speed Mode", ["print_speed_mode"], None),
    ("Fan Speed", ["fan_speed_pct"], "%"),
    ("Aux Fan Speed", ["aux_fan_speed_pct"], "%"),
    ("Box Fan Level", ["box_fan_level"], "%"),
]

PRINT_SENSOR_TYPES = [
    ("Print State", "__state__", None),
    ("Print Progress", "progress", "%"),
    ("Current Layer", "curr_layer", None),
    ("Total Layers", "total_layers", None),
    ("Remaining Time", "remain_time", "min"),
    ("Print Time", "print_time", "min"),
    ("File Name", "filename", None),
    ("Supplies Usage", "supplies_usage", "mm"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    entities = []

    # Standard sensors
    for name, path, unit in SENSOR_TYPES:
        entities.append(AnycubicSensor(coordinator, name, path, unit))

    # Print-related sensors
    for name, field, unit in PRINT_SENSOR_TYPES:
        entities.append(AnycubicPrintSensor(coordinator, name, field, unit))

    async_add_entities(entities)

    # Add slot sensors dynamically
    async def handle_new_slots(new_slots):
        new_entities = []
        for index in new_slots:
            new_entities.append(AnycubicSlotSensor(coordinator, index, "Type", "type"))
            new_entities.append(AnycubicSlotSensor(coordinator, index, "Color", "color"))
            new_entities.append(AnycubicSlotSensor(coordinator, index, "SKU", "sku"))
        _LOGGER.debug("Adding new slot sensors: %s", [e.name for e in new_entities])
        async_add_entities(new_entities)

    async_dispatcher_connect(hass, f"{DOMAIN}_new_slots", handle_new_slots)


class AnycubicSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name: str, path: list[str], unit: str | None):
        super().__init__(coordinator)
        self._attr_name = f"Anycubic {name}"
        self._attr_unique_id = f"anycubic_{'_'.join(path)}"
        self._path = path
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data.get("info", {}).get("data")
        for key in self._path:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data


class AnycubicPrintSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name: str, field: str, unit: str | None):
        super().__init__(coordinator)
        self._attr_name = f"Anycubic {name}"
        self._attr_unique_id = f"anycubic_print_{field}"
        self._field = field
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> Any:
        if self._field == "__state__":
            return self.coordinator.data.get("print", {}).get("state")
        data = self.coordinator.data.get("print", {}).get("data", {})
        return data.get(self._field)


class AnycubicSlotSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, slot_index: int, name: str, field: str):
        super().__init__(coordinator)
        self._slot_index = slot_index
        self._field = field
        self._attr_name = f"Anycubic Slot {slot_index} {name}"
        self._attr_unique_id = f"anycubic_slot_{slot_index}_{field}"

    @property
    def native_value(self) -> Any:
        slot = self._find_slot()
        return slot.get(self._field) if slot else None

    @property
    def available(self) -> bool:
        return self._find_slot() is not None

    def _find_slot(self):
        multi_color_boxes = self.coordinator.data.get("multiColorBox", {}).get("data", {}).get("multi_color_box", [])
        for box in multi_color_boxes:
            for slot in box.get("slots", []):
                if slot.get("index") == self._slot_index:
                    return slot
        return None
