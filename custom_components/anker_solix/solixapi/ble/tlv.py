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


# Convenience command builders

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


def cmd_set_min_soc(soc_percent: int) -> TlvCommand:
    """Build a SET_MIN_SOC command.

    Args:
        soc_percent: Minimum state of charge (0-100).

    """
    return TlvCommand(
        opcode=Opcodes.SET_MIN_SOC,
        fields=[TlvField(tag=0x01, value=struct.pack("!B", min(100, max(0, soc_percent))))],
    )


def cmd_set_output_power_limit(watts: int) -> TlvCommand:
    """Build a SET_POWER_LIMIT command.

    Args:
        watts: Output power limit in watts.

    """
    return TlvCommand(
        opcode=Opcodes.SET_POWER_LIMIT,
        fields=[TlvField(tag=0x01, value=struct.pack("!H", watts))],
    )


def cmd_get_schedule() -> TlvCommand:
    """Build a GET_SCHEDULE command."""
    return TlvCommand(opcode=Opcodes.GET_SCHEDULE)
