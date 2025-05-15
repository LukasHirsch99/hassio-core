"""Somfy RTS Hub integration."""

import logging

from somfyrtshub import Hub

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Safe metadata and forward the setup to cover.py."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": Hub(entry.data["host"], int(entry.data["port"])),
        "host": entry.data["host"],
        "port": entry.data["port"],
    }
    entry.runtime_data = {}

    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    return await hass.config_entries.async_unload_platforms(entry, [Platform.COVER])


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of a config entry."""

    # Example: Clean up API instance or unregister listeners
    if entry.entry_id in hass.data[DOMAIN]:
        # api = hass.data[DOMAIN][entry.entry_id]["api"]
        # await api.close()  # or your own cleanup logic
        hass.data[DOMAIN].pop(entry.entry_id)
