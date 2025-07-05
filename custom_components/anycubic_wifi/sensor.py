import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    entities = [
        AnycubicPrinterInfoSensor(coordinator),
        AnycubicTemperatureSensor(coordinator),
        AnycubicFanSensor(coordinator),
        AnycubicPrintJobSensor(coordinator),
        AnycubicSlotsSensor(coordinator),
    ]
    async_add_entities(entities)


class AnycubicPrinterInfoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Anycubic Printer Info"
        self._attr_unique_id = "anycubic_printer_info"

    @property
    def native_value(self):
        return self.coordinator.data.get("info", {}).get("data", {}).get("model")

    @property
    def extra_state_attributes(self):
        info = self.coordinator.data.get("info", {}).get("data", {})
        return {
            "ip": info.get("ip"),
            "firmware_version": info.get("version"),
        }


class AnycubicTemperatureSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Anycubic Temperatures"
        self._attr_unique_id = "anycubic_temperatures"

    @property
    def native_value(self):
        return self.coordinator.data.get("info", {}).get("data", {}).get("temp", {}).get("curr_nozzle_temp")

    @property
    def extra_state_attributes(self):
        temp = self.coordinator.data.get("info", {}).get("data", {}).get("temp", {})
        return {
            "current_bed_temp": temp.get("curr_hotbed_temp"),
            "target_bed_temp": temp.get("target_hotbed_temp"),
            "target_nozzle_temp": temp.get("target_nozzle_temp"),
        }


class AnycubicFanSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Anycubic Fans"
        self._attr_unique_id = "anycubic_fans"

    @property
    def native_value(self):
        return self.coordinator.data.get("info", {}).get("data", {}).get("fan_speed_pct")

    @property
    def extra_state_attributes(self):
        info = self.coordinator.data.get("info", {}).get("data", {})
        return {
            "aux_fan_speed": info.get("aux_fan_speed_pct"),
            "box_fan_level": info.get("box_fan_level"),
        }


class AnycubicPrintJobSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Anycubic Print Job"
        self._attr_unique_id = "anycubic_print_job"

    @property
    def native_value(self):
        return self.coordinator.data.get("print", {}).get("state")

    @property
    def extra_state_attributes(self):
        print_data = self.coordinator.data.get("print", {}).get("data", {})
        return {
            "progress": print_data.get("progress"),
            "current_layer": print_data.get("curr_layer"),
            "total_layers": print_data.get("total_layers"),
            "remaining_time": print_data.get("remain_time"),
            "print_time": print_data.get("print_time"),
            "file_name": print_data.get("filename"),
            "supplies_usage": print_data.get("supplies_usage"),
        }


class AnycubicSlotsSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Anycubic Slots"
        self._attr_unique_id = "anycubic_slots"

    @property
    def native_value(self):
        slots = self._get_slots()
        return len(slots) if slots else 0

    @property
    def extra_state_attributes(self):
        return {"slots": self._get_slots()}

    def _get_slots(self):
        boxes = self.coordinator.data.get("multiColorBox", {}).get("data", {}).get("multi_color_box", [])
        all_slots = []
        for box in boxes:
            for slot in box.get("slots", []):
                all_slots.append({
                    "index": slot.get("index"),
                    "type": slot.get("type"),
                    "color": slot.get("color"),
                    "sku": slot.get("sku"),
                })
        return all_slots
