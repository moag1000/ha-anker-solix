"""BLE coordinator for Anker Solix devices.

Provides local BLE communication as a supplemental/fallback data source
alongside the cloud API coordinator. Based on patterns from
beurer_daylight_lamps (moag1000) and SolixBLE (flip-dots).

IMPORTANT LIMITATION: All reference projects (SolixBLE, AnkerSolixBLE,
HaSolixBLE) confirm that BLE and WiFi are mutually exclusive on current
Anker firmware. WiFi-connected devices disable BLE. This coordinator is
primarily useful for:
  - Off-grid / portable devices (no WiFi)
  - Initial device setup (before WiFi provisioning)
  - Manual BLE re-activation (IoT button press)
  - Future firmware with BLE+WiFi dual-mode support (unconfirmed)

The persistent cache (BleDeviceCache) retains data from previous BLE
sessions, providing degraded-mode data even when BLE is currently unavailable.

Data origin: Anker APK v3.18.0 reverse engineering + SolixBLE protocol analysis.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER
from .solixapi.ble.cache import BleDeviceCache
from .solixapi.ble.client import SolixBleClient, SolixBleDeviceInfo

if TYPE_CHECKING:
    from homeassistant.components import bluetooth
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
        config_dir: Path | None = None,
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

        # Persistent local cache for degraded-mode operation
        cache_path = config_dir or Path(hass.config.config_dir)
        self._cache = BleDeviceCache(cache_path)
        self._cache.load()

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
        # Cache telemetry snapshot for degraded-mode operation
        if info.serial_number:
            self._cache_telemetry(info)

        # Push update to cloud coordinator if available
        if self._cloud_coordinator:
            self._push_to_cloud_coordinator(info)
        # Notify our own listeners
        self.async_set_updated_data(self.telemetry_data)

    def _push_to_cloud_coordinator(self, info: SolixBleDeviceInfo) -> None:
        """Write BLE telemetry into cloud coordinator data for entity fallback.

        Maps BLE telemetry fields to the same dict keys that cloud API uses
        (verified against sensor.py DEVICE_SENSORS json_key values).
        When the cloud API is unavailable, existing HA entities will show
        BLE-sourced data instead of going unavailable.

        Data is written into self._cloud_coordinator.data[serial_number]
        which is a dict keyed by device serial number.
        """
        if not self._cloud_coordinator or not self._cloud_coordinator.data:
            return

        sn = info.serial_number
        if not sn:
            return

        if sn not in self._cloud_coordinator.data:
            # Device not in cloud data — create a minimal entry so entities
            # can be created from BLE data during cloud outage
            LOGGER.info(
                "BLE device SN %s not in cloud data, creating stub entry (known: %s)",
                sn,
                list(self._cloud_coordinator.data.keys())[:5],
            )
            self._cloud_coordinator.data[sn] = {
                "type": "device",
                "device_sn": sn,
                "name": f"Solix {sn[-4:]}",
                "status_desc": "ble_only",
                "_ble_source": True,
            }

        # Build overlay using exact keys from sensor.py DEVICE_SENSORS
        ble_overlay: dict[str, str | bool] = {}
        if info.battery_percent >= 0:
            ble_overlay["battery_soc"] = str(info.battery_percent)
        if info.solar_power_w > 0:
            ble_overlay["solar_power_1"] = str(info.solar_power_w)
        if info.ac_power_w > 0:
            ble_overlay["ac_power"] = str(info.ac_power_w)
        if info.battery_temperature > -40.0:
            ble_overlay["temperature"] = str(info.battery_temperature)
        if info.discharge_power_w > 0:
            ble_overlay["bat_discharge_power"] = str(info.discharge_power_w)
        if info.battery_charge_power_w > 0:
            ble_overlay["bat_charge_power"] = str(info.battery_charge_power_w)
        # Per-MPPT solar (keys match sensor.py: solar_power_1..4)
        for i, pv_w in enumerate(
            [info.solar_pv1_power_w, info.solar_pv2_power_w,
             info.solar_pv3_power_w, info.solar_pv4_power_w], 1
        ):
            if pv_w > 0:
                ble_overlay[f"solar_power_{i}"] = str(pv_w)
        # SB2 Pro grid/consumption fields
        if info.grid_to_home_power_w > 0:
            ble_overlay["grid_to_home_power"] = str(info.grid_to_home_power_w)
        if info.pv_to_grid_power_w > 0:
            ble_overlay["photovoltaic_to_grid_power"] = str(info.pv_to_grid_power_w)
        if info.house_demand_w > 0:
            ble_overlay["home_load_power"] = str(info.house_demand_w)
        if info.power_out_w > 0:
            ble_overlay["output_power"] = str(info.power_out_w)
        # Energy fields (BLE provides Wh, cloud uses kWh)
        if info.grid_import_energy_wh > 0:
            ble_overlay["grid_import_energy"] = str(info.grid_import_energy_wh / 1000.0)
        if info.grid_export_energy_wh > 0:
            ble_overlay["grid_export_energy"] = str(info.grid_export_energy_wh / 1000.0)
        if info.consumed_energy_wh > 0:
            ble_overlay["consumed_energy"] = str(info.consumed_energy_wh / 1000.0)

        if not ble_overlay:
            return

        # Mark data as BLE-sourced for debugging
        ble_overlay["_ble_source"] = True
        ble_overlay["_ble_timestamp"] = datetime.now().astimezone().isoformat()

        # Write into cloud coordinator data dict
        self._cloud_coordinator.data[sn].update(ble_overlay)
        LOGGER.debug(
            "BLE overlay written for SN %s (%d fields)",
            sn,
            len(ble_overlay) - 2,  # exclude _ble_source and _ble_timestamp
        )

    def _cache_telemetry(self, info: SolixBleDeviceInfo) -> None:
        """Write telemetry snapshot to the persistent cache."""
        sn = info.serial_number
        if not sn:
            return
        self._cache.update_identity(sn, mac_address=self._mac_for_serial(sn))
        self._cache.update_telemetry(sn, {
            "battery_soc": info.battery_percent,
            "solar_power": info.solar_power_w,
            "ac_power": info.ac_power_w,
            "battery_temperature": info.battery_temperature,
            "discharge_power": info.discharge_power_w,
            "charge_power": info.battery_charge_power_w,
            "grid_to_home_power": info.grid_to_home_power_w,
            "pv_to_grid_power": info.pv_to_grid_power_w,
            "house_demand": info.house_demand_w,
            "power_out": info.power_out_w,
        })
        # Periodic save (dirty flag ensures no-op if nothing changed)
        self._cache.save()

    async def _query_and_cache_config(self, mac: str) -> None:
        """Query device config via BLE and cache it.

        Called after a successful BLE connection to populate the cache
        with current device settings.
        """
        client = self._clients.get(mac)
        if not client or not client.is_connected:
            return

        sn = client.last_device_info.serial_number if client.last_device_info else None
        if not sn:
            LOGGER.debug("Cannot query config for %s: no serial number yet", mac)
            return

        LOGGER.debug("Querying device config via BLE for %s (%s)", sn, mac)
        try:
            config = await client.async_query_device_config()
            # Filter out None values (unsupported commands)
            valid_config: dict[str, Any] = {
                k: v for k, v in config.items() if v is not None
            }
            if valid_config:
                self._cache.update_config(sn, valid_config)
                self._cache.save()
                LOGGER.info(
                    "Cached BLE config for %s: %s",
                    sn,
                    list(valid_config.keys()),
                )
        except Exception:  # noqa: BLE001
            LOGGER.debug("Failed to query BLE config for %s", sn, exc_info=True)

    def _mac_for_serial(self, serial: str) -> str:
        """Find the MAC address associated with a serial number."""
        for mac, client in self._clients.items():
            if client.last_device_info and client.last_device_info.serial_number == serial:
                return mac
        return ""

    def get_cached_device(self, serial: str) -> dict[str, Any]:
        """Get cached data for a device (for degraded-mode operation).

        Returns the full cache entry including identity, config, telemetry,
        and schedule. Returns empty dict if device is unknown.
        """
        return self._cache.get_device(serial)

    async def _async_update_data(self) -> dict[str, SolixBleDeviceInfo]:
        """Poll all registered BLE devices for telemetry."""
        results: dict[str, SolixBleDeviceInfo] = {}

        for mac, client in list(self._clients.items()):
            try:
                was_disconnected = not client.is_connected
                if not client.is_connected:
                    LOGGER.debug("Attempting BLE connection to %s", mac)
                    if not await client.connect():
                        continue

                # On fresh connection, query and cache device config
                if was_disconnected and client.is_connected:
                    await self._query_and_cache_config(mac)

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
        """Disconnect all BLE clients and save cache on shutdown."""
        self._cache.save()
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
