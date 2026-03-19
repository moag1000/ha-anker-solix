"""Local device state cache for BLE-discovered Anker Solix devices.

Persists device configuration and telemetry snapshots to disk so that
the cloud coordinator can bootstrap from last-known data on startup
when the cloud API is unreachable. The cache is JSON-based and stored
in the HA config directory.

The cache is populated whenever BLE is active (device setup, off-grid
use, manual BLE activation). Current Anker firmware disables BLE on
WiFi-connected devices, so the cache may contain data from a previous
BLE session rather than live data.

This is NOT a replacement for the cloud API — it provides stale data
as a last resort when no live data source is available.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Cache structure version (bump when format changes)
_CACHE_VERSION = 1


class BleDeviceCache:
    """Persistent cache for BLE device state.

    Stores per-device:
    - Identity: serial, model, site_id
    - Last known config: min_soc, power_limit, ems_mode, etc.
    - Last telemetry snapshot: power, battery, grid values + timestamp
    - Last schedule: raw schedule data from GET_SCHEDULE response
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files (e.g. hass.config.path()).

        """
        self._cache_dir = cache_dir / "anker_solix_ble"
        self._cache_file = self._cache_dir / "device_cache.json"
        self._data: dict[str, dict[str, Any]] = {}
        self._dirty = False

    def load(self) -> None:
        """Load cache from disk."""
        if not self._cache_file.exists():
            self._data = {}
            return

        try:
            raw = json.loads(self._cache_file.read_text(encoding="utf-8"))
            if raw.get("_version") != _CACHE_VERSION:
                _LOGGER.info(
                    "BLE cache version mismatch (%s vs %s), starting fresh",
                    raw.get("_version"),
                    _CACHE_VERSION,
                )
                self._data = {}
                return
            self._data = raw.get("devices", {})
            _LOGGER.debug("BLE cache loaded: %d devices", len(self._data))
        except (json.JSONDecodeError, OSError):
            _LOGGER.warning("Failed to load BLE cache, starting fresh", exc_info=True)
            self._data = {}

    def save(self) -> None:
        """Save cache to disk (only if dirty)."""
        if not self._dirty:
            return

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "_version": _CACHE_VERSION,
                "_updated": time.time(),
                "devices": self._data,
            }
            self._cache_file.write_text(
                json.dumps(payload, indent=2, default=str),
                encoding="utf-8",
            )
            self._dirty = False
            _LOGGER.debug("BLE cache saved: %d devices", len(self._data))
        except OSError:
            _LOGGER.warning("Failed to save BLE cache", exc_info=True)

    def get_device(self, serial: str) -> dict[str, Any]:
        """Get cached data for a device, or empty dict if unknown."""
        return self._data.get(serial, {})

    def get_all_devices(self) -> dict[str, dict[str, Any]]:
        """Get all cached device data."""
        return dict(self._data)

    def update_identity(
        self,
        serial: str,
        *,
        model: str = "",
        site_id: str = "",
        mac_address: str = "",
    ) -> None:
        """Update device identity information."""
        dev = self._data.setdefault(serial, {})
        identity = dev.setdefault("identity", {})
        if model:
            identity["model"] = model
        if site_id:
            identity["site_id"] = site_id
        if mac_address:
            identity["mac_address"] = mac_address
        identity["serial"] = serial
        self._dirty = True

    def update_config(self, serial: str, config: dict[str, Any]) -> None:
        """Update cached device configuration (min_soc, limits, mode, etc.).

        Args:
            serial: Device serial number.
            config: Dict of config key→value. None values are stored
                to indicate the device didn't respond to that query.

        """
        dev = self._data.setdefault(serial, {})
        cached_config = dev.setdefault("config", {})
        cached_config.update(config)
        cached_config["_timestamp"] = time.time()
        self._dirty = True

    def update_telemetry(self, serial: str, telemetry: dict[str, float | int | str]) -> None:
        """Update cached telemetry snapshot.

        Args:
            serial: Device serial number.
            telemetry: Dict of telemetry field→value from SolixBleDeviceInfo.

        """
        dev = self._data.setdefault(serial, {})
        dev["telemetry"] = {
            **telemetry,
            "_timestamp": time.time(),
        }
        self._dirty = True

    def update_schedule(self, serial: str, schedule_data: dict[str, Any]) -> None:
        """Update cached schedule data.

        Args:
            serial: Device serial number.
            schedule_data: Parsed schedule dict from GET_SCHEDULE response.

        """
        dev = self._data.setdefault(serial, {})
        dev["schedule"] = {
            **schedule_data,
            "_timestamp": time.time(),
        }
        self._dirty = True

    def get_telemetry_age(self, serial: str) -> float:
        """Get age of cached telemetry in seconds. Returns inf if no cache."""
        dev = self._data.get(serial, {})
        ts = dev.get("telemetry", {}).get("_timestamp", 0)
        if ts == 0:
            return float("inf")
        return time.time() - ts

    def get_config_age(self, serial: str) -> float:
        """Get age of cached config in seconds. Returns inf if no cache."""
        dev = self._data.get(serial, {})
        ts = dev.get("config", {}).get("_timestamp", 0)
        if ts == 0:
            return float("inf")
        return time.time() - ts

    def remove_device(self, serial: str) -> None:
        """Remove a device from the cache."""
        if serial in self._data:
            del self._data[serial]
            self._dirty = True
