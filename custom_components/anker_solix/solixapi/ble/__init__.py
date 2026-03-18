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

# Timing constants
RECONNECT_DELAY = 3
RECONNECT_ATTEMPTS_MAX = -1  # unlimited
DISCONNECT_TIMEOUT = 120
NEGOTIATION_TIMEOUT = 90
NEGOTIATION_RESPONSE_TIMEOUT = 15

# Telemetry parsing offsets (byte positions in decrypted telemetry)
TELEMETRY_SERIAL_OFFSET = 0x10
TELEMETRY_SERIAL_LENGTH = 16
TELEMETRY_BATTERY_PCT_OFFSET = 35
TELEMETRY_BATTERY_TEMP_OFFSET = 73
TELEMETRY_SOLAR_POWER_OFFSET = 77  # 2 bytes LE, W * 10
TELEMETRY_AC_POWER_OFFSET = 84  # 2 bytes LE, W * 10
TELEMETRY_TOTAL_SOLAR_OFFSET = 110  # 4 bytes, Wh * 10
TELEMETRY_BATTERY_ENERGY_OFFSET = 117  # 4 bytes, Wh * 100
TELEMETRY_TOTAL_OUTPUT_OFFSET = 124  # 4 bytes, Wh * 10
TELEMETRY_DISCHARGE_POWER_OFFSET = 132  # 4 bytes, W * 100
