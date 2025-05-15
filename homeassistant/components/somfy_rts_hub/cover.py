"""Cover Platform."""

import logging
from typing import Any

from somfyrtshub import Cover as SomfyApiCover, Hub
from somfyrtshub.errors import HubException
import voluptuous as vol

from homeassistant.components.cover import (
    PLATFORM_SCHEMA as COVER_PLATFORM_SCHEMA,
    CoverEntity,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# Validation of the user's configuration
PLATFORM_SCHEMA = COVER_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.positive_int,
    }
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create cover entities for covers saved on ESP."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api: Hub = data["api"]

    try:
        covers = await api.getAllCovers()
    except HubException as e:
        _LOGGER.error(e)
        raise ConfigEntryError(e) from e

    existing_entity_ids = [str(c.remoteId) for c in covers]

    # fetch current known entities from entity registry
    entity_registry = er.async_get(hass)
    known_entities = er.async_entries_for_config_entry(
        entity_registry, config_entry.entry_id
    )

    for entry in known_entities:
        entity_id = entry.entity_id
        if entity_id.split(".")[1] not in existing_entity_ids:
            _LOGGER.debug("Removing orphaned entity: %s", entity_id)
            entity_registry.async_remove(entity_id)
            hass.states.async_remove(entity_id)

    async_add_entities(SomfyCover(cover) for cover in covers)


class SomfyCover(CoverEntity):
    """Somfy Cover Entity."""

    def __init__(self, cover: SomfyApiCover) -> None:
        """Initialize a SomfyCover."""
        self._cover = cover
        self._name = cover.name
        self._remoteId = cover.remoteId

        self._attr_is_closed = None
        self._attr_name = cover.name
        self._attr_unique_id = f"somfy_{cover.remoteId}"
        self.entity_id = f"cover.{cover.remoteId}"

    @property
    def name(self) -> str:
        """Return the display name of this cover."""
        return self._name

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, "somfy-hub")},
            "name": "Somfy RTS Hub",
            "model": "Somfy RTS Hub",
        }

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Instruct the cover to close."""
        await self._cover.open()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Instruct the cover to open."""
        await self._cover.close()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._cover.stop()

    @property
    def is_closed(self):
        """Returns always None because covers are stateless."""
        return None  # This makes the cover stateless

    @property
    def current_cover_position(self):
        """Returns always None because covers are stateless."""
        return None

    @property
    def assumed_state(self):
        """Returns True because covers are stateless."""
        return True
