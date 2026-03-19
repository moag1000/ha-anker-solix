"""Anker Solix BLE TLV (Type-Length-Value) command protocol.

Implements encoding and decoding of TLV-structured BLE commands
used by Anker Solix devices. Commands are identified by opcodes
grouped into families:
    - 0x71xx: Device info and control
    - 0x73xx: Configuration
    - 0x75xx: Advanced operations
    - 0xA5xx: Solix-specific commands

Packet format (reverse-engineered from AssembleCmdUtil in Dart):
    [Header (2 bytes)] [Opcode (2 bytes)] [Payload Length (2 bytes)] [TLV Data...] [Checksum]

NOTE: SET command field structures are derived from MQTT command analysis
(mqttcmdmap.py) and APK reverse engineering. The exact BLE TLV tag mapping
has NOT been validated against a real device. GET commands with no payload
are safe; SET commands need device testing before production use.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum


class OpcodeFamily(IntEnum):
    """Opcode family prefixes for BLE commands."""

    DEVICE_INFO = 0x71  # Device info and control
    CONFIG = 0x73  # Configuration
    ADVANCED = 0x75  # Advanced operations
    SOLIX = 0xA5  # Solix-specific


# Known opcodes (reverse-engineered from APK)
class Opcodes(IntEnum):
    """Known BLE command opcodes."""

    # 0x71xx - Device info
    GET_DEVICE_INFO = 0x7102
    GET_DEVICE_STATE = 0x7108
    GET_BATTERY_INFO = 0x7109
    GET_POWER_INFO = 0x710C
    GET_CHARGING_INFO = 0x710D
    GET_SOLAR_INFO = 0x710E
    SET_POWER_LIMIT = 0x7111
    GET_POWER_LIMIT = 0x7112
    GET_SCHEDULE = 0x7114
    SET_SCHEDULE = 0x7115
    GET_GRID_STATE = 0x7116
    SET_GRID_STATE = 0x7117
    GET_FIRMWARE_VER = 0x711B
    GET_WIFI_INFO = 0x711C
    SET_WIFI_CONFIG = 0x711D
    GET_SYSTEM_TIME = 0x711E

    # 0x73xx - Configuration
    GET_MIN_SOC = 0x7302
    SET_MIN_SOC = 0x7304
    GET_OUTPUT_MODE = 0x7306
    SET_OUTPUT_MODE = 0x7307
    GET_AC_LIMIT = 0x7308
    SET_AC_LIMIT = 0x7309
    GET_PV_LIMIT = 0x730B
    SET_PV_LIMIT = 0x730C
    GET_ZERO_EXPORT = 0x730D
    SET_ZERO_EXPORT = 0x730E
    GET_TOU_SCHEDULE = 0x7310
    SET_TOU_SCHEDULE = 0x7312
    GET_SMART_METER = 0x7313
    GET_CT_STATUS = 0x7314
    SET_CT_CONFIG = 0x7315
    GET_EMS_MODE = 0x7318
    SET_EMS_MODE = 0x7319
    GET_BACKUP_MODE = 0x731A
    SET_BACKUP_MODE = 0x731B
    GET_GRID_EXPORT = 0x731C

    # 0xA5xx - Solix specific
    SOLIX_GET_SCENE = 0xA513
    SOLIX_SET_PARAM = 0xA549
    SOLIX_GET_ENERGY = 0xA54D
    SOLIX_GET_STATUS = 0xA550
    SOLIX_GET_ABILITIES = 0xA5A6


@dataclass
class TlvField:
    """A single TLV field."""

    tag: int  # 1-2 bytes type identifier
    value: bytes  # raw value bytes

    @property
    def length(self) -> int:
        """Return the length of the value."""
        return len(self.value)

    def as_int(self, byteorder: str = "big", signed: bool = False) -> int:
        """Interpret value as integer."""
        return int.from_bytes(self.value, byteorder=byteorder, signed=signed)

    def as_str(self, encoding: str = "utf-8") -> str:
        """Interpret value as string."""
        return self.value.decode(encoding).rstrip("\x00")


@dataclass
class TlvCommand:
    """A TLV-encoded BLE command."""

    opcode: int
    fields: list[TlvField] = field(default_factory=list)

    def encode(self) -> bytes:
        """Encode the command to bytes for BLE transmission.

        Format: [Opcode (2B)] [Payload Length (2B)] [TLV fields...] [Checksum (1B)]
        """
        # Encode TLV fields
        payload = b""
        for f in self.fields:
            if f.tag <= 0xFF:
                payload += struct.pack("!BH", f.tag, f.length) + f.value
            else:
                payload += struct.pack("!HH", f.tag, f.length) + f.value

        # Build packet: opcode + payload length + payload
        packet = struct.pack("!HH", self.opcode, len(payload)) + payload

        # XOR checksum over entire packet
        checksum = 0
        for b in packet:
            checksum ^= b
        packet += bytes([checksum])

        return packet


def decode_tlv_response(data: bytes) -> tuple[int, list[TlvField]]:
    """Decode a TLV-encoded BLE response.

    Args:
        data: Raw response bytes.

    Returns:
        Tuple of (opcode, list of TlvField).

    """
    if len(data) < 5:
        msg = f"Response too short ({len(data)} bytes)"
        raise ValueError(msg)

    opcode = struct.unpack("!H", data[0:2])[0]
    payload_len = struct.unpack("!H", data[2:4])[0]
    payload = data[4 : 4 + payload_len]

    # Parse TLV fields from payload
    fields: list[TlvField] = []
    offset = 0
    while offset < len(payload):
        # Determine tag size (1 or 2 bytes)
        tag = payload[offset]
        if tag & 0x80:  # High bit set = 2-byte tag
            if offset + 1 >= len(payload):
                break
            tag = struct.unpack("!H", payload[offset : offset + 2])[0]
            offset += 2
        else:
            offset += 1

        # Read length (2 bytes)
        if offset + 2 > len(payload):
            break
        length = struct.unpack("!H", payload[offset : offset + 2])[0]
        offset += 2

        # Read value
        if offset + length > len(payload):
            break
        value = payload[offset : offset + length]
        offset += length

        fields.append(TlvField(tag=tag, value=value))

    return opcode, fields


def fields_to_dict(fields: list[TlvField]) -> dict[int, TlvField]:
    """Convert a list of TlvFields to a dict keyed by tag for easier access."""
    return {f.tag: f for f in fields}


# ──────────────────────────────────────────────────────────────────────
# GET command builders (no payload — safe to send, response format TBD)
# ──────────────────────────────────────────────────────────────────────

def cmd_get_device_info() -> TlvCommand:
    """Build a GET_DEVICE_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_DEVICE_INFO)


def cmd_get_device_state() -> TlvCommand:
    """Build a GET_DEVICE_STATE command."""
    return TlvCommand(opcode=Opcodes.GET_DEVICE_STATE)


def cmd_get_battery_info() -> TlvCommand:
    """Build a GET_BATTERY_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_BATTERY_INFO)


def cmd_get_power_info() -> TlvCommand:
    """Build a GET_POWER_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_POWER_INFO)


def cmd_get_charging_info() -> TlvCommand:
    """Build a GET_CHARGING_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_CHARGING_INFO)


def cmd_get_solar_info() -> TlvCommand:
    """Build a GET_SOLAR_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_SOLAR_INFO)


def cmd_get_power_limit() -> TlvCommand:
    """Build a GET_POWER_LIMIT command."""
    return TlvCommand(opcode=Opcodes.GET_POWER_LIMIT)


def cmd_get_schedule() -> TlvCommand:
    """Build a GET_SCHEDULE command."""
    return TlvCommand(opcode=Opcodes.GET_SCHEDULE)


def cmd_get_grid_state() -> TlvCommand:
    """Build a GET_GRID_STATE command."""
    return TlvCommand(opcode=Opcodes.GET_GRID_STATE)


def cmd_get_firmware_ver() -> TlvCommand:
    """Build a GET_FIRMWARE_VER command."""
    return TlvCommand(opcode=Opcodes.GET_FIRMWARE_VER)


def cmd_get_wifi_info() -> TlvCommand:
    """Build a GET_WIFI_INFO command."""
    return TlvCommand(opcode=Opcodes.GET_WIFI_INFO)


def cmd_get_system_time() -> TlvCommand:
    """Build a GET_SYSTEM_TIME command."""
    return TlvCommand(opcode=Opcodes.GET_SYSTEM_TIME)


def cmd_get_min_soc() -> TlvCommand:
    """Build a GET_MIN_SOC command."""
    return TlvCommand(opcode=Opcodes.GET_MIN_SOC)


def cmd_get_output_mode() -> TlvCommand:
    """Build a GET_OUTPUT_MODE command."""
    return TlvCommand(opcode=Opcodes.GET_OUTPUT_MODE)


def cmd_get_ac_limit() -> TlvCommand:
    """Build a GET_AC_LIMIT command."""
    return TlvCommand(opcode=Opcodes.GET_AC_LIMIT)


def cmd_get_pv_limit() -> TlvCommand:
    """Build a GET_PV_LIMIT command."""
    return TlvCommand(opcode=Opcodes.GET_PV_LIMIT)


def cmd_get_zero_export() -> TlvCommand:
    """Build a GET_ZERO_EXPORT command."""
    return TlvCommand(opcode=Opcodes.GET_ZERO_EXPORT)


def cmd_get_tou_schedule() -> TlvCommand:
    """Build a GET_TOU_SCHEDULE command."""
    return TlvCommand(opcode=Opcodes.GET_TOU_SCHEDULE)


def cmd_get_smart_meter() -> TlvCommand:
    """Build a GET_SMART_METER command."""
    return TlvCommand(opcode=Opcodes.GET_SMART_METER)


def cmd_get_ct_status() -> TlvCommand:
    """Build a GET_CT_STATUS command."""
    return TlvCommand(opcode=Opcodes.GET_CT_STATUS)


def cmd_get_ems_mode() -> TlvCommand:
    """Build a GET_EMS_MODE command."""
    return TlvCommand(opcode=Opcodes.GET_EMS_MODE)


def cmd_get_backup_mode() -> TlvCommand:
    """Build a GET_BACKUP_MODE command."""
    return TlvCommand(opcode=Opcodes.GET_BACKUP_MODE)


def cmd_get_grid_export() -> TlvCommand:
    """Build a GET_GRID_EXPORT command."""
    return TlvCommand(opcode=Opcodes.GET_GRID_EXPORT)


def cmd_solix_get_scene() -> TlvCommand:
    """Build a SOLIX_GET_SCENE command (site/device topology)."""
    return TlvCommand(opcode=Opcodes.SOLIX_GET_SCENE)


def cmd_solix_get_energy() -> TlvCommand:
    """Build a SOLIX_GET_ENERGY command (energy stats)."""
    return TlvCommand(opcode=Opcodes.SOLIX_GET_ENERGY)


def cmd_solix_get_status() -> TlvCommand:
    """Build a SOLIX_GET_STATUS command."""
    return TlvCommand(opcode=Opcodes.SOLIX_GET_STATUS)


def cmd_solix_get_abilities() -> TlvCommand:
    """Build a SOLIX_GET_ABILITIES command (device capabilities)."""
    return TlvCommand(opcode=Opcodes.SOLIX_GET_ABILITIES)


# ──────────────────────────────────────────────────────────────────────
# SET command builders (SPECULATIVE — derived from MQTT field structures
# in mqttcmdmap.py. Exact BLE TLV tag mapping needs device validation.)
# ──────────────────────────────────────────────────────────────────────

def cmd_set_min_soc(soc_percent: int) -> TlvCommand:
    """Build a SET_MIN_SOC command.

    Args:
        soc_percent: Minimum state of charge. MQTT allows only 5 or 10
            for SB1/SB2. SB3 may accept wider range. Clamped to 0-100.

    """
    return TlvCommand(
        opcode=Opcodes.SET_MIN_SOC,
        fields=[TlvField(tag=0x01, value=struct.pack("!B", min(100, max(0, soc_percent))))],
    )


def cmd_set_output_power_limit(watts: int, load_type: int = 0) -> TlvCommand:
    """Build a SET_POWER_LIMIT command.

    Args:
        watts: Output power limit in watts.
            MQTT typical values: 350, 600, 800, 1000, 1200 (model-dependent).
            Parallel mode: 1200, 2400, 3600, 4800.
        load_type: Load mode (0=individual, 2=parallel, 3=single).

    """
    fields = [TlvField(tag=0x01, value=struct.pack("!H", watts))]
    if load_type != 0:
        fields.append(TlvField(tag=0x02, value=struct.pack("!H", load_type)))
    return TlvCommand(opcode=Opcodes.SET_POWER_LIMIT, fields=fields)


def cmd_set_zero_export(enabled: bool, export_limit_w: int = 0) -> TlvCommand:
    """Build a SET_ZERO_EXPORT command.

    Args:
        enabled: True to disable grid export (zero-export mode).
        export_limit_w: Grid export limit in watts (0-100000, step 100).
            Only used when zero-export is enabled.

    """
    fields = [
        TlvField(tag=0x01, value=struct.pack("!B", 1 if enabled else 0)),
    ]
    if export_limit_w > 0:
        fields.append(TlvField(tag=0x02, value=struct.pack("!H", export_limit_w)))
    return TlvCommand(opcode=Opcodes.SET_ZERO_EXPORT, fields=fields)


def cmd_set_ac_limit(watts: int) -> TlvCommand:
    """Build a SET_AC_LIMIT command.

    Args:
        watts: AC input power limit in watts (0-1200, step 100).
            Supported on SB2 AC (A17C2), SB3 Pro (A17C5), Power Dock (AE100).

    """
    clamped = max(0, min(1200, watts))
    return TlvCommand(
        opcode=Opcodes.SET_AC_LIMIT,
        fields=[TlvField(tag=0x01, value=struct.pack("!H", clamped))],
    )


def cmd_set_pv_limit(watts: int) -> TlvCommand:
    """Build a SET_PV_LIMIT command.

    Args:
        watts: PV MPPT input limit in watts. MQTT allows 2000 or 3600.
            Only supported on SB3 Pro (A17C5).

    """
    return TlvCommand(
        opcode=Opcodes.SET_PV_LIMIT,
        fields=[TlvField(tag=0x01, value=struct.pack("!H", watts))],
    )


def cmd_set_output_mode(mode: int) -> TlvCommand:
    """Build a SET_OUTPUT_MODE command.

    Args:
        mode: Output mode (0=smart, 1=normal). For PPS devices.

    """
    return TlvCommand(
        opcode=Opcodes.SET_OUTPUT_MODE,
        fields=[TlvField(tag=0x01, value=struct.pack("!B", mode))],
    )


def cmd_set_grid_state(state: int) -> TlvCommand:
    """Build a SET_GRID_STATE command.

    Args:
        state: Grid connection state. Exact values TBD (needs device testing).

    """
    return TlvCommand(
        opcode=Opcodes.SET_GRID_STATE,
        fields=[TlvField(tag=0x01, value=struct.pack("!B", state))],
    )


def cmd_set_ems_mode(
    mode: int,
    *,
    backup_charge: bool = False,
    dynamic_soc_limit: int = 0,
    backup_start_ts: int = 0,
    backup_end_ts: int = 0,
) -> TlvCommand:
    """Build a SET_EMS_MODE command.

    WARNING: Complex multi-field command. Field structure varies by mode.
    Derived from MQTT CMD_SB_USAGE_MODE analysis. Needs device testing.

    Args:
        mode: EMS/usage mode:
            1=manual, 2=smartmeter, 3=smartplugs, 4=backup,
            5=use_time, 7=smart, 8=time_slot
        backup_charge: Enable backup charging (mode 4).
        dynamic_soc_limit: Dynamic SOC limit 10-100% (mode 4, default 0).
        backup_start_ts: Unix timestamp for backup start (mode 4).
        backup_end_ts: Unix timestamp for backup end (mode 4).

    """
    fields = [
        TlvField(tag=0x01, value=struct.pack("!B", mode)),
    ]
    if mode == 4:  # backup mode with extra fields
        fields.append(TlvField(tag=0x02, value=struct.pack("!B", 1 if backup_charge else 0)))
        if dynamic_soc_limit > 0:
            fields.append(TlvField(tag=0x03, value=struct.pack("!B", min(100, dynamic_soc_limit))))
        if backup_start_ts > 0:
            fields.append(TlvField(tag=0x04, value=struct.pack("<I", backup_start_ts)))
        if backup_end_ts > 0:
            fields.append(TlvField(tag=0x05, value=struct.pack("<I", backup_end_ts)))
    return TlvCommand(opcode=Opcodes.SET_EMS_MODE, fields=fields)


def cmd_set_backup_mode(
    enabled: bool,
    soc_limit: int = 100,
    start_ts: int = 0,
    end_ts: int = 0,
) -> TlvCommand:
    """Build a SET_BACKUP_MODE command.

    Args:
        enabled: Enable backup mode.
        soc_limit: SOC limit for backup (10-100%).
        start_ts: Unix timestamp for backup window start.
        end_ts: Unix timestamp for backup window end.

    """
    fields = [
        TlvField(tag=0x01, value=struct.pack("!B", 1 if enabled else 0)),
        TlvField(tag=0x02, value=struct.pack("!B", min(100, max(10, soc_limit)))),
    ]
    if start_ts > 0:
        fields.append(TlvField(tag=0x03, value=struct.pack("<I", start_ts)))
    if end_ts > 0:
        fields.append(TlvField(tag=0x04, value=struct.pack("<I", end_ts)))
    return TlvCommand(opcode=Opcodes.SET_BACKUP_MODE, fields=fields)


def cmd_set_tou_schedule(slots: list[int]) -> TlvCommand:
    """Build a SET_TOU_SCHEDULE command (time-of-use 48 half-hour slots).

    Args:
        slots: List of 48 slot values (one per 30-min period, 00:00-23:30).
            Values: 1=discharge, 4=charge, 6=default.
            If fewer than 48 provided, remaining slots default to 6.

    """
    padded = (slots + [6] * 48)[:48]
    return TlvCommand(
        opcode=Opcodes.SET_TOU_SCHEDULE,
        fields=[TlvField(tag=0x01, value=bytes(padded))],
    )


def cmd_set_wifi_config(ssid: str, password: str) -> TlvCommand:
    """Build a SET_WIFI_CONFIG command (BLE-only, used during device setup).

    Args:
        ssid: WiFi network name.
        password: WiFi password.

    """
    ssid_bytes = ssid.encode("utf-8")
    pwd_bytes = password.encode("utf-8")
    return TlvCommand(
        opcode=Opcodes.SET_WIFI_CONFIG,
        fields=[
            TlvField(tag=0x01, value=ssid_bytes),
            TlvField(tag=0x02, value=pwd_bytes),
        ],
    )


def cmd_set_schedule(schedule_data: bytes) -> TlvCommand:
    """Build a SET_SCHEDULE command with raw schedule binary data.

    The schedule binary format is complex and model-dependent.
    Use raw bytes from a previously captured GET_SCHEDULE response
    (modified as needed) for safety.

    Args:
        schedule_data: Raw binary schedule structure.

    """
    return TlvCommand(
        opcode=Opcodes.SET_SCHEDULE,
        fields=[TlvField(tag=0x01, value=schedule_data)],
    )


def cmd_set_ct_config(ct_data: bytes) -> TlvCommand:
    """Build a SET_CT_CONFIG command for smart meter CT clamp configuration.

    Args:
        ct_data: Raw CT configuration bytes. Structure TBD.

    """
    return TlvCommand(
        opcode=Opcodes.SET_CT_CONFIG,
        fields=[TlvField(tag=0x01, value=ct_data)],
    )
