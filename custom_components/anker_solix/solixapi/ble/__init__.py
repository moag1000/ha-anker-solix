"""Anker Solix BLE communication module.

This module implements direct Bluetooth Low Energy communication with Anker Solix
devices, enabling local control and data retrieval without cloud dependency.

BLE Protocol Stack (reverse-engineered from Anker app v3.18.0 + SolixBLE):
    1. GATT connection via service/characteristic UUIDs
    2. ECDH key exchange (secp256r1) for shared secret
    3. AES-128-CBC session encryption (key = secret[:16], iv = secret[16:])
    4. Packet framing: [FF09][Length LE][Pattern 3B][Cmd 2B][Payload][XOR Checksum]
    5. Telemetry fragmentation/reassembly for large payloads
"""

from __future__ import annotations

# BLE GATT UUIDs (from SolixBLE / reverse-engineered from APK)
UUID_TELEMETRY = "8c850003-0302-41c5-b46e-cf057c562025"
UUID_COMMAND = "8c850002-0302-41c5-b46e-cf057c562025"
UUID_IDENTIFIER = "0000ff09-0000-1000-8000-00805f9b34fb"

# Packet header
PACKET_HEADER = bytes.fromhex("ff09")

# Packet patterns
PATTERN_NEGOTIATION = bytes.fromhex("030001")
PATTERN_COMMAND = bytes.fromhex("03000f")
PATTERN_TELEMETRY = bytes.fromhex("03010f")

# Anti-replay base timestamp agreed during negotiation
BASE_TIMESTAMP = bytes.fromhex("42ad8c69")

# Hardcoded ECDH private key for BLE negotiation
# (Anker devices use a fixed key exchange - this is from the SolixBLE project)
ECDH_PRIVATE_KEY_HEX = "7dfbea61cd95cee49c458ad7419e817f1ade9a66136de3c7d5787af1458e39f4"

# Negotiation command sequence (6 stages)
NEGOTIATION_COMMANDS = [
    bytes.fromhex("ff0936000300010001a10442ad8c69a22462326463306231372d623735642d346162662d626136652d656337633939376332336537b9"),
    bytes.fromhex("ff093d000300010003a10442ad8c69a22462326463306231372d623735642d346162662d626136652d656337633939376332336537a30120a40200f064"),
    bytes.fromhex("ff0936000300010029a10442ad8c69a22462326463306231372d623735642d346162662d626136652d65633763393937633233653791"),
    bytes.fromhex("ff0940000300010005a10443ad8c69a22462326463306231372d623735642d346162662d626136652d656337633939376332336537a30120a40200f0a50140fa"),
    bytes.fromhex("ff094c000300010021a140060ea168f232aedb37fb2d120c49180329ac72ab5ec3eb8fd30a2f252dc5e151dabccd9b1dc1e288704ca760a0d8c918e5c94823a1f609a4bf07fb4c33ee219085"),
    bytes.fromhex("ff095a000300014022580bc0532a53c739adf3da7b994a7b5f221bcc16bab6392c215cb4faaf41d9d58e2c81c016e474c78eed5569147cb74a1f22ca2b3fad2e209dbbcfbdaca352034a6c479f055f68581b5f1e22348809f526"),
]

# Timing constants (used by client.py negotiation flow)
NEGOTIATION_TIMEOUT = 90
NEGOTIATION_RESPONSE_TIMEOUT = 15

# TLV tag keys for telemetry fields (from flip-dots/SolixBLE)
# Format: [1B tag][1B length][N bytes value], value[0] is type/flags byte
# Integers are little-endian in value[1:]
TLV_SERIAL = 0xA2  # string (16 bytes after type byte)
TLV_BATTERY_PCT = 0xA3  # uint8
TLV_SW_VERSION = 0xA6  # uint16 → digit-separated version
TLV_SW_VERSION_CTRL = 0xA7  # uint16
TLV_SW_VERSION_EXP = 0xA8  # uint16
TLV_TEMPERATURE = 0xAA  # int16 signed, °C
TLV_SOLAR_POWER = 0xAB  # uint16, raw/10 = W
TLV_AC_POWER = 0xAC  # uint16, raw/10 = W
TLV_BATTERY_PCT_AGG = 0xAD  # uint16, average across batteries
TLV_CHARGE_POWER = 0xB0  # uint16, raw/100 = W
TLV_PV_YIELD = 0xB1  # uint32, raw/10 = Wh (raw/10000 = kWh)
TLV_CHARGED_ENERGY = 0xB2  # uint32, raw/10 = Wh
TLV_OUTPUT_ENERGY = 0xB3  # uint32, raw/10 = Wh
TLV_DISCHARGE_POWER = 0xB7  # uint32, raw/100 = W
TLV_GRID_TO_HOME = 0xBC  # uint16, raw/10 = W
TLV_PV_TO_GRID = 0xBD  # uint16, raw/10 = W
TLV_GRID_IMPORT = 0xBE  # uint32, raw/10 = Wh
TLV_GRID_EXPORT = 0xBF  # uint32, raw/10 = Wh
TLV_HOUSE_DEMAND = 0xC4  # uint16, raw/10 = W
TLV_AC_SOCKETS = 0xC8  # uint16, raw/10 = W
TLV_CONSUMED_ENERGY = 0xC9  # uint32, raw/10 = Wh
TLV_PV1_POWER = 0xCA  # uint16, raw/10 = W
TLV_PV2_POWER = 0xCB  # uint16, raw/10 = W
TLV_PV3_POWER = 0xCC  # uint16, raw/10 = W
TLV_PV4_POWER = 0xCD  # uint16, raw/10 = W
TLV_POWER_OUT = 0xD3  # uint16, raw/10 = W
