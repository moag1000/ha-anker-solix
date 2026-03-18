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

| Source | What it provided |
|--------|-----------------|
| **Anker App v3.18.0 APK** | Decompiled `libapp.so` + Dart analysis: REST endpoint URLs, MQTT topic structures, BLE GATT UUIDs, ECDH key material, TLV opcode tables, negotiation sequences |
| **[SolixBLE](https://github.com/flip-dots/SolixBLE)** (flip-dots) | BLE protocol reverse engineering: ECDH crypto flow, GATT characteristic UUIDs, packet framing, telemetry parsing offsets, command opcodes |
| **[AnkerSolixBLE](https://github.com/thomluther/AnkerSolixBLE)** (thomluther) | Telemetry-only BLE reference implementation, data structure validation |
| **[HaSolixBLE](https://github.com/flip-dots/HaSolixBLE)** (flip-dots) | HA integration patterns for BLE: config flow, coordinator, entity structure |
| **[beurer_daylight_lamps](https://github.com/moag1000/beurer_daylight_lamps)** (moag1000) | HA BLE best practices: `bleak-retry-connector` patterns, multi-adapter support, exponential backoff reconnection, connection health metrics |
| **Anker official HA integration** | Local Modbus TCP reference for `iot_class: local_polling` approach |

---

## New Features

### 1. BLE Communication Module (`solixapi/ble/`)

Complete BLE protocol implementation for direct device communication:

| File | Purpose |
|------|---------|
| `__init__.py` | Constants: GATT UUIDs, negotiation commands, telemetry offsets |
| `crypto.py` | ECDH key exchange (secp256r1) + AES-128-CBC session encryption |
| `tlv.py` | TLV command encoding/decoding with 40+ opcodes |
| `client.py` | Full BLE client with connection management and telemetry parsing |

**BLE Protocol Stack:**
1. Device discovery via `UUID_IDENTIFIER` (`0000ff09-...`)
2. GATT connection via `bleak-retry-connector` (with retry + multi-adapter)
3. 6-stage ECDH negotiation handshake
4. AES-128-CBC encrypted commands via `UUID_COMMAND` (`8c850002-...`)
5. Encrypted telemetry via `UUID_TELEMETRY` (`8c850003-...`)
6. Fragmented telemetry reassembly (large + small packet merging)

**Telemetry data available via BLE:**
- Battery percentage, temperature
- Solar power input (W)
- AC power output (W)
- Total solar/output energy (Wh)
- Battery stored energy, discharge power

**Connection features (inspired by beurer_daylight_lamps):**
- `bleak-retry-connector` with multi-adapter support (ESPHome/Shelly BLE proxies)
- Auto-reconnection with exponential backoff (3s initial, 120s max)
- Connection health metrics (reconnect count, command success/failure)
- Push update callback for coordinator integration
- HA Bluetooth stack integration (`bluetooth` dependency)

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

- **Gzip decompression**: Not yet implemented. The APK shows compressed MQTT payloads for certain device models; handler stubs are identified but decompression is pending.
- **Port 443 fallback**: Not yet implemented. The APK reveals a TLS-over-443 fallback path for restrictive networks where port 8883 is blocked. The current implementation uses port 8883 only.
- **New message handler stubs**: The APK-discovered topic structures are mapped in `mqttmap.py` and `mqttcmdmap.py`. New commands discovered from APK analysis include additional device status/control commands.
- **5 previously disabled commands**: The `SolixMqttCommands` dataclass includes commands that were identified in the APK but marked as cloud-driven (not directly controllable via MQTT publish): `sb_3rd_party_pv_switch`, `sb_ev_charger_switch`, `sb_usage_mode`, `plug_schedule`, `plug_delayed_toggle`. These remain as stubs and could potentially be enabled for local MQTT control.

### 5. Manifest Changes

- Added `bluetooth` to `dependencies` (for HA BLE stack)
- Added `bleak>=0.19.0` and `bleak-retry-connector>=3.0.0` to `requirements`
- Changed `iot_class` from `cloud_polling` to `local_polling`

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

## Dependencies

- `bleak>=0.19.0` -- BLE GATT communication
- `bleak-retry-connector>=3.0.0` -- Robust connection management with multi-adapter
- `cryptography>=3.4.8` -- ECDH + AES (already existing)
- `paho-mqtt>=2.1.0` -- MQTT client (already existing)

---

## TODO

### Done
- [x] BLE module: ECDH crypto, TLV encoding, client with telemetry parsing
- [x] BLE connection management with exponential backoff (beurer_daylight_lamps patterns)
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
- [x] Manifest updated (`bluetooth` dep, `bleak` requirements, `local_polling`)
- [x] Utility endpoints: electrician, device bind details, strategy record, device alias, service config

### Pending
- [ ] HA config flow with BLE device discovery
- [ ] BLE coordinator with adaptive polling intervals
- [ ] HA `bluetooth` matchers in manifest for auto-discovery
- [ ] Local LAN fallback (`10.10.100.254` AP mode)
- [ ] MQTT gzip decompression for compressed payloads
- [ ] MQTT port 443 fallback for restrictive networks
- [ ] Enable cloud-driven MQTT commands for local control
- [ ] API methods for remaining new endpoint groups (VPP, dynamic pricing, reports, EV orders)
- [ ] Integration tests for BLE module
- [ ] Integration tests for new API methods
