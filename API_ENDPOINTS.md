# API Endpoints - Reverse Engineered from Anker App v3.18.0

> **Data source:** Decompiled `libapp.so` (58 MB compiled Dart) from Anker App v3.18.0 APK
> **Total endpoints found:** ~347 | **Integration implements:** ~188 (across 3 dicts) | **Newly added:** ~45 | **Still unimplemented:** ~159

This document catalogues all API endpoints discovered through reverse engineering of the Anker mobile application, cross-referenced with the integration's `apitypes.py`. It serves as both a development roadmap and a PR description reference for the `feat/ble-and-local-features` branch.

---

## Table of Contents

- [Priority Legend](#priority-legend)
- [Architecture Overview](#architecture-overview)
- [Newly Added Endpoints (in API dicts)](#newly-added-endpoints)
  - [Range Extender System (A7320 Smart Meter Pro)](#range-extender-system-a7320-smart-meter-pro)
  - [AI EMS (HES)](#ai-ems-hes)
  - [VPP / Evergen (Virtual Power Plant)](#vpp--evergen-virtual-power-plant)
  - [Dynamic Pricing (Nordpool / Tibber)](#dynamic-pricing-nordpool--tibber)
  - [Auto Disaster Preparedness (Storm Guard)](#auto-disaster-preparedness-storm-guard)
  - [Location Services](#location-services)
  - [Useful Lookups](#useful-lookups)
  - [EV Charger Orders](#ev-charger-orders)
  - [Monthly / Annual Reports](#monthly--annual-reports)
  - [Device Management](#device-management)
  - [Electrician / Installer](#electrician--installer)
- [Previously Existing Endpoints (Reference)](#previously-existing-endpoints-reference)
- [Unimplemented Endpoints (Comment Section)](#unimplemented-endpoints-comment-section)
- [MQTT Command Gaps](#mqtt-command-gaps)
- [Potential HA Entities from New Endpoints](#potential-ha-entities-from-new-endpoints)
- [Integration Suggestions](#integration-suggestions)

---

## Priority Legend

| Icon | Priority | Description |
|------|----------|-------------|
| :red_circle: | **P1 (High)** | Direct user value, fills major functional gaps |
| :yellow_circle: | **P2 (Medium)** | Enhances existing features, useful for advanced users |
| :green_circle: | **P3 (Low)** | Niche, admin-only, or rarely needed |

---

## Architecture Overview

The Anker Cloud API is split across multiple service prefixes:

| Service Prefix | Dict in Code | Purpose | Implemented |
|---|---|---|---|
| `power_service/v1/` | `API_ENDPOINTS` | Solarbanks, Inverters, Smart Plugs, EV Chargers | 147 endpoints |
| `charging_energy_service/` | `API_CHARGING_ENDPOINTS` | Home Power Panel (A17B1), PPS in Home | 15 endpoints |
| `charging_hes_svc/` | `API_HES_SVC_ENDPOINTS` | Home Energy Systems (X1) | 26 endpoints |
| `charging_pv_svc/` | (in `API_ENDPOINTS`) | Standalone Anker inverters | 6 endpoints |
| `charging_common_svc/` | (in `API_ENDPOINTS`) | Location services | 3 endpoints |
| `mini_power/v1/` | (in `API_ENDPOINTS`) | Prime Charger devices | 5 endpoints |
| `app/` | (in `API_ENDPOINTS`) | Device management, OTA, sharing | 6 endpoints |
| `passport/` | (none) | Authentication (login handled separately) | 2 endpoints |
| `charging_hes_dynamic_price_svc/` | (none) | HES dynamic pricing | 0 endpoints |
| `charging_disaster_prepared/` | (none) | Power Panel disaster prep | 0 endpoints |

**All endpoints use HTTP POST** unless noted otherwise (`get_message_unread`, `get_message`, `get_product_categories`, `get_product_accessories` use GET).

---

## Newly Added Endpoints

These endpoints were newly added to the `API_ENDPOINTS`, `API_CHARGING_ENDPOINTS`, and `API_HES_SVC_ENDPOINTS` dictionaries based on APK reverse engineering.

---

### Range Extender System (A7320 Smart Meter Pro) :red_circle: P1

The Range Extender System manages multi-device solar setups with the A7320 Smart Meter Pro as a coordination hub. This is a key feature for users with larger installations.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_extender_system_list` | `power_service/v1/app/get_extender_system_list` | List all range extender systems for the account | `{}` | `sensor` - Discovery of available systems |
| `get_extender_system_detail` | `power_service/v1/app/get_extender_system_detail` | Get full detail for one range extender system | `{"system_id": systemId}` | `sensor` - System status, connected devices, power flow |
| `add_extender_system` | `power_service/v1/app/add_extender_system` | Create a new range extender system | System config object | `service` call - `anker_solix.add_extender_system` |
| `del_extender_system` | `power_service/v1/app/del_extender_system` | Delete a range extender system | `{"system_id": systemId}` | `service` call - Admin only |
| `update_extender_system_strategy` | `power_service/v1/app/update_extender_system_strategy` | Update power management strategy | Strategy config | `select` / `service` - Strategy selection |
| `get_extender_system_cumulative_data` | `power_service/v1/app/get_extender_system_cumulative_data` | Get cumulative energy data (total kWh) | `{"system_id": systemId}` | `sensor` - Total energy production/consumption |
| `set_extender_system_name` | `power_service/v1/app/set_extender_system_name` | Rename the system | `{"system_id": systemId, "name": newName}` | `text` entity or `service` call |
| `add_extender_system_device_list` | `power_service/v1/app/add_extender_system_device_list` | List devices eligible for addition | `{"system_id": systemId}` | Diagnostics / setup helper |
| `batch_add_extender_system_device` | `power_service/v1/app/batch_add_extender_system_device` | Batch add devices to the system | Device SN list | `service` call |
| `batch_del_extender_system_device` | `power_service/v1/app/batch_del_extender_system_device` | Batch remove devices from the system | Device SN list | `service` call |
| `get_extender_system_pn_ota` | `power_service/v1/app/get_extender_system_pn_ota` | Get OTA info for system devices | `{"system_id": systemId}` | `update` entity - Firmware update availability |
| `set_extender_system_cumulative_data` | `power_service/v1/app/set_extender_system_cumulative_data` | Set/correct cumulative data | Cumulative data object | `service` call - Manual correction |

---

### AI EMS (HES) :red_circle: P1

AI-based Energy Management System for Home Energy Systems (X1). These endpoints control the AI learning mode which optimizes battery charge/discharge based on usage patterns.

**In `API_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_ai_ems_status` | `power_service/v1/ai_ems/get_status` | Get AI learning status and remaining seconds | `{"site_id": siteId}` | `sensor` - AI status (untrained/learning/trained), `sensor` - remaining learning time |
| `get_ai_ems_profit` | `power_service/v1/ai_ems/profit` | Get AI EMS profit data (energy savings) | `{"site_id": siteId, "start_time": "00:00", "end_time": "24:00", "type": "grid"}` | `sensor` - Daily/cumulative savings in EUR/kWh |

**In `API_HES_SVC_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `authorize_aiems` | `charging_hes_svc/authorize_aiems` | Authorize AI EMS for HES site | `{"siteId": siteId}` | `switch` / `service` - Enable AI mode |
| `enable_aiems_mode4` | `charging_hes_svc/enable_aiems_mode4` | Enable AI EMS mode 4 | `{"siteId": siteId}` | `switch` - Specific AI mode toggle |
| `get_aiems_profit` | `charging_hes_svc/get_aiems_profit` | Get AI EMS profit via HES path | `{"siteId": siteId}` | `sensor` - Savings/profit tracking |

---

### VPP / Evergen (Virtual Power Plant) :yellow_circle: P2

Virtual Power Plant integration via Evergen. Allows battery systems to participate in grid balancing programs for financial incentives. Relevant for markets where VPP programs are active (AU, UK, parts of EU).

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `vpp_get_enrollment_status` | `power_service/v1/app/vpp/get_enrollment_status` | Check VPP enrollment status for site | `{"site_id": siteId}` | `binary_sensor` - Enrolled yes/no |
| `vpp_enrollment_verification` | `power_service/v1/app/vpp/enrollment_verification` | Verify/complete VPP enrollment | Enrollment data | `service` call |
| `vpp_get_policy` | `power_service/v1/app/vpp/get_policy` | Get VPP policy details (terms, compensation) | `{"site_id": siteId}` | `sensor` - Policy info as attributes |
| `vpp_dispatch_control` | `power_service/v1/app/vpp/dispatch_control` | Manual VPP dispatch control | Control params | `switch` / `service` - Override dispatch |
| `vpp_get_dispatch_history` | `power_service/v1/app/vpp/get_dispatch_history` | Get VPP dispatch event history | `{"site_id": siteId}` | `sensor` - Last dispatch event, total events |

**Additional VPP endpoints in unimplemented HES comments:**

| Path | Purpose |
|------|---------|
| `charging_hes_svc/get_vpp_check_code` | Get VPP verification code |
| `charging_hes_svc/get_vpp_service_policy_by_agg_user` | Get VPP service policy by aggregator user |

---

### Dynamic Pricing (Nordpool / Tibber) :yellow_circle: P2

Dynamic electricity pricing integration. Supports Nordpool (most EU countries) and Tibber as price providers. Enables the system to charge the battery during cheap periods and discharge during expensive ones.

**Already in `API_ENDPOINTS` (existing):**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_dynamic_price_sites` | `power_service/v1/dynamic_price/check_available` | Get site IDs with dynamic pricing | `{}` | Discovery |
| `get_dynamic_price_providers` | `power_service/v1/dynamic_price/support_option` | Get provider list for device | `{"device_pn": "A5102"}` | `select` - Provider selection |
| `get_dynamic_price_details` | `power_service/v1/dynamic_price/price_detail` | Get price data for area/date | `{"area": "GER", "company": "Nordpool", "date": "<posix_ts>", "device_sn": ""}` | `sensor` - Current/next hour price |

**Newly added:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_dynamic_price_plan` | `power_service/v1/dynamic_price/get_plan` | Get active dynamic price plan for site | `{"site_id": siteId}` | `sensor` - Active plan details |
| `set_dynamic_price_plan` | `power_service/v1/dynamic_price/set_plan` | Set/update dynamic price plan | Plan config | `service` / `select` - Plan configuration |
| `get_dynamic_price_rates` | `power_service/v1/dynamic_price/get_rates` | Get current dynamic price rates | Rate query params | `sensor` - Rate timeline as attributes |
| `check_dynamic_price_adjust` | `power_service/v1/dynamic_price/check_adjust` | Check price adjustment status | `{}` | `binary_sensor` - Adjustment active |
| `get_dynamic_price_provider_list` | `power_service/v1/dynamic_price/get_providers` | Get full provider list | `{}` | Configuration helper |

**Unimplemented HES Dynamic Price endpoints:**

| Path | Purpose | Params |
|------|---------|--------|
| `charging_hes_dynamic_price_svc/get_area_by_code` | Get area by country code | Needs owner |
| `charging_hes_dynamic_price_svc/get_price_company` | Get price company for area | Needs owner |
| `charging_hes_dynamic_price_svc/get_price` | Get dynamic prices | Needs owner |
| `charging_hes_dynamic_price_svc/save_time_of_use` | Save TOU tariff config | Needs owner |
| `charging_hes_dynamic_price_svc/save_dynamic_price` | Save dynamic price config | Needs owner |
| `charging_hes_dynamic_price_svc/get_third_jump_url` | Get third-party redirect URL (e.g., Tibber OAuth) | Unknown |

---

### Auto Disaster Preparedness (Storm Guard) :yellow_circle: P2

Storm Guard / Auto Disaster Preparedness automatically reserves battery capacity when severe weather is detected. Uses location data to check weather warnings.

**In `API_HES_SVC_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_auto_disaster_status` | `charging_hes_svc/get_auto_disaster_prepare_status` | Get Storm Guard enabled status | `{"siteId": siteId}` | `binary_sensor` - Storm Guard on/off |
| `get_auto_disaster_detail` | `charging_hes_svc/get_auto_disaster_prepare_detail` | Get Storm Guard config details | `{"siteId": siteId}` | `sensor` - Reserve SOC%, trigger conditions |
| `get_current_disaster_detail` | `charging_hes_svc/get_current_disaster_prepare_detail` | Get currently active storm event | `{"siteId": siteId}` | `binary_sensor` - Storm active, `sensor` - severity level |
| `get_backup_history` | `charging_hes_svc/get_back_up_history` | Get backup event history | `{"siteId": siteId}` | `sensor` - Last backup event as attributes |

**Unimplemented HES endpoints (also in comments):**

| Path | Purpose |
|------|---------|
| `charging_hes_svc/quit_auto_disaster_prepare` | Disable storm guard mode |
| `charging_hes_svc/sync_back_up_history` | Sync backup history |

**Unimplemented Power Panel disaster endpoints:**

| Path | Purpose | Params |
|------|---------|--------|
| `charging_disaster_prepared/get_site_device_disaster` | Get disaster status for Power Panel | `{"identifier_id": siteId, "type": 2}` |
| `charging_disaster_prepared/get_site_device_disaster_status` | Get disaster device status | `{"identifier_id": siteId, "type": 2}` |
| `charging_disaster_prepared/set_site_device_disaster` | Configure disaster preparedness | Unknown |
| `charging_disaster_prepared/clear` | Clear disaster state | Unknown |
| `charging_disaster_prepared/quit_disaster_prepare` | Exit disaster prep mode | Unknown |
| `charging_disaster_prepared/get_support_func` | Check supported functions | `{"identifier_id": siteId, "type": 2}` |
| `charging_disaster_prepared/disaster_detail` | Get current disaster detail | Unknown |

---

### Location Services :yellow_circle: P2

Location services for weather-based features (Storm Guard, solar forecasting). The device location is used to determine weather zone and solar irradiance predictions.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_device_location` | `charging_common_svc/location/get` | Get device location (lon/lat/country) | `{"identifier_id": deviceSn, "identifier_type": type, "business_type": type}` | `sensor` - Device coordinates as attributes |
| `set_device_location` | `charging_common_svc/location/set` | Set device location | Location data | `service` call - Override location |
| `check_location_support` | `charging_common_svc/location/support` | Check if location features supported | `{"identifier_id": deviceSn}` | Internal - Feature detection |

---

### Useful Lookups :red_circle: P1

General-purpose lookup endpoints that are valuable for device discovery and configuration.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_site_detail_by_sn` | `power_service/v1/site/get_site_detail_by_sn` | Reverse lookup: find site by device SN | `{"device_sn": deviceSn}` | Device setup / diagnostics |
| `get_all_service_config` | `power_service/v1/get_all_service_config` | Get all service configuration flags | `{}` | Internal - Feature flags for capabilities |
| `get_message_sn_list` | `power_service/v1/get_message_sn_list` | Get device SNs with messaging enabled | `{}` | Internal - Message routing |

---

### EV Charger Orders :green_circle: P3

EV charger session tracking and statistics. Only relevant for users with the Anker SOLIX V1 Smart EV Charger (A5191).

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_charging_order_list` | `power_service/v1/app/order/get_charging_order_list` | Get all charging orders in range | `{"device_sn": deviceSn, "start_time": "2026-02-09"}` | `sensor` - Session list, total kWh charged |
| `get_charging_order_detail` | `power_service/v1/app/order/get_charging_order_detail` | Get data points for a charging session | `{"device_sn": deviceSn, "order_id": orderId}` | `sensor` - Session energy, duration, cost |
| `export_charge_order` | `power_service/v1/app/order/export_charge_order` | Export charge order data (CSV?) | Unknown | `service` call |

**Also already existing in API_ENDPOINTS:**

| Key | Path | Purpose |
|-----|------|---------|
| `get_device_charge_order_stats` | `power_service/v1/app/order/get_charge_order_stats` | Aggregated stats (week/month/year/all) |
| `get_device_charge_order_stats_list` | `power_service/v1/app/order/get_charge_order_stats_list` | Paginated stats list |

---

### Monthly / Annual Reports :green_circle: P3

Report generation and retrieval. Useful for long-term monitoring dashboards.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_annual_report` | `power_service/v1/app/get_annual_report` | Get annual report (available since Jan 2025) | `{"site_id": siteId, "year": "2025"}` | `sensor` - Annual summary as attributes |
| `get_monthly_report_list` | `power_service/v1/app/mothly_report_list` | List existing monthly reports (**typo is intentional** - matches Anker API!) | `{"site_id": siteId}` | `sensor` - Available reports list |
| `get_monthly_report_configs` | `power_service/v1/app/get_monthly_report_configs` | Get monthly report notification settings | `{"site_id": siteId}` | Configuration helper |
| `set_monthly_report_configs` | `power_service/v1/app/set_monthly_report_configs` | Configure monthly report notifications | Config object | `switch` / `service` - Enable/disable reports |

> **Note:** `power_service/v1/app/mothly_report_show` exists in the unimplemented section and provides an HTML link to the actual report, but requires the Anker App to view.

---

### Device Management :green_circle: P3

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_device_bind_details` | `power_service/v1/app/get_device_bind_details` | Get device binding details | `{"device_sn": deviceSn}` | Diagnostics |
| `get_strategy_last_record` | `power_service/v1/app/get_strategy_last_record` | Get last strategy execution record | `{"device_sn": deviceSn}` | `sensor` - Last strategy change timestamp |
| `site_data_exported` | `power_service/v1/site/site_data_exported` | Export site data | `{"site_id": siteId}` | `service` call |
| `batch_check_update` | `app/ota/batch/check_update` | Batch check firmware updates | Device SN list | `update` entity |
| `relate_device` | `app/devicerelation/relate_device` | Relate/bind a device | Device data | `service` call |
| `get_shared_device_relation` | `app/devicerelation/get_shared_device` | Get shared device relation | `{"device_sn": deviceSn}` | Diagnostics |
| `update_device_alias` | `app/devicerelation/up_alias_name` | Update device alias name | `{"device_sn": deviceSn, "alias_name": name}` | `text` entity |
| `get_mi_status` | `charging_pv_svc/getMiStatus` | Get micro inverter status | `{"device_sn": deviceSn}` | `sensor` - MI operational status |

---

### Electrician / Installer :green_circle: P3

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `add_electrician` | `power_service/v1/site/electrician/add` | Add electrician/installer to site | Installer details | `service` call - Setup only |
| `get_electrician` | `power_service/v1/site/electrician/get` | Get installer info for site | `{"site_id": siteId}` | `sensor` - Installer contact as attributes |

---

## Previously Existing Endpoints (Reference)

These endpoints were already in the integration before the APK analysis. Listed here for completeness.

<details>
<summary><b>API_ENDPOINTS - Core Power Service (click to expand)</b></summary>

### Site Management

| Key | Path | Purpose |
|-----|------|---------|
| `homepage` | `power_service/v1/site/get_site_homepage` | App home page scene info |
| `site_list` | `power_service/v1/site/get_site_list` | List available sites |
| `site_detail` | `power_service/v1/site/get_site_detail` | Site details by site_id |
| `site_rules` | `power_service/v1/site/get_site_rules` | Supported power site types |
| `scene_info` | `power_service/v1/site/get_scen_info` | Scene info (main data source) |
| `user_devices` | `power_service/v1/site/list_user_devices` | Owned device list |
| `charging_devices` | `power_service/v1/site/get_charging_device` | Portable power stations |
| `get_device_parm` | `power_service/v1/site/get_site_device_param` | Device settings by param type (1-26) |
| `set_device_parm` | `power_service/v1/site/set_site_device_param` | Apply device settings |
| `energy_analysis` | `power_service/v1/site/energy_analysis` | Energy data for time frames |
| `home_load_chart` | `power_service/v1/site/get_home_load_chart` | Schedule adjustment chart |
| `wifi_list` | `power_service/v1/site/get_wifi_info_list` | Available WiFi networks |
| `get_site_price` | `power_service/v1/site/get_site_price` | Power price and CO2 |
| `update_site_price` | `power_service/v1/site/update_site_price` | Update power price |
| `get_forecast_schedule` | `power_service/v1/site/get_schedule` | Remaining energy & negative price slots |
| `get_co2_ranking` | `power_service/v1/site/co2_ranking` | CO2 ranking for SB2/3 |
| `get_site_power_limit` | `power_service/v1/site/get_power_limit` | Power limits for system |

### App/Device Endpoints

| Key | Path | Purpose |
|-----|------|---------|
| `get_auto_upgrade` | `power_service/v1/app/get_auto_upgrade` | Auto-upgrade config |
| `set_auto_upgrade` | `power_service/v1/app/set_auto_upgrade` | Set auto-upgrade |
| `bind_devices` | `power_service/v1/app/get_relate_and_bind_devices` | Bound devices with firmware info |
| `get_device_load` | `power_service/v1/app/device/get_device_home_load` | Device schedule |
| `set_device_load` | `power_service/v1/app/device/set_device_home_load` | Set device schedule |
| `get_ota_info` | `power_service/v1/app/compatible/get_ota_info` | OTA status |
| `get_ota_update` | `power_service/v1/app/compatible/get_ota_update` | Available OTA update |
| `solar_info` | `power_service/v1/app/compatible/get_compatible_solar_info` | Solar inverter definitions |
| `get_cutoff` | `power_service/v1/app/compatible/get_power_cutoff` | Min SOC settings |
| `set_cutoff` | `power_service/v1/app/compatible/set_power_cutoff` | Set Min SOC |
| `compatible_process` | `power_service/v1/app/compatible/get_compatible_process` | Solar info + OTA codes |
| `get_device_fittings` | `power_service/v1/app/get_relate_device_fittings` | Accessories (e.g., 0W Switch) |
| `get_upgrade_record` | `power_service/v1/app/get_upgrade_record` | Firmware update history |
| `check_upgrade_record` | `power_service/v1/app/check_upgrade_record` | Single upgrade record |
| `get_device_attributes` | `power_service/v1/app/device/get_device_attrs` | Device attributes (rssi, limits, etc.) |
| `set_device_attributes` | `power_service/v1/app/device/set_device_attrs` | Set device attributes |
| `get_config` | `power_service/v1/app/get_config` | Config list |
| `get_installation` | `power_service/v1/app/compatible/get_installation` | Install mode & solar SN |
| `set_installation` | `power_service/v1/app/compatible/set_installation` | Set installation mode |
| `get_third_platforms` | `power_service/v1/app/third/platform/list` | Third-party device models |
| `get_token_by_userid` | `power_service/v1/app/get_token_by_userid` | Token for Shelly queries? |
| `get_shelly_status` | `power_service/v1/app/get_user_op_shelly_status` | Shelly operation status |
| `get_device_income` | `power_service/v1/app/device/get_device_income` | Device income data |
| `get_device_group` | `power_service/v1/app/group/get_group_devices` | Device grouping info |

### Vehicle & OCPP

| Key | Path | Purpose |
|-----|------|---------|
| `get_ocpp_endpoint_list` | `power_service/v1/app/get_ocpp_endpoint_list` | OCPP endpoints |
| `get_device_ocpp_info` | `power_service/v1/app/get_ocpp_info` | Device OCPP source |
| `get_vehicle_brands` | `power_service/v1/app/get_brand_list` | EV brand list |
| `get_vehicle_brand_models` | `power_service/v1/app/get_models` | Model list per brand |
| `get_vehicle_model_years` | `power_service/v1/app/get_model_years` | Production years per model |
| `get_vehicle_year_attributes` | `power_service/v1/app/get_model_list` | Attributes per model+year |
| `get_user_vehicles` | `power_service/v1/app/vehicle/get_vehicle_list` | User's vehicle list |
| `get_user_vehicle_details` | `power_service/v1/app/vehicle/get_vehicle_detail` | Vehicle details |
| `vehicle_add` | `power_service/v1/app/vehicle/add_vehicle` | Add vehicle |
| `vehicle_update` | `power_service/v1/app/vehicle/update_vehicle` | Update vehicle |
| `vehicle_delete` | `power_service/v1/app/vehicle/delete_vehicle` | Delete vehicle |
| `vehicle_set_charging` | `power_service/v1/app/vehicle/set_charging_vehicle` | Link vehicle to EV charger |
| `vehicle_set_default` | `power_service/v1/app/vehicle/set_default` | Set default vehicle |

### Other

| Key | Path | Purpose |
|-----|------|---------|
| `get_tamper_records` | `power_service/v1/device/get_tamper_records` | Tamper detection records |
| `get_currency_list` | `power_service/v1/currency/get_list` | Supported currencies |
| `get_message_unread` | `power_service/v1/get_message_unread` | Unread messages (GET) |
| `get_message` | `power_service/v1/get_message` | Message list (GET) |
| `get_product_categories` | `power_service/v1/product_categories` | Product catalog (GET) |
| `get_product_accessories` | `power_service/v1/product_accessories` | Accessories catalog (GET) |
| `get_device_rfid_cards` | `power_service/v1/rfid/get_device_cards` | RFID cards for EV charger |
| `get_ota_batch` | `app/ota/batch/check_update` | Batch OTA check |
| `get_mqtt_info` | `app/devicemanage/get_user_mqtt_info` | MQTT server and certificates |
| `get_shared_device` | `app/devicerelation/get_shared_device` | Device sharing details |

</details>

<details>
<summary><b>API_CHARGING_ENDPOINTS - Power Panel (click to expand)</b></summary>

| Key | Path | Purpose |
|-----|------|---------|
| `get_error_info` | `charging_energy_service/get_error_infos` | Error info for account |
| `get_system_running_info` | `charging_energy_service/get_system_running_info` | Cumulative energy savings |
| `energy_statistics` | `charging_energy_service/energy_statistics` | Energy stats (solar/hes/grid/home/pps/diesel) |
| `get_rom_versions` | `charging_energy_service/get_rom_versions` | Firmware versions |
| `get_device_info` | `charging_energy_service/get_device_infos` | WiFi/MAC info |
| `get_wifi_info` | `charging_energy_service/get_wifi_info` | Connected WiFi |
| `get_installation_inspection` | `charging_energy_service/get_installation_inspection` | Installation page tracking |
| `get_utility_rate_plan` | `charging_energy_service/get_utility_rate_plan` | Utility rate plan |
| `report_device_data` | `charging_energy_service/report_device_data` | Report device data |
| `get_configs` | `charging_energy_service/get_configs` | System configs |
| `get_sns` | `charging_energy_service/get_sns` | PPS serial numbers in Home |
| `get_monetary_units` | `charging_energy_service/get_world_monetary_unit` | Monetary units |

</details>

<details>
<summary><b>API_HES_SVC_ENDPOINTS - Home Energy System X1 (click to expand)</b></summary>

| Key | Path | Purpose |
|-----|------|---------|
| `get_product_info` | `charging_hes_svc/get_device_product_info` | HES device list |
| `get_heat_pump_plan` | `charging_hes_svc/get_heat_pump_plan_json` | Heat pump plan |
| `get_electric_plan_list` | `charging_hes_svc/get_electric_utility_and_electric_plan_list` | Energy plan by country/state |
| `get_system_running_info` | `charging_hes_svc/get_system_running_info` | System runtime info |
| `get_system_profit` | `charging_hes_svc/get_system_profit_detail` | Profit detail (day/week/month/year) |
| `energy_statistics` | `charging_hes_svc/get_energy_statistics` | Energy stats (solar/hes/grid/home) |
| `get_monetary_units` | `charging_hes_svc/get_world_monetary_unit` | Monetary units |
| `get_install_info` | `charging_hes_svc/get_install_info` | Installation location |
| `get_wifi_info` | `charging_hes_svc/get_wifi_info` | Device WiFi info |
| `get_installer_info` | `charging_hes_svc/get_installer_info` | Installer contact info |
| `get_system_running_time` | `charging_hes_svc/get_system_running_time` | System running time |
| `get_mi_layout` | `charging_hes_svc/get_mi_layout` | Micro inverter layout |
| `get_conn_net_tips` | `charging_hes_svc/get_conn_net_tips` | Connection tips |
| `get_hes_dev_info` | `charging_hes_svc/get_hes_dev_info` | HES device structure and SNs |
| `report_device_data` | `charging_hes_svc/report_device_data` | Report device data |
| `get_evcharger_standalone` | `charging_hes_svc/get_user_bind_and_not_in_station_evchargers` | Standalone EV chargers |
| `get_evcharger_station_info` | `charging_hes_svc/get_evcharger_station_info` | EV charger station info |

</details>

---

## Unimplemented Endpoints (Comment Section)

These ~159 endpoints are known from APK analysis but remain in the comment section of `apitypes.py` (lines ~299-528). They are not yet in any API dict.

<details>
<summary><b>Power Service - Site Management (24 endpoints)</b></summary>

| Path | Purpose | Notes |
|------|---------|-------|
| `power_service/v1/site/can_create_site` | Check if new site can be created | Setup |
| `power_service/v1/site/create_site` | Create a new site | Setup |
| `power_service/v1/site/update_site` | Update site configuration | Setup |
| `power_service/v1/site/delete_site` | Delete a site | Destructive |
| `power_service/v1/site/add_charging_device` | Add charging device to site | Setup |
| `power_service/v1/site/update_charging_device` | Update charging device | Setup |
| `power_service/v1/site/reset_charging_device` | Reset charging device | Admin |
| `power_service/v1/site/delete_charging_device` | Delete charging device | Destructive |
| `power_service/v1/site/add_site_devices` | Add devices to site | Setup |
| `power_service/v1/site/delete_site_devices` | Delete devices from site | Destructive |
| `power_service/v1/site/update_site_devices` | Update site devices | Setup |
| `power_service/v1/site/get_addable_site_list` | List sites a model can be added to | Setup |
| `power_service/v1/site/get_comb_addable_sites` | Get combinable addable sites | Setup |
| `power_service/v1/site/shift_power_site_type` | Convert system type | `{"site_id": siteId, "power_site_type": 11}` |
| `power_service/v1/site/local_net` | Local network info | Unknown |
| `power_service/v1/site/set_device_feature` | Set smart plug feature for site | `{"site_id": siteId, "smart_plug": [value]}` |
| `power_service/v1/site/site_data_check` | Check if site has data for date | `{"site_id": siteId, "current_time": "2025-12-10"}` |

</details>

<details>
<summary><b>Power Service - App Compatibility (7 endpoints)</b></summary>

| Path | Purpose | Notes |
|------|---------|-------|
| `power_service/v1/app/compatible/check_third_sn` | Check third-party serial number | Setup |
| `power_service/v1/app/compatible/confirm_permissions_settings` | Confirm permission settings | Setup |
| `power_service/v1/app/compatible/get_confirm_permissions` | Get permission confirmation | `{"device_model": "A17C0"}` |
| `power_service/v1/app/compatible/installation_popup` | Installation popup trigger | Setup |
| `power_service/v1/app/compatible/save_compatible_solar` | Save compatible solar config | Setup |
| `power_service/v1/app/compatible/set_ota_update` | Trigger OTA update | Admin |
| `power_service/v1/app/compatible/save_ota_complete_status` | Mark OTA as complete | Admin |

</details>

<details>
<summary><b>Power Service - Device Groups (5 endpoints)</b></summary>

| Path | Purpose | Notes |
|------|---------|-------|
| `power_service/v1/app/group/replace_group_devices` | Replace devices in group | Admin |
| `power_service/v1/app/group/save_group_devices` | Save group configuration | Admin |
| `power_service/v1/app/group/force_save_group_devices` | Force save group | Admin |
| `power_service/v1/app/group/delete_group_devices` | Delete device group | Destructive |

</details>

<details>
<summary><b>Power Service - Sharing (6 endpoints)</b></summary>

| Path | Purpose |
|------|---------|
| `power_service/v1/app/share_site/anonymous_join_site` | Anonymous site join |
| `power_service/v1/app/share_site/delete_site_member` | Remove site member |
| `power_service/v1/app/share_site/invite_member` | Invite member to site |
| `power_service/v1/app/share_site/delete_inviting_member` | Cancel invite |
| `power_service/v1/app/share_site/get_invited_list` | Get pending invites |
| `power_service/v1/app/share_site/join_site` | Join a site (accept invite) |

</details>

<details>
<summary><b>Power Service - After Sale (4 endpoints)</b></summary>

| Path | Purpose | Notes |
|------|---------|-------|
| `power_service/v1/app/after_sale/get_popup` | Get active popups | `{"site_id": siteId}` |
| `power_service/v1/app/after_sale/check_popup` | Check popup status | Unknown |
| `power_service/v1/app/after_sale/check_sn` | Check SN for battery recall eligibility | Safety |
| `power_service/v1/app/after_sale/mark_sn` | Mark SN (acknowledge recall) | Safety |

</details>

<details>
<summary><b>Power Service - Oil/Generator Maintenance (15 endpoints)</b></summary>

These are for generator-based hybrid systems (e.g., F3800 with generator). Lower priority for most EU users.

| Path | Purpose |
|------|---------|
| `power_service/v1/app/get_device_last_exercise_log` | Last exercise log |
| `power_service/v1/app/get_device_exercise_log` | Exercise log history |
| `power_service/v1/app/get_parts_maintenance_logs` | Parts maintenance logs |
| `power_service/v1/app/get_parts_maintenance_plan` | Maintenance plan |
| `power_service/v1/app/get_oil_consumption_reminder_plan_details` | Oil consumption reminder |
| `power_service/v1/app/get_device_exercise_details` | Exercise details |
| `power_service/v1/app/batch_maintain_oil_engine_parts` | Batch maintain parts |
| `power_service/v1/app/set_maintain_parts_notice_switch` | Maintenance notification |
| `power_service/v1/app/set_parts_maintenance_plan` | Set maintenance plan |
| `power_service/v1/app/set_oil_machine_exercise_plan` | Set exercise plan |
| `power_service/v1/app/start_oil_machine_exercise` | Start oil machine exercise |
| `power_service/v1/app/switch_exercise_mode` | Switch exercise mode |
| `power_service/v1/app/set_oil_consumption_reminder_switch` | Toggle oil reminder |
| `power_service/v1/app/set_oil_consumption_reminder_plan` | Set oil reminder plan |
| `power_service/v1/app/set_maintain_parts_ignore_reminders` | Ignore maintenance reminders |

</details>

<details>
<summary><b>Power Service - Miscellaneous (8 endpoints)</b></summary>

| Path | Purpose | Notes |
|------|---------|-------|
| `power_service/v1/get_message_not_disturb` | Get DND settings | Notifications |
| `power_service/v1/message_not_disturb` | Set DND settings | Notifications |
| `power_service/v1/read_message` | Mark message as read | Notifications |
| `power_service/v1/add_message` | Add a message | Notifications |
| `power_service/v1/del_message` | Delete a message | Notifications |
| `power_service/v1/app/shelly_ctrl_device` | Control Shelly device | `{"device_sn": deviceSn, "op_type": "parameter", "value": value}` |
| `power_service/v1/app/whitelist/feature/check` | Check feature whitelist | `{"check_list": [{"feature_code": "smartmeter", "product_code": "A17C5"}]}` |
| `power_service/v1/app/report_tlv_event` | Report TLV event (tamper?) | `{"device_sn": deviceSn, "events": [{}]}` |

</details>

<details>
<summary><b>HES Unimplemented (46 endpoints)</b></summary>

| Path | Purpose | Access |
|------|---------|--------|
| `charging_hes_svc/adjust_station_price_unit` | Adjust station price unit | Owner |
| `charging_hes_svc/cancel_pop` | Cancel popup | Unknown |
| `charging_hes_svc/check_update` | Check for updates | Owner |
| `charging_hes_svc/check_device_bluetooth_password` | Check BLE password | Owner |
| `charging_hes_svc/check_function` | Check function support | Unknown |
| `charging_hes_svc/device_command` | Send device command | Owner |
| `charging_hes_svc/device_self_check` | Trigger self-check | Owner |
| `charging_hes_svc/deal_share_data` | Handle share data | Unknown |
| `charging_hes_svc/download_energy_statistics` | Download energy stats | Owner |
| `charging_hes_svc/get_device_command` | Get pending device commands | Unknown |
| `charging_hes_svc/get_device_pn_info` | Get device part number info | Unknown |
| `charging_hes_svc/get_device_card_list` | Get device card list | Unknown |
| `charging_hes_svc/get_device_card_details` | Get device card details | Unknown |
| `charging_hes_svc/get_device_self_check` | Get self-check results | Owner |
| `charging_hes_svc/get_external_device_config` | Get external device config | Unknown |
| `charging_hes_svc/get_history_setting` | Get history settings | Owner |
| `charging_hes_svc/get_site_mi_list` | Get micro inverter list for site | Unknown |
| `charging_hes_svc/get_station_config_and_status` | Get station config and status | Unknown |
| `charging_hes_svc/get_system_device_time` | Get system device time | Unknown |
| `charging_hes_svc/get_tou_price_plan_detail` | Get TOU price plan detail | Unknown |
| `charging_hes_svc/get_user_fault_info` | Get user fault info | Unknown |
| `charging_hes_svc/get_station_evchargers` | Get station EV chargers | Owner |
| `charging_hes_svc/get_utility_rate_plan` | Get utility rate plan | Unknown |
| `charging_hes_svc/update_device_info_by_app` | Update device info | Owner |
| `charging_hes_svc/update_hes_utility_rate_plan` | Update HES utility rate plan | Owner |
| `charging_hes_svc/update_wifi_config` | Update WiFi config | Owner |
| `charging_hes_svc/upload_device_status` | Upload device status | Owner |
| `charging_hes_svc/user_event_alarm` | User event alarm | Unknown |
| `charging_hes_svc/user_fault_alarm` | User fault alarm | Unknown |
| `charging_hes_svc/ota` | Trigger OTA update | Owner |
| `charging_hes_svc/remove_user_fault_info` | Remove fault info | Unknown |
| `charging_hes_svc/restart_peak_session` | Restart peak session | Unknown |
| `charging_hes_svc/start` | Start HES system | Owner |
| `charging_hes_svc/set_station_evchargers` | Set station EV chargers | Owner |
| `charging_hes_svc/set_evcharger_station_feature` | Set EV charger station feature | Owner |
| `charging_hes_svc/share_device/delete_installer_inviting_member` | Delete installer invite | Owner |
| `charging_hes_svc/share_device/invite_installer_member` | Invite installer | Owner |
| `charging_hes_svc/share_device/get_installer_invited_list` | Get installer invite list | Owner |

</details>

<details>
<summary><b>Passport / Authentication (28 endpoints)</b></summary>

These are auth-related and mostly handled by the login flow. Not relevant for HA entities.

| Path | Purpose |
|------|---------|
| `passport/login` | Login (already implemented separately) |
| `passport/logout` | Logout |
| `passport/get_profile` | Get user profile |
| `passport/update_profile` | Update profile |
| `passport/change_password` | Change password |
| `passport/forget_password` | Password reset |
| `passport/register` | Register new account |
| `passport/destroy_user` | Delete account |
| `passport/validate_email` | Check if email is registered |
| `passport/get_subscriptions` | Get email/SMS preferences |
| `passport/set_subscriptions` | Set email/SMS preferences |
| ... and 17 more auth endpoints |

</details>

<details>
<summary><b>App Service (18 endpoints)</b></summary>

| Path | Purpose |
|------|---------|
| `app/devicemanage/update_relate_device_info` | Update device info |
| `app/cloudstor/get_app_up_token_general` | Get cloud storage upload token |
| `app/cloudstor/get_app_up_token_without_login` | Get upload token (no login) |
| `app/logging/get_device_logging` | Get device logs |
| `app/logging/upload` | Upload logs |
| `app/logging/upload_pb_events` | Upload protobuf events |
| `app/devicerelation/un_relate_and_unbind_device` | Unbind device |
| `app/devicerelation/device_invite` | Share EV charger device |
| `app/devicerelation/confirm_invite` | Accept sharing invite |
| `app/devicerelation/ignore_invite` | Ignore sharing invite |
| `app/devicerelation/update_share` | Update sharing settings |
| `app/devicerelation/clear_share` | Clear sharing |
| `app/news/get_popups` | Get news popups |
| `app/news/popup_record` | Record popup interaction |
| `app/push/clear_count` | Clear push notification count |
| `app/push/register_push_token` | Register push token |

</details>

<details>
<summary><b>Mini Power / Prime Charger (12 unimplemented endpoints)</b></summary>

| Path | Purpose |
|------|---------|
| `mini_power/v1/app/charging/update_charging_mode` | Update charging mode |
| `mini_power/v1/app/charging/add_charging_mode` | Add custom charging mode |
| `mini_power/v1/app/charging/delete_charging_mode` | Delete charging mode |
| `mini_power/v1/app/setting/set_charging_mode_status` | Set active charging mode |
| `mini_power/v1/app/setting/set_compatibility_status` | Set compatibility mode |
| `mini_power/v1/app/egg/add_easter_egg_trigger_record` | Easter egg trigger record |
| `mini_power/v1/app/egg/report_easter_egg_trigger_status` | Easter egg status report |
| `mini_power/v1/app/style/get_manual_clock_screensavers` | Get manual screensavers |
| `mini_power/v1/app/style/add_manual_clock_screensavers` | Add screensaver |
| `mini_power/v1/app/style/delete_manual_clock_screensavers` | Delete screensaver |
| `mini_power/v1/app/style/get_url` | Get style URL |
| `mini_power/v1/app/style/set_manual_clock_screensaver_name` | Set screensaver name |

</details>

<details>
<summary><b>Charging Energy Service - Unimplemented (6 endpoints)</b></summary>

| Path | Purpose |
|------|---------|
| `charging_energy_service/sync_installation_inspection` | Sync installation data |
| `charging_energy_service/sync_config` | Sync configuration |
| `charging_energy_service/restart_peak_session` | Restart peak session |
| `charging_energy_service/preprocess_utility_rate_plan` | Preprocess rate plan |
| `charging_energy_service/ack_utility_rate_plan` | Acknowledge rate plan |
| `charging_energy_service/adjust_station_price_unit` | Adjust price unit |

</details>

---

## MQTT Command Gaps

The integration communicates with devices via MQTT for real-time data and control commands. The `mqttcmdmap.py` defines **59 command types** across the `SolixMqttCommands` dataclass, with **221 message type entries** in the MQTT map. However, several gaps exist.

### 5 Disabled-but-Defined Commands

These commands are defined in `SolixMqttCommands` but are marked as non-functional or cloud-driven:

| Command | Status | Reason | APK Evidence |
|---------|--------|--------|-------------|
| `sb_usage_mode` | **Not supported** | Uses various field patterns per mode with the same command message. Too complex for single MQTT command | APK shows this is set through cloud API `set_device_parm` with param type 6 (SB2 schedule) instead |
| `sb_3rd_party_pv_switch` | **Driven through cloud** | Cloud API required (`get_device_parm` type 26) | APK confirms cloud-side handling |
| `sb_ev_charger_switch` | **Driven through cloud** | Cloud API required | APK confirms cloud-side handling |
| `ac_charge_limit` | **Commented out** (import line 8 in mqttmap.py) | Correct message type unknown | APK shows field `CMD_AC_CHARGE_LIMIT` at commented TODO line ~2425: "Range 100-800 W, step 100?" |
| `sb_ac_input_limit` | **Partially implemented** | Only for A17C5 (SB3). Message type for other models unclear | APK shows this is an A17C5-specific feature via `set_device_attrs` |

### 19 Missing MQTT Message Handlers

Based on APK analysis and cross-referencing device capabilities, the following MQTT message types are seen in traffic but not yet decoded/handled:

| # | Area | Description | Expected Fields | Potential HA Entity |
|---|------|-------------|-----------------|---------------------|
| 1 | Solarbank | Battery cell voltage details | Per-cell voltages (mV) | `sensor` per cell, `diagnostic` |
| 2 | Solarbank | Battery temperature per pack | Per-pack temps (C) | `sensor` per pack |
| 3 | Solarbank | Grid frequency measurement | Hz value | `sensor.grid_frequency` |
| 4 | Solarbank | Grid voltage per phase | V per phase (L1/L2/L3) | `sensor` per phase |
| 5 | Solarbank | Power factor / cos(phi) | Power factor value | `sensor.power_factor` |
| 6 | Solarbank | Cumulative energy counters | kWh import/export | `sensor` with `state_class: total_increasing` |
| 7 | Solarbank | MPPT tracker details | Per-tracker V/A/W | `sensor` per MPPT channel |
| 8 | Smart Meter | Phase current readings | A per phase | `sensor` per phase |
| 9 | Smart Meter | Phase power readings | W per phase | `sensor` per phase |
| 10 | Smart Meter | Energy import/export counters | kWh values | `sensor` with `state_class: total_increasing` |
| 11 | EV Charger | Charging session real-time data | kWh, A, V, duration | `sensor` - session energy, current, voltage |
| 12 | EV Charger | RFID card authentication events | Card ID, status | `event` entity |
| 13 | EV Charger | Cable lock status | locked/unlocked | `binary_sensor.cable_lock` |
| 14 | EV Charger | Vehicle connection state details | Connected/charging/error | `sensor.vehicle_state` |
| 15 | PPS | Individual port power details (beyond current) | Per-port W values for USB-A/C/DC | `sensor` per port (partially implemented) |
| 16 | PPS | Battery cycle count | Cycle count integer | `sensor.battery_cycles` |
| 17 | HES / X1 | Battery module individual status | Per-module SOC/temp/status | `sensor` per battery module |
| 18 | HES / X1 | PCU (Power Conversion Unit) details | Efficiency, temp, status | `sensor` - PCU metrics |
| 19 | HES / X1 | Backup controller status | Grid/backup mode, transfer time | `binary_sensor`, `sensor` |

> **Note:** The exact message type codes (e.g., `0405`, `0407`) for these missing handlers need to be mapped by capturing MQTT traffic from devices. The APK `libapp.so` contains the Dart code that processes these messages, but the binary field mappings require device-specific traffic analysis.

---

## Potential HA Entities from New Endpoints

| Endpoint Group | Possible HA Entities | Entity Type | Priority |
|---|---|---|---|
| **Range Extender System** | System status, strategy mode, cumulative energy, device count | `sensor`, `select`, `number` | :red_circle: P1 |
| **AI EMS** | AI status (untrained/learning/trained), learning progress %, profit/savings | `sensor`, `binary_sensor` | :red_circle: P1 |
| **VPP / Evergen** | Enrollment status, dispatch active, dispatch count, policy details | `binary_sensor`, `sensor` | :yellow_circle: P2 |
| **Dynamic Pricing** | Current price, next-hour price, price timeline (attributes), active plan | `sensor` | :yellow_circle: P2 |
| **Storm Guard** | Guard enabled, storm active, reserve SOC%, last event | `binary_sensor`, `sensor`, `switch` | :yellow_circle: P2 |
| **Location** | Device coordinates, country code | `sensor` (attributes) | :yellow_circle: P2 |
| **Lookups** | Site-by-SN reverse lookup, service config flags | Internal / diagnostics | :red_circle: P1 |
| **EV Charger Orders** | Last session kWh, total sessions, weekly/monthly stats | `sensor` | :green_circle: P3 |
| **Reports** | Annual summary, monthly report availability | `sensor` (attributes) | :green_circle: P3 |
| **Device Management** | Strategy record, device alias, binding info | `text`, diagnostics | :green_circle: P3 |
| **Electrician** | Installer name, phone, company | `sensor` (attributes) | :green_circle: P3 |

---

## Integration Suggestions

### Immediate Wins (P1 - Next PR)

1. **Range Extender System polling**: Add `get_extender_system_list` + `get_extender_system_detail` to the regular API polling cycle. Create sensors for system status and cumulative energy. The strategy update via `update_extender_system_strategy` could be a `select` entity.

2. **AI EMS Status sensor**: `get_ai_ems_status` is lightweight and provides learning status + remaining time. This maps directly to a `sensor` with state (`untrained`/`learning`/`trained`) and `remaining_seconds` as an attribute.

3. **Site-by-SN lookup**: `get_site_detail_by_sn` is useful for device discovery during integration setup (config flow). Could replace the current multi-step site lookup.

### Medium-Term (P2 - Feature PRs)

4. **Dynamic Pricing sensors**: The `get_dynamic_price_details` endpoint already works. Adding `get_dynamic_price_plan` and `get_dynamic_price_rates` would complete the picture. Sensors for current price, next-hour price, and a price forecast attribute.

5. **Storm Guard integration**: For HES (X1) users, the disaster preparedness endpoints are valuable. A `binary_sensor` for storm guard active + `switch` for enabling/disabling would be a good start.

6. **VPP Status**: For users enrolled in VPP programs, a `binary_sensor` for enrollment and `sensor` for dispatch count/history provides visibility into grid participation.

### Long-Term / Community Contributions (P3)

7. **EV Charger session tracking**: The order/stats endpoints could feed a dedicated EV charger dashboard card. Sensors for last session energy, total sessions, and cost.

8. **Monthly/Annual reports**: These could be exposed as `button` entities to trigger report retrieval, with the report data available as `sensor` attributes.

9. **Shelly device control**: The `shelly_ctrl_device` endpoint in the unimplemented section could enable direct Shelly control through the Anker cloud (though local Shelly control via HA is preferred).

### MQTT Priority

10. **Smart Meter phase data** (handlers #8-10): Phase-level power/current/voltage from the smart meter would be extremely valuable for energy dashboards. These are the highest-priority MQTT gaps.

11. **Battery cell diagnostics** (handlers #1-2): Cell voltage and per-pack temperature for battery health monitoring. Useful for long-term battery degradation tracking.

12. **EV Charger real-time** (handlers #11-14): Session data, RFID events, and cable lock status for the A5191 EV Charger.

---

## Endpoint Statistics Summary

| Category | Count | Notes |
|----------|-------|-------|
| **API_ENDPOINTS** (implemented) | 147 | Core power_service + app + charging_pv + mini_power + charging_common |
| **API_CHARGING_ENDPOINTS** (implemented) | 15 | Power Panel (A17B1) |
| **API_HES_SVC_ENDPOINTS** (implemented) | 26 | Home Energy System (X1) |
| **Total implemented** | **188** | Across 3 API dicts |
| Unimplemented (comments) | ~159 | Known but not in dicts |
| - power_service | 83 | Largest group |
| - charging_hes_svc | 46 | HES-specific |
| - passport | 28 | Auth (mostly not needed) |
| - app | 18 | Device management |
| - mini_power | 12 | Prime Charger |
| - charging_disaster_prepared | 7 | Power Panel disaster |
| - charging_hes_dynamic_price_svc | 6 | HES dynamic pricing |
| - charging_energy_service | 6 | Power Panel misc |
| - charging_pv_svc | 1 | MI status |
| **Grand total known** | **~347** | |
| MQTT Commands defined | 59 | In `SolixMqttCommands` |
| MQTT Message type entries | 221 | Across all device models |

---

> **Last updated:** 2026-03-18
> **Source file:** `custom_components/anker_solix/solixapi/apitypes.py`
> **Branch:** `feat/ble-and-local-features`
