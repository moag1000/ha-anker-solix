# Gap Analysis: APK Findings vs Implementation

> Cross-reference of APK v3.18.0 `strings` findings against the current `ha-anker-solix` codebase.
> Date: 2026-03-19 | Branch: `feat/new-api-endpoints`
>
> This documents what is **missing or incomplete**. Nothing here is verified against the live API.

---

## Table of Contents

- [1. API Endpoint Gaps](#1-api-endpoint-gaps)
  - [1a. Dict + Fileprefix but No Implementation](#1a-dict--fileprefix-but-no-implementation)
  - [1b. Entire Services Not in Any Dict](#1b-entire-services-not-in-any-dict)
  - [1c. HES Endpoints Only in Comment Section](#1c-hes-endpoints-only-in-comment-section)
  - [1d. New Methods Not Wired to Poller/Cache](#1d-new-methods-not-wired-to-pollercache)
- [2. MQTT Gaps](#2-mqtt-gaps)
  - [2a. Device Models Missing from MQTT Map](#2a-device-models-missing-from-mqtt-map)
  - [2b. Gzip Decompression](#2b-gzip-decompression)
  - [2c. SceneInfo via MQTT](#2c-sceneinfo-via-mqtt)
  - [2d. MQTT Feature State Models](#2d-mqtt-feature-state-models)
  - [2e. IoT SDK Commands](#2e-iot-sdk-commands)
  - [2f. Action Commands](#2f-action-commands)
  - [2g. Local MQTT / Local Device API](#2g-local-mqtt--local-device-api)
- [3. Device Model Gaps](#3-device-model-gaps)
  - [3a. In APK but Not in SolixDeviceCategory](#3a-in-apk-but-not-in-solixdevicecategory)
  - [3b. In APK but Not in MQTT Map](#3b-in-apk-but-not-in-mqtt-map)
- [4. Summary Table](#4-summary-table)

---

## 1. API Endpoint Gaps

### 1a. Dict + Fileprefix but No Implementation

These 4 HES disaster preparedness endpoints have entries in `API_HES_SVC_ENDPOINTS` and `API_FILEPREFIXES` but **zero** methods in `api.py`, `hesapi.py`, `poller.py`, or anywhere else:

| Dict Key | Endpoint Path | Why It Matters |
|----------|--------------|----------------|
| `get_auto_disaster_status` | `charging_hes_svc/get_auto_disaster_prepare_status` | Storm guard auto-mode status |
| `get_auto_disaster_detail` | `charging_hes_svc/get_auto_disaster_prepare_detail` | Storm guard detail |
| `get_current_disaster_detail` | `charging_hes_svc/get_current_disaster_prepare_detail` | Active storm event detail |
| `get_backup_history` | `charging_hes_svc/get_back_up_history` | Backup event history |

**Status:** Dict entry and fileprefix exist — needs api.py method, poller integration, cache handling.

---

### 1b. Entire Services Not in Any Dict

These service prefixes were added to `ApiEndpointServices` but none of their endpoints are in any endpoint dict:

#### charging_hes_dynamic_price_svc (6 endpoints)
HES-specific dynamic pricing — separate from the `power_service` dynamic pricing that IS implemented.

| APK Endpoint | Purpose |
|-------------|---------|
| `charging_hes_dynamic_price_svc/get_area_by_code` | Area lookup by code |
| `charging_hes_dynamic_price_svc/get_price` | Get current dynamic price |
| `charging_hes_dynamic_price_svc/get_price_company` | Get pricing provider |
| `charging_hes_dynamic_price_svc/get_third_jump_url` | Third-party redirect (Tibber/Octopus auth?) |
| `charging_hes_dynamic_price_svc/save_dynamic_price` | Save dynamic price config |
| `charging_hes_dynamic_price_svc/save_time_of_use` | Save TOU schedule |

#### charging_disaster_prepared (7 endpoints)
Power Panel (A17B1) disaster preparedness — separate from the HES storm guard endpoints.

| APK Endpoint | Purpose |
|-------------|---------|
| `charging_disaster_prepared/get_site_device_disaster` | Get disaster config |
| `charging_disaster_prepared/get_site_device_disaster_status` | Get disaster status |
| `charging_disaster_prepared/set_site_device_disaster` | Set disaster config |
| `charging_disaster_prepared/clear` | Clear disaster state |
| `charging_disaster_prepared/quit_disaster_prepare` | Exit disaster mode |
| `charging_disaster_prepared/get_support_func` | Check supported functions |
| `charging_disaster_prepared/disaster_detail` | Disaster detail |

#### charging_imsg_svc (2 endpoints)
Fault/alarm messaging service.

| APK Endpoint | Purpose |
|-------------|---------|
| `charging_imsg_svc/remove_user_floating_fault_info` | Clear floating fault |
| `charging_imsg_svc/user_fault_alarm` | Fault alarm notification |

**Status:** Service prefix constants exist in `ApiEndpointServices` — needs dict entries, fileprefixes, methods, etc.

---

### 1c. HES Endpoints Only in Comment Section

These `charging_hes_svc` endpoints are in the comment block of `apitypes.py` (not in any active dict). Potentially useful ones:

| Endpoint | Why It Could Matter |
|----------|-------------------|
| `get_station_config_and_status` | Station configuration and status — core data |
| `get_tou_price_plan_detail` | Time-of-use price plan details |
| `get_external_device_config` | External device config (heat pump, etc.) |
| `get_device_pn_info` | Device part number info |
| `get_device_command` / `device_command` | Send/get device commands |
| `download_energy_statistics` | Energy data download/export |
| `get_utility_rate_plan` | HES utility rate plan |
| `update_hes_utility_rate_plan` | Update HES rate plan |
| `get_history_setting` | History settings |
| `check_update` / `ota` | Firmware check and update |
| `device_self_check` / `get_device_self_check` | System self-check |
| `get_device_card_list` / `get_device_card_details` | Device cards |

Also notable in `charging_energy_service` (Power Panel) comment section:
- `restart_peak_session` — restart peak session
- `preprocess_utility_rate_plan` / `ack_utility_rate_plan` — rate plan management
- `adjust_station_price_unit` — price unit adjustment
- `sync_config` / `sync_installation_inspection` — sync operations

---

### 1d. New Methods Not Wired to Poller/Cache

ALL newly added api.py methods from `feat/new-api-endpoints` are **standalone** — they can be called but are **not integrated** into the poller refresh cycle or cache update logic. They return raw API responses only.

| Feature Area | Methods | Poller? | Cache? |
|-------------|---------|---------|--------|
| Range Extender (12) | `get_extender_system_list`, `get_extender_system_detail`, etc. | No | No |
| VPP / Evergen (5) | `vpp_get_enrollment_status`, `vpp_get_policy`, etc. | No | No |
| Dynamic Pricing (5) | `get_dynamic_price_plan`, `get_dynamic_price_rates`, etc. | No | No |
| Location (3) | `get_device_location`, `set_device_location`, `check_location_support` | No | No |
| Electrician (2) | `add_electrician`, `get_electrician` | No | No |
| Device Mgmt (3) | `get_device_bind_details`, `get_strategy_last_record`, `site_data_exported` | No | No |
| Reports (4) | `get_annual_report`, `get_monthly_report_list`, etc. | No | No |
| EV Orders (3) | `get_charging_order_list`, `get_charging_order_detail`, `export_charge_order` | No | No |
| AI EMS HES (3) | `hes_authorize_aiems`, `hes_enable_aiems_mode4`, `hes_get_aiems_profit` | No | No |
| MI Status (1) | `get_mi_status` | No | No |
| Batch OTA (1) | `batch_check_update` | No | No |
| Device Relations (3) | `relate_device`, `get_shared_device_relation`, `update_device_alias` | No | No |

**Impact:** These methods exist and work for manual/export use, but HA entities cannot be created until poller/cache integration happens. That requires live API response data to know the actual JSON structure.

---

## 2. MQTT Gaps

### 2a. Device Models Missing from MQTT Map

Current `mqttmap.py` has 27 device entries. These APK-referenced models have **no MQTT map**:

| Model | Device | Notes |
|-------|--------|-------|
| **A5190** | Smart EV Charger (WiFi only) | Only A5191 has MQTT map |
| **A7320** | Range Extender / Generator | New device type, no MQTT at all |
| **A17A0-A17A5** | Power Coolers / Everfrost | 6 models, APK has `a17a3` decoder name |
| **A17E1** | Solarbank Prime E10 (US) | In SolixDeviceCategory but not MQTT |
| **A1725** | C200(X) | Similar to A1722 but no mapping |
| **A1727** | C200 DC | Similar to A1726 but no mapping |
| **A1729** | C200X DC | Similar to A1728 but no mapping |
| **A1753-A1755** | C800 / C800 Plus / C800X | No mapping |
| **A1762** | Portable Power Station 1000 | No mapping |
| **A1765** | C1000X Gen 2 | No mapping |
| **A1770** | F1200 (BT) | No mapping |
| **A1771** | F1200 (BT+WLAN) | APK has `a1771` decoder name |
| **A1772** | F1500 | No mapping |
| **A1781** | F2600 | APK has `a1781` decoder name |
| **A1783** | C2000 Gen 2 | In SolixDeviceCategory, no MQTT |
| **A1785** | C2000X Gen 2 | In SolixDeviceCategory, no MQTT |
| **A110A, A110B** | Power Banks | No MQTT |
| **A2687, A25X7, A91B2, A1903** | Chargers (sub-models) | Only A2345 has MQTT map |

Many of these probably share MQTT maps with similar models (e.g., A1725 likely uses A1722's map). But no aliasing is set up.

---

### 2b. Gzip Decompression

**APK:** `MqttDecompressionUtil` transparently decompresses gzip MQTT payloads.

**Code:** `session.py` line 8 has `# TODO(COMPRESSION): from gzip import compress, decompress`. HTTP responses use aiohttp's auto-decompression, but **MQTT binary payloads have no gzip handling**.

**Impact:** If Anker starts sending gzip-compressed MQTT payloads (as the APK is prepared for), the integration would fail to decode them.

---

### 2c. SceneInfo via MQTT

**APK:** `SceneInfo` is the main MQTT payload type. The app receives `SceneInfo` via MQTT push — the same data structure returned by the `get_scen_info` REST endpoint. This is how the app gets real-time site overview updates without polling.

**Code:** `scene_info` is fetched via REST API only (`get_scene_info()` in `apibase.py`). The MQTT layer processes only binary hex telemetry (device-level data from `mqttmap.py`), not JSON `SceneInfo` payloads.

**Impact:** The integration polls `scene_info` at intervals instead of receiving real-time MQTT pushes. This is why the APK app responds faster to state changes.

---

### 2d. MQTT Feature State Models

APK has dedicated MQTT state handlers for features the integration doesn't process via MQTT:

| Model Class | Feature | In Code? |
|-------------|---------|----------|
| `MqttAIEmsStateModel` | AI EMS state pushed in real time | No |
| `A5101MqttAutoDisasterStateModel` | Storm guard auto-disaster state | No |
| `A5101MQTTDeviceInfoModel` | HES device info via MQTT | No |
| `MqttResultModel` | Generic MQTT operation result | No |

**Impact:** These features could be updated in real-time via MQTT but currently rely on REST polling only.

---

### 2e. IoT SDK Commands (akiot.*)

**APK:** 76 `akiot.*` commands found — these are the native SDK bridge between Flutter and the AKIoT native library.

**Code:** Zero `akiot.*` references anywhere in the codebase.

Relevant categories:
- `akiot.device.read_property` / `write_property` / `invoke_action` — device control
- `akiot.ems.get_ems_mode` / `set_ems_mode` — EMS mode switching
- `akiot.mqtt.publish_message` / `subscribe_topic` — MQTT operations
- `akiot.energy.*` — energy data and fault info
- `akiot.pairing.*` — device pairing (BLE + WiFi)
- `akiot.initflow.*` — site/device setup

**Impact:** These are internal SDK method calls, not REST endpoints. They wrap MQTT commands and BLE operations. The integration already implements MQTT commands directly via `mqttmap.py` — the `akiot.*` names are the app-layer wrappers, not a separate protocol. Low priority.

---

### 2f. Action Commands

**APK:** 48 `action_set_*` commands + 13 control actions found in binary.

**Code:** No `action_set_*` or `action_get_*` patterns in the codebase. However, many of these overlap functionally with existing MQTT commands in `mqttcmdmap.py` under different names.

Potentially new actions not covered by existing MQTT commands:

| Action | Purpose | Existing MQTT Equivalent? |
|--------|---------|--------------------------|
| `action_set_oil_machine_params` | Generator params | No — A7320 not in MQTT |
| `action_set_standby_oil_machine_params` | Generator standby | No |
| `action_set_third_oil_AX170` | Third-party oil device | No |
| `action_set_third_oil_params` | Third-party oil params | No |
| `action_set_third_oil_type` | Third-party oil type | No |
| `action_set_distribution_box` | Distribution box config | No |
| `action_set_third_party_pv` | Third-party PV settings | Partially (0085 msg type) |
| `action_set_custom_branch` | Branch circuit setup | No |
| `action_set_tou_system_params` | TOU system params | Partially (schedule commands) |
| `action_set_car_charger_params` | EV charger params | Partially (EV MQTT commands) |

---

### 2g. Local MQTT / Local Device API

**APK:** References to `http://10.10.100.254` (local device API), port 5353 (mDNS), `supportModbusTcp` flag.

**Code:** Cloud MQTT only (`aiot-mqtt-eu.anker.com:8883`). No local connectivity.

**Impact:** Local control would enable offline operation — the original motivation for this APK analysis project. This requires implementing:
1. mDNS discovery (port 5353)
2. Local HTTP API at `10.10.100.254`
3. Possibly local MQTT on the device
4. Modbus TCP (if device supports `supportModbusTcp`)

---

## 3. Device Model Gaps

### 3a. In APK but Not in SolixDeviceCategory

These device identifiers appear in APK strings but have no entry in `SolixDeviceCategory`:

| Model | Possible Type | Notes |
|-------|--------------|-------|
| A17D0 | Unknown | New model, no info |
| A17D4 | Unknown | New model, no info |
| A17Y0 | Unknown | New model, no info |
| A1340 | Unknown | Possibly power bank accessory |
| A120J | Unknown | Possibly power bank |
| A110G | Power Bank variant? | Similar to A110A/A110B range |
| AX1C0 | Unknown | AX-series, possibly HES-related |
| AS200 | PPS variant? | Similar to AS100 pattern |
| A5141 | Inverter variant? | Between A5140 and A5143 |
| A5142 | Inverter variant? | Between A5140 and A5143 |
| A520 | Unknown | Partial string? |
| A2693E1 | Charger variant? | A26xx series |
| A2693E2 | Charger variant? | A26xx series |

Sub-variants not in code (probably map to parent model):
- A1782A-H, A1782L-S, A1782W (F3000 variants)
- A1790B/D/G/H/S/T (F3800 variants)
- A2687B-G, A2687L (160W charger variants)
- A5101 has 20+ sub-variants (X1 regional variants)
- A5191 has 10+ sub-variants (EV charger regional variants)

### 3b. In APK but Not in MQTT Map

See section [2a](#2a-device-models-missing-from-mqtt-map) above. Key missing models:
- **A7320** — completely new device type with no MQTT support
- **A5190** — EV charger variant, only A5191 has MQTT
- **A17A0-A17A5** — entire Power Cooler family
- **~15 PPS models** — likely need aliases to existing maps

---

## 4. Summary Table

| Category | Found in APK | In Code | Gap |
|----------|-------------|---------|-----|
| **REST API Endpoints** | ~333 | ~188 in dicts | ~145 not in any dict |
| **REST API Methods** | — | ~80 methods | 4 dict entries have no method |
| **Poller/Cache Integration** | — | ~45 new methods | 45 methods not in poller |
| **Service Prefixes** | 12 | 7 in `ApiEndpointServices` | 5 services not referenced |
| **MQTT Device Models** | 95+ identifiers | 27 in mqttmap.py | ~68 not in MQTT map |
| **MQTT Feature States** | 4 state models | 0 | 4 missing |
| **MQTT Gzip** | Used (`MqttDecompressionUtil`) | TODO only | Not implemented |
| **MQTT SceneInfo** | Main payload type | Not processed | REST polling only |
| **IoT SDK Commands** | 76 akiot.* | 0 | Low priority (internal SDK) |
| **Action Commands** | 61 total | ~40 MQTT cmds (overlap) | ~10 genuinely new |
| **Device Categories** | 95+ models | 62 in SolixDeviceCategory | ~13 unknown models |
| **Local Control** | mDNS, local HTTP, Modbus | None | Not implemented |

### What Blocks Progress

Most gaps **cannot be closed without live API testing**:
1. New API methods return raw responses — we don't know the JSON structure
2. Poller/cache integration requires knowing which fields exist in responses
3. HA entities require knowing field types, units, and update frequency
4. MQTT state models require captured message samples

The APK tells us **what endpoints exist** and **what field names to expect**, but the actual response format, error handling, and data flow can only be determined with real hardware and active accounts.
