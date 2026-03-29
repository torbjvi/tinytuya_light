"""TinyTuya Light platform for Tuya bulbs."""
import logging
from functools import partial
from typing import Any

import tinytuya
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ColorMode,
    LightEntity,
    PLATFORM_SCHEMA,
)
from homeassistant.const import CONF_HOST, CONF_NAME
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL,
    DPS_ON_OFF,
    DPS_MODE,
    DPS_BRIGHTNESS,
    DPS_COLOR_TEMP,
    DPS_COLOR,
    DEV_BRIGHTNESS_MIN,
    DEV_BRIGHTNESS_MAX,
    DEV_CT_MIN,
    DEV_CT_MAX,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_LOCAL_KEY): cv.string,
        vol.Optional(CONF_PROTOCOL, default=3.5): vol.Coerce(float),
        vol.Optional(CONF_NAME, default="TinyTuya Light"): cv.string,
        vol.Optional("min_kelvin", default=2700): int,
        vol.Optional("max_kelvin", default=6500): int,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities(
        [
            TinyTuyaLight(
                hass,
                config[CONF_NAME],
                config[CONF_DEVICE_ID],
                config[CONF_HOST],
                config[CONF_LOCAL_KEY],
                config[CONF_PROTOCOL],
                config["min_kelvin"],
                config["max_kelvin"],
            )
        ]
    )


class TinyTuyaLight(LightEntity):
    """A Tuya light controlled via tinytuya."""

    def __init__(self, hass, name, device_id, host, local_key, protocol, min_k, max_k):
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = f"tinytuya_{device_id}"
        self._device_id = device_id
        self._host = host
        self._local_key = local_key
        self._protocol = protocol
        self._attr_is_on = None
        self._attr_brightness = None
        self._attr_color_temp_kelvin = None
        self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
        self._attr_color_mode = ColorMode.COLOR_TEMP
        self._attr_min_color_temp_kelvin = min_k
        self._attr_max_color_temp_kelvin = max_k
        self._device = None

    def _new_device(self):
        dev = tinytuya.BulbDevice(self._device_id, self._host, self._local_key)
        dev.set_version(self._protocol)
        dev.set_socketTimeout(5)
        return dev

    def _get_device(self):
        if self._device is None:
            self._device = self._new_device()
        return self._device

    def _do_send(self, dps_values: dict):
        try:
            self._get_device().set_multiple_values(dps_values)
        except Exception:
            self._device = None
            try:
                self._get_device().set_multiple_values(dps_values)
            except Exception:
                _LOGGER.exception("Failed to send to %s", self._attr_name)

    def _do_status(self):
        try:
            return self._get_device().status()
        except Exception:
            self._device = None
            try:
                return self._get_device().status()
            except Exception:
                _LOGGER.debug("Failed to poll %s", self._attr_name)
                return None

    def _kelvin_to_dev(self, kelvin):
        """Convert kelvin to device color temp (0=warm/2700K, 1000=cold/6500K)."""
        ratio = (kelvin - self._attr_min_color_temp_kelvin) / (
            self._attr_max_color_temp_kelvin - self._attr_min_color_temp_kelvin
        )
        return max(DEV_CT_MIN, min(DEV_CT_MAX, int(ratio * DEV_CT_MAX)))

    def _dev_to_kelvin(self, dev_ct):
        """Convert device color temp to kelvin (0=warm/2700K, 1000=cold/6500K)."""
        ratio = dev_ct / DEV_CT_MAX
        return int(
            self._attr_min_color_temp_kelvin
            + ratio
            * (self._attr_max_color_temp_kelvin - self._attr_min_color_temp_kelvin)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        dps = {DPS_ON_OFF: True}

        if ATTR_BRIGHTNESS in kwargs:
            ha_bri = kwargs[ATTR_BRIGHTNESS]
            dps[DPS_BRIGHTNESS] = max(
                DEV_BRIGHTNESS_MIN,
                min(DEV_BRIGHTNESS_MAX, int(ha_bri * DEV_BRIGHTNESS_MAX / 255)),
            )

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            dps[DPS_COLOR_TEMP] = self._kelvin_to_dev(kwargs[ATTR_COLOR_TEMP_KELVIN])

        await self.hass.async_add_executor_job(partial(self._do_send, dps))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            partial(self._do_send, {DPS_ON_OFF: False})
        )

    async def async_update(self) -> None:
        status = await self.hass.async_add_executor_job(self._do_status)
        if status is None:
            return

        dps = status.get("dps", {})
        if not dps:
            error = status.get("Error")
            if error:
                _LOGGER.warning("Device %s: %s", self._attr_name, error)
                self._device = None
            return

        self._attr_is_on = dps.get(DPS_ON_OFF, self._attr_is_on)

        dev_bri = dps.get(DPS_BRIGHTNESS)
        if dev_bri is not None:
            self._attr_brightness = max(
                1, min(255, int(dev_bri * 255 / DEV_BRIGHTNESS_MAX))
            )

        dev_ct = dps.get(DPS_COLOR_TEMP)
        if dev_ct is not None:
            self._attr_color_temp_kelvin = self._dev_to_kelvin(dev_ct)
