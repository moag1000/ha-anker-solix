"""Anker Solix BLE client for direct device communication.

Handles GATT connection, ECDH negotiation, encrypted command exchange,
and telemetry reception.

Connection flow:
    1. Discover devices via HA bluetooth stack or manual scan (UUID_IDENTIFIER)
    2. Connect via bleak-retry-connector (with retry + multi-adapter support)
    3. Subscribe to UUID_TELEMETRY notifications
    4. Run 6-stage ECDH negotiation handshake
    5. Send/receive encrypted commands via UUID_COMMAND
    6. Receive and reassemble fragmented telemetry data

Credits:
    - BLE protocol + TLV telemetry parsing: SolixBLE by @flip-dots
      https://github.com/flip-dots/SolixBLE
    - Data structure validation: AnkerSolixBLE by @thomluther
      https://github.com/thomluther/AnkerSolixBLE
    - Connection patterns (bleak-retry-connector, backoff): beurer_daylight_lamps by @moag1000
      https://github.com/moag1000/beurer_daylight_lamps
    - Endpoint discovery: Anker APK v3.18.0 reverse engineering
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from . import (
    BASE_TIMESTAMP,
    NEGOTIATION_COMMANDS,
    NEGOTIATION_RESPONSE_TIMEOUT,
    NEGOTIATION_TIMEOUT,
    PACKET_HEADER,
    PATTERN_COMMAND,
    PATTERN_NEGOTIATION,
    PATTERN_TELEMETRY,
    TLV_AC_POWER,
    TLV_AC_SOCKETS,
    TLV_BATTERY_PCT,
    TLV_BATTERY_PCT_AGG,
    TLV_CHARGE_POWER,
    TLV_CHARGED_ENERGY,
    TLV_CONSUMED_ENERGY,
    TLV_DISCHARGE_POWER,
    TLV_GRID_EXPORT,
    TLV_GRID_IMPORT,
    TLV_GRID_TO_HOME,
    TLV_HOUSE_DEMAND,
    TLV_OUTPUT_ENERGY,
    TLV_POWER_OUT,
    TLV_PV1_POWER,
    TLV_PV2_POWER,
    TLV_PV3_POWER,
    TLV_PV4_POWER,
    TLV_PV_TO_GRID,
    TLV_PV_YIELD,
    TLV_SERIAL,
    TLV_SOLAR_POWER,
    TLV_SW_VERSION,
    TLV_SW_VERSION_CTRL,
    TLV_SW_VERSION_EXP,
    TLV_TEMPERATURE,
    UUID_COMMAND,
    UUID_IDENTIFIER,
    UUID_TELEMETRY,
)
from .crypto import BleSessionKeys, aes_decrypt_raw, aes_encrypt, compute_session_keys
from .tlv import (
    Opcodes,
    TlvCommand,
    TlvField,
    cmd_get_ac_limit,
    cmd_get_backup_mode,
    cmd_get_battery_info,
    cmd_get_device_info,
    cmd_get_ems_mode,
    cmd_get_grid_export,
    cmd_get_grid_state,
    cmd_get_min_soc,
    cmd_get_output_mode,
    cmd_get_power_info,
    cmd_get_power_limit,
    cmd_get_pv_limit,
    cmd_get_schedule,
    cmd_get_zero_export,
    cmd_set_ac_limit,
    cmd_set_ems_mode,
    cmd_set_min_soc,
    cmd_set_output_power_limit,
    cmd_set_pv_limit,
    cmd_set_zero_export,
    decode_tlv_response,
    fields_to_dict,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Reconnection parameters (inspired by beurer_daylight_lamps)
RECONNECT_INITIAL_BACKOFF = 3.0
RECONNECT_MAX_BACKOFF = 120.0
RECONNECT_BACKOFF_MULTIPLIER = 2.0
MAX_CONNECT_ATTEMPTS = 5


@dataclass
class SolixBleDeviceInfo:
    """Parsed telemetry data from a Solix BLE device.

    Fields map to TLV keys from the decrypted 253-byte telemetry blob.
    Scaling factors verified against flip-dots/SolixBLE (Python, little-endian).
    """

    # Identity
    serial_number: str = ""  # TLV key 0xa2

    # Battery
    battery_percent: int = -1  # TLV key 0xa3
    battery_percent_aggregate: int = -1  # TLV key 0xad (avg across all batteries)
    battery_temperature: float = -1.0  # TLV key 0xaa (signed, °C)
    battery_charge_power_w: float = 0.0  # TLV key 0xb0 (raw/100 = W)
    discharge_power_w: float = 0.0  # TLV key 0xb7 (raw/100 = W)
    battery_energy_wh: float = 0.0  # TLV key 0xb2 (raw/10 = Wh)

    # Solar
    solar_power_w: float = 0.0  # TLV key 0xab (raw/10 = W, total)
    solar_pv1_power_w: float = 0.0  # TLV key 0xca (raw/10 = W, MPPT 1)
    solar_pv2_power_w: float = 0.0  # TLV key 0xcb (raw/10 = W, MPPT 2)
    solar_pv3_power_w: float = 0.0  # TLV key 0xcc (raw/10 = W, MPPT 3)
    solar_pv4_power_w: float = 0.0  # TLV key 0xcd (raw/10 = W, MPPT 4)
    total_solar_wh: float = 0.0  # TLV key 0xb1 (raw/10 = Wh)

    # Output / consumption
    ac_power_w: float = 0.0  # TLV key 0xac (raw/10 = W)
    ac_power_out_sockets_w: float = 0.0  # TLV key 0xc8 (raw/10 = W, pass-through)
    power_out_w: float = 0.0  # TLV key 0xd3 (raw/10 = W)
    total_output_wh: float = 0.0  # TLV key 0xb3 (raw/10 = Wh)
    house_demand_w: float = 0.0  # TLV key 0xc4 (raw/10 = W)
    consumed_energy_wh: float = 0.0  # TLV key 0xc9 (raw/10 = Wh)

    # Grid
    grid_to_home_power_w: float = 0.0  # TLV key 0xbc (raw/10 = W)
    pv_to_grid_power_w: float = 0.0  # TLV key 0xbd (raw/10 = W)
    grid_import_energy_wh: float = 0.0  # TLV key 0xbe (raw/10 = Wh)
    grid_export_energy_wh: float = 0.0  # TLV key 0xbf (raw/10 = Wh)

    # Firmware
    software_version: str = ""  # TLV key 0xa6
    software_version_controller: str = ""  # TLV key 0xa7
    software_version_expansion: str = ""  # TLV key 0xa8


def xor_checksum(data: bytes) -> bytes:
    """Calculate XOR checksum over all bytes."""
    result = 0
    for b in data:
        result ^= b
    return result.to_bytes(1)


async def discover_solix_devices(
    timeout: float = 5.0,
) -> list[BLEDevice]:
    """Scan for Anker Solix BLE devices nearby.

    Discovers devices that advertise the UUID_IDENTIFIER service.
    For HA integrations, prefer using async_discovered_service_info() instead.

    Args:
        timeout: Scan duration in seconds.

    Returns:
        List of discovered BLEDevice objects.

    """
    devices: list[BLEDevice] = []

    def _callback(device: BLEDevice, advertising_data: Any) -> None:
        if UUID_IDENTIFIER in advertising_data.service_uuids and device not in devices:
            devices.append(device)
            _LOGGER.debug("Discovered Solix device: %s (%s)", device.name, device.address)

    scanner = BleakScanner(detection_callback=_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return devices


class SolixBleClient:
    """BLE client for communicating with Anker Solix devices.

    Manages the full lifecycle: connection, ECDH negotiation,
    encrypted command exchange, and telemetry reception.

    Uses bleak-retry-connector for robust connection management
    with automatic retries and multi-adapter support (including
    ESPHome/Shelly BLE proxies in Home Assistant).
    """

    def __init__(
        self,
        device: BLEDevice,
        mac_address: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the BLE client.

        Args:
            device: BLEDevice from discovery or HA bluetooth stack.
            mac_address: MAC address string (for reconnection via ble_device_callback).
            logger: Optional logger instance.

        """
        self._device = device
        self._mac = mac_address or (device.address if isinstance(device, BLEDevice) else str(device))
        self._logger = logger or _LOGGER
        self._client: BleakClient | None = None
        self._session_keys: BleSessionKeys | None = None
        self._negotiated = False
        self._negotiation_timestamp: float = 0.0
        self._negotiation_stage = 0
        self._ble_available = True
        self._reconnect_lock = asyncio.Lock()

        # Last parsed telemetry
        self._last_device_info: SolixBleDeviceInfo | None = None

        # Telemetry reassembly buffers
        self._telemetry_large: bytes | None = None
        self._telemetry_small: bytes | None = None

        # Callbacks
        self._telemetry_callback: Callable[[SolixBleDeviceInfo], Any] | None = None
        self._state_callback: Callable[[bool], Any] | None = None
        self._update_callback: Callable[[], Any] | None = None

        # Response listener for command replies
        self._pending_response: asyncio.Future[tuple[bytes, bytes]] | None = None
        self._pending_cmd: bytes | None = None

        # Connection health metrics (inspired by beurer_daylight_lamps)
        self._reconnect_count: int = 0
        self._command_success_count: int = 0
        self._command_failure_count: int = 0

    @property
    def is_connected(self) -> bool:
        """Return True if connected and negotiated."""
        return self._client is not None and self._client.is_connected and self._negotiated

    @property
    def ble_available(self) -> bool:
        """Return True if BLE device is reachable."""
        return self._ble_available

    @property
    def last_device_info(self) -> SolixBleDeviceInfo | None:
        """Return the most recently parsed telemetry data."""
        return self._last_device_info

    @property
    def reconnect_count(self) -> int:
        """Return number of reconnections since startup."""
        return self._reconnect_count

    def update_ble_device(self, device: BLEDevice) -> None:
        """Update the BLE device reference (e.g. after adapter change).

        Called by HA bluetooth callbacks when the device is rediscovered
        on a different adapter or proxy.
        """
        self._device = device
        self._ble_available = True

    def set_ble_unavailable(self) -> None:
        """Mark the BLE device as unreachable."""
        self._ble_available = False

    def set_telemetry_callback(self, callback: Callable[[SolixBleDeviceInfo], Any]) -> None:
        """Set callback for telemetry updates."""
        self._telemetry_callback = callback

    def set_state_callback(self, callback: Callable[[bool], Any]) -> None:
        """Set callback for connection state changes."""
        self._state_callback = callback

    def set_update_callback(self, callback: Callable[[], Any]) -> None:
        """Set callback for push data updates (triggers coordinator refresh)."""
        self._update_callback = callback

    async def connect(self) -> bool:
        """Connect to the device and perform ECDH negotiation.

        Uses bleak-retry-connector's establish_connection for robust
        connection with automatic retries and multi-adapter support.

        Returns:
            True if connection and negotiation succeeded.

        """
        try:
            self._client = await establish_connection(
                BleakClient,
                self._device,
                self._mac,
                disconnected_callback=self._on_disconnect,
                max_attempts=MAX_CONNECT_ATTEMPTS,
            )
            self._logger.info("BLE connected to %s", self._mac)

            # Subscribe to telemetry notifications
            await self._client.start_notify(UUID_TELEMETRY, self._on_notification)

            # Perform ECDH negotiation
            success = await self._negotiate()
            if success:
                self._negotiated = True
                self._negotiation_timestamp = time.time()
                if self._state_callback:
                    self._state_callback(True)
                self._logger.info("BLE negotiation complete with %s", self._mac)
            return success

        except Exception:
            self._logger.exception("BLE connection failed to %s", self._mac)
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        self._negotiated = False
        self._session_keys = None
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception:
                self._logger.debug("Error during BLE disconnect", exc_info=True)
        self._client = None

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle unexpected disconnection.

        Triggers auto-reconnection if the device is still BLE-reachable.
        """
        self._logger.warning("BLE device disconnected: %s", self._mac)
        self._negotiated = False
        if self._state_callback:
            self._state_callback(False)
        # Auto-reconnect if device is still reachable
        if self._ble_available:
            asyncio.get_running_loop().create_task(self._auto_reconnect())

    async def _auto_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff.

        Pattern adapted from beurer_daylight_lamps integration.
        """
        if self._reconnect_lock.locked():
            return  # Already reconnecting

        async with self._reconnect_lock:
            backoff = RECONNECT_INITIAL_BACKOFF
            while self._ble_available and not self.is_connected:
                self._logger.debug(
                    "BLE reconnect attempt in %.1fs for %s", backoff, self._mac
                )
                await asyncio.sleep(backoff)

                if not self._ble_available:
                    break

                if await self.connect():
                    self._reconnect_count += 1
                    self._logger.info("BLE reconnected to %s (count: %d)", self._mac, self._reconnect_count)
                    return

                backoff = min(backoff * RECONNECT_BACKOFF_MULTIPLIER, RECONNECT_MAX_BACKOFF)

            self._logger.warning("BLE reconnect gave up for %s (device unavailable)", self._mac)

    async def _negotiate(self) -> bool:
        """Perform the 6-stage ECDH negotiation handshake.

        Sends negotiation commands and waits for device responses.
        Stage 5 extracts the device's ECDH public key for shared secret computation.

        Returns:
            True if negotiation completed successfully.

        """
        self._negotiation_stage = 0
        negotiation_event = asyncio.Event()

        async def _wait_for_stage(target_stage: int, timeout: float) -> bool:
            """Wait until negotiation reaches target stage."""
            try:
                deadline = time.time() + timeout
                while self._negotiation_stage < target_stage and time.time() < deadline:
                    negotiation_event.clear()
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    with contextlib.suppress(asyncio.TimeoutError):
                        await asyncio.wait_for(negotiation_event.wait(), timeout=min(remaining, 2.0))
                return self._negotiation_stage >= target_stage
            except Exception:
                self._logger.exception("Negotiation wait error")
                return False

        self._negotiation_event = negotiation_event

        try:
            if not self._client or not self._client.is_connected:
                return False
            await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[0])
            self._logger.debug("Sent negotiation command 0")

            if not await _wait_for_stage(6, NEGOTIATION_TIMEOUT):
                self._logger.error(
                    "BLE negotiation timed out at stage %d", self._negotiation_stage
                )
                return False

            return self._session_keys is not None

        except Exception:
            self._logger.exception("BLE negotiation failed")
            return False
        finally:
            self._negotiation_event = None  # type: ignore[assignment]

    def _on_notification(self, sender: Any, data: bytearray) -> None:
        """Handle incoming BLE notifications.

        Routes data to negotiation handler or telemetry parser.
        """
        try:
            packet = bytes(data)
            pattern, cmd, payload = self._split_packet(packet)

            pattern_hex = pattern.hex()
            cmd_hex = cmd.hex()

            if pattern_hex == PATTERN_NEGOTIATION.hex():
                asyncio.get_running_loop().create_task(
                    self._handle_negotiation_response(cmd, payload)
                )
            elif pattern_hex == PATTERN_TELEMETRY.hex() and cmd_hex == "c402":
                self._handle_telemetry_fragment(payload)
            elif pattern_hex == PATTERN_COMMAND.hex():
                if self._pending_response and not self._pending_response.done() and self._pending_cmd == cmd:
                    self._pending_response.set_result((cmd, payload))

        except Exception:
            self._logger.debug("Failed to process BLE notification", exc_info=True)

    def _split_packet(self, packet: bytes) -> tuple[bytes, bytes, bytes]:
        """Validate and split a raw BLE packet.

        Format: [FF09][Length 2B LE][Pattern 3B][Cmd 2B][Payload...][Checksum 1B]

        Returns:
            Tuple of (pattern, command, payload).

        """
        if len(packet) < 9:
            msg = f"Packet too short ({len(packet)} bytes)"
            raise ValueError(msg)

        buf = bytearray(packet)

        header = bytes([buf.pop(0), buf.pop(0)])
        if header != PACKET_HEADER:
            msg = f"Invalid header: {header.hex()} (expected ff09)"
            raise ValueError(msg)

        encoded_len = int.from_bytes(bytes([buf.pop(0), buf.pop(0)]), byteorder="little")
        if encoded_len != len(packet):
            msg = f"Length mismatch: encoded={encoded_len}, actual={len(packet)}"
            raise ValueError(msg)

        checksum_byte = buf.pop(-1).to_bytes(1)
        if checksum_byte != xor_checksum(packet[:-1]):
            msg = "Checksum invalid"
            raise ValueError(msg)

        pattern = bytes([buf.pop(0) for _ in range(3)])
        cmd = bytes([buf.pop(0), buf.pop(0)])

        # Handle telemetry special byte
        if pattern.hex() == "03010f" and cmd.hex() == "c402":
            if buf:
                buf.pop(0)

        return pattern, cmd, bytes(buf)

    async def _handle_negotiation_response(self, cmd: bytes, payload: bytes) -> None:
        """Process a negotiation stage response and advance to next stage."""
        cmd_hex = cmd.hex()
        stage = self._negotiation_stage

        try:
            if stage == 0 and cmd_hex == "0002":
                await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[1])  # type: ignore[union-attr]
                self._negotiation_stage = 1
                self._logger.debug("Negotiation stage 1")

            elif stage == 1 and cmd_hex == "0004":
                await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[2])  # type: ignore[union-attr]
                self._negotiation_stage = 2
                self._logger.debug("Negotiation stage 2")

            elif stage == 2 and cmd_hex == "002a":
                await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[3])  # type: ignore[union-attr]
                self._negotiation_stage = 3
                self._logger.debug("Negotiation stage 3")

            elif stage == 3 and cmd_hex == "0006":
                await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[4])  # type: ignore[union-attr]
                self._negotiation_stage = 4
                self._logger.debug("Negotiation stage 4")

            elif stage == 4 and cmd_hex == "0821":
                device_pub_key = self._extract_ecdh_key(payload)
                if device_pub_key:
                    self._session_keys = compute_session_keys(device_pub_key)
                    self._logger.debug("ECDH shared secret computed")
                    await self._client.write_gatt_char(UUID_COMMAND, NEGOTIATION_COMMANDS[5])  # type: ignore[union-attr]
                    self._negotiation_stage = 5
                    self._logger.debug("Negotiation stage 5")
                else:
                    self._logger.error("Failed to extract device ECDH public key")
                    return

            elif stage == 5:
                self._negotiation_stage = 6
                self._logger.debug("Negotiation complete (stage 6)")

        except Exception:
            self._logger.exception("Negotiation error at stage %d", stage)
            return

        if hasattr(self, "_negotiation_event") and self._negotiation_event:
            self._negotiation_event.set()

    def _extract_ecdh_key(self, payload: bytes) -> bytes | None:
        """Extract the device's ECDH public key (64 bytes) from negotiation payload.

        The key is in TLV parameter 'a1' (tag 0xa1) containing 64 bytes (x + y coordinates).
        """
        offset = 0
        while offset < len(payload):
            tag = payload[offset]
            offset += 1
            if tag == 0xA1:
                if offset >= len(payload):
                    break
                length = payload[offset]
                offset += 1
                if length == 0x40 and offset + 64 <= len(payload):
                    return payload[offset : offset + 64]
                offset += length
            elif tag in (0xA2, 0xA3, 0xA4, 0xA5):
                if offset >= len(payload):
                    break
                length = payload[offset]
                offset += 1
                offset += length
            else:
                offset += 1
        return None

    def _handle_telemetry_fragment(self, payload: bytes) -> None:
        """Handle fragmented telemetry data.

        Telemetry arrives in two fragments that must be reassembled:
        - Large fragment (>230 bytes): first part
        - Small fragment (<50 bytes): second part
        """
        if len(payload) < 50:
            self._telemetry_small = payload
        elif len(payload) > 230:
            self._telemetry_large = payload
            self._telemetry_small = None
        else:
            self._logger.debug("Unexpected telemetry payload size: %d", len(payload))
            return

        if self._telemetry_large is None or self._telemetry_small is None:
            return

        combined = self._telemetry_large + self._telemetry_small
        self._telemetry_large = None
        self._telemetry_small = None

        if not self._session_keys:
            self._logger.debug("Cannot decrypt telemetry: no session keys")
            return

        try:
            decrypted = aes_decrypt_raw(combined, self._session_keys.aes_key, self._session_keys.aes_iv)
            info = self._parse_telemetry(decrypted)
            if info:
                self._last_device_info = info
                if self._telemetry_callback:
                    self._telemetry_callback(info)
                if self._update_callback:
                    self._update_callback()
        except Exception:
            self._logger.debug("Failed to decrypt/parse telemetry", exc_info=True)

    def _parse_telemetry(self, data: bytes) -> SolixBleDeviceInfo | None:
        """Parse decrypted telemetry data into structured info.

        Uses TLV (Tag-Length-Value) parsing matching flip-dots/SolixBLE.
        Format: [1B tag][1B length][N bytes value] with little-endian integers.
        TLV values use begin=1 convention (first byte is type/flags, skip it).
        """
        if len(data) < 100:
            self._logger.debug("Telemetry data too short: %d bytes", len(data))
            return None

        if data[8] != 0x05 or data[9] != 0x13:
            self._logger.debug("Unexpected telemetry message type: %02x%02x", data[8], data[9])
            return None

        # Parse TLV fields from the decrypted blob
        tlv = self._parse_telemetry_tlv(data)
        if not tlv or TLV_SERIAL not in tlv:
            self._logger.debug("TLV parsing failed or serial tag (0xa2) missing")
            return None

        try:
            return self._build_info_from_tlv(tlv)
        except Exception:
            self._logger.debug("Telemetry parse error", exc_info=True)
            return None

    @staticmethod
    def _parse_telemetry_tlv(data: bytes) -> dict[int, bytes] | None:
        """Parse TLV fields from decrypted telemetry data.

        Scans for the start of TLV data by locating tag 0xa2 (serial_number)
        in the expected header region. TLV format per flip-dots/SolixBLE:
        [1B tag][1B length][length bytes value].
        """
        # Find TLV start by scanning for the serial number tag (0xa2)
        start = None
        for i in range(10, 20):
            if i < len(data) and data[i] == TLV_SERIAL:
                # Next byte should be a reasonable length for serial (16-18 bytes)
                if i + 1 < len(data) and 15 <= data[i + 1] <= 20:
                    start = i
                    break
        if start is None:
            return None

        # Parse TLV triplets
        result: dict[int, bytes] = {}
        offset = start
        while offset + 2 <= len(data):
            tag = data[offset]
            length = data[offset + 1]
            offset += 2
            if length == 0 or offset + length > len(data):
                break
            result[tag] = data[offset : offset + length]
            offset += length

        return result if result else None

    def _build_info_from_tlv(self, tlv: dict[int, bytes]) -> SolixBleDeviceInfo:
        """Build SolixBleDeviceInfo from parsed TLV fields.

        TLV value convention: value[0] is a type/flags byte, actual data at value[1:].
        Integer fields use little-endian byte order (confirmed from flip-dots source).
        """
        info = SolixBleDeviceInfo()

        def _uint(tag: int, size: int = 2) -> int:
            """Parse unsigned int from TLV value, skipping type byte."""
            v = tlv.get(tag)
            if v is None or len(v) < size + 1:
                return 0
            return int.from_bytes(v[1 : 1 + size], byteorder="little")

        def _sint(tag: int, size: int = 2) -> int:
            """Parse signed int from TLV value, skipping type byte."""
            v = tlv.get(tag)
            if v is None or len(v) < size + 1:
                return 0
            return int.from_bytes(v[1 : 1 + size], byteorder="little", signed=True)

        def _str(tag: int) -> str:
            """Parse string from TLV value, skipping type byte."""
            v = tlv.get(tag)
            if v is None or len(v) < 2:
                return ""
            return v[1:].decode("ascii", errors="replace").rstrip("\x00")

        def _version(tag: int) -> str:
            """Parse firmware version from TLV value (2B uint → digit-separated)."""
            raw = _uint(tag, 2)
            if raw == 0:
                return ""
            digits = str(raw)
            return ".".join(digits)

        # Identity
        info.serial_number = _str(TLV_SERIAL)

        # Battery
        if TLV_BATTERY_PCT in tlv and len(tlv[TLV_BATTERY_PCT]) >= 2:
            info.battery_percent = tlv[TLV_BATTERY_PCT][1]
        if TLV_BATTERY_PCT_AGG in tlv:
            info.battery_percent_aggregate = _uint(TLV_BATTERY_PCT_AGG, 2)
        info.battery_temperature = float(_sint(TLV_TEMPERATURE, 2))
        info.battery_charge_power_w = _uint(TLV_CHARGE_POWER, 2) / 100.0
        info.discharge_power_w = _uint(TLV_DISCHARGE_POWER, 4) / 100.0
        info.battery_energy_wh = _uint(TLV_CHARGED_ENERGY, 4) / 10.0

        # Solar (total + per-MPPT)
        info.solar_power_w = _uint(TLV_SOLAR_POWER, 2) / 10.0
        info.solar_pv1_power_w = _uint(TLV_PV1_POWER, 2) / 10.0
        info.solar_pv2_power_w = _uint(TLV_PV2_POWER, 2) / 10.0
        info.solar_pv3_power_w = _uint(TLV_PV3_POWER, 2) / 10.0
        info.solar_pv4_power_w = _uint(TLV_PV4_POWER, 2) / 10.0
        info.total_solar_wh = _uint(TLV_PV_YIELD, 4) / 10.0

        # Output / consumption
        info.ac_power_w = _uint(TLV_AC_POWER, 2) / 10.0
        info.ac_power_out_sockets_w = _uint(TLV_AC_SOCKETS, 2) / 10.0
        info.power_out_w = _uint(TLV_POWER_OUT, 2) / 10.0
        info.total_output_wh = _uint(TLV_OUTPUT_ENERGY, 4) / 10.0
        info.house_demand_w = _uint(TLV_HOUSE_DEMAND, 2) / 10.0
        info.consumed_energy_wh = _uint(TLV_CONSUMED_ENERGY, 4) / 10.0

        # Grid
        info.grid_to_home_power_w = _uint(TLV_GRID_TO_HOME, 2) / 10.0
        info.pv_to_grid_power_w = _uint(TLV_PV_TO_GRID, 2) / 10.0
        info.grid_import_energy_wh = _uint(TLV_GRID_IMPORT, 4) / 10.0
        info.grid_export_energy_wh = _uint(TLV_GRID_EXPORT, 4) / 10.0

        # Firmware versions
        info.software_version = _version(TLV_SW_VERSION)
        info.software_version_controller = _version(TLV_SW_VERSION_CTRL)
        info.software_version_expansion = _version(TLV_SW_VERSION_EXP)

        return info

    async def send_command(self, cmd: bytes, payload: bytes = b"") -> tuple[bytes, bytes] | None:
        """Send an encrypted command and wait for the response.

        Args:
            cmd: 2-byte command identifier.
            payload: Command payload data.

        Returns:
            Tuple of (response_cmd, response_payload) or None on timeout.

        """
        if not self.is_connected or not self._session_keys:
            self._logger.error("Cannot send command: not connected/negotiated")
            return None

        # Build payload with anti-replay timestamp
        time_passed = int(time.time() - self._negotiation_timestamp)
        base_ts = int.from_bytes(BASE_TIMESTAMP, byteorder="little")
        new_ts = (base_ts + time_passed).to_bytes(4, byteorder="little")
        full_payload = payload + bytes.fromhex("fe0503") + new_ts

        # Encrypt
        encrypted = aes_encrypt(full_payload, self._session_keys.aes_key, self._session_keys.aes_iv)

        # Build packet: [FF09][Length LE][Pattern 03000f][Cmd 2B][Encrypted payload][Checksum]
        packet_len = 2 + 2 + 3 + 2 + len(encrypted) + 1
        length_bytes = packet_len.to_bytes(2, byteorder="little")
        packet = PACKET_HEADER + length_bytes + PATTERN_COMMAND + cmd + encrypted
        packet = packet + xor_checksum(packet)

        # Set up response listener
        loop = asyncio.get_running_loop()
        self._pending_cmd = cmd
        self._pending_response = loop.create_future()

        try:
            await self._client.write_gatt_char(UUID_COMMAND, packet)  # type: ignore[union-attr]
            result = await asyncio.wait_for(self._pending_response, timeout=NEGOTIATION_RESPONSE_TIMEOUT)
            self._command_success_count += 1
            return result
        except asyncio.TimeoutError:
            self._logger.warning("Command response timeout for %s", cmd.hex())
            self._command_failure_count += 1
            return None
        except Exception:
            self._logger.exception("Command send error")
            self._command_failure_count += 1
            return None
        finally:
            self._pending_response = None
            self._pending_cmd = None

    # ──────────────────────────────────────────────────────────────────
    # High-level BLE command API
    #
    # These methods wrap send_command() with proper TLV encoding/decoding.
    # GET commands return parsed dict or None on failure.
    # SET commands return True on success.
    #
    # NOTE: Response parsing is speculative — response TLV field tags
    # have not been validated on a real device. The generic dict return
    # allows callers to inspect raw tag→value mappings regardless.
    # ──────────────────────────────────────────────────────────────────

    async def send_tlv_command(
        self, tlv_cmd: TlvCommand
    ) -> dict[int, TlvField] | None:
        """Send a TLV command and decode the response.

        Args:
            tlv_cmd: TlvCommand to send.

        Returns:
            Dict of tag→TlvField from the response, or None on failure.

        """
        opcode_bytes = struct.pack("!H", tlv_cmd.opcode)

        # Encode TLV fields as the command payload
        payload = b""
        for f in tlv_cmd.fields:
            if f.tag <= 0xFF:
                payload += struct.pack("!BH", f.tag, f.length) + f.value
            else:
                payload += struct.pack("!HH", f.tag, f.length) + f.value

        result = await self.send_command(opcode_bytes, payload)
        if result is None:
            return None

        _resp_cmd, resp_payload = result
        try:
            _opcode, fields = decode_tlv_response(
                opcode_bytes + struct.pack("!H", len(resp_payload)) + resp_payload
            )
            return fields_to_dict(fields)
        except (ValueError, struct.error):
            self._logger.debug("Failed to decode TLV response", exc_info=True)
            return None

    async def async_get_device_info(self) -> dict[int, TlvField] | None:
        """Query device info (serial, model, etc.)."""
        return await self.send_tlv_command(cmd_get_device_info())

    async def async_get_battery_info(self) -> dict[int, TlvField] | None:
        """Query battery details (SOC, SOH, cell voltages, temperature)."""
        return await self.send_tlv_command(cmd_get_battery_info())

    async def async_get_power_info(self) -> dict[int, TlvField] | None:
        """Query power flow details (solar, grid, output, battery)."""
        return await self.send_tlv_command(cmd_get_power_info())

    async def async_get_schedule(self) -> dict[int, TlvField] | None:
        """Query the current charge/discharge schedule."""
        return await self.send_tlv_command(cmd_get_schedule())

    async def async_get_min_soc(self) -> int | None:
        """Query the minimum SOC setting.

        Returns:
            SOC percentage, or None on failure.

        """
        result = await self.send_tlv_command(cmd_get_min_soc())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_set_min_soc(self, soc_percent: int) -> bool:
        """Set the minimum SOC (power cutoff).

        Args:
            soc_percent: 0-100 (MQTT only allows 5 or 10 for SB1/SB2).

        """
        result = await self.send_tlv_command(cmd_set_min_soc(soc_percent))
        return result is not None

    async def async_get_power_limit(self) -> int | None:
        """Query the output power limit.

        Returns:
            Power limit in watts, or None on failure.

        """
        result = await self.send_tlv_command(cmd_get_power_limit())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_set_power_limit(self, watts: int) -> bool:
        """Set the output power limit.

        Args:
            watts: Limit in watts (model-dependent options, e.g. 350-1200).

        """
        result = await self.send_tlv_command(cmd_set_output_power_limit(watts))
        return result is not None

    async def async_get_ac_limit(self) -> int | None:
        """Query the AC input power limit.

        Returns:
            AC limit in watts, or None on failure.

        """
        result = await self.send_tlv_command(cmd_get_ac_limit())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_set_ac_limit(self, watts: int) -> bool:
        """Set the AC input power limit (0-1200W, step 100).

        Only supported on SB2 AC (A17C2), SB3 Pro (A17C5), Power Dock (AE100).
        """
        result = await self.send_tlv_command(cmd_set_ac_limit(watts))
        return result is not None

    async def async_get_pv_limit(self) -> int | None:
        """Query the PV MPPT input limit.

        Returns:
            PV limit in watts, or None on failure.

        """
        result = await self.send_tlv_command(cmd_get_pv_limit())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_set_pv_limit(self, watts: int) -> bool:
        """Set the PV MPPT input limit (2000 or 3600W, A17C5 only)."""
        result = await self.send_tlv_command(cmd_set_pv_limit(watts))
        return result is not None

    async def async_get_zero_export(self) -> bool | None:
        """Query zero-export (grid export disabled) state.

        Returns:
            True if zero-export enabled, or None on failure.

        """
        result = await self.send_tlv_command(cmd_get_zero_export())
        if result and 0x01 in result:
            return result[0x01].as_int() != 0
        return None

    async def async_set_zero_export(self, enabled: bool, limit_w: int = 0) -> bool:
        """Set zero-export mode (disable grid export).

        Args:
            enabled: True to prevent grid export.
            limit_w: Export limit in watts (when enabled, 0-100000, step 100).

        """
        result = await self.send_tlv_command(cmd_set_zero_export(enabled, limit_w))
        return result is not None

    async def async_get_ems_mode(self) -> int | None:
        """Query the EMS/usage mode.

        Returns:
            Mode int (1=manual, 2=smartmeter, ..., 8=time_slot), or None.

        """
        result = await self.send_tlv_command(cmd_get_ems_mode())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_set_ems_mode(self, mode: int, **kwargs: int | bool) -> bool:
        """Set the EMS/usage mode.

        WARNING: Complex command with mode-dependent fields. Needs device testing.

        Args:
            mode: 1=manual, 2=smartmeter, 3=smartplugs, 4=backup,
                5=use_time, 7=smart, 8=time_slot
            **kwargs: backup_charge, dynamic_soc_limit, backup_start_ts, backup_end_ts

        """
        result = await self.send_tlv_command(cmd_set_ems_mode(mode, **kwargs))
        return result is not None

    async def async_get_output_mode(self) -> int | None:
        """Query output mode (smart/normal, PPS devices).

        Returns:
            Mode int (0=smart, 1=normal), or None.

        """
        result = await self.send_tlv_command(cmd_get_output_mode())
        if result and 0x01 in result:
            return result[0x01].as_int()
        return None

    async def async_get_grid_state(self) -> dict[int, TlvField] | None:
        """Query grid connection state."""
        return await self.send_tlv_command(cmd_get_grid_state())

    async def async_get_grid_export(self) -> dict[int, TlvField] | None:
        """Query grid export settings (limit, enabled)."""
        return await self.send_tlv_command(cmd_get_grid_export())

    async def async_get_backup_mode(self) -> dict[int, TlvField] | None:
        """Query backup mode configuration."""
        return await self.send_tlv_command(cmd_get_backup_mode())

    async def async_query_device_config(self) -> dict[str, int | bool | None]:
        """Query all readable device configuration in one batch.

        Returns a dict with named config values. None values indicate
        the command failed or was unsupported by the device.
        """
        config: dict[str, int | bool | None] = {}

        config["min_soc"] = await self.async_get_min_soc()
        config["power_limit"] = await self.async_get_power_limit()
        config["ac_limit"] = await self.async_get_ac_limit()
        config["pv_limit"] = await self.async_get_pv_limit()
        config["zero_export"] = await self.async_get_zero_export()
        config["ems_mode"] = await self.async_get_ems_mode()
        config["output_mode"] = await self.async_get_output_mode()

        return config
