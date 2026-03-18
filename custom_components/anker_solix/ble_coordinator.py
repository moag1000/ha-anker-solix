"""BLE coordinator for Anker Solix devices.

Provides local BLE communication as a supplemental/fallback data source
alongside the cloud API coordinator. Based on patterns from
beurer_daylight_lamps (moag1000) and SolixBLE (flip-dots).

Data origin: Anker APK v3.18.0 reverse engineering + SolixBLE protocol analysis.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER
from .solixapi.ble.client import SolixBleClient, SolixBleDeviceInfo

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

    from .coordinator import AnkerSolixDataUpdateCoordinator

# Adaptive polling intervals (from beurer_daylight_lamps patterns)
POLL_INTERVAL_ACTIVE: int = 30  # seconds - device actively producing/consuming
POLL_INTERVAL_IDLE: int = 300  # 5 min - device idle/standby
POLL_INTERVAL_UNAVAILABLE: int = 900  # 15 min - device disconnected, retry slowly

# BLE connection limits
MAX_CONCURRENT_CONNECTIONS: int = 3
STALE_DATA_THRESHOLD: int = 600  # 10 min - consider BLE data stale after this


class AnkerSolixBleCoordinator(DataUpdateCoordinator[dict[str, SolixBleDeviceInfo]]):
    """Coordinate BLE communication with Anker Solix devices.

    Manages multiple BLE connections and provides telemetry data
    that supplements the cloud API coordinator.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        cloud_coordinator: AnkerSolixDataUpdateCoordinator | None = None,
    ) -> None:
        """Initialize the BLE coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_ble",
            update_interval=timedelta(seconds=POLL_INTERVAL_ACTIVE),
        )
        self._cloud_coordinator = cloud_coordinator
        self._clients: dict[str, SolixBleClient] = {}
        self._last_telemetry: dict[str, tuple[datetime, SolixBleDeviceInfo]] = {}

    @property
    def available_devices(self) -> set[str]:
        """Return set of MAC addresses with active BLE connections."""
        return {mac for mac, client in self._clients.items() if client.is_connected}

    @property
    def telemetry_data(self) -> dict[str, SolixBleDeviceInfo]:
        """Return latest telemetry data for all connected devices."""
        return {
            mac: info for mac, (_, info) in self._last_telemetry.items()
        }

    def get_device_telemetry(self, mac: str) -> SolixBleDeviceInfo | None:
        """Get latest telemetry for a specific device, or None if stale/missing."""
        if mac not in self._last_telemetry:
            return None
        timestamp, info = self._last_telemetry[mac]
        age = (datetime.now().astimezone() - timestamp).total_seconds()
        if age > STALE_DATA_THRESHOLD:
            LOGGER.debug(
                "BLE telemetry for %s is stale (%.0fs old), returning None",
                mac,
                age,
            )
            return None
        return info

    async def register_device(self, ble_device: BLEDevice) -> bool:
        """Register a discovered BLE device for telemetry polling.

        Returns True if the device was successfully registered.
        """
        mac = ble_device.address
        if mac in self._clients:
            LOGGER.debug("BLE device %s already registered", mac)
            return True

        if len(self.available_devices) >= MAX_CONCURRENT_CONNECTIONS:
            LOGGER.warning(
                "BLE connection limit reached (%d), cannot register %s",
                MAX_CONCURRENT_CONNECTIONS,
                mac,
            )
            return False

        client = SolixBleClient(ble_device, mac)
        client.set_telemetry_callback(self._on_telemetry_update)
        self._clients[mac] = client
        LOGGER.info("Registered BLE device %s for telemetry", mac)
        return True

    async def unregister_device(self, mac: str) -> None:
        """Unregister and disconnect a BLE device."""
        if client := self._clients.pop(mac, None):
            await client.disconnect()
            self._last_telemetry.pop(mac, None)
            LOGGER.info("Unregistered BLE device %s", mac)

    @callback
    def _on_telemetry_update(self, info: SolixBleDeviceInfo) -> None:
        """Handle push telemetry update from BLE notification."""
        # Find which client sent this by matching the serial number
        for mac, client in self._clients.items():
            if client.last_device_info and client.last_device_info.serial_number == info.serial_number:
                self._last_telemetry[mac] = (
                    datetime.now().astimezone(),
                    info,
                )
                break
        else:
            # Fallback: store by serial number if no MAC match
            if info.serial_number:
                self._last_telemetry[info.serial_number] = (
                    datetime.now().astimezone(),
                    info,
                )
        # Push update to cloud coordinator if available
        if self._cloud_coordinator:
            self._push_to_cloud_coordinator(info)
        # Notify our own listeners
        self.async_set_updated_data(self.telemetry_data)

    def _push_to_cloud_coordinator(self, info: SolixBleDeviceInfo) -> None:
        """Build BLE overlay data for potential cloud coordinator integration.

        Maps BLE telemetry fields to the same keys the cloud API uses.
        Currently logs at debug level only. Full integration into cloud
        coordinator data (to supplement entities during cloud outages)
        requires matching device serial numbers to coordinator data keys.

        TODO: Once device SN mapping is established, write overlay into
        self._cloud_coordinator.data[sn] to enable entity fallback.
        """
        if not self._cloud_coordinator or not self._cloud_coordinator.data:
            return

        # Build overlay dict from BLE telemetry
        # Field names from SolixBleDeviceInfo (ble/client.py)
        ble_overlay: dict[str, str | bool] = {}
        if info.battery_percent >= 0:
            ble_overlay["battery_soc"] = str(info.battery_percent)
        if info.solar_power_w > 0:
            ble_overlay["solar_power"] = str(info.solar_power_w)
        if info.ac_power_w > 0:
            ble_overlay["ac_power"] = str(info.ac_power_w)
        if info.battery_temperature >= 0:
            ble_overlay["battery_temperature"] = str(info.battery_temperature)
        if info.total_solar_wh > 0:
            ble_overlay["solar_energy"] = str(info.total_solar_wh)
        if info.total_output_wh > 0:
            ble_overlay["output_energy"] = str(info.total_output_wh)

        if not ble_overlay:
            return

        # Mark data as BLE-sourced for debugging
        ble_overlay["_ble_source"] = True
        ble_overlay["_ble_timestamp"] = datetime.now().astimezone().isoformat()

        LOGGER.debug(
            "BLE overlay for SN %s: %s",
            info.serial_number,
            ble_overlay,
        )

    async def _async_update_data(self) -> dict[str, SolixBleDeviceInfo]:
        """Poll all registered BLE devices for telemetry."""
        results: dict[str, SolixBleDeviceInfo] = {}

        for mac, client in list(self._clients.items()):
            try:
                if not client.is_connected:
                    LOGGER.debug("Attempting BLE connection to %s", mac)
                    if not await client.connect():
                        continue

                # Request telemetry (the client will handle negotiation if needed)
                info = client.last_device_info
                if info:
                    self._last_telemetry[mac] = (
                        datetime.now().astimezone(),
                        info,
                    )
                    results[mac] = info

                    # Push to cloud coordinator
                    if self._cloud_coordinator:
                        self._push_to_cloud_coordinator(info)

            except Exception as err:  # noqa: BLE001
                LOGGER.debug(
                    "BLE poll failed for %s: %s",
                    mac,
                    err,
                )
                # Don't fail the entire update for one device
                continue

        # Adapt polling interval based on activity
        self._adapt_polling_interval(results)

        return results

    def _adapt_polling_interval(
        self, results: dict[str, SolixBleDeviceInfo]
    ) -> None:
        """Adjust polling interval based on device activity.

        Adaptive intervals (from beurer_daylight_lamps patterns):
        - Active (producing/consuming power): 30s
        - Idle (no power flow): 5min
        - Unavailable (no connected devices): 15min
        """
        if not self._clients:
            return

        connected = sum(1 for c in self._clients.values() if c.is_connected)
        if connected == 0:
            new_interval = POLL_INTERVAL_UNAVAILABLE
        elif any(
            (info.solar_power_w and info.solar_power_w > 0)
            or (info.ac_power_w and info.ac_power_w > 0)
            for info in results.values()
        ):
            new_interval = POLL_INTERVAL_ACTIVE
        else:
            new_interval = POLL_INTERVAL_IDLE

        if self.update_interval != timedelta(seconds=new_interval):
            self.update_interval = timedelta(seconds=new_interval)
            LOGGER.debug(
                "BLE polling interval adjusted to %ds (%d connected devices)",
                new_interval,
                connected,
            )

    async def async_shutdown(self) -> None:
        """Disconnect all BLE clients on shutdown."""
        for mac in list(self._clients):
            await self.unregister_device(mac)
        await super().async_shutdown()

    @staticmethod
    def device_matches_solix(service_info: bluetooth.BluetoothServiceInfoBleak) -> bool:
        """Check if a discovered BLE device is an Anker Solix device.

        Matches based on the Solix-specific GATT service UUID used for
        device identification (discovered via APK reverse engineering).
        """
        from .solixapi.ble import UUID_IDENTIFIER  # noqa: PLC0415

        return UUID_IDENTIFIER.lower() in [
            str(uuid).lower() for uuid in service_info.service_uuids
        ]
