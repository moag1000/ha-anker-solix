# API Endpoints - Reverse Engineered from Anker App v3.18.0

> **Data source:** Decompiled `libapp.so` (58 MB compiled Dart) from Anker App v3.18.0 APK
> **Total endpoints found:** ~347 | **Integration implements:** ~188 (across 3 dicts) | **Newly added:** ~45 | **Still unimplemented:** ~159

> **⚠️ IMPORTANT DISCLAIMER**
>
> **Everything in this document is derived from static reverse engineering of one APK version (v3.18.0).** None of the newly documented endpoints have been called against the live Anker cloud API. We do not know:
> - Whether these endpoints are still active in the current server version
> - What the actual response JSON structures look like (though Dart model classes with `.fromJson` confirm structured responses exist)
> - What error codes or rate limits apply
> - Whether parameter names/types are correct (inferred from Dart class fields, not documentation)
> - Whether endpoints require specific device models, firmware versions, or account flags
>
> **Deep APK analysis (2026-03-19)** extracted 763 Dart model classes with `.fromJson`, confirmed response field names from `toString()` patterns, and identified per-device MQTT decoder functions. This raises confidence for several feature groups from "pure guess" to "structurally plausible" — but **no substitute for live API testing**.
>
> Anker can change, deprecate, or gate any endpoint without notice.

This document catalogues all API endpoints discovered through reverse engineering of the Anker mobile application, cross-referenced with the integration's `apitypes.py`. It serves as a reference for the `feat/new-api-endpoints` branch — not a confirmed API specification.

---

## Table of Contents

- [Priority Legend](#priority-legend)
- [Architecture Overview](#architecture-overview)
- [Newly Added Endpoints (in API dicts)](#newly-added-endpoints)
  - [Range Extender System (A7320 Smart Meter Pro)](#range-extender-system-a7320-smart-meter-pro)
  - [AI EMS (HES)](#ai-ems-hes)
  - [VPP / Evergen (Virtual Power Plant)](#vpp--evergen-virtual-power-plant)
  - [Dynamic Pricing (Nordpool / Tibber / Octopus Energy)](#dynamic-pricing-nordpool--tibber--octopus-energy)
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
- [Speculative HA Entities from New Endpoints](#speculative-ha-entities-from-new-endpoints)
- [Next Steps: Testing Required](#next-steps-testing-required)
- [APK Deep Analysis Findings (2026-03-19)](#apk-deep-analysis-findings-2026-03-19)

---

## Priority Legend

| Icon | Priority | Description |
|------|----------|-------------|
| :red_circle: | **P1 (High)** | Would have direct user value **if** the endpoint works as expected |
| :yellow_circle: | **P2 (Medium)** | Would enhance existing features — requires testing first |
| :green_circle: | **P3 (Low)** | Niche, admin-only, or rarely needed — low priority for testing |

> **Note:** Priority reflects *potential* value, not implementation readiness. Every endpoint needs live API testing before any HA entity work begins.

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
| `smart_service/v1/` | (none) | Anka AI Agent (chat) | 0 endpoints |
| `privacy_service/v1/` | (none) | Privacy data export | 0 endpoints |

**All endpoints use HTTP POST** unless noted otherwise (`get_message_unread`, `get_message`, `get_product_categories`, `get_product_accessories` use GET).

**APK-confirmed network ports:** 443 (HTTPS), 8883 (MQTT over TLS), 5353 (mDNS)

---

## Newly Added Endpoints

These endpoint URL paths were extracted from the decompiled APK and added to the API dictionaries. **None have been tested against the live API.** Parameter names are inferred from Dart class fields and may be incorrect. Response structures are entirely unknown.

---

### Range Extender System (A7320 Generator/PPS Hybrid) :red_circle: P1

**APK Evidence (confirmed from `libapp.so` string analysis):**

This is **not** a "multi-device solar system" — it's a **generator + PPS hybrid system**. The A7320 pairs a fuel-based generator (gasoline/LPG/diesel) with a Portable Power Station for backup power. The `oe_a7320` Dart package contains 90+ source files.

**14 Dart model classes with `.fromJson`** confirm JSON API responses exist:
`RangeExtenderSystem`, `RangeExtenderSystemDetailModel`, `RangeExtenderSystemsModel`, `RangeExtenderDeviceModel`, `RangeExtenderBySocStrategyModel`, `RangeExtenderByTimeStrategyModel`, `RangeExtenderStrategyParamsModel`, `RangeExtenderStrategyRecordModel`, `RangeExtenderGeneratorModeModel`, `ExtenderSystemCumulativeDataModel`, `ExtenderSystemPnOtaModel`, `ExtenderSystemPnOtaItemModel`, `RangeExtenderFromDevice`, `ReSystemJoinedExtenderSystemDevice`

**Confirmed response field names** (from `toString()` patterns and field references):
- System: `extenderSystemId`, `extenderSystemName`, `systemStatus`, `deviceCount`
- Generator: `generatorPower`, `startGeneratorPower`, `stopGeneratorPower`, `fuelType`, `fuelLevel`, `hundredFuelConsumption`, `fuelConsumptionNow`, `totalFuelConsumption`, `oilEngineSystemStatus`, `runTime`, `runningMode`
- Energy: `totalPowerGeneration`, `batteryDischargePower`, `dischargePower`
- Strategy: `strategyType` (SOC-based via `BySocStrategyModel` or time-based via `ByTimeStrategyModel`)
- Links: `generatorDeviceSn`, `ppsDeviceSn`, `connectionStatus`, `linkageOnlineStatus`
- Booleans: `isAcMode`, `isOilDeviceRunning`, `can_extender_system`

> **Caveat:** Field names are confirmed in the binary, but actual JSON key casing (camelCase vs snake_case) and nesting structure are unknown until a live response is captured. This system is niche — requires a physical A7320 generator.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_extender_system_list` | `power_service/v1/app/get_extender_system_list` | List generator/PPS systems | `{}` | Probably returns `extenderSystemId`, `extenderSystemName` per system |
| `get_extender_system_detail` | `power_service/v1/app/get_extender_system_detail` | Full system detail | `{"system_id": systemId}` | Likely contains generator status, fuel level, power flow fields listed above |
| `add_extender_system` | `power_service/v1/app/add_extender_system` | Create a new system | System config (unknown) | Setup-only, not for HA |
| `del_extender_system` | `power_service/v1/app/del_extender_system` | Delete a system | `{"system_id": systemId}` | Destructive — should not be exposed |
| `update_extender_system_strategy` | `power_service/v1/app/update_extender_system_strategy` | Update SOC-based or time-based strategy | Strategy config | Write — two strategy types confirmed (BySoc, ByTime) |
| `get_extender_system_cumulative_data` | `power_service/v1/app/get_extender_system_cumulative_data` | Cumulative energy/fuel data | `{"system_id": systemId}` | Likely returns `totalPowerGeneration`, `totalFuelConsumption` |
| `set_extender_system_name` | `power_service/v1/app/set_extender_system_name` | Rename the system | `{"system_id": systemId, "name": newName}` | Low value for HA |
| `add_extender_system_device_list` | `power_service/v1/app/add_extender_system_device_list` | List eligible devices | `{"system_id": systemId}` | Setup-only |
| `batch_add_extender_system_device` | `power_service/v1/app/batch_add_extender_system_device` | Batch add devices | Device SN list (format unknown) | Setup-only |
| `batch_del_extender_system_device` | `power_service/v1/app/batch_del_extender_system_device` | Batch remove devices | Device SN list (format unknown) | Destructive — setup-only |
| `get_extender_system_pn_ota` | `power_service/v1/app/get_extender_system_pn_ota` | OTA info | `{"system_id": systemId}` | `ExtenderSystemPnOtaModel` confirmed |
| `set_extender_system_cumulative_data` | `power_service/v1/app/set_extender_system_cumulative_data` | Correct cumulative data | Cumulative data object (unknown) | Risky write — manual correction only |

---

### AI EMS (HES) :red_circle: P1

**APK Evidence (confirmed from `libapp.so` string analysis):**

AI-based Energy Management System for Home Energy Systems. The APK reveals a **multi-day training cycle** with defined states and MQTT real-time updates.

**6 Dart model classes with `.fromJson`**: `AiEmsProfitModel`, `AiEmsProfitInfo`, `AiEmsParamData`, `AiModeStatusModel`, `LargeChargerAiEmsProfit`, `MqttAIEmsStateModel`

**Confirmed training states** (from UI asset names): `studying` (training in progress, days countdown) → `study_failed` (can retry for %s more days) → `study_success` (completed)

**Confirmed response field names**: `aiems_profit`, `aiems_profit_total`, `aiems_lifetime_profit`, `aiems_self_use_diff`, `self_use_diff_percent`, `enable_aiems_v2`

**5 EMS mode types confirmed**: `AIEMS`, `Add`, `Custom`, `ManualBackup`, `UseTime`

**IoT commands**: `akiot.ems.get_ems_mode`, `akiot.ems.set_ems_mode`

**MQTT real-time state**: `MqttAIEmsStateModel.fromJson` via `_handleMqttAIEmsState` — AI EMS state is pushed to clients in real time.

> **Caveat:** Requires X1/HES hardware. Unknown if the AI feature requires server-side enablement or specific firmware. The `enable_aiems_v2` flag suggests feature versioning.

**In `API_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_ai_ems_status` | `power_service/v1/ai_ems/get_status` | Get AI learning status | `{"site_id": siteId}` | Likely returns training state + remaining days — `AiModeStatusModel` exists |
| `get_ai_ems_profit` | `power_service/v1/ai_ems/profit` | Get AI EMS savings data | `{"site_id": siteId, "start_time": "00:00", "end_time": "24:00", "type": "grid"}` | Fields confirmed: `aiems_profit`, `aiems_profit_total`, `aiems_lifetime_profit` |

**In `API_HES_SVC_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `authorize_aiems` | `charging_hes_svc/authorize_aiems` | Authorize AI EMS for HES site | `{"siteId": siteId}` | Write — one-time authorization, flow: authorize → enable → profit |
| `enable_aiems_mode4` | `charging_hes_svc/enable_aiems_mode4` | Enable AI EMS (mode4 = one of 5 EMS types) | `{"siteId": siteId}` | Write — triggers training cycle |
| `get_aiems_profit` | `charging_hes_svc/get_aiems_profit` | Get AI EMS profit via HES path | `{"siteId": siteId}` | `AiEmsProfitModel` confirmed — duplicate path to power_service profit endpoint |

---

### VPP / Evergen (Virtual Power Plant) :yellow_circle: P2

**APK Evidence (confirmed from `libapp.so` string analysis):**

VPP platform is **confirmed as Evergen**. Strings: `applyToJoinEvergen`, `evergenAccept`, `evergenDecline`, `evergenEnrolled`, `evergenEnrollingIn`, `isEvergen`, `EvergenState`.

**Critical finding**: VPP takes full control of the battery — verbatim from APK: *"Your system is now connected to the Evergen VPP platform. EMS Mode and battery charging / discharging operations are now controlled by the platform."*

**Grid Dispatch (DRED/RCR)** is A5101-specific: `GridDispatchLogic`, `GridDispatchBinding`, `a5101GridDispatch`, `dred_rcr_state`

**Model classes**: `VppInfoModel.fromJson`, `VppServicePolicyModel.fromJson` — only 2 models, relatively simple feature.

**Confirmed fields**: `vppEnable`, `vppType`, `vppstatus`, `vppstatus_des`

> **Caveat:** VPP is region-locked (likely AU, potentially UK). Requires active Evergen enrollment agreement. Non-enrolled accounts will likely get empty/error responses. The `power_service` VPP endpoints may be a different code path from the `charging_hes_svc` ones — untestable without Evergen access.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `vpp_get_enrollment_status` | `power_service/v1/app/vpp/get_enrollment_status` | Check Evergen enrollment | `{"site_id": siteId}` | Likely returns `vppEnable`, `vppstatus` — but empty for non-VPP accounts |
| `vpp_enrollment_verification` | `power_service/v1/app/vpp/enrollment_verification` | Complete Evergen enrollment | Enrollment data (unknown) | Write — Evergen agreement flow only |
| `vpp_get_policy` | `power_service/v1/app/vpp/get_policy` | Get policy details | `{"site_id": siteId}` | `VppServicePolicyModel` exists |
| `vpp_dispatch_control` | `power_service/v1/app/vpp/dispatch_control` | VPP dispatch control | Control params (unknown) | Dangerous — controls battery charge/discharge via Evergen |
| `vpp_get_dispatch_history` | `power_service/v1/app/vpp/get_dispatch_history` | Dispatch event history | `{"site_id": siteId}` | Unknown response format |

**Additional VPP endpoints in unimplemented HES comments:**

| Path | Purpose |
|------|---------|
| `charging_hes_svc/get_vpp_check_code` | Get VPP verification code (Evergen onboarding) |
| `charging_hes_svc/get_vpp_service_policy_by_agg_user` | Get Evergen service policy by aggregator user |

---

### Dynamic Pricing (Nordpool / Tibber / Octopus Energy) :yellow_circle: P2

**APK Evidence (confirmed from `libapp.so` string analysis):**

**Three providers confirmed** (not two): Nordpool, Tibber, and **Octopus Energy** (`OctopusArea.fromJson`, `OctopusParam.fromJson`).

**11 Dart model classes**: `DynamicPrice`, `DynamicPriceChartData`, `DynamicPriceCompanyModel`, `DynamicPriceCountryAreaModel`, `DynamicPriceDetailModel`, `DynamicPriceModel`, `DynamicPriceModuleModel`, `DynamicPriceParam`, `DynamicPriceParamData`, `DynamicPriceStatisticDataModel`, `SaveDynamicPriceResponse` — plus `NordpoolArea`, `NordpoolParam`, `UserNordpoolParam`, `UserTibberParam`, `OctopusArea`, `OctopusParam`

**Negative electricity price feature confirmed**: Dart sources include `negative_electricity_price/negative_using_view.dart` and `negative_period_no_main_power_view.dart` — the app has UI for managing negative price periods.

**Tibber uses OAuth/WebView flow**: `_saveTibberWebToken`, `Push to tibber webView url`

The existing `get_dynamic_price_details` endpoint is already implemented and working — so these related endpoints have a somewhat higher chance of also working. Response formats for new endpoints are still unconfirmed.

**Already in `API_ENDPOINTS` (existing):**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_dynamic_price_sites` | `power_service/v1/dynamic_price/check_available` | Get site IDs with dynamic pricing | `{}` | Discovery |
| `get_dynamic_price_providers` | `power_service/v1/dynamic_price/support_option` | Get provider list for device | `{"device_pn": "A5102"}` | `select` - Provider selection |
| `get_dynamic_price_details` | `power_service/v1/dynamic_price/price_detail` | Get price data for area/date | `{"area": "GER", "company": "Nordpool", "date": "<posix_ts>", "device_sn": ""}` | `sensor` - Current/next hour price |

**Newly added:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_dynamic_price_plan` | `power_service/v1/dynamic_price/get_plan` | Get active dynamic price plan for site | `{"site_id": siteId}` | Possibly `sensor` — response format unconfirmed |
| `set_dynamic_price_plan` | `power_service/v1/dynamic_price/set_plan` | Set/update dynamic price plan | Plan config (unknown) | Write — needs testing before exposing |
| `get_dynamic_price_rates` | `power_service/v1/dynamic_price/get_rates` | Get current dynamic price rates? | Rate query params (guessed) | Possibly `sensor` — response format unconfirmed |
| `check_dynamic_price_adjust` | `power_service/v1/dynamic_price/check_adjust` | Check price adjustment status? | `{}` | Unknown what "adjust" means here |
| `get_dynamic_price_provider_list` | `power_service/v1/dynamic_price/get_providers` | Get full provider list | `{}` | Configuration helper only |

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

**APK Evidence (confirmed from `libapp.so` string analysis):**

This is a **comprehensive weather warning system** with two distinct modes:
- **Auto mode**: Weather-triggered via `AutoDisasterPreparednessMixin` — automatically reserves battery when severe weather detected
- **Manual mode**: User-triggered via `ManualDisasterPreparednessMixin`

**9+ Dart model classes with `.fromJson`**: `AutoDisasterPrepareStatusModel`, `AutoDisasterDetailModel`, `AutoDisasterQuitPrepareModel`, `A5101MqttAutoDisasterStateModel`, `DisasterStatus`, `DisasterEvent`, `DisasterSetting`, `DisasterPrepareDetail`, `DisasterPrepareDetailsModel`, `DisasterPreparednessInfo`, `DisasterPreparednessPlans`, `BackUpHistory`, `BackupHistoryModel`

**Confirmed response fields**: `auto_disaster_enable`, `auto_disaster_status`, `auto_disaster_switch`, `disaster_preparedness_enable`, `disaster_preparedness_soc`, `disaster_preparedness_start`, `disaster_preparedness_end`, `disaster_preparedness_plans`, `manual_disaster_status`, `manual_disaster_switch`, `support_auto_disaster`, `pps_auto_disaster_preparedness_switch`

**40+ weather event types confirmed** (examples): `disasterTypeExtremelyHeavyRain`, `disasterTypeThunderstormsAndHail`, `disasterTypeAvalanches`, `disasterTypeFireWeather`, `disasterTypeTropicalStormWarning`, `disasterCoastalFloodWarning`, `disasterFlashFloodWarning`, etc.

**MQTT real-time state**: `A5101MqttAutoDisasterStateModel.fromJson` — storm guard state pushed to clients. Also: `====A17B1 StationMqttMixin AutoDisaster cmd:`, `====A1782 StationMqttMixin AutoDisaster cmd:` — multiple device models support this.

> **Caveat:** Requires HES/X1 or Power Panel (A17B1, A1782) hardware. Weather data source unknown (likely NWS or similar). Region availability unclear. The `disaster_preparedness_soc` field suggests a configurable reserve SOC percentage during weather events.

**In `API_HES_SVC_ENDPOINTS`:**

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_auto_disaster_status` | `charging_hes_svc/get_auto_disaster_prepare_status` | Get Storm Guard status | `{"siteId": siteId}` | Likely returns `auto_disaster_enable`, `auto_disaster_status`, `support_auto_disaster` |
| `get_auto_disaster_detail` | `charging_hes_svc/get_auto_disaster_prepare_detail` | Get Storm Guard config | `{"siteId": siteId}` | Likely returns `disaster_preparedness_soc`, `disaster_preparedness_plans` |
| `get_current_disaster_detail` | `charging_hes_svc/get_current_disaster_prepare_details` | Get active storm event | `{"siteId": siteId}` | `DisasterEvent.fromJson` — returns event type + details during active weather |
| `get_backup_history` | `charging_hes_svc/get_back_up_history` | Get backup event history | `{"siteId": siteId}` | `BackupHistoryModel.fromJson` confirmed |

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

Location services endpoints. Likely used internally by Storm Guard and solar forecasting. May not return useful data outside of those features.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_device_location` | `charging_common_svc/location/get` | Get device location | `{"identifier_id": deviceSn, "identifier_type": type, "business_type": type}` | Unknown — `identifier_type` and `business_type` values unclear |
| `set_device_location` | `charging_common_svc/location/set` | Set device location | Location data (unknown format) | Write — risky without knowing exact format |
| `check_location_support` | `charging_common_svc/location/support` | Check if location features supported | `{"identifier_id": deviceSn}` | Internal only |

---

### Useful Lookups :yellow_circle: P2

General-purpose lookup endpoints. May be useful for device discovery, but response formats are unconfirmed.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_site_detail_by_sn` | `power_service/v1/site/get_site_detail_by_sn` | Reverse lookup: find site by device SN | `{"device_sn": deviceSn}` | Possibly useful for config flow — needs testing |
| `get_all_service_config` | `power_service/v1/get_all_service_config` | Get all service configuration flags? | `{}` | Unknown response structure |
| `get_message_sn_list` | `power_service/v1/get_message_sn_list` | Get device SNs with messaging enabled? | `{}` | Internal — low HA value |

---

### EV Charger Orders :green_circle: P3

EV charger session tracking and statistics. Only relevant for users with the Anker SOLIX V1 Smart EV Charger (A5191).

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_charging_order_list` | `power_service/v1/app/order/get_charging_order_list` | Get all charging orders in range | `{"device_sn": deviceSn, "start_time": "2026-02-09"}` | Unknown response format — `start_time` format guessed |
| `get_charging_order_detail` | `power_service/v1/app/order/get_charging_order_detail` | Get data points for a charging session | `{"device_sn": deviceSn, "order_id": orderId}` | Unknown — requires valid order_id from list call |
| `export_charge_order` | `power_service/v1/app/order/export_charge_order` | Export charge order data (CSV?) | Unknown | Unknown — may return file download, not JSON |

**Also already existing in API_ENDPOINTS:**

| Key | Path | Purpose |
|-----|------|---------|
| `get_device_charge_order_stats` | `power_service/v1/app/order/get_charge_order_stats` | Aggregated stats (week/month/year/all) |
| `get_device_charge_order_stats_list` | `power_service/v1/app/order/get_charge_order_stats_list` | Paginated stats list |

---

### Monthly / Annual Reports :green_circle: P3

Report generation and retrieval. May return HTML links rather than raw data — unclear how useful these are for HA sensors.

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_annual_report` | `power_service/v1/app/get_annual_report` | Get annual report | `{"site_id": siteId, "year": "2025"}` | Unknown — may return HTML link, not data |
| `get_monthly_report_list` | `power_service/v1/app/mothly_report_list` | List existing monthly reports (**typo is intentional** — matches Anker API!) | `{"site_id": siteId}` | Unknown response format |
| `get_monthly_report_configs` | `power_service/v1/app/get_monthly_report_configs` | Get monthly report notification settings? | `{"site_id": siteId}` | Low HA value |
| `set_monthly_report_configs` | `power_service/v1/app/set_monthly_report_configs` | Configure monthly report notifications? | Config object (unknown) | Write — low HA value |

> **Note:** `power_service/v1/app/mothly_report_show` exists in the unimplemented section and provides an HTML link to the actual report, but requires the Anker App to view.

---

### Device Management :green_circle: P3

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `get_device_bind_details` | `power_service/v1/app/get_device_bind_details` | Get device binding details | `{"device_sn": deviceSn}` | Diagnostics only |
| `get_strategy_last_record` | `power_service/v1/app/get_strategy_last_record` | Get last strategy execution record? | `{"device_sn": deviceSn}` | Unknown response format |
| `site_data_exported` | `power_service/v1/site/site_data_exported` | Export site data | `{"site_id": siteId}` | Unknown — may trigger email/download, not JSON |
| `batch_check_update` | `app/ota/batch/check_update` | Batch check firmware updates | Device SN list (format unknown) | Possibly `update` — if format matches existing OTA endpoints |
| `relate_device` | `app/devicerelation/relate_device` | Relate/bind a device | Device data (unknown) | Setup-only, not for regular HA use |
| `get_shared_device_relation` | `app/devicerelation/get_shared_device` | Get shared device relation | `{"device_sn": deviceSn}` | Diagnostics only |
| `update_device_alias` | `app/devicerelation/up_alias_name` | Update device alias name | `{"device_sn": deviceSn, "alias_name": name}` | Possibly `text` — low value |
| `get_mi_status` | `charging_pv_svc/getMiStatus` | Get micro inverter status | `{"device_sn": deviceSn}` | Unknown response format |

---

### Electrician / Installer :green_circle: P3

| Key | Path | Purpose | Params | HA Integration Use |
|-----|------|---------|--------|--------------------|
| `add_electrician` | `power_service/v1/site/electrician/add` | Add electrician/installer to site | Installer details (unknown) | Setup-only, no HA value |
| `get_electrician` | `power_service/v1/site/electrician/get` | Get installer info for site | `{"site_id": siteId}` | Low HA value — diagnostics only |

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

The integration communicates with devices via MQTT for real-time data and control commands. The `mqttcmdmap.py` defines **63 command types** across the `SolixMqttCommands` dataclass, with **174 mapped message types** across device models. Several gaps exist.

**APK Evidence — per-device MQTT decoders confirmed:**
`a172x_mqtt_decode_`, `a1771_mqtt_decode_`, `a1781_mqtt_decode_`, `a17a3_mqtt_decode_`, `a17b1_mqtt_decode_`, `a17c0_mqtt_decode_`, `a17c1_mqtt_decode_`, `a17x7_mqtt_decode_`, `a17x8_mqtt_decode_`, `a91b2_mqtt_decode_`, `iot_mqtt_decode_3`

**MQTT gzip decompression confirmed:** `MqttDecompressionUtil` — payloads can be gzip-compressed or plain JSON. Main data payload is `SceneInfo`.

**MQTT feature state models confirmed:**
- `MqttAIEmsStateModel.fromJson` — AI EMS state pushed real-time
- `A5101MqttAutoDisasterStateModel.fromJson` — Storm Guard state pushed real-time
- `A5101MQTTDeviceInfoModel.fromJson`, `A5101MqttDeviceStateModel.fromJson` — X1 device info/state
- `A17b1MqttDeviceInfoModel.fromJson` — Power Panel device info

### 5 Disabled-but-Defined Commands

These commands are defined in `SolixMqttCommands` but are marked as non-functional or cloud-driven:

| Command | Status | Reason | APK Evidence |
|---------|--------|--------|-------------|
| `sb_usage_mode` | **Not supported** | Uses various field patterns per mode with the same command message. Too complex for single MQTT command | APK shows this is set through cloud API `set_device_parm` with param type 6 (SB2 schedule) instead |
| `sb_3rd_party_pv_switch` | **Driven through cloud** | Cloud API required (`get_device_parm` type 26) | APK confirms cloud-side handling |
| `sb_ev_charger_switch` | **Driven through cloud** | Cloud API required | APK confirms cloud-side handling |
| `ac_charge_limit` | **Commented out** (import line 8 in mqttmap.py) | Correct message type unknown | APK shows field `CMD_AC_CHARGE_LIMIT` at commented TODO line ~2425: "Range 100-800 W, step 100?" |
| `sb_ac_input_limit` | **Partially implemented** | Only for A17C5 (SB3). Message type for other models unclear | APK shows this is an A17C5-specific feature via `set_device_attrs` |

### 19 Suspected Missing MQTT Message Handlers

Based on APK code analysis and guesses about device capabilities. **These are speculative** — we have not captured MQTT traffic to confirm these message types actually exist or contain the fields listed. "Expected Fields" are inferred from APK class names and may be entirely wrong.

| # | Area | Description | APK Evidence | Status |
|---|------|-------------|-------------|--------|
| 1 | Solarbank | Battery cell voltage details | `DEVICE_BATTER_CELL_CYCLE_TIMES` field confirmed; BLE: `prop_read_battery_pack_info` | **Partial** — field exists, MQTT mapping unknown |
| 2 | Solarbank | Battery temperature per pack | `sub_pack_temp_alarm`, `rn_battery_temperature` confirmed | **Partial** — fields exist, MQTT mapping unknown |
| 3 | Solarbank | Grid frequency | `action_set_biggest_frequency` confirmed | **Partial** — write action exists, read path unknown |
| 4 | Solarbank | Grid voltage per phase | No specific APK evidence | Unconfirmed |
| 5 | Solarbank | Power factor / cos(phi) | No specific APK evidence | Unconfirmed |
| 6 | Solarbank | Cumulative energy counters | `grid_exported_total`, `grid_imported_total`, `solar_to_grid_total`, `solar_to_home_total`, `battery_to_home_total`, `grid_to_battery_total` confirmed | **Confirmed** — fields exist in APK, MQTT message type unknown |
| 7 | Solarbank | MPPT tracker details | `solar_power_1` through `solar_power_4` confirmed (A17C5: 4 MPPT) | **Confirmed** — per-MPPT fields exist |
| 8 | Smart Meter | Phase current/power readings | `a17x7_mqtt_decode_` and `a17a3_mqtt_decode_` confirmed; Shelly3EM integration | **Partial** — device decoders exist |
| 9 | Smart Meter | Energy import/export | `grid_exported_total`, `grid_imported_total` confirmed | **Partial** — fields exist |
| 10 | EV Charger | Session real-time data | `A5101MqttOrderResultModel.fromJson`; `prop_read_charging_real_time_data` via BLE | **Partial** — MQTT order model + BLE read exist |
| 11 | EV Charger | RFID events | Full RFID management via BLE (`prop_read_rfid`, `prop_write_rfid`) + API (`rfid/get_device_cards`) | **Confirmed** — but MQTT event path unknown |
| 12 | EV Charger | Cable/connector lock | `ChargingConnectorLockMenuController`, `requestConnectorLockConfig` confirmed | **Partial** — controller exists, MQTT mapping unknown |
| 13 | EV Charger | Vehicle connection | `isConnectedToEnodeapi`, `enode_vehicle_id` — Enode API vehicle integration | **Partial** — API integration, MQTT path unknown |
| 14 | EV Charger | Load balancing | `A5190LoadBalancingModel.fromJson`, `dynamicLoadBalancing` confirmed | **Partial** — model exists |
| 15 | PPS | Port power details | Partially implemented in integration | Existing |
| 16 | PPS | Battery cycle count | `DEVICE_BATTER_CELL_CYCLE_TIMES` confirmed | **Confirmed** — field name exists |
| 17 | HES / X1 | Battery module status | `A5101MqttDeviceStateModel.fromJson` confirmed | **Partial** — MQTT state model exists |
| 18 | HES / X1 | PCU details | No specific APK evidence for PCU | Unconfirmed |
| 19 | HES / X1 | Backup controller | `action_set_backup_mode`, `action_set_backup_strategy` confirmed | **Partial** — write actions exist |
| 20 | HES / X1 | **Heat pump state** (NEW) | `HeatPumpModel.fromJson`, `_handleMqttDeviceHeatPumpState` confirmed | **Confirmed** — MQTT handler exists |
| 21 | HES / X1 | **AI EMS state** (NEW) | `MqttAIEmsStateModel.fromJson`, `_handleMqttAIEmsState` confirmed | **Confirmed** — MQTT handler exists |
| 22 | HES / X1 | **Storm Guard state** (NEW) | `A5101MqttAutoDisasterStateModel.fromJson` confirmed | **Confirmed** — MQTT handler exists |

> **Note:** Message type codes remain unknown for most entries. However, the APK now provides stronger evidence than before: confirmed field names, Dart model classes with `.fromJson`, and device-specific MQTT decoder functions. Items marked "Confirmed" have both field names and MQTT model classes. Items marked "Partial" have field names but no confirmed MQTT message mapping. Traffic capture from specific devices remains the only way to complete the picture.

---

## Speculative HA Entities from New Endpoints

> **⚠️ No live API responses have been observed.** However, the deep APK analysis has confirmed Dart model classes (`.fromJson`), response field names, and MQTT state models for several feature groups. This raises confidence from "pure guess" to "structurally plausible" — but still needs live testing.

| Endpoint Group | Likely Response Fields (from APK) | Guessed Entity Type | Priority | Confidence |
|---|---|---|---|---|
| **Range Extender** | `systemStatus`, `fuelLevel`, `generatorPower`, `totalPowerGeneration`, `totalFuelConsumption` — 14 model classes | `sensor` | :red_circle: P1 | **Medium** — rich model structure, but niche hardware (A7320 generator) |
| **AI EMS** | `aiems_profit`, `aiems_profit_total`, `aiems_lifetime_profit`, training state — 6 model classes + MQTT state | `sensor` | :red_circle: P1 | **Medium** — model classes + MQTT handler confirmed |
| **VPP / Evergen** | `vppEnable`, `vppstatus`, `vppstatus_des` — 2 model classes | `binary_sensor` | :yellow_circle: P2 | Low — region-locked to Evergen markets |
| **Dynamic Pricing** | `DynamicPriceDetailModel` + `NordpoolParam` + `OctopusParam` + negative price — 11+ models | `sensor` | :yellow_circle: P2 | **Medium-High** — existing endpoint works, 3 providers confirmed |
| **Storm Guard** | `auto_disaster_enable`, `disaster_preparedness_soc`, 40+ event types — 9+ model classes + MQTT state | `binary_sensor`, `sensor` | :yellow_circle: P2 | **Medium** — rich model structure, MQTT handler confirmed |
| **Heat Pump** (NEW) | `HeatPumpModel`, `HeatPumpPlan` — MQTT state handler confirmed | `sensor`? | :yellow_circle: P2 | **Medium** — MQTT handler exists |
| **Location** | `identifier_id`, `identifier_type`, `business_type` | Internal | :green_circle: P3 | Low — param semantics unclear |
| **EV Charger** | RFID, connector lock, load balancing, Enode vehicle — multiple models confirmed | `sensor`, `binary_sensor` | :yellow_circle: P2 | **Medium** — A5190/A5191 models have rich BLE+API support |
| **Reports** | Unknown — may return HTML links | `sensor`? | :green_circle: P3 | Very Low — may not return JSON data |
| **Device Management** | Various | Diagnostics | :green_circle: P3 | Low |

---

## Next Steps: Testing Required

> **Nothing in this document is implementation-ready.** Before writing any HA entity code, each endpoint needs:
> 1. A live API call with a real account/device to capture the actual response JSON
> 2. Confirmation that required parameters are correct
> 3. Understanding of error responses and edge cases
> 4. Verification that the endpoint isn't gated behind specific firmware, region, or account flags

### Candidates for Initial Testing (highest confidence from APK analysis)

1. **Dynamic Pricing extensions** (`get_dynamic_price_plan`, `get_dynamic_price_rates`): The existing `get_dynamic_price_details` already works. 11+ Dart model classes confirm rich response structures. Three providers confirmed (Nordpool, Tibber, Octopus Energy). Negative price handling exists. **Highest confidence** among new endpoints.

2. **`get_ai_ems_status`**: Read-only. 6 model classes confirmed. Training state machine (studying/failed/success) with days countdown. MQTT real-time push via `MqttAIEmsStateModel`. But: requires X1/HES hardware and possibly server-side AI feature enablement.

3. **Storm Guard** (`get_auto_disaster_status`, `get_auto_disaster_detail`): Read-only. 9+ model classes, 40+ weather event types, confirmed fields (`disaster_preparedness_soc`, auto/manual modes). MQTT state handler exists. But: requires HES/Power Panel hardware, region-dependent weather data source.

4. **`get_site_detail_by_sn`**: Simple lookup. If it works, could improve config flow. Low risk.

### Lower Priority / Higher Risk

5. **Range Extender System**: 14 model classes, 90+ Dart source files — the largest feature. But this is a **generator/PPS hybrid** (A7320), not solar. Very niche hardware. Rich field evidence (`fuelLevel`, `generatorPower`, `totalFuelConsumption`) suggests the API is mature, but testing requires physical A7320.

6. **VPP / Evergen**: Region-locked. Requires active Evergen enrollment agreement. Only 2 model classes — relatively simple, but completely untestable without VPP access.

7. **MQTT message handlers**: The APK analysis upgraded several gaps from "pure guess" to "confirmed fields exist" (battery cycle count, MPPT per-tracker power, cumulative energy counters, heat pump, AI EMS state, Storm Guard state). However, the MQTT message type codes that carry these fields remain unknown. Traffic capture from specific device types is still required.

### Newly Discovered Features (not in previous documentation)

8. **Heat Pump Integration**: `HeatPumpModel.fromJson`, `HeatPumpPlan.fromJson`, `_handleMqttDeviceHeatPumpState` — undocumented feature with MQTT state handler. Endpoint: `charging_hes_svc/get_heat_pump_plan_json`. Requires HES/X1 hardware with heat pump connected.

9. **Anka AI Agent**: WebSocket-based AI chat (`AiChatManager`), endpoints at `/smart_service/v1/app/anka/`. Not useful for HA entities but confirms Anker is building AI features.

10. **IoT Command Namespace** (`akiot.*`): Complete IoT SDK with 40+ commands for BLE, MQTT, device management, energy analysis. These are the native SDK methods the app uses internally — may reveal additional control paths.

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

> **Last updated:** 2026-03-19 (deep APK analysis pass)
> **Source file:** `custom_components/anker_solix/solixapi/apitypes.py`
> **APK analyzed:** `com.anker.charging` v3.18.0 (build 160), `libapp.so` 56 MB
> **Branch:** `feat/new-api-endpoints`

---

## APK Deep Analysis Findings (2026-03-19)

### Confirmed Power Flow Field Names (from `libapp.so` strings)

These field names appear in the compiled Dart binary and represent the internal data model for energy flow. Many are already implemented in the integration — listed here for completeness and cross-reference.

**Directional flows:** `solar_to_battery`, `solar_to_grid`, `solar_to_home`, `battery_to_grid`, `battery_to_home`, `grid_to_battery`, `grid_to_home`, `grid_to_ev` (with `_total` suffix variants for cumulative values)

**Battery:** `battery_power`, `battery_capacity`, `battery_level`, `battery_health`, `battery_reserve`, `battery_status`, `DEVICE_BATTER_CELL_CYCLE_TIMES`, `sub_pack_temp_alarm`, `max_battery_pack_num`

**PV/Solar:** `solar_power_1` through `solar_power_4` (4 MPPT on A17C5), `pv_power_limit`, `pv_power_limit_option`, `third_party_pv_power`, `third_party_pv_enable`, `third_party_pv_connect_status`

**Grid:** `grid_power`, `grid_available`, `grid_online`, `grid_status`, `grid_code`, `grid_exported_total`, `grid_imported_total`

**Home:** `home_load_power`, `current_home_load`, `default_home_load`

### Shelly Integration Clarification

Shelly devices are controlled via **Anker Cloud → Shelly Cloud** authorization flow, **not** local MQTT. Confirmed: `ShellyPluginMixin`, `changeShellyDeviceStatus`, `changeShellyPlugSwitch`, `_isShellyPlugWithAuth`. The `ShellyProDevice` model supports Shelly Pro Meters as smart meters. The `shelly_ctrl_device` API endpoint sends commands through the Anker cloud server.

### EV Charger (A5190/A5191) Concrete Findings

- **RFID**: Full card management (add/delete/read) via BLE and API
- **OCPP**: Full Open Charge Point Protocol support with internal/third-party server switching
- **Connector Lock**: `ChargingConnectorLockMenuController` with configuration
- **Dynamic Load Balancing**: `A5190LoadBalancingModel`, `dynamicLoadBalancing` field
- **Enode API Vehicle Integration**: `enode_vehicle_id`, `isConnectedToEnodeapi` — vehicles managed through Enode platform
- **Tamper Proof**: `tamper_proof` field with push notification alerts
- **A5191 wired ethernet**: Network cable support (not just WiFi)

### IoT SDK Command Namespace (`akiot.*`)

The APK uses an internal IoT SDK with 40+ commands:
- **BLE**: `akiot.ble.connect_device`, `write_characteristic`, `set_ble_state`
- **MQTT**: `akiot.mqtt.connect_mqtt`, `publish_message`, `subscribe_topic`
- **Device**: `akiot.device.invoke_action`, `read_property`, `write_property`, `fetch_device_info`
- **EMS**: `akiot.ems.get_ems_mode`, `akiot.ems.set_ems_mode`
- **Energy**: `akiot.energy.platform_energy_analysis`, `get_backup_records`

### BLE Property Commands (per device model)

Device-specific BLE read/write commands discovered:
- `prop_read_device_info`, `prop_read_device_version`, `prop_read_device_current_wifi`
- `prop_read_battery_pack_info` — battery pack diagnostics
- `prop_read_charging_real_time_data` — real-time charging data
- `prop_read_port_detail_data`, `prop_read_rfid`, `prop_read_ocpp_info`
- `prop_read_oil_engine_and_PPS_linkage_information` — generator/PPS link
- `prop_write_evcharger`, `prop_write_green_energy_priority`, `prop_write_load_balancing`, `prop_write_ocpp_info`, `prop_write_rfid`

### Statistics

| Metric | Count |
|--------|-------|
| Dart model classes with `.fromJson` | **763** |
| Device models identified | **60+** (with sub-variants) |
| Per-device MQTT decoders | **11** |
| IoT SDK commands (`akiot.*`) | **40+** |
| BLE property commands | **15+** |
| Confirmed power flow field names | **30+** |

---

## Credits

- **[@thomluther](https://github.com/thomluther)** -- Original [ha-anker-solix](https://github.com/thomluther/ha-anker-solix) API implementation that all these additions build upon
- **Anker App v3.18.0 APK** -- Source of all newly discovered endpoint URLs via `libapp.so` decompilation
- **[@flip-dots](https://github.com/flip-dots)** -- [SolixBLE](https://github.com/flip-dots/SolixBLE) project provided cross-reference for MQTT topic structures and BLE command-to-API mappings
