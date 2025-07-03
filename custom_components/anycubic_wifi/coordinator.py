import logging
import re
from datetime import timedelta

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnycubicAPI
from .const import DOMAIN
from .mqtt import AnycubicMQTT

_LOGGER = logging.getLogger(__name__)


class AnycubicDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, host):
        super().__init__(
            hass,
            _LOGGER,
            name="Anycubic discovery",
            update_interval=timedelta(seconds=60),
        )
        self.api: AnycubicAPI | None = None
        self.mqtt: AnycubicMQTT | None = None
        self._host: str = host
        self._current_creds = None
        self._current_slots = set()

    def async_set_updated_data(self, data):
        """Callback to set updated data from MQTT."""
        # Check slots
        multi_color_box = data.get("multiColorBox", {}).get("data", {}).get("multi_color_box", [])
        slots_now = set()
        for box in multi_color_box:
            for slot in box.get("slots", []):
                index = slot.get("index")
                if index is not None:
                    slots_now.add(index)

        new_slots = slots_now - self._current_slots
        if new_slots:
            self._current_slots.update(new_slots)
            async_dispatcher_send(self.hass, f"{DOMAIN}_new_slots", new_slots)

        super().async_set_updated_data(data)

    async def _async_update_data(self):
        if not self.api:
            self.api = AnycubicAPI(self._host)

        try:
            data = await self.hass.async_add_executor_job(self.api.discover)
        except Exception as err:
            raise UpdateFailed(f"Could not fetch Anycubic data: {err}") from err

        creds = (data["username"], data["password"])
        if self._current_creds is None:
            self._current_creds = creds
            await self._async_init_mqtt(data)
        elif creds != self._current_creds:
            self._current_creds = creds
            await self._async_reconfigure_mqtt(*creds)

        # Must be triggered manually because the data is not updated automatically
        if self.mqtt:
            payload = {"type": "multiColorBox", "action": "getInfo"}
            topic = self.mqtt.web_topic("multiColorBox")
            self.mqtt.publish_json(topic, payload)

        return self.data or {}

    async def _async_init_mqtt(self, data):
        match = re.match(r"mqtts?://([^:]+):(\d+)", data["broker"])
        if not match:
            raise ValueError(f"Invalid broker URL: {data['broker']}")
        broker = match.group(1)
        port = int(match.group(2))

        self.mqtt = AnycubicMQTT(
            self.hass,
            broker,
            port,
            data["username"],
            data["password"],
            data["modeId"],
            data["deviceId"],
        )
        self.mqtt.on_update = self.async_set_updated_data

        await self.hass.async_add_executor_job(self.mqtt.connect)

    async def _async_reconfigure_mqtt(self, username, password):
        if self.mqtt is None:
            return await self._async_init_mqtt(await self.hass.async_add_executor_job(self.api.discover))
        self.mqtt.client.username_pw_set(username, password)
        await self.hass.async_add_executor_job(self.mqtt.client.reconnect)
