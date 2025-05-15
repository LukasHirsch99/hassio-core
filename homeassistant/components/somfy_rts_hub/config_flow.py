"""Somfy RTS Config Flow."""

import logging
from typing import Any

from somfyrtshub import Hub
from somfyrtshub.errors import HubException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SomfyRtsHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SomfyRtsHub config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Create SomfyRtsHubConfigFlow instance."""
        self.discovery_info: ZeroconfServiceInfo

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options-flow-handler."""
        return SomfyRtsHubOptionsFlowHandler()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle Zeroconf discovery."""

        self.discovery_info = discovery_info

        await self.async_set_unique_id("somfy-rts-hub")
        self._abort_if_unique_id_configured()

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input=None
    ) -> config_entries.ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title="Somfy RTS Hub",
                data={
                    CONF_HOST: self.discovery_info.hostname,
                    CONF_PORT: self.discovery_info.port,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                CONF_HOST: "Host",
                CONF_PORT: "Port",
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self.discovery_info.hostname
                    ): cv.string,
                    vol.Required(
                        CONF_PORT, default=self.discovery_info.port
                    ): cv.positive_int,
                }
            ),
        )

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle manual setup via UI (optional)."""
        if user_input is not None:
            return self.async_create_entry(title="Somfy RTS Hub", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_PORT, default=42069): cv.positive_int,
                }
            ),
        )


class SomfyRtsHubOptionsFlowHandler(config_entries.OptionsFlow):
    """SomfyRtsHub options flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Create OptionsFlowHandler."""
        self._rename_remote_id: int

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show dialog for configuring integration."""
        if user_input is not None:
            if user_input["action"] == "add":
                return await self.async_step_add()
            if user_input["action"] == "rename":
                return await self.async_step_select_for_rename()
            if user_input["action"] == "remove":
                return await self.async_step_select_for_removal()
            if user_input["action"] == "getCovers":
                return await self.async_step_get_covers()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): vol.In(
                        {
                            "add": "Add cover",
                            "rename": "Rename cover",
                            "remove": "Remove cover",
                            "getCovers": "Get a list of all covers safed on the hub.",
                        }
                    )
                }
            ),
        )

    async def async_step_get_covers(
        self, user_input=None
    ) -> config_entries.ConfigFlowResult:
        """Show all covers saved on the hub."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})

        api: Hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["api"]

        try:
            covers = await api.getAllCovers()
        except HubException as e:
            _LOGGER.error(e)
            return self.async_abort(reason=e.args)

        text = "\n".join(
            f"- {c.name} remoteId: {c.remoteId}, rc: {c.rollingCode}" for c in covers
        )

        return self.async_show_form(
            step_id="get_covers",
            data_schema=vol.Schema({}),
            description_placeholders={"controller_list": text},
        )

    async def async_step_add(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Show add cover dialog."""
        if user_input is None:
            return self.async_show_form(
                step_id="add",
                data_schema=vol.Schema(
                    {
                        vol.Required("name"): cv.string,
                        vol.Optional("remote_id"): cv.positive_int,
                        vol.Optional("rolling_code"): cv.positive_int,
                    }
                ),
            )

        name = user_input["name"]
        remote_id = user_input.get("remote_id", 0)
        rolling_code = user_input.get("rolling_code", 0)

        api: Hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["api"]

        try:
            await api.addCover(name, remote_id, rolling_code)
        except HubException as e:
            _LOGGER.error(e)
            return self.async_abort(reason=e.args)

        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

        return self.async_create_entry(title="Cover Added", data={})

    async def async_step_select_for_rename(
        self, user_input=None
    ) -> config_entries.ConfigFlowResult:
        """Select cover for renaming."""
        api: Hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["api"]
        try:
            covers = await api.getAllCovers()
        except HubException as e:
            _LOGGER.error(e)
            return self.async_abort(reason=e)

        name_map = {c.name: c.remoteId for c in covers}

        if user_input is not None:
            self._rename_remote_id = name_map[user_input["cover"]]
            return await self.async_step_rename()

        return self.async_show_form(
            step_id="select_for_rename",
            data_schema=vol.Schema(
                {vol.Required("cover"): vol.In(list(name_map.keys()))}
            ),
        )

    async def async_step_rename(
        self, user_input=None
    ) -> config_entries.ConfigFlowResult:
        """Rename cover."""
        if user_input is not None:
            new_name = user_input["new_name"]

            api: Hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["api"]
            try:
                await api.renameCover(self._rename_remote_id, new_name)
            except HubException as e:
                _LOGGER.error(e)
                return self.async_abort(reason=e)

            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="rename",
            data_schema=vol.Schema({vol.Required("new_name"): cv.string}),
        )

    async def async_step_select_for_removal(
        self, user_input=None
    ) -> config_entries.ConfigFlowResult:
        """Select cover for removal."""
        api: Hub = self.hass.data[DOMAIN][self.config_entry.entry_id]["api"]
        try:
            covers = await api.getAllCovers()
        except HubException as e:
            _LOGGER.error(e)
            return self.async_abort(reason=e)

        cover_map = {c.name: c.remoteId for c in covers}

        if user_input is not None:
            try:
                await api.removeCover(cover_map[user_input["cover"]])
            except HubException as e:
                _LOGGER.error(e)
                return self.async_abort(reason=e)

            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="select_for_removal",
            data_schema=vol.Schema(
                {vol.Required("cover"): vol.In(list(cover_map.keys()))}
            ),
        )
