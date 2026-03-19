# Anker APK v3.18.0 — Analysis Notes (unverified)

> **Binary**: `libapp.so` (56 MB compiled Dart) from `com.anker.charging` v3.18.0 (build 160)
> **Date**: 2026-03-19
> **Method**: `strings` extraction + cross-reference with `apitypes.py`

---

## 1. Complete API Endpoint Census (333 unique paths)

### power_service/v1 (~131 endpoints)

#### AI EMS (2)
```
power_service/v1/ai_ems/get_status
power_service/v1/ai_ems/profit
```

#### Extender System (12)
```
power_service/v1/app/add_extender_system
power_service/v1/app/add_extender_system_device_list
power_service/v1/app/batch_add_extender_system_device
power_service/v1/app/batch_del_extender_system_device
power_service/v1/app/del_extender_system
power_service/v1/app/get_extender_system_cumulative_data
power_service/v1/app/get_extender_system_detail
power_service/v1/app/get_extender_system_list
power_service/v1/app/get_extender_system_pn_ota
power_service/v1/app/set_extender_system_cumulative_data
power_service/v1/app/set_extender_system_name
power_service/v1/app/update_extender_system_strategy
```

#### After Sale (4)
```
power_service/v1/app/after_sale/check_popup
power_service/v1/app/after_sale/check_sn
power_service/v1/app/after_sale/get_popup
power_service/v1/app/after_sale/mark_sn
```

#### Compatible / Third-party Solar (13)
```
power_service/v1/app/compatible/check_third_sn
power_service/v1/app/compatible/confirm_permissions_settings
power_service/v1/app/compatible/get_compatible_process
power_service/v1/app/compatible/get_compatible_solar_info
power_service/v1/app/compatible/get_confirm_permissions
power_service/v1/app/compatible/get_installation
power_service/v1/app/compatible/get_ota_info
power_service/v1/app/compatible/get_ota_update
power_service/v1/app/compatible/get_power_cutoff
power_service/v1/app/compatible/installation_popup
power_service/v1/app/compatible/save_compatible_solar
power_service/v1/app/compatible/save_ota_complete_status
power_service/v1/app/compatible/set_installation
power_service/v1/app/compatible/set_ota_update
power_service/v1/app/compatible/set_power_cutoff
```

#### Device Management (8)
```
power_service/v1/app/device/get_device_attrs
power_service/v1/app/device/get_device_home_load
power_service/v1/app/device/get_device_income
power_service/v1/app/device/get_mes_device_info
power_service/v1/app/device/get_relate_belong
power_service/v1/app/device/remove_param_config_key
power_service/v1/app/device/set_device_attrs
power_service/v1/app/device/set_device_home_load
```

#### Group Management (5)
```
power_service/v1/app/group/delete_group_devices
power_service/v1/app/group/force_save_group_devices
power_service/v1/app/group/get_group_devices
power_service/v1/app/group/replace_group_devices
power_service/v1/app/group/save_group_devices
```

#### Order / EV Charging Sessions (8)
```
power_service/v1/app/order/delete_charging_order
power_service/v1/app/order/export_charge_order
power_service/v1/app/order/get_charge_order_stats
power_service/v1/app/order/get_charge_order_stats_list
power_service/v1/app/order/get_charging_order_detail
power_service/v1/app/order/get_charging_order_list
power_service/v1/app/order/get_charging_order_sec_detail
power_service/v1/app/order/get_charging_order_sec_preview
```

#### Share Site (6)
```
power_service/v1/app/share_site/anonymous_join_site
power_service/v1/app/share_site/delete_inviting_member
power_service/v1/app/share_site/delete_site_member
power_service/v1/app/share_site/get_invited_list
power_service/v1/app/share_site/invite_member
power_service/v1/app/share_site/join_site
```

#### User Params (2)
```
power_service/v1/app/user/get_user_params
power_service/v1/app/user/set_user_params
```

#### Vehicle (7)
```
power_service/v1/app/vehicle/add_vehicle
power_service/v1/app/vehicle/delete_vehicle
power_service/v1/app/vehicle/get_vehicle_detail
power_service/v1/app/vehicle/get_vehicle_list
power_service/v1/app/vehicle/set_charging_vehicle
power_service/v1/app/vehicle/set_default
power_service/v1/app/vehicle/update_vehicle
```

#### Oil Engine / Generator (15)
```
power_service/v1/app/batch_maintain_oil_engine_parts
power_service/v1/app/get_device_exercise_details
power_service/v1/app/get_device_exercise_log
power_service/v1/app/get_device_last_exercise_log
power_service/v1/app/get_oil_consumption_reminder_plan_details
power_service/v1/app/get_parts_maintenance_logs
power_service/v1/app/get_parts_maintenance_plan
power_service/v1/app/set_maintain_parts_ignore_reminders
power_service/v1/app/set_maintain_parts_notice_switch
power_service/v1/app/set_oil_consumption_reminder_plan
power_service/v1/app/set_oil_consumption_reminder_switch
power_service/v1/app/set_oil_machine_exercise_plan
power_service/v1/app/set_parts_maintenance_plan
power_service/v1/app/start_oil_machine_exercise
power_service/v1/app/switch_exercise_mode
```

#### Dynamic Price (4)
```
power_service/v1/dynamic_price/check_adjust
power_service/v1/dynamic_price/check_available
power_service/v1/dynamic_price/price_detail
power_service/v1/dynamic_price/support_option
```

#### Site Management (33)
```
power_service/v1/site/add_charging_device
power_service/v1/site/add_site_devices
power_service/v1/site/can_create_site
power_service/v1/site/co2_ranking
power_service/v1/site/create_site
power_service/v1/site/delete_charging_device
power_service/v1/site/delete_site
power_service/v1/site/delete_site_devices
power_service/v1/site/electrician/add
power_service/v1/site/electrician/get
power_service/v1/site/energy_analysis
power_service/v1/site/get_addable_site_list
power_service/v1/site/get_charging_device
power_service/v1/site/get_comb_addable_sites
power_service/v1/site/get_home_load_chart
power_service/v1/site/get_power_limit
power_service/v1/site/get_scen_info
power_service/v1/site/get_schedule
power_service/v1/site/get_site_detail
power_service/v1/site/get_site_detail_by_sn
power_service/v1/site/get_site_device_param
power_service/v1/site/get_site_list
power_service/v1/site/get_site_price
power_service/v1/site/get_site_rules
power_service/v1/site/get_wifi_info_list
power_service/v1/site/list_user_devices
power_service/v1/site/local_net
power_service/v1/site/reset_charging_device
power_service/v1/site/set_device_feature
power_service/v1/site/set_site_device_param
power_service/v1/site/shift_power_site_type
power_service/v1/site/site_data_check
power_service/v1/site/site_data_exported
power_service/v1/site/update_charging_device
power_service/v1/site/update_site
power_service/v1/site/update_site_devices
power_service/v1/site/update_site_price
```

#### Misc App (24)
```
power_service/v1/app/check_upgrade_record
power_service/v1/app/get_annual_report
power_service/v1/app/get_auto_upgrade
power_service/v1/app/get_brand_list
power_service/v1/app/get_device_bind_details
power_service/v1/app/get_model_list
power_service/v1/app/get_model_years
power_service/v1/app/get_models
power_service/v1/app/get_monthly_report_configs
power_service/v1/app/get_ocpp_endpoint_list
power_service/v1/app/get_ocpp_info
power_service/v1/app/get_phonecode_list
power_service/v1/app/get_relate_and_bind_devices
power_service/v1/app/get_relate_device_fittings
power_service/v1/app/get_strategy_last_record
power_service/v1/app/get_token_by_userid
power_service/v1/app/get_upgrade_record
power_service/v1/app/get_user_op_shelly_status
power_service/v1/app/mothly_report_list
power_service/v1/app/mothly_report_show
power_service/v1/app/report_tlv_event
power_service/v1/app/set_auto_upgrade
power_service/v1/app/set_monthly_report_configs
power_service/v1/app/shelly_ctrl_device
power_service/v1/app/third/platform/list
power_service/v1/app/upgrade_event_report
power_service/v1/app/whitelist/feature/check
```

#### VPP (5 - in apitypes.py, not in binary strings directly)
```
power_service/v1/app/vpp/get_enrollment_status
power_service/v1/app/vpp/enrollment_verification
power_service/v1/app/vpp/get_policy
power_service/v1/app/vpp/dispatch_control
power_service/v1/app/vpp/get_dispatch_history
```

#### Other (8)
```
power_service/v1/add_message
power_service/v1/currency/get_list
power_service/v1/del_message
power_service/v1/device/get_tamper_records
power_service/v1/get_all_service_config
power_service/v1/get_message
power_service/v1/get_message_not_disturb
power_service/v1/get_message_sn_list
power_service/v1/get_message_unread
power_service/v1/message_not_disturb
power_service/v1/product_accessories
power_service/v1/product_categories
power_service/v1/read_message
power_service/v1/rfid/delete_device_card
power_service/v1/rfid/get_device_cards
power_service/v1/rfid/save_device_card
```

### power_service/v2 (5 endpoints — NEW API version!)
```
power_service/v2/app/get_custom_branch_icon
power_service/v2/app/get_hardware_relation
power_service/v2/app/set_device_pv_name
power_service/v2/platform_get_pn_region_code
power_service/v2/site/platform_energy_analysis_options
```

### charging_hes_svc (56 endpoints)
```
charging_hes_svc/adjust_station_price_unit
charging_hes_svc/authorize_aiems
charging_hes_svc/cancel_pop
charging_hes_svc/check_device_bluetooth_password
charging_hes_svc/check_function
charging_hes_svc/check_update
charging_hes_svc/deal_share_data
charging_hes_svc/device_command
charging_hes_svc/device_self_check
charging_hes_svc/download_energy_statistics
charging_hes_svc/enable_aiems_mode4
charging_hes_svc/get_aiems_profit
charging_hes_svc/get_auto_disaster_prepare_detail
charging_hes_svc/get_auto_disaster_prepare_status
charging_hes_svc/get_back_up_history
charging_hes_svc/get_conn_net_tips
charging_hes_svc/get_current_disaster_prepare_details
charging_hes_svc/get_device_card_details
charging_hes_svc/get_device_card_list
charging_hes_svc/get_device_command
charging_hes_svc/get_device_pn_info
charging_hes_svc/get_device_product_info
charging_hes_svc/get_device_self_check
charging_hes_svc/get_electric_utility_and_electric_plan_list
charging_hes_svc/get_energy_statistics
charging_hes_svc/get_external_device_config
charging_hes_svc/get_heat_pump_plan_json
charging_hes_svc/get_hes_dev_info
charging_hes_svc/get_history_setting
charging_hes_svc/get_install_info
charging_hes_svc/get_installer_info
charging_hes_svc/get_mi_layout
charging_hes_svc/get_site_mi_list
charging_hes_svc/get_station_config_and_status
charging_hes_svc/get_station_evchargers
charging_hes_svc/get_system_device_time
charging_hes_svc/get_system_profit_detail
charging_hes_svc/get_system_running_info
charging_hes_svc/get_system_running_time
charging_hes_svc/get_tou_price_plan_detail
charging_hes_svc/get_user_bind_and_not_in_station_evchargers
charging_hes_svc/get_user_fault_info
charging_hes_svc/get_utility_rate_plans
charging_hes_svc/get_vpp_check_code
charging_hes_svc/get_vpp_service_policy_by_agg_user
charging_hes_svc/get_wifi_info
charging_hes_svc/get_world_monetary_unit
charging_hes_svc/ota
charging_hes_svc/quit_auto_disaster_prepare
charging_hes_svc/remove_user_fault_info
charging_hes_svc/report_device_data
charging_hes_svc/restart_peak_session
charging_hes_svc/set_evcharger_station_feature
charging_hes_svc/set_station_evchargers
charging_hes_svc/share_device/delete_installer_inviting_member
charging_hes_svc/share_device/get_installer_invited_list
charging_hes_svc/share_device/invite_installer_member
charging_hes_svc/start
charging_hes_svc/sync_back_up_history
charging_hes_svc/update_device_info_by_app
charging_hes_svc/update_hes_utility_rate_plan
charging_hes_svc/update_wifi_config
charging_hes_svc/upload_device_status
charging_hes_svc/user_event_alarm
charging_hes_svc/user_fault_alarm
```

### charging_energy_service (18 endpoints)
```
charging_energy_service/ack_utility_rate_plan
charging_energy_service/adjust_station_price_unit
charging_energy_service/energy_statistics
charging_energy_service/get_configs
charging_energy_service/get_device_infos
charging_energy_service/get_error_infos
charging_energy_service/get_installation_inspection
charging_energy_service/get_rom_versions
charging_energy_service/get_sns
charging_energy_service/get_system_running_info
charging_energy_service/get_utility_rate_plan
charging_energy_service/get_wifi_info
charging_energy_service/get_world_monetary_unit
charging_energy_service/preprocess_utility_rate_plan
charging_energy_service/report_device_data
charging_energy_service/restart_peak_session
charging_energy_service/sync_config
charging_energy_service/sync_installation_inspection
```

### charging_disaster_prepared (6 endpoints)
```
charging_disaster_prepared/clear
charging_disaster_prepared/get_site_device_disaster
charging_disaster_prepared/get_site_device_disaster_status
charging_disaster_prepared/get_support_func
charging_disaster_prepared/quit_disaster_prepare
charging_disaster_prepared/set_site_device_disaster
```

### charging_hes_dynamic_price_svc (6 endpoints)
```
charging_hes_dynamic_price_svc/get_area_by_code
charging_hes_dynamic_price_svc/get_price
charging_hes_dynamic_price_svc/get_price_company
charging_hes_dynamic_price_svc/get_third_jump_url
charging_hes_dynamic_price_svc/save_dynamic_price
charging_hes_dynamic_price_svc/save_time_of_use
```

### charging_pv_svc (7 endpoints)
```
charging_pv_svc/getMiStatus
charging_pv_svc/getPvStatus
charging_pv_svc/getPvTotalStatistics
charging_pv_svc/selectUserTieredElecPrice
charging_pv_svc/set_aps_power
charging_pv_svc/statisticsPv
charging_pv_svc/updateUserTieredElecPrice
```

### charging_common_svc (3 endpoints)
```
charging_common_svc/location/get
charging_common_svc/location/set
charging_common_svc/location/support
```

### charging_imsg_svc (2 endpoints — NEW SERVICE)
```
charging_imsg_svc/remove_user_floating_fault_info
charging_imsg_svc/user_fault_alarm
```

### mini_power/v1 (31 endpoints)
```
mini_power/v1/app/charging/add_charging_mode
mini_power/v1/app/charging/delete_charging_mode
mini_power/v1/app/charging/get_charging_mode_list
mini_power/v1/app/charging/update_charging_mode
mini_power/v1/app/egg/add_easter_egg_trigger_record
mini_power/v1/app/egg/get_easter_egg_trigger_list
mini_power/v1/app/egg/report_easter_egg_trigger_status
mini_power/v1/app/power/get_day_power_data
mini_power/v1/app/setting/get_charging_device_identity_new_status
mini_power/v1/app/setting/get_charging_device_identity_status_default_true
mini_power/v1/app/setting/get_device_setting
mini_power/v1/app/setting/get_port_protocol_status
mini_power/v1/app/setting/get_port_remarks
mini_power/v1/app/setting/get_power_range_support_protocols
mini_power/v1/app/setting/get_protocol_status
mini_power/v1/app/setting/set_charging_device_identity_new_status
mini_power/v1/app/setting/set_charging_device_identity_status
mini_power/v1/app/setting/set_charging_device_identity_status_default_true
mini_power/v1/app/setting/set_charging_mode_status
mini_power/v1/app/setting/set_compatibility_status
mini_power/v1/app/setting/set_mode_sub_status
mini_power/v1/app/setting/set_port_protocol_status
mini_power/v1/app/setting/set_port_remark
mini_power/v1/app/setting/set_protocol_status
mini_power/v1/app/style/add_manual_clock_screensavers
mini_power/v1/app/style/delete_manual_clock_screensavers
mini_power/v1/app/style/get_clock_screensavers
mini_power/v1/app/style/get_manual_clock_screensavers
mini_power/v1/app/style/get_screensaver_img_url
mini_power/v1/app/style/get_url
mini_power/v1/app/style/set_manual_clock_screensaver_name
```

### app/ (29 endpoints)
```
app/ai/anka
app/cloudstor/get_app_up_token_general
app/cloudstor/get_app_up_token_without_login
app/devicemanage/update_relate_device_info
app/devicerelation/clear_share
app/devicerelation/confirm_invite
app/devicerelation/device_invite
app/devicerelation/get_shared_device
app/devicerelation/ignore_invite
app/devicerelation/relate_device
app/devicerelation/un_relate_and_unbind_device
app/devicerelation/up_alias_name
app/devicerelation/update_share
app/help/add_feedback
app/help/app_versions/check
app/help/banner/nps
app/help/banners
app/help/dst
app/help/dynamic/config/list
app/help/faqs
app/help/handle_survey_popup
app/help/manual_list
app/help/product_tutorial_search
app/help/scan_code_white_list
app/help/terms_and_conditions/
app/help/xtest/data
app/logging/get_device_logging
app/logging/upload
app/logging/upload_pb_events
app/news/get_popups
app/news/popup_record
app/ota/batch/check_update
app/push/clear_count
app/push/register_push_token
```

### passport/ (28 endpoints)
```
passport/change_password
passport/discount_desc
passport/estimate_domain
passport/external_login
passport/forget_password
passport/freeze_account
passport/get_profile
passport/get_subscriptions
passport/get_user_param
passport/login
passport/logout
passport/phone_bind_account
passport/phone_code_list
passport/phone_reset_password
passport/phone_verification_code
passport/phone_verification_login
passport/phone_verification_regist
passport/register
passport/resend_active_email
passport/set_account_password
passport/set_subscriptions
passport/subscription_configs
passport/terminal_id
passport/third_party_login
passport/update_profile
passport/update_user_param
passport/validate_email
passport/validate_pass
```

### smart_service/v1 (3 endpoints)
```
smart_service/v1/app/anka/get_entry_config
smart_service/v1/app/anka/get_menu_config
smart_service/v1/app/anka/set_entry_switch
```

### privacy_service/v1 (2 endpoints)
```
privacy_service/v1/export_account_data
privacy_service/v1/export_record_list
```

### v2/anka (4 endpoints — AI chat history)
```
v2/anka/devmgr/sync
v2/anka/history/del_msg
v2/anka/history/get_msg
v2/anka/history/update_msg
```

---

## 2. Dart Model Classes with `.fromJson` (758 total)

### By Feature Area

| Feature | Count | Key Models |
|---------|-------|------------|
| A5101 (HES/X1) | 41 | `A5101SystemInfoModel`, `A5101MqttDeviceStateModel`, `A5101MqttAutoDisasterStateModel` |
| Site/Station | 34 | `SiteInfo`, `SiteDeviceParam`, `StationModel`, `SceneInfo` |
| Device Mgmt | 34 | `DeviceInfo`, `DeviceAttributes`, `DeviceBindDetailsModel` |
| Price/TOU/Rates | 25 | `PeakValleyModel`, `UtilityRatePlan`, `TouPlanModel` |
| Currency/Price | 22 | `CurrencyInfo`, `PriceModel`, `WeekdayPrice` |
| Range Extender | 21 | `RangeExtenderSystemDetailModel`, `RangeExtenderBySocStrategyModel` |
| Dynamic Price | 20 | `DynamicPriceDetailModel`, `NordpoolParam`, `OctopusParam`, `UserTibberParam` |
| A7320 Generator | 19 | `A7320DeviceInfo`, `A7320RealTimeInfo`, `A7320OilExerciseDetailsModel` |
| Solar/PV | 19 | `SolarInfo`, `PvStatus`, `PvStatisticsModel` |
| Disaster/Backup | 17 | `DisasterPreparednessPlans`, `AutoDisasterPrepareStatusModel`, `BackupHistoryModel` |
| Location/Maps | 18 | `PlaceDetails`, `CommonLocationResponse` |
| Statistics | 15 | `EnergyAnalysisModel`, `EnergyStatisticsModel` |
| OTA/Firmware | 14 | `OtaUpdateModel`, `FirmwareUpdateModel` |
| BLE/WiFi | 15 | `BleConnectDeviceModel`, `WifiListModel` |
| EV Charger | 20 | `A5190DeviceInfo`, `A5190RfidCardModel`, `A5190LoadBalancingModel` |
| EV Vehicle | 12 | `VehicleModel`, `EvBrandListModel` |
| MQTT | 11 | `MqttAIEmsStateModel`, `MqttResultModel` |
| Generator/Oil | 12 | `AnkerGeneratorModel`, `MaintenanceLogsModel` |
| AI Chat | 10 | `AiChatHomeChatMsgModel` |
| AI EMS | 8 | `AiEmsProfitModel`, `AiModeStatusModel`, `EmsModeModel` |
| PPS | 9 | `PpsRealTimeData`, `PpsStatisticsModel` |
| BMS/Battery | 7 | `BmsSubPackList`, `SubPackageModel` |
| Heat Pump | 4 | `HeatPumpModel`, `HeatPumpPlan`, `HeatPumpPlanJsonModel` |
| Shelly | 3 | `IntegratorDeviceStatusModel`, `ThirdPartyPlatformInfoModel` |
| VPP/Evergen | 2 | `VppInfoModel`, `VppServicePolicyModel` |
| Screen Saver | 11 | `ScreenSaverThemeData` |
| OCPP | 6 | `OcppServerInfoModel`, `PortProtocolConfig` |
| Branch Circuit | 4 | `BranchCircuitModel`, `BranchIconModel` |
| Generic/Infra | ~200 | `ResponseModel`, `Head`, `Data`, etc. |

---

## 3. Field Names Found in Binary (by Feature)

### Range Extender System
```
extender_system_id, extender_system_name, extender_system_img, extender_system_params
strategy_type, by_soc_strategy, by_time_strategy
fuel_level, fuel_type, fuel_total, fuel_unit, fuel_units, fuel_filter, fuel_pipe, fuel_tank
hundred_fuel_consumption, fuel_gas_history_remaining, fuel_gas_history_total
generator_mode, generator_list, generator_oil, generator_start_time
oil_consumption_reminder_switch, oil_engine_operation_mode
range_extender_systems, extender_system_relation_ota
```

### AI EMS
```
ai_ems, ems_mode, ems_data, ems_disable
aiems_profit, aiems_profit_total, aiems_lifetime_profit, aiems_self_use_diff
enable_aiems_v2
```
EMS Mode Types: `ModeTypeAIEMS`, `ModeTypeAdd`, `ModeTypeCustom`, `ModeTypeManualBackup`, `ModeTypeUseTime`

### Dynamic Pricing
```
dynamic_price, electricity_price, electricity_price_type, price_type, price_mode
is_dynamic_price_down_grade
nordpool, tibber, octopus
negative_price, negative_value
average_purchase_price, average_sell_price
```

### Disaster Preparedness / Storm Guard
```
auto_disaster, auto_disaster_preparedness_enable, auto_disaster_status, auto_disaster_switch
manual_disaster_detail, manual_disaster_status, manual_disaster_switch
disaster_details, disaster_preparedness_enable, disaster_preparedness_end
disaster_preparedness_plans, disaster_preparedness_soc, disaster_preparedness_start, disaster_type
pps_auto_disaster_preparedness_switch, support_auto_disaster
```

### Heat Pump
```
heat_pump_manual_enable, heat_pump_min_launch_time, heat_pump_min_running_time
heat_pump_mode, heat_pump_plan, heat_pump_plan_json, heat_pump_power
heat_pump_setting, heat_pump_state
```
CamelCase: `heatPumpSGEnable`, `heatPumpSGReady`, `heatPumpActiveRatePower`, `heatPumpActiveTime`, `heatPumpStartingProtectionDelay`

### VPP / Evergen
```
vppEnable, vppType, vppStatus, vppName, vppPolicy, vppServicePolicy
evergenAccept, evergenDecline, evergenEnrolled, evergenEnrollingIn, evergenJoinTime, evergenVppName
```

### Energy Flow (directional)
```
solar_to_battery, solar_to_grid, solar_to_home (+_total variants)
battery_to_grid, battery_to_home (+_total variants)
grid_to_battery, grid_to_home (+_total +_power variants)
grid_to_ev
pv_to_bat_total, pv_to_home_total
third_party_pv_to_bat, third_party_pv_to_grid, third_party_pv_to_home_total
third_party_disel_to_bat_total, third_party_disel_to_home_total
```

### Battery
```
battery_power, battery_capacity, battery_level, battery_health
battery_reserve, battery_status, battery_type
battery_discharge_power, battery_discharging_total, battery_extra_saving
sub_pack_temp_alarm, DEVICE_BATTER_CELL_CYCLE_TIMES
```

### Grid
```
grid_power, grid_available, grid_online, grid_status, grid_code
grid_exported_total, grid_exported_trend, grid_imported_total, grid_imported_trend
grid_recharging, grid_total
```

### EV Charger
```
ev_charger, ev_load_balancing_breaker, ev_max_current
ev_ocpp_connection_status, ev_ocpp_server_name
ev_smart_charging_on, ev_solar_charging_on
ev_schedule_mode, ev_smart_touch_feature
```

---

## 4. IoT SDK Commands (76 akiot.* entries)

### BLE (5)
```
akiot.ble.connect_device, akiot.ble.disconnect_device
akiot.ble.set_ble_state, akiot.ble.stop_connect_device, akiot.ble.write_characteristic
```

### Device (17)
```
akiot.device.accessory.bind, akiot.device.accessory.unbind
akiot.device.connection_status, akiot.device.fetch_device_fault_info, akiot.device.fetch_device_info
akiot.device.invoke_action, akiot.device.notification_events
akiot.device.read_property, akiot.device.write_property
akiot.device.reconnect_device, akiot.device.stop_reconnect_device
akiot.device.remove_user_floating_fault_info, akiot.device.send_report_heart_cmd
akiot.device.set_device_encrypt_key, akiot.device.set_device_negotiated, akiot.device.setup_devices
akiot.device.start_ota, akiot.device.unbind_device, akiot.device.user_fault_alarm
```

### EMS (2)
```
akiot.ems.get_ems_mode, akiot.ems.set_ems_mode
```

### Energy (5)
```
akiot.energy.fetch_site_fault_info, akiot.energy.get_backup_records
akiot.energy.platform_energy_analysis, akiot.energy.platform_get_site_scene
akiot.energy.remove_site_floating_fault_info
```

### Init Flow (10)
```
akiot.initflow.get_multiple_devices_wifi_info, akiot.initflow.initflow_opening_params
akiot.initflow.platform_add_site_devices, akiot.initflow.platform_create_site
akiot.initflow.platform_delete_site, akiot.initflow.platform_delete_site_devices
akiot.initflow.platform_get_addable_site_list
akiot.initflow.platform_get_site_addable_devices_by_type
akiot.initflow.platform_set_device_init_status, akiot.initflow.platform_set_site_init_status
```

### MQTT (7)
```
akiot.mqtt.connect_mqtt, akiot.mqtt.disconnect_mqtt
akiot.mqtt.get_client_id, akiot.mqtt.get_mqtt_connection_status
akiot.mqtt.publish_message, akiot.mqtt.subscribe_topic, akiot.mqtt.unsubscribe_topic
```

### Pairing (8)
```
akiot.pairing.activate_device_ethernet, akiot.pairing.activate_device_wifi
akiot.pairing.activate_multi_device_wifi, akiot.pairing.ble_bind_device
akiot.pairing.fetch_relate_belong, akiot.pairing.get_wifi_list
akiot.pairing.scan_devices, akiot.pairing.stop_scan_devices
```

### Receive Events (10)
```
akiot.receive.ble_connect, akiot.receive.ble_data
akiot.receive.device_fault_info, akiot.receive.mqtt_connect
akiot.receive.mqtt_data, akiot.receive.mqtt_online
akiot.receive.ocpp_service_switching, akiot.receive.smart_charging_update
akiot.receive.station_scene_info
```

### Other (3)
```
akiot.product.fetch_kvconfig, akiot.track.event, akiot.cloud_api
```

---

## 5. Action Commands (48 + 13 control actions)

```
action_get_charging_schedule
action_set_ac_params, action_set_ambient_light_switch, action_set_backup_strategy
action_set_biggest_frequency, action_set_bms_params, action_set_car_charger_params
action_set_charging_fixed_protocol, action_set_charging_protocol, action_set_charging_schedule
action_set_connection_sensitivity, action_set_custom_branch, action_set_custom_mode_delete
action_set_custom_mode_switch_type, action_set_cycle_charging_power
action_set_dc_port_countdown, action_set_dc_port_switch, action_set_distribution_box
action_set_electricity_price_and_unit, action_set_gyroscope_switch
action_set_laboratory_charging_protocol, action_set_laboratory_function_switch
action_set_language_type, action_set_lcd_backlight_brightness
action_set_offline_port_switch, action_set_offline_port_switch_memory
action_set_oil_machine_params, action_set_power_limit_country_code
action_set_protocol_switch, action_set_schedule
action_set_screen_off_time, action_set_screen_orientation, action_set_screen_saver_params
action_set_sleep_mode, action_set_standby_oil_machine_params, action_set_standby_rated_power
action_set_system_params, action_set_system_self_check, action_set_temperature_type
action_set_third_oil_AX170, action_set_third_oil_params, action_set_third_oil_type
action_set_third_party_pv, action_set_tomato_time, action_set_tou_system_params
```

Control actions (non action_set/get):
```
action_bind_ble_device_list, action_channel_self_check, action_control_charging
action_delete_task, action_device_reset, action_disconnect_function
action_manual_set_oil_machine_params, action_network_communication_control
action_rcd_test, action_read_device_error_message, action_restart_device
action_start_self_check, action_unbind_extended_device
```

---

## 6. BLE Property Commands (16)

```
prop_read_battery_pack_info, prop_read_charging_real_time_data
prop_read_device_current_wifi, prop_read_device_info, prop_read_device_version
prop_read_ocpp_info, prop_read_oil_engine_and_PPS_linkage_information
prop_read_port_detail_data, prop_read_rfid, prop_read_screen_saver_params
prop_write_by_evcharger_rfid, prop_write_evcharger
prop_write_green_energy_priority, prop_write_load_balancing
prop_write_ocpp_info, prop_write_rfid
```

---

## 7. Device Models (95+ A-series identifiers)

```
A110A, A110B, A110G, A120J, A1340
A1722, A1723, A1726, A1728, A1729
A1753, A1755
A1761, A1763, A1765
A1770, A1771, A1772
A1780, A1781, A1782, A1782A-H, A1782L-S, A1782W, A1785, A1785P
A1790, A1790B, A1790D, A1790G, A1790H, A1790P, A1790S, A1790T
A1903
A17B1, A17B2, A17B6
A17C0, A17C1, A17C2, A17C5
A17D0, A17D4
A17E1
A17X7, A17X7US, A17X8
A17Y0
A2345
A2687, A2687B, A2687C, A2687D, A2687E, A2687F, A2687G, A2687L
A2693E1, A2693E2
A25x7
A5101 (+20 sub-variants), A5102, A5103
A5140, A5141, A5142, A5143, A5150
A5190, A5191 (+10 sub-variants)
A520, A5220, A5341, A5450
A7320
AE100, AE1R0, AS200, AX170, AX1C0, AX1S0
```

---

## 8. Feature Flags (71 supportX flags)

Key flags indicating device capabilities:
```
supportACEnergyMode, supportAcLimit, supportAutoTou, supportBackupDisaster
supportCarChargeMode, supportChargingLimits, supportCustomChargingMode
supportDiesel, supportDynamic, supportDynamicPrice
supportEVLinkage, supportEthernet, supportFeedElectricity
supportHesNem, supportIOPowerControl, supportManualOffGrid
supportModbusTcp, supportOcppServiceSwitching, supportOctopusSell
supportPPSTOU, supportSell, supportSellPackage, supportShareMeter
supportSmartMode, supportTimeSlot, supportWeekendTOU
```

---

## 9. API Base URLs

```
Production US:  https://ankerpower-api.anker.com
Production EU:  https://ankerpower-api-eu.anker.com
Beta US:        https://ankerpower-api-beta.anker.com
Beta EU:        https://ankerpower-api-eu-beta.anker.com
QA US:          https://ankerpower-api-qa.anker.com
QA2 US:         https://ankerpower-api-qa2.anker.com
QA EU:          https://ankerpower-api-eu-qa.anker.com
QA2 EU:         https://ankerpower-api-eu-qa2.anker.com
China:          https://aiot-api-cn.anker.com.cn
Local Device:   http://10.10.100.254
```

---

## 10. Key New Discoveries

1. **power_service/v2** — 5 endpoints. Anker is beginning API versioning
2. **charging_imsg_svc** — completely new service for fault/alarm messaging (2 endpoints)
3. **Local device API** at `http://10.10.100.254` with `/status.html`
4. **Modbus TCP** support: `supportModbusTcp`, `modbusTcpSwitch`
5. **Heat pump SG Ready**: `heatPumpSGEnable`, `heatPumpSGReady` — Smart Grid Ready protocol
6. **NEM (Net Energy Metering)**: `supportHesNem`, `NemPlanInfo`, `NemUtilityRateModel`
7. **Branch Circuit monitoring**: `BranchCircuitModel`, `branch_ct_number`, `branch_ct_power`
8. **AFCI**: Arc Fault Circuit Interrupter support
9. **Outage tracking**: `blackoutDuration`, `outageDate`, `outageFrequency`, `outageTotal`
10. **Sell/Export pricing**: `sellCompany`, `sellFixRate`, `sellPrice`, `sellRate`, `supportSell`, `supportOctopusSell`
11. **380+ disaster weather event types** for Storm Guard
12. **Enode vehicle API** integration for EV chargers
