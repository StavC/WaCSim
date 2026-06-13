# ============================================================================
# WaCSim Demo Files — README
# ============================================================================
#
# This folder contains ready-to-use example files for every configurable
# data input in WaCSim. Copy any file into your active experiment folder and
# reference it in your main config YAML.
#
# All CSV files here have been expanded to show realistic configurations:
# - They support multiple PLCs (PLC1, PLC2, PLC3, PLC4) and the SCADA node.
# - They include 3 rows of data to show how sequential batch simulations work.
#
# IMPORTANT: Column headers in CSV files must match the names defined in
# your PLC config (for PLC/scada columns) or your INP file (for tank and
# demand pattern columns). Adjust headers to match your specific network.
#
# ============================================================================
# Files List & Usage
# ============================================================================
#
# COMPLETE EXAMPLE CONFIG
#   demo_config.yaml            Full config referencing all demo files below.
#                               Shows all syntax, settings, and defaults.
#                               Use with: sudo wacsim demo_config.yaml
#
# SENSOR NOISE
#   demo_sensor_noise.yaml      Advanced multi-type, per-sensor noise config.
#                               Supports: gaussian, gaussian_absolute,
#                               uniform, percentage, drift
#                               Use with: sensor_noise: !include <file>.yaml
#
#   demo_noise_scale_data.csv   Legacy per-PLC Gaussian noise (single-run).
#                               Use with: noise_scale_data: <file>.csv
#
#   demo_noise_scale_batch.csv  Legacy noise scales for a 3-simulation batch run.
#                               Use with: noise_scale_data: <file>.csv
#                                         batch_simulations: 3
#
# NETWORK CONDITIONS
#   demo_network_loss_data.csv  Per-PLC packet loss probability (0.0 to 100.0%).
#                               Shows 3 batch rows (Zero, Nominal, Severe loss).
#                               Use with: network_loss_data: <file>.csv
#
#   demo_network_delay_data.csv Per-PLC constant link delay/latency (ms).
#                               Shows 3 batch rows (Low, Nominal, High delay).
#                               Use with: network_delay_data: <file>.csv
#
#   demo_network_jitter_data.csv Per-PLC random delay jitter standard deviation (ms).
#                               Shows 3 batch rows (Zero, Nominal, High jitter).
#                               Use with: network_jitter_data: <file>.csv
#
# TRIGGERED NETWORK EVENTS
#   demo_events.yaml            YAML file showing all 8 triggered network events:
#                               packet_loss, network_delay, network_delay_loss,
#                               link_down, rate_limit, bursty_loss, ip_conflict,
#                               packet_reorder
#                               Use with: events: !include <file>.yaml
#
# CYBER ATTACKS
#   demo_attacks.yaml           YAML file showing network attacks: simple_dos,
#                               mitm, noise_injection, rogue_scada.
#                               Shows static and CSV-based overrides.
#                               Use with: attacks: !include <file>.yaml
#
#   demo_rogue_command_data.csv CSV file with time-varying command override values.
#                               Used by demo_attacks.yaml for sequential overrides.
#
# HYDRAULIC DATA
#   demo_initial_tank_data.csv  Override starting water levels (meters) for
#                               tanks T1, T2, T3 across 3 batch simulations
#                               (Low, Nominal, High starting points).
#                               Use with: initial_tank_data: <file>.csv
#
#   demo_demand_patterns.csv    Diurnal multipliers (24 hourly steps) for
#                               4 custom demand patterns (pattern1 to pattern4).
#                               Use with: demand_patterns: <file>.csv
#
# ============================================================================
