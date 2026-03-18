# Feature Branch: BLE Support & Additional API Features

> **EXPERIMENTAL** - This branch is highly experimental. All BLE, MQTT and API
> additions are based on reverse-engineered data from the Anker APK and
> third-party open-source projects (see [Data Origin](#data-origin) below and
> [API_ENDPOINTS.md](API_ENDPOINTS.md) for full details). None of this has been
> validated against official Anker documentation (which does not exist publicly).
> Use at your own risk. Endpoints may change, break, or behave differently than
> expected. The BLE protocol in particular has only been tested via SolixBLE
> reference implementations, not in a production HA environment.

> Branch: `feat/ble-and-local-features`
> Status: **Experimental / Work in Progress**
> Target: Upstream PR to [thomluther/ha-anker-solix](https://github.com/thomluther/ha-anker-solix)

## Motivation

During a cloud API downtime, the Anker mobile app continued working while the
ha-anker-solix integration went completely offline. Investigation revealed the
app uses **three parallel communication channels**: REST API, MQTT, and BLE.

This branch adds direct BLE (Bluetooth Low Energy) communication with Anker
Solix devices plus additional API methods and endpoint groups discovered during
reverse engineering, enabling local device access without cloud dependency.

---

## Data Origin

All reverse-engineered data in this branch comes from the following sources:

| Source | Author | What it provided | Files affected |
|--------|--------|-----------------|----------------|
| **Anker App v3.18.0 APK** | Anker Innovations | Decompiled `libapp.so` + Dart analysis: ~50 REST endpoint URLs, MQTT topic structures, BLE GATT UUIDs, ECDH key material, TLV opcode tables, 6-stage negotiation sequences | `apitypes.py`, `ble/__init__.py`, `mqtt.py` |
| **[SolixBLE](https://github.com/flip-dots/SolixBLE)** | [@flip-dots](https://github.com/flip-dots) | BLE protocol RE: TLV-based telemetry parsing (26 tag keys, scaling factors, little-endian), ECDH crypto flow, GATT UUIDs, packet framing, command opcodes | `ble/client.py` (TLV parser), `ble/__init__.py` (TLV constants), `ble/crypto.py` |
| **[AnkerSolixBLE](https://github.com/thomluther/AnkerSolixBLE)** | [@thomluther](https://github.com/thomluther) | Telemetry byte-offset validation, SB2 Pro data structure confirmation, cross-reference for scaling factor verification | `ble/client.py` (offset validation) |
| **[HaSolixBLE](https://github.com/flip-dots/HaSolixBLE)** | [@flip-dots](https://github.com/flip-dots) | HA integration patterns: config flow `async_step_bluetooth`, coordinator structure, bluetooth matchers, entity platform design | `ble_coordinator.py`, `config_flow.py`, `manifest.json` |
| **[beurer_daylight_lamps](https://github.com/moag1000/beurer_daylight_lamps)** | [@moag1000](https://github.com/moag1000) | HA BLE best practices: `bleak-retry-connector` with `establish_connection()`, exponential backoff (3s-120s), adaptive polling intervals (30s/5min/15min), connection health metrics | `ble/client.py` (reconnection), `ble_coordinator.py` (adaptive polling) |
| **[ha-anker-solix](https://github.com/thomluther/ha-anker-solix)** | [@thomluther](https://github.com/thomluther) | Base integration: cloud API, MQTT coordinator, entity platforms, device registry — all our additions build on this foundation | All files (base) |

---

## New Features

### 1. BLE Communication Module (`solixapi/ble/`)

Complete BLE protocol implementation for direct device communication:

| File | Purpose |
|------|---------|
| `__init__.py` | Constants: GATT UUIDs, negotiation commands, TLV tag keys (26 fields) |
| `crypto.py` | ECDH key exchange (secp256r1) + AES-128-CBC session encryption |
| `tlv.py` | TLV command encoding/decoding with 40+ opcodes (scaffolding for future BLE commands) |
| `client.py` | Full BLE client with connection management, TLV-based telemetry parsing |

**BLE Protocol Stack:**
1. Device discovery via `UUID_IDENTIFIER` (`0000ff09-...`)
2. GATT connection via `bleak-retry-connector` (with retry + multi-adapter)
3. 6-stage ECDH negotiation handshake
4. AES-128-CBC encrypted commands via `UUID_COMMAND` (`8c850002-...`)
5. Encrypted telemetry via `UUID_TELEMETRY` (`8c850003-...`)
6. Fragmented telemetry reassembly (large + small packet merging)

**Telemetry parsing:** TLV-based (Tag-Length-Value), matching flip-dots/SolixBLE.
Format: `[1B tag][1B length][N bytes value]`, value[0] is type byte, data at value[1:].
Little-endian integers. Robust to firmware field reordering (unlike fixed byte offsets).

**Telemetry fields available via BLE (26 fields for SB2 Pro):**

| Category | Field | TLV Key | Unit | Description |
|----------|-------|---------|------|-------------|
| Identity | serial_number | 0xa2 | - | Device serial |
| Battery | battery_percent | 0xa3 | % | State of charge |
| Battery | battery_percent_aggregate | 0xad | % | Average across all batteries |
| Battery | battery_temperature | 0xaa | °C | Signed temperature |
| Battery | battery_charge_power_w | 0xb0 | W | Charging power (raw/100) |
| Battery | discharge_power_w | 0xb7 | W | Discharge power (raw/100) |
| Battery | battery_energy_wh | 0xb2 | Wh | Cumulative charged energy |
| Solar | solar_power_w | 0xab | W | Total solar input (raw/10) |
| Solar | solar_pv1-4_power_w | 0xca-cd | W | Per-MPPT solar input |
| Solar | total_solar_wh | 0xb1 | Wh | Cumulative solar yield |
| Output | ac_power_w | 0xac | W | AC power output |
| Output | ac_power_out_sockets_w | 0xc8 | W | Pass-through socket output |
| Output | power_out_w | 0xd3 | W | Total power out |
| Output | total_output_wh | 0xb3 | Wh | Cumulative output energy |
| Output | house_demand_w | 0xc4 | W | Real-time house consumption |
| Output | consumed_energy_wh | 0xc9 | Wh | Cumulative consumed energy |
| Grid | grid_to_home_power_w | 0xbc | W | Grid import power |
| Grid | pv_to_grid_power_w | 0xbd | W | PV export to grid |
| Grid | grid_import_energy_wh | 0xbe | Wh | Cumulative grid import |
| Grid | grid_export_energy_wh | 0xbf | Wh | Cumulative grid export |
| FW | software_version | 0xa6 | - | Main firmware |
| FW | software_version_controller | 0xa7 | - | Controller MCU firmware |
| FW | software_version_expansion | 0xa8 | - | Expansion battery firmware |

**Connection features (inspired by beurer_daylight_lamps):**
- `bleak-retry-connector` with multi-adapter support (ESPHome/Shelly BLE proxies)
- Auto-reconnection with exponential backoff (3s initial, 120s max)
- Connection health metrics (reconnect count, command success/failure)
- Push update callback for coordinator integration
- HA Bluetooth stack integration (`after_dependencies: ["bluetooth"]`, optional)
- BLE coordinator (`ble_coordinator.py`) with adaptive polling (30s/5min/15min)
- HA config flow `async_step_bluetooth()` redirects to cloud credentials setup
- Cloud coordinator overlay: BLE telemetry supplements cloud data (debug logging stage)

### 2. New API Methods (`api.py`)

All methods added to the `AnkerSolixApi` class:

| Method | Endpoint Key | Description |
|--------|-------------|-------------|
| `get_ai_ems_profit()` | `get_ai_ems_profit` | AI EMS savings/profit data per site |
| `get_device_income()` | `get_device_income` | Device income/savings data |
| `get_shelly_status()` | `get_shelly_status` | Shelly device status via Anker cloud |
| `get_extender_system_list()` | `get_extender_system_list` | List all range extender systems |
| `get_extender_system_detail()` | `get_extender_system_detail` | Detail for one range extender system |
| `get_site_detail_by_sn()` | `get_site_detail_by_sn` | Reverse lookup site by device serial |
| `hes_get_aiems_profit()` | `get_aiems_profit` (HES) | AI EMS profit via HES service path |
| `hes_authorize_aiems()` | `authorize_aiems` (HES) | Authorize AI EMS for HES site |
| `hes_enable_aiems_mode4()` | `enable_aiems_mode4` (HES) | Enable AI EMS mode 4 for HES site |
| `update_extender_system_strategy()` | `update_extender_system_strategy` | Update strategy for range extender system |
| `get_extender_system_cumulative_data()` | `get_extender_system_cumulative_data` | Cumulative energy data for range extender |
| `set_extender_system_cumulative_data()` | `set_extender_system_cumulative_data` | Set cumulative data for range extender |
| `set_extender_system_name()` | `set_extender_system_name` | Set name for range extender system |
| `get_extender_system_pn_ota()` | `get_extender_system_pn_ota` | OTA info for range extender devices |
| `get_all_service_config()` | `get_all_service_config` | Get all service configuration |
| `get_message_sn_list()` | `get_message_sn_list` | List message-enabled device serial numbers |
| `get_device_location()` | `get_device_location` | Get device location (lat/lon/country) |
| `set_device_location()` | `set_device_location` | Set device location |
| `get_electrician()` | `get_electrician` | Get electrician/installer info for site |
| `get_device_bind_details()` | `get_device_bind_details` | Get device binding details |
| `get_strategy_last_record()` | `get_strategy_last_record` | Get last strategy record for device |
| `get_shared_device_relation()` | `get_shared_device_relation` | Get shared device relation details |
| `update_device_alias()` | `update_device_alias` | Update device alias name |

### 3. New Endpoint Groups

The following endpoint groups were discovered in the APK and added to `API_ENDPOINTS` and `API_HES_SVC_ENDPOINTS`:

#### Range Extender System (A7320) -- 12 endpoints
| Key | Path |
|-----|------|
| `get_extender_system_list` | `power_service/v1/app/get_extender_system_list` |
| `get_extender_system_detail` | `power_service/v1/app/get_extender_system_detail` |
| `add_extender_system` | `power_service/v1/app/add_extender_system` |
| `del_extender_system` | `power_service/v1/app/del_extender_system` |
| `update_extender_system_strategy` | `power_service/v1/app/update_extender_system_strategy` |
| `get_extender_system_cumulative_data` | `power_service/v1/app/get_extender_system_cumulative_data` |
| `set_extender_system_name` | `power_service/v1/app/set_extender_system_name` |
| `add_extender_system_device_list` | `power_service/v1/app/add_extender_system_device_list` |
| `batch_add_extender_system_device` | `power_service/v1/app/batch_add_extender_system_device` |
| `batch_del_extender_system_device` | `power_service/v1/app/batch_del_extender_system_device` |
| `get_extender_system_pn_ota` | `power_service/v1/app/get_extender_system_pn_ota` |
| `set_extender_system_cumulative_data` | `power_service/v1/app/set_extender_system_cumulative_data` |

#### VPP / Evergen -- 5 endpoints
| Key | Path |
|-----|------|
| `vpp_get_enrollment_status` | `power_service/v1/app/vpp/get_enrollment_status` |
| `vpp_enrollment_verification` | `power_service/v1/app/vpp/enrollment_verification` |
| `vpp_get_policy` | `power_service/v1/app/vpp/get_policy` |
| `vpp_dispatch_control` | `power_service/v1/app/vpp/dispatch_control` |
| `vpp_get_dispatch_history` | `power_service/v1/app/vpp/get_dispatch_history` |

#### Dynamic Pricing (Nordpool/Tibber) -- 8 endpoints
Original 3 (already existed) plus 5 new:

| Key | Path | Status |
|-----|------|--------|
| `get_dynamic_price_sites` | `.../dynamic_price/check_available` | existing |
| `get_dynamic_price_providers` | `.../dynamic_price/support_option` | existing |
| `get_dynamic_price_details` | `.../dynamic_price/price_detail` | existing |
| `get_dynamic_price_plan` | `.../dynamic_price/get_plan` | **new** |
| `set_dynamic_price_plan` | `.../dynamic_price/set_plan` | **new** |
| `get_dynamic_price_rates` | `.../dynamic_price/get_rates` | **new** |
| `check_dynamic_price_adjust` | `.../dynamic_price/check_adjust` | **new** |
| `get_dynamic_price_provider_list` | `.../dynamic_price/get_providers` | **new** |

#### Auto Disaster Preparedness (Storm Guard) -- 4 endpoints (HES)
| Key | Path |
|-----|------|
| `get_auto_disaster_status` | `charging_hes_svc/get_auto_disaster_prepare_status` |
| `get_auto_disaster_detail` | `charging_hes_svc/get_auto_disaster_prepare_detail` |
| `get_current_disaster_detail` | `charging_hes_svc/get_current_disaster_prepare_detail` |
| `get_backup_history` | `charging_hes_svc/get_back_up_history` |

#### AI EMS via HES -- 3 endpoints
| Key | Path |
|-----|------|
| `authorize_aiems` | `charging_hes_svc/authorize_aiems` |
| `enable_aiems_mode4` | `charging_hes_svc/enable_aiems_mode4` |
| `get_aiems_profit` | `charging_hes_svc/get_aiems_profit` |

#### Location Services -- 3 endpoints
| Key | Path |
|-----|------|
| `get_device_location` | `charging_common_svc/location/get` |
| `set_device_location` | `charging_common_svc/location/set` |
| `check_location_support` | `charging_common_svc/location/support` |

#### EV Charger Orders -- 3 endpoints
| Key | Path |
|-----|------|
| `get_charging_order_list` | `power_service/v1/app/order/get_charging_order_list` |
| `get_charging_order_detail` | `power_service/v1/app/order/get_charging_order_detail` |
| `export_charge_order` | `power_service/v1/app/order/export_charge_order` |

#### Monthly/Annual Reports -- 4 endpoints
| Key | Path |
|-----|------|
| `get_annual_report` | `power_service/v1/app/get_annual_report` |
| `get_monthly_report_list` | `power_service/v1/app/mothly_report_list` *(typo matches Anker API)* |
| `get_monthly_report_configs` | `power_service/v1/app/get_monthly_report_configs` |
| `set_monthly_report_configs` | `power_service/v1/app/set_monthly_report_configs` |

#### Additional Utility Endpoints
| Key | Path | Description |
|-----|------|-------------|
| `get_site_detail_by_sn` | `.../site/get_site_detail_by_sn` | Reverse lookup site by device SN |
| `get_all_service_config` | `.../get_all_service_config` | All service configuration |
| `get_message_sn_list` | `.../get_message_sn_list` | Message-enabled device SNs |
| `add_electrician` | `.../site/electrician/add` | Add installer to site |
| `get_electrician` | `.../site/electrician/get` | Get installer info |
| `get_device_bind_details` | `.../app/get_device_bind_details` | Device binding details |
| `get_strategy_last_record` | `.../app/get_strategy_last_record` | Last strategy record |
| `site_data_exported` | `.../site/site_data_exported` | Export site data |
| `relate_device` | `app/devicerelation/relate_device` | Relate/bind a device |
| `get_shared_device_relation` | `app/devicerelation/get_shared_device` | Shared device details |
| `update_device_alias` | `app/devicerelation/up_alias_name` | Update device alias |
| `get_mi_status` | `charging_pv_svc/getMiStatus` | Micro inverter status |

### 4. MQTT Enhancements

The following improvements were made to the MQTT module (`mqtt.py`):

- **Gzip decompression** (implemented): `_try_decompress()` detects gzip magic bytes (`\x1f\x8b`) and decompresses transparently. Non-gzip payloads pass through unchanged. Safe for all existing users.
- **Port 443 TLS fallback** (implemented): `connect_client_async()` tries port 8883 first, falls back to 443 on failure. Primary port retried on each reconnect. Enables operation behind restrictive firewalls.
- **Topic suffix logging**: 6 APK-discovered topic suffixes (`/thing/product/device`, `/ota/firmware`, `/shadow/update`, `/rule/action`, `/thing/event/post`, `/thing/property/set`) logged at debug level for future handler development.
- **5 previously disabled commands**: The `SolixMqttCommands` dataclass includes commands identified in the APK but marked as cloud-driven: `sb_3rd_party_pv_switch`, `sb_ev_charger_switch`, `sb_usage_mode`, `plug_schedule`, `plug_delayed_toggle`. These remain as TODO stubs.

### 5. HA Integration Wiring

- **manifest.json**: `after_dependencies: ["bluetooth"]` (optional, not hard dependency), `bluetooth` matchers for auto-discovery, `bleak`/`bleak-retry-connector`/`cryptography` in requirements, `iot_class` remains `cloud_polling`
- **`__init__.py`**: `_async_setup_ble()` creates BLE coordinator if Bluetooth scanners available, registers UUID-based discovery callback, graceful skip if no BLE hardware
- **`config_flow.py`**: `async_step_bluetooth()` redirects to cloud credentials setup
- **`ble_coordinator.py`**: Manages multiple BLE connections, adaptive polling, cloud coordinator overlay (debug stage)

---

## Known Opcodes (BLE TLV Commands)

| Family | Opcode Range | Purpose | Example |
|--------|-------------|---------|---------|
| Device Info | `0x71xx` | Device state, battery, power, WiFi, firmware | `GET_BATTERY_INFO = 0x7109` |
| Config | `0x73xx` | Min SOC, output mode, AC/PV limits, EMS, CT, TOU | `SET_MIN_SOC = 0x7304` |
| Advanced | `0x75xx` | Advanced operations | (reserved) |
| Solix | `0xA5xx` | Scene, energy, status, abilities | `SOLIX_GET_STATUS = 0xA550` |

Full opcode list in `solixapi/ble/tlv.py` (40+ opcodes).

---

## Acknowledgments & Credits

This work would not have been possible without the contributions of several open-source developers and projects:

- **[@thomluther](https://github.com/thomluther)** -- Creator and maintainer of the [ha-anker-solix](https://github.com/thomluther/ha-anker-solix) integration that this branch extends. Also author of [AnkerSolixBLE](https://github.com/thomluther/AnkerSolixBLE), a telemetry-only BLE reference implementation that helped validate our data structures and byte offsets.

- **[@flip-dots](https://github.com/flip-dots)** -- Author of [SolixBLE](https://github.com/flip-dots/SolixBLE), the most comprehensive BLE protocol reverse engineering for Anker Solix devices. Our TLV-based telemetry parser, scaling factors, and all 26 TLV tag definitions are directly derived from SolixBLE's implementation. Also author of [HaSolixBLE](https://github.com/flip-dots/HaSolixBLE) which provided HA-specific integration patterns (config flow, coordinator, entity structure).

- **[@moag1000](https://github.com/moag1000)** -- Author of [beurer_daylight_lamps](https://github.com/moag1000/beurer_daylight_lamps), whose HA BLE integration patterns we adapted: `bleak-retry-connector` usage, exponential backoff reconnection, multi-adapter support, adaptive polling intervals, and connection health metrics.

- **[bleak](https://github.com/hbldh/bleak)** (Henrik Blidh et al.) and **[bleak-retry-connector](https://github.com/bluetooth-devices/bleak-retry-connector)** (J. Nick Koston / @bdraco) -- BLE GATT communication and robust connection management libraries.

- **[Eclipse Paho MQTT](https://github.com/eclipse/paho.mqtt.python)** -- MQTT client library used for the cloud pub/sub channel.

---

## Dependencies

- `bleak>=0.19.0` -- BLE GATT communication
- `bleak-retry-connector>=3.0.0` -- Robust connection management with multi-adapter
- `cryptography>=3.4.8` -- ECDH + AES (already existing)
- `paho-mqtt>=2.1.0` -- MQTT client (already existing)

---

## TODO

### Done
- [x] BLE module: ECDH crypto, TLV encoding, client with TLV-based telemetry parsing (26 fields)
- [x] BLE connection management with exponential backoff (beurer_daylight_lamps patterns)
- [x] BLE coordinator with adaptive polling (30s/5min/15min)
- [x] HA config flow `async_step_bluetooth()` for BLE discovery
- [x] HA `bluetooth` matchers in manifest for auto-discovery
- [x] BLE coordinator wired into HA lifecycle (setup, shutdown, discovery callback)
- [x] MQTT gzip decompression (`_try_decompress()`, magic byte detection)
- [x] MQTT port 443 TLS fallback for restrictive networks
- [x] Range Extender System (A7320) -- 12 endpoints defined, API methods implemented
- [x] AI EMS profit endpoints (power_service + HES paths)
- [x] Device income, Shelly status, site-detail-by-SN API methods
- [x] VPP / Evergen -- 5 endpoints defined in `API_ENDPOINTS`
- [x] Dynamic Pricing -- 5 new endpoints added (plan, rates, providers, adjust)
- [x] Auto Disaster Preparedness -- 4 HES endpoints defined
- [x] AI EMS via HES -- 3 endpoints defined + `hes_authorize_aiems`, `hes_enable_aiems_mode4`
- [x] Location Services -- 3 endpoints defined + `get_device_location`, `set_device_location`
- [x] EV Charger Orders -- 3 endpoints defined
- [x] Monthly/Annual Reports -- 4 endpoints defined
- [x] Manifest: `after_dependencies: ["bluetooth"]`, `bleak` requirements, `iot_class: cloud_polling`
- [x] Utility endpoints: electrician, device bind details, strategy record, device alias, service config
- [x] Telemetry scaling factors verified against flip-dots/SolixBLE reference
- [x] Battery energy divisor fix (/100 -> /10, matching other energy fields)
- [x] TLV-based parsing replacing fragile fixed byte offsets
- [x] Cloud coordinator overlay: BLE data written into cloud coordinator data dict for entity fallback during cloud outages
- [x] API methods for VPP/Evergen (5), Dynamic Pricing (5), EV Orders (3), Reports (4), MI Status (1) — total 18 new methods

### Pending
- [ ] BLE entity platform: Create dedicated HA sensor entities from BLE telemetry (currently BLE supplements existing cloud entities via overlay)
- [ ] Local LAN fallback (`10.10.100.254` AP mode)
- [ ] Enable cloud-driven MQTT commands for local control
- [ ] BLE config flow option to enable/disable BLE (currently auto-enabled)
- [ ] Integration tests for BLE module
- [ ] Integration tests for new API methods
- [ ] Real-device validation of TLV parsing with Solarbank 2 E1600 Pro (A17C1)
