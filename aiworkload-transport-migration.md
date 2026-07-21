# AI-Workload Transport Settings Migration

Network-stack (layers 1–4) settings were moved out from under `Config.ai_workload`
and merged onto the native OTG config surface (`ports`, `layer1`, `devices`,
`captures`, `options.per_port_options`). Cross-references from `ai_workload` into
the network model now use OTG name strings (`x-constraint` pattern).

Rules observed:

- Breaking changes were made **only inside** `Config.ai_workload`. All changes to
  native OTG schemas are additive; Keysight extension fields on existing OTG
  schemas use `x-field-uid` 101+ (precedent: `Config.ai_workload` = 101).
- Retired `x-field-uid`s inside aiworkload are reserved with comments and never
  reused.

## 1. Moved fields — old location → new location

Old paths are relative to `Config.ai_workload.bindings.custom_binding` unless
noted. New paths are relative to `Config`.

### Physical bindings / locations

| Old | New |
|---|---|
| `physical_bindings[].config.keysight_hw.chassis_location` (`ChassisInfo.address`/`.port`) | `ports[].location` — chassis convention below |
| `physical_bindings[].config.{keysight_sw,keysight_nccl_test}.server_location` (`ServerInfo.address`/`.nic_interface`) | `ports[].location` — server convention below |
| `physical_bindings[].config.*.layer1` | `layer1[]` entry whose `port_names` includes the binding's port |
| `physical_bindings[].config.*.capture` (PRIVATE) | `captures[]` entry whose `port_names` includes the binding's port |
| — (new) | `physical_bindings[].port_name` references `Port.name` (`x-field-uid` 4) |

**`Port.location` encoding convention** (documented, not schema-enforced —
`Port.location` is deliberately implementation-specific):

- Keysight chassis (was `ChassisInfo`): `"<chassis-address>;<front-panel-port>[.<fanout>]"`,
  e.g. `"10.1.1.1;1.4"`.
- Server/agent (was `ServerInfo`): `"<server-address>;<nic-interface>"`,
  e.g. `"svr-01.example.com;eth0"`.

The platform interpreting the location is selected by
`PhysicalBinding.platform_name` (or region assignment), so the two formats
cannot be confused.

### Layer 1

`Layer1.speed_mode` combined three orthogonal facts (speed, lane signaling, FEC).
It decomposes onto OTG `Layer1.speed` plus two new vendor-neutral fields
`Layer1.signaling` (uid 101) and `Layer1.fec_mode` (uid 102):

| Old `speed_mode` | `speed` | `signaling` | `fec_mode` |
|---|---|---|---|
| speed_800ge_pam4_106g_kp4_fec | speed_800_gbps | pam4_106_gbps | rs_fec_kp4 |
| speed_400ge_pam4_106g_kp4_fec (default) | speed_400_gbps | pam4_106_gbps | rs_fec_kp4 |
| speed_400ge_pam4_53g_kp4_fec | speed_400_gbps | pam4_53_gbps | rs_fec_kp4 |
| speed_200ge_pam4_106g_kp4_fec | speed_200_gbps | pam4_106_gbps | rs_fec_kp4 |
| speed_200ge_pam4_53g_kp4_fec | speed_200_gbps | pam4_53_gbps | rs_fec_kp4 |
| speed_100ge_pam4_106g_kp4_fec | speed_100_gbps | pam4_106_gbps | rs_fec_kp4 |
| speed_100ge_pam4_106g_rs_fec | speed_100_gbps | pam4_106_gbps | rs_fec |
| speed_100ge_pam4_53g_kp4_fec | speed_100_gbps | pam4_53_gbps | rs_fec_kp4 |
| speed_100ge_nrz_rs_fec | speed_100_gbps | nrz | rs_fec |
| speed_100ge_nrz_no_fec | speed_100_gbps | nrz | no_fec |

| Old | New |
|---|---|
| `...layer1.speed_mode` | `layer1[].speed` + `layer1[].signaling` + `layer1[].fec_mode` |
| `...layer1.auto_negotiate` | `layer1[].auto_negotiate` |
| `...layer1.link_training` | `layer1[].auto_negotiation.link_training` |
| `...layer1.ieee_defaults` | `layer1[].ieee_media_defaults` |

### NIC settings → Device.Ethernet

`NicBinding.nic_settings` was removed; `NicBinding.ethernet_name` (uid 4) now
references a `Device.Ethernet` by name.

| Old (`nic_bindings[].nic_settings.`) | New | Notes |
|---|---|---|
| `ethernet_mtu` (default 8192, 68–14000) | `devices[].ethernets[].mtu` | OTG default 1500, max 65535 |
| `mac_address` (`00:00:00:00:00:00` = auto) | `devices[].ethernets[].mac` | OTG requires an explicit MAC (except simulated_link); no auto sentinel |
| `vlan.enabled` | presence of entries in `devices[].ethernets[].vlans` | no boolean; empty list = disabled |
| `vlan.vlan_tags[].priority` | `devices[].ethernets[].vlans[].priority` | |
| `vlan.vlan_tags[].vlan_id` | `devices[].ethernets[].vlans[].id` | OTG range 0–4095 (was 1–4094); gains `tpid`, `name` |
| `ip_addressing.ip_version` + `ipv4`/`ipv6` | `devices[].ethernets[].ipv4_addresses[]` / `ipv6_addresses[]` | lists, not a choice |
| `ip_addressing.ipv4.ip_address` (default 192.0.2.2) | `Device.Ipv4.address` | required, no default |
| `ip_addressing.ipv4.ip_prefix` (default 24) | `Device.Ipv4.prefix` | default 24 |
| `ip_addressing.ipv4.ip_gateway_address` (default 192.0.2.1) | `Device.Ipv4.gateway` | required, no default; gains `gateway_mac` |
| `ip_addressing.ipv6.*` (defaults 2001:db8::2 / 32 / 2001:db8::1) | `Device.Ipv6.address` / `.prefix` (default 64) / `.gateway` | address/gateway required |
| `qos` (PRIVATE) | `devices[].ethernets[].qos` (uid 101) → `Qos.Settings` (new `device/qos.yaml`) | see below |
| `packet_capture` (PRIVATE) | `captures[]` | see below |
| `transport.rocev2.*` and `congestion_control.*` | see §2 | |

### PRIVATE QoS (`Qos` → `Qos.Settings`)

`additionalProperties` maps were replaced with entry lists (OTG core never uses
maps; entry lists generate cleanly through openapiart/protobuf).

| Old | New |
|---|---|
| `qos.priority_trust_mode` | `Qos.Settings.priority_trust_mode` |
| `qos.map_dscp_to_prio` (IntegerMap) | `Qos.Settings.dscp_to_priority[]` (`{dscp, priority}` entries) |
| `qos.map_prio_to_traffic_class` (IntegerMap) | `Qos.Settings.priority_to_traffic_class[]` (`{priority, traffic_class}` entries) |

### PRIVATE packet capture (`PacketCapture` → `Capture`)

Capture is port-scoped in OTG; NICs resolve to ports via their
`Device.Ethernet` connection.

| Old | New | Notes |
|---|---|---|
| `enabled` | presence of a `Capture` object listing the port in `port_names` | |
| `capture_max_file_size` (default 10 MiB) | `Capture.max_file_size` (new, uid 101, PRIVATE) | 0/null = no explicit limit |
| `buffer_full_action` (override/stop, default override) | `Capture.overwrite` (true/false, default true) | |
| `packet_slice_size` (0 = whole packet, default 80) | `Capture.packet_size` (null = whole packet) | 0-sentinel becomes null |

## 2. RoCEv2 / congestion control — field-by-field mapping

OTG places data-packet DSCP/ECN **per QP** (`devices[].rocev2` →
`Rocev2.QPParameters`) and CNP/ACK/NAK/DCQCN **per port**
(`options.per_port_options[].protocols[].rocev2` → `Rocev2.PerPortSettings`).
aiworkload placed everything per NIC — see §3 for the granularity note.

| Old (`nic_settings.`) (default) | New (default) | Notes |
|---|---|---|
| `transport.rocev2.data_dscp` (26) | `Rocev2.QPParameters.dscp` (24) | per-QP; default differs |
| `transport.rocev2.ack_dscp` (26) | `Rocev2.ACK.ip_dscp.value` (48) | per-port; default differs |
| `transport.rocev2.nack_dscp` (26) | `Rocev2.NAK.ip_dscp.value` (48) | per-port; default differs |
| `congestion_control.ecn.cnp_dscp` (48) | `Rocev2.CNP.ip_dscp.value` (48) | |
| `congestion_control.ecn.data_ecn_bits` (ect1) | `Rocev2.QPParameters.ecn` (ect_1) | enum rename: disabled→non_ect, ect1→ect_1, ect0→ect_0; OTG adds `ce` |
| `congestion_control.ecn.control_ecn_bits` (ect1) | `Rocev2.ACK.ecn_value` **and** `Rocev2.NAK.ecn_value` | one field splits into two |
| `congestion_control.ecn.cnp_ecn_bits` (ect1) | `Rocev2.CNP.ecn_value` (ect_1) | |
| `congestion_control.pfc.enabled` (true) | presence of `layer1[].flow_control` with choice `ieee_802_1qbb` | |
| `congestion_control.pfc.priorities` ([3]) | `Layer1.Ieee8021qbb.pfc_class_<p>` | priority p enabled → `pfc_class_p: p`; classes not in the list must be explicitly nulled — OTG defaults populate all classes 0–7 |
| `congestion_control.dcqcn_rate_control.enabled` (**false**) | `Rocev2.DCQCN.enable_dcqcn` (**true**) | default inverted — converters must always set explicitly |
| `...dcqcn.alpha_factor` (1019) | `Rocev2.DCQCN.alpha_g` (1019) | |
| `...dcqcn.alpha_interval` µs (21) | `Rocev2.DCQCN.alpha_update_period` µs (21) | |
| `...dcqcn.initial_alpha` (1023) | `Rocev2.DCQCN.initial_alpha` (1023) | |
| `...dcqcn.rate_after_first_cnp` **Mbps** (10000) | `Rocev2.DCQCN.initial_rate_after_first_cnp` **% of line rate** (0.002) | unit conversion: % = Mbps / line-rate-Mbps × 100 |
| `...dcqcn.rate_decrement_factor` % (50) | `Rocev2.DCQCN.maximum_rate_decrement_at_time` % (10) | both percent; default differs |
| `...dcqcn.min_rate_limit` **Mbps** (1) | `Rocev2.DCQCN.minimum_rate_limmit` **%** (0.002) | unit conversion; pre-existing OTG spelling (`limmit`) kept — additive-only rule |
| `...dcqcn.rate_decrement_coefficient` (11) | `Rocev2.DCQCN.rate_decrement_coefficient` (11) | new additive OTG field, uid 101 — the only DCQCN field with no OTG twin |
| `...dcqcn.rate_decrement_interval` µs (21) | `Rocev2.DCQCN.rate_reduction_time_period` µs (21) | |
| `...dcqcn.clamp_target_rate` (false) | `Rocev2.DCQCN.clamp_target_rate` (false) | |
| `...dcqcn.rate_increment_interval` µs (300) | `Rocev2.DCQCN.rate_increment_time` µs (250) | default differs |
| `...dcqcn.rate_increment_byte_counter` **64B units** (32767) | `Rocev2.DCQCN.rate_increment_byte_counter` **bytes** (32767) | unit ambiguity (64B units vs bytes) — implementations must confirm |
| `...dcqcn.rate_increment_threshold` (1) | `Rocev2.DCQCN.rate_increment_threshold` (25) | default differs |
| `...dcqcn.additive_rate_increment` **Mbps** (5) | `Rocev2.DCQCN.additive_increment_rate` **%** (0.001) | unit conversion |
| `...dcqcn.hyper_rate_increment` **Mbps** (50) | `Rocev2.DCQCN.hyper_increment_rate` **%** (0.001) | unit conversion |
| `...dcqcn.time_between_cnps` µs (4) | `Rocev2.CNP.cnp_delay_timer` µs (55) | default differs |

Not migrated (dead schema removed): `TcpStoreConfig` — orphan left over from the
earlier RoCEv2 QP-negotiation removal; nothing referenced it.

## 3. Semantics changes

- **Per-NIC → per-port**: DCQCN, CNP, and ACK/NAK settings are now configured
  per test port (`Config.options.per_port_options`). Where an emulated NIC is
  backed by multiple ports (`Ethernet.Connection.port_names`), apply the
  settings to each backing port.
- **Per-NIC → per-QP**: data-packet DSCP/ECN are now per-QP parameters under
  `Device.Rocev2Peer`; for dynamically created QPs they act as templates.
- **PFC granularity**: aiworkload's enabled+priority-list becomes OTG's
  per-class mapping (`pfc_class_0..7`) under `Layer1.FlowControl`, shared by
  all ports listed in the `Layer1.port_names`.

## 4. Design decisions

1. **Breaking-change boundary.** Free restructuring only inside
   `Config.ai_workload`; all other schema changes additive (uid 101+). This
   keeps the fork mergeable with upstream OTG.
2. **Physical locations → `Port.location`.** Options: (a) keep structured
   `ChassisInfo`/`ServerInfo` under aiworkload; (b) add a structured location
   object to `Port`; (c) use the existing free-form `Port.location` string.
   **Chosen: (c)** — matches how every OTG implementation binds ports;
   encoding convention documented in §1.
3. **Vendor-neutral modeling.** New elements (`signaling`, `fec_mode`,
   `port_names` connection, `Qos.*`, `max_file_size`,
   `rate_decrement_coefficient`) are modeled upstream-candidate style (dotted
   naming, `Named.Object`, `x-constraint`) rather than as Keysight-scoped
   extensions.
4. **Name references.** New cross-references use OTG name strings
   (`NicBinding.ethernet_name`, `PhysicalBinding.port_name`,
   `Ethernet.Connection.port_names`). The internal `InfraRef` addressing for
   ranks/NPUs is retained for now (§5); may be reconsidered.
5. **Emulated-fabric speeds stay.** `RackPlaneFabric.scale_up/scale_out_switch_speed`
   and `GenericHost.npu_interconnect_bandwidth_gbps` parameterize the emulated
   Chakra fabric, not test-port L1 — they remain under aiworkload.
6. **PRIVATE Qos/PacketCapture.** Options: drop; relocate within aiworkload;
   move to vendor-neutral OTG schemas. **Chosen: vendor-neutral OTG schemas
   with descriptions retaining the `PRIVATE:` designation** (`device/qos.yaml`;
   `Capture.max_file_size`).
7. **RoCEv2 merge.** Options: keep aiworkload's per-NIC `CongestionControl` as
   a parallel device-level schema; or adopt OTG's existing schemas. **Chosen:
   adopt OTG schemas** (renames + unit conversions per §2), adding only
   `rate_decrement_coefficient` where OTG had no equivalent.
8. **NIC↔port many-to-many.** aiworkload's `associated_physical_bindings`
   allowed one NIC's flows to be generated by several test ports, which
   `Ethernet.Connection.port_name` (1:1) cannot express. Options: (a) a list of
   Connection objects on `Device.Ethernet` — rejected, breaks the existing
   single-connection shape; (b) keep the association list in aiworkload —
   rejected, keeps stack knowledge in the extension; (c) additive `port_names`
   choice member on `Ethernet.Connection` — **chosen**, purely additive and
   vendor-neutral (a multi-homed emulated interface is not Keysight-specific).
   openapiart 0.3.42 accepted the array-typed choice member (no fallback
   needed).
9. **Layer-1 speed decomposition.** A combined `speed_mode`-style enum was
   rejected (combinatorial explosion, not upstreamable); two orthogonal enums
   (`signaling`, `fec_mode`) compose with the existing `speed` enum.

## 5. Remaining internal-address (`InfraRef`) sites in aiworkload

`InfraRef` (device_instance_name + device_index + component_name +
component_index) still addresses the emulated Chakra infrastructure at:

- `RankBinding.infra_ref` — the NPU used by a rank
- `RankBinding.nic_refs[]` — NICs available to that NPU
- `NicBinding.infra_ref` — the Chakra NIC an `ethernet_name` models
- `PhysicalBinding.infra_ref` — the logical element a test resource represents
- `CollectiveMatchConditions.src_nic` / `.dst_nic` — impairment flow matching
- `InfraRegion.boundary_refs[]` — platform region boundaries

Plus the opaque JSON-encoded escape hatch:
`TrialBindings.infrastructure` / `TrialBindings.infrastructure_annotations`
(keysight_chakra Infrastructure/Annotation blobs).

These may be revisited in a later change (e.g. replacing InfraRef with OTG-style
name references once the emulated infrastructure elements are named objects).
